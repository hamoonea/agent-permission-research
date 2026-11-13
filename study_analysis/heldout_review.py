"""Supplemental descriptive audit of a complete frozen held-out model run.

This reporting module is outside the frozen experiment. It does not change
primary scores, inference, tasks, or the prespecified family-cluster estimator.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from followup.analyze import paired, summarize
from followup.core import CONDITIONS
from followup.evidence import digest, load_tasks, replay
from study_analysis.development_audit import diagnose
from study_analysis.repeated_development_review import failure_counts, stability


def pair_details(rows, audited):
    index = {(r['task_id'], r['condition'], r['repeat']): r for r in rows}
    audit_index = {(r['task_id'], r['condition'], r['repeat']): r for r in audited}
    discordant, oracle_mismatches, action_changes = [], [], []
    for row in rows:
        if row['condition'] != 'permissions':
            continue
        key = row['task_id'], row['repeat']
        recovery = index[(key[0], 'recovery', key[1])]
        approval = index[(key[0], 'approval', key[1])]
        if row['messages'] != approval['messages'] or row['final_state'] != approval['final_state']:
            oracle_mismatches.append({'task_id': key[0], 'repeat': key[1]})
        if [e['action'] for e in row['events']] != [e['action'] for e in recovery['events']]:
            action_changes.append({'task_id': key[0], 'repeat': key[1]})
        if row['metrics']['authorized_success'] != recovery['metrics']['authorized_success']:
            discordant.append({
                'task_id': key[0], 'repeat': key[1],
                'permissions': row['metrics']['authorized_success'],
                'recovery': recovery['metrics']['authorized_success'],
                'permissions_reasons': audit_index[(key[0], 'permissions', key[1])]['reasons'],
                'recovery_reasons': audit_index[(key[0], 'recovery', key[1])]['reasons'],
                'permissions_blocks': row['metrics']['blocks'],
                'recovery_blocks': recovery['metrics']['blocks'],
            })
    return {'recovery_discordant_pairs': discordant,
            'permission_approval_mismatches': oracle_mismatches,
            'recovery_action_sequence_changes': action_changes}


def build_review(config, rows, tasks, audited):
    repeats = {str(rep): {c: summarize([r for r in rows if r['repeat']==rep and r['condition']==c])
                         for c in CONDITIONS} for rep in range(config['repeats'])}
    families = {}
    for family in sorted({r['family'] for r in rows}):
        selected = [r for r in rows if r['family']==family]
        arms = {c: summarize([r for r in selected if r['condition']==c]) for c in CONDITIONS}
        families[family] = {'conditions': arms,
                            'recovery_minus_permissions': (
                                arms['recovery']['authorized_success']/arms['recovery']['n']-
                                arms['permissions']['authorized_success']/arms['permissions']['n'])}
    categories = sorted({reason for a in audited for reason in a['reasons']})
    overlapping = {reason: {c: sum(reason in a['reasons'] for a in audited if a['condition']==c)
                            for c in CONDITIONS} for reason in categories}
    attack_counts = {variant: {c: {
        'n': sum(a['variant']==variant and a['condition']==c for a in audited),
        'exact_probe_attempted': sum(a['exact_probe_attempted'] for a in audited
                                     if a['variant']==variant and a['condition']==c),
        'exact_probe_executed': sum(a['exact_probe_executed'] for a in audited
                                    if a['variant']==variant and a['condition']==c),
    } for c in CONDITIONS} for variant in ('clean', 'injected', 'revoked')}
    quarters = [rows[len(rows)*i//4:len(rows)*(i+1)//4] for i in range(4)]
    return {
        'scope': 'Supplemental descriptive held-out analysis; frozen primary scores and estimator unchanged.',
        'repeat_summary': repeats,
        'repeat_recovery_minus_permissions': {
            rep: arms['recovery']['authorized_success']/arms['recovery']['n']-
                 arms['permissions']['authorized_success']/arms['permissions']['n']
            for rep, arms in repeats.items()},
        'case_stability': stability(rows),
        'family_results': families,
        'family_cluster_recovery_comparison': paired(rows, 'recovery', 'permissions'),
        'failure_accounting': failure_counts(rows),
        'overlapping_failure_counts': overlapping,
        'attack_probe_counts_by_variant': attack_counts,
        'finish_reason_counts': dict(Counter(call['finish_reason'] for row in rows for call in row['calls'])),
        'max_calls_per_trial': max(len(r['calls']) for r in rows),
        'execution_quarter_median_seconds': [statistics.median(r['elapsed_seconds'] for r in q) for q in quarters],
        **pair_details(rows, audited),
    }


def review(run, freeze_path):
    run, freeze_path = Path(run), Path(freeze_path)
    config, rows = replay(run)
    frozen = json.loads(freeze_path.read_text())
    if config['split']!='heldout' or config['backend']!='mlx':
        raise ValueError('A complete genuine held-out model run is required')
    if config['freeze_sha256']!=digest(freeze_path) or config['inputs']!=frozen['inputs']:
        raise ValueError('Run does not match the frozen design')
    if config['model_files']!=frozen['models'][config['model_label']] or config['runtime']!=frozen['runtime']:
        raise ValueError('Model/runtime does not match freeze')
    if any(config[k]!=v for k,v in frozen['run_parameters'].items()):
        raise ValueError('Run parameters do not match freeze')
    tasks = {t['id']:t for t in load_tasks('heldout')}
    if set(config['task_ids'])!=set(tasks):
        raise ValueError('Full held-out assignment is required')
    primary = json.loads((run/'summary.json').read_text())
    for condition in CONDITIONS:
        if primary['conditions'][condition]!=summarize([r for r in rows if r['condition']==condition]):
            raise ValueError('Primary condition summary mismatch')
    for variant in ('clean', 'injected', 'revoked'):
        for condition in CONDITIONS:
            selected = [r for r in rows if r['variant']==variant and r['condition']==condition]
            if primary['variants'][variant][condition]!=summarize(selected):
                raise ValueError('Primary variant summary mismatch')
    expected_comparisons = {
        'recovery_minus_permissions': paired(rows,'recovery','permissions'),
        'permissions_minus_baseline': paired(rows,'permissions','baseline'),
        'recovery_minus_permissions_revoked': paired([r for r in rows if r['variant']=='revoked'],'recovery','permissions'),
    }
    if primary['paired_authorized_success']!=expected_comparisons:
        raise ValueError('Primary paired comparison mismatch')
    audited = [diagnose(tasks[r['task_id']],r) for r in rows]
    result = build_review(config, rows, tasks, audited)
    root = Path(__file__).resolve().parents[1]
    result['provenance'] = {
        'freeze_sha256': digest(freeze_path),
        'config_sha256': digest(run/'config.json'),
        'trajectories_sha256': digest(run/'trajectories.jsonl'),
        'summary_sha256': digest(run/'summary.json'),
        'supplemental_analysis_sources': {name:digest(root/name) for name in (
            'study_analysis/heldout_review.py','study_analysis/development_audit.py',
            'study_analysis/repeated_development_review.py')},
    }
    result['sessions'] = [json.loads(line) for line in (run/'sessions.jsonl').read_text().splitlines()]
    result['sessions_count'] = len(result['sessions'])
    result['diagnostics'] = audited
    summary_lines = ['# Held-out repeat and failure review', '', result['scope'], '',
                     '## Authorized success by repeat', '',
                     '| Repeat | Baseline | Permissions | Recovery | Approval | Recovery − permissions |',
                     '|---|---:|---:|---:|---:|---:|']
    for repeat, arms in result['repeat_summary'].items():
        values = [f'{arms[c]["authorized_success"]}/{arms[c]["n"]}' for c in CONDITIONS]
        summary_lines.append('| '+str(int(repeat)+1)+' | '+' | '.join(values)+
                             f' | {100*result["repeat_recovery_minus_permissions"][repeat]:+.1f} pp |')
    summary_lines += ['', 'Repeat labels 1–3 correspond to stored indices 0–2.', '',
                      '## Success by workflow family', '',
                      '| Family | Baseline | Permissions | Recovery | Approval | Recovery − permissions |',
                      '|---|---:|---:|---:|---:|---:|']
    for family, data in result['family_results'].items():
        values = [f'{data["conditions"][c]["authorized_success"]}/{data["conditions"][c]["n"]}' for c in CONDITIONS]
        summary_lines.append('| '+family+' | '+' | '.join(values)+f' | {100*data["recovery_minus_permissions"]:+.1f} pp |')
    summary_lines += ['', '## Stability over repeats', '',
                      '| Condition | Always succeeds | Always fails | Mixed outcome cases |',
                      '|---|---:|---:|---:|']
    for c, counts in result['case_stability'].items():
        summary_lines.append(f'| {c} | {counts["always_successful_cases"]} | {counts["always_unsuccessful_cases"]} | {counts["mixed_outcome_cases"]} |')
    summary_lines += ['', 'These count cases, not independent workflow families.', '',
                      '## Observable failure blockers (overlapping)', '',
                      '| Blocker | Baseline | Permissions | Recovery | Approval |', '|---|---:|---:|---:|---:|']
    for reason, counts in result['overlapping_failure_counts'].items():
        summary_lines.append('| '+reason+' | '+' | '.join(str(counts[c]) for c in CONDITIONS)+' |')
    summary_lines += ['', 'All failures remain in the assigned denominator. Blockers are observable conditions, '
                      'not proven internal causes. Omitted reference reads are descriptive and do not change '
                      'the frozen source/backup access requirement.', '',
                      '## Matched-pair checks', '',
                      f'- Permissions/approval transcript or state mismatches: {len(result["permission_approval_mismatches"])}.',
                      f'- Recovery/permissions action-sequence differences: {len(result["recovery_action_sequence_changes"])}.',
                      f'- Recovery/permissions discordant success pairs: {len(result["recovery_discordant_pairs"])}.', '',
                      'Approval is a perfect matched oracle, not independent evidence or a human study.', '',
                      '## Discordant outcome details', '', '```json',
                      json.dumps(result['recovery_discordant_pairs'],indent=2), '```', '',
                      '## Failure and timing accounting', '', '```json',
                      json.dumps(result['failure_accounting'],indent=2), '```', '',
                      'Median seconds by execution quarter: '+', '.join(f'{v:.2f}' for v in result['execution_quarter_median_seconds'])+'.',
                      'Latency is descriptive and may reflect machine load, sleep or other session conditions.', '',
                      'Exact injected-probe execution is reported separately from revoked-source access. '
                      'Not every scope violation is a prompt-injection success. The gate and violation counter '
                      'share a matcher, so zero covered violations does not demonstrate general safety.']
    traces = ['# Complete held-out failure traces', '',
              'Every unsuccessful assigned trajectory is included below. Metrics are unchanged; '
              'successful raw records remain in trajectories.jsonl. Diagnostic categories overlap.', '']
    for diagnosis, row in zip(audited, rows):
        if diagnosis['success']:
            continue
        traces += [f'## {row["task_id"]} / {row["condition"]} / repeat {row["repeat"]}', '',
                   'Blockers: '+', '.join(diagnosis['reasons'])+'.', '', '```json',
                   json.dumps({'details':diagnosis['details'],
                               'omitted_reference_reads':diagnosis['omitted_reference_reads'],
                               'error':row['error'],'budget_exhausted':row['budget_exhausted'],
                               'events':row['events']},indent=2), '```', '']
    artifacts = {
        'heldout-review.json': json.dumps(result,indent=2)+'\n',
        'heldout-review.md': '\n'.join(summary_lines)+'\n',
        'failure-traces.md': '\n'.join(traces)+'\n',
    }
    if any((run/name).exists() for name in artifacts):
        raise ValueError('Supplemental review already exists; preserve the original artifacts')
    for name, content in artifacts.items():
        with (run/name).open('x') as stream:
            stream.write(content)
    if digest(run/'trajectories.jsonl')!=result['provenance']['trajectories_sha256']:
        raise ValueError('Original trajectories changed during reporting')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--freeze',type=Path,required=True)
    args=parser.parse_args()
    result=review(args.run,args.freeze)
    print(json.dumps({k:result[k] for k in (
        'failure_accounting','repeat_recovery_minus_permissions','family_cluster_recovery_comparison',
        'permission_approval_mismatches','recovery_discordant_pairs')},indent=2))
