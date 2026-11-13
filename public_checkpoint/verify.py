"""Replay public development evidence without claiming to verify withheld inputs.

Does not import the private generator, run a model, or change any study artifact.
The two withheld hashes are commitments only, not independently verified files.
"""
import argparse
import hashlib
import json
from pathlib import Path

from followup.core import CONDITIONS, Environment, initial_messages
from followup.run import trajectory_seed

ROOT = Path(__file__).resolve().parents[1]
WITHHELD = {'followup/tasks.py', 'data/followup/heldout.json'}
PUBLIC_INPUTS = {
    'followup/__init__.py', 'followup/analyze.py', 'followup/core.py',
    'followup/evidence.py', 'followup/freeze.py', 'followup/run.py',
    'data/followup/dev.json', 'docs/followup-protocol.md',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs(config, run, root=ROOT):
    require(config['split'] == 'dev', 'Only development evidence is accepted')
    require(set(config['inputs']) == PUBLIC_INPUTS | WITHHELD, 'Unexpected input set')
    for name in sorted(PUBLIC_INPUTS):
        require(digest(root/name) == config['inputs'][name], 'Public input changed: '+name)
        require(digest(run/'source-snapshot'/name) == config['inputs'][name],
                'Public snapshot changed: '+name)
    withheld = json.loads((root/'public_checkpoint/manifest.json').read_text())['withheld_original_inputs']
    require(withheld == {name: config['inputs'][name] for name in WITHHELD},
            'Withheld hash commitment mismatch')
    # Do not open a reserved file, even if someone later places one in the checkout.
    require(not (root/'data/followup/heldout.json').exists(), 'Reserved data unexpectedly present')
    for name in WITHHELD:
        require(not (run/'source-snapshot'/name).exists(), 'Reserved snapshot unexpectedly present')


def verify_rows(config, rows, tasks):
    require(config['split'] == 'dev', 'Only development evidence is accepted')
    require(all(t['split'] == 'dev' for t in tasks.values()), 'Non-development task')
    require(set(config['task_ids']) <= set(tasks), 'Unknown task assignment')
    require(len(set(config['task_ids'])) == len(config['task_ids']), 'Duplicate task assignment')
    expected = {(t, c, r) for t in config['task_ids'] for c in CONDITIONS for r in range(config['repeats'])}
    observed = set()
    for row in rows:
        key = row['task_id'], row['condition'], row['repeat']
        require(key in expected and key not in observed, 'Duplicate or unplanned trajectory')
        observed.add(key)
        task = tasks[row['task_id']]
        require(row['rng_seed'] == trajectory_seed(config['seed'], row['task_id'], row['repeat']),
                'Sampling seed mismatch')
        require(row['family'] == task['family'] and row['variant'] == task['variant']
                and row['backend'] == config['backend'], 'Trajectory metadata mismatch')
        require(len(row['calls']) == len(row['events']), 'Call/event mismatch')
        env = Environment(task, row['condition'])
        messages = initial_messages(task)
        for call, event in zip(row['calls'], row['events']):
            try:
                action = json.loads(call['raw'])
            except (ValueError, TypeError):
                action = None
            require(action == event['action'], 'Raw response/action mismatch')
            result = env.step(action)
            require(env.events[-1] == event, 'Event replay mismatch')
            messages.extend([{'role': 'assistant', 'content': call['raw']},
                             {'role': 'user', 'content': 'Tool result: '+json.dumps(result, sort_keys=True)}])
        require(messages == row['messages'], 'Prompt transcript mismatch')
        require(env.state == row['final_state'] and env.score() == row['metrics'],
                'State/score replay mismatch')
        for token in ('prompt_tokens', 'generation_tokens'):
            require(sum(c[token] for c in row['calls']) == row[token], 'Token total mismatch')
        require(len(row['calls']) <= config['max_steps'], 'Exceeded step limit')
        exhausted = not env.closed and row['error'] is None
        require(row['budget_exhausted'] == exhausted, 'Exhaustion mismatch')
        require(not exhausted or len(row['calls']) == config['max_steps'], 'Premature truncation')
    require(observed == expected, 'Incomplete run')


def verify(run):
    run = Path(run)
    config = json.loads((run/'config.json').read_text())
    require(config['backend'] == 'mlx', 'Expected recorded model evidence')
    verify_inputs(config, run)
    task_list = json.loads((ROOT/'data/followup/dev.json').read_text())
    tasks = {t['id']: t for t in task_list}
    require(len(tasks) == len(task_list), 'Duplicate task ID')
    require(set(config['task_ids']) == set(tasks), 'Full development assignment required')
    rows = [json.loads(line) for line in (run/'trajectories.jsonl').read_text().splitlines()]
    verify_rows(config, rows, tasks)
    audit = json.loads((run/'failure-audit.json').read_text())
    for key, path in [('config_sha256', run/'config.json'),
                      ('trajectories_sha256', run/'trajectories.jsonl'),
                      ('audit_source_sha256', ROOT/'study_analysis/development_audit.py')]:
        require(audit['provenance'][key] == digest(path), 'Diagnostic provenance mismatch: '+key)
    from study_analysis.development_audit import diagnose
    require(audit['rows'] == [diagnose(tasks[r['task_id']], r) for r in rows], 'Diagnostic replay mismatch')
    summary = json.loads((run/'summary.json').read_text())
    from followup.analyze import paired, summarize
    counts = {}
    for condition in CONDITIONS:
        selected = [r for r in rows if r['condition'] == condition]
        success = sum(r['metrics']['authorized_success'] for r in selected)
        counts[condition] = {'authorized_success': success, 'n': len(selected)}
        require(summary['conditions'][condition] == summarize(selected), 'Condition summary mismatch')
    require(summary['backend'] == config['backend'] and summary['split'] == config['split'],
            'Summary metadata mismatch')
    variants = {v: {c: summarize([r for r in rows if r['variant'] == v and r['condition'] == c])
                    for c in CONDITIONS} for v in ('clean', 'injected', 'revoked')}
    require(summary['variants'] == variants, 'Variant summary mismatch')
    comparisons = {f'{t}_minus_{c}': paired(rows, t, c)
                   for t, c in [('recovery', 'permissions'), ('permissions', 'baseline')]}
    comparisons['recovery_minus_permissions_revoked'] = paired(
        [r for r in rows if r['variant'] == 'revoked'], 'recovery', 'permissions')
    require(summary['paired_authorized_success'] == comparisons, 'Paired comparison mismatch')
    review = json.loads((run/'repeat-review.json').read_text())
    for key, path in [('config_sha256', run/'config.json'),
                      ('trajectories_sha256', run/'trajectories.jsonl'),
                      ('analysis_sha256', ROOT/'study_analysis/repeated_development_review.py')]:
        require(review['provenance'][key] == digest(path), 'Repeat review provenance mismatch: '+key)
    from study_analysis.repeated_development_review import failure_counts, stability
    require(review['case_stability'] == stability(rows), 'Repeat stability mismatch')
    require(review['failure_accounting'] == failure_counts(rows), 'Failure accounting mismatch')
    repeat_summary = {str(rep): {c: summarize([r for r in rows if r['repeat'] == rep and r['condition'] == c])
                                for c in CONDITIONS} for rep in range(config['repeats'])}
    require(review['repeat_summary'] == repeat_summary, 'Per-repeat summary mismatch')
    return {
        'status': 'public development replay passed', 'trajectories': len(rows),
        'verified_public_source_inputs': len(PUBLIC_INPUTS),
        'withheld_inputs_not_independently_verified': sorted(WITHHELD),
        'authorized_success': counts,
        'scope': 'Software/event/score consistency only; no model rerun or held-out evaluation.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', nargs='?', type=Path, default=ROOT/'outputs/followup-dev-v2-repeats3')
    print(json.dumps(verify(parser.parse_args().run), indent=2))
