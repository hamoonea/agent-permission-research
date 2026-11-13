"""Read-only verification of the complete frozen-study publication.

Uses only Python's standard library. No model inference, model download, live
runtime enforcement, artifact rewriting, or new evaluation claim is performed.
"""
import argparse
import json
from pathlib import Path

from followup.analyze import paired, summarize
from followup.core import CONDITIONS
from followup.evidence import digest, load_tasks, replay, verify_rows as verify_saved_rows
from followup.transition import replay_development_transition
from study_analysis.development_audit import diagnose
from study_analysis.heldout_review import build_review

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_rows(config, rows, tasks):
    """Retain the development-only helper used by the earlier publication tests."""
    require(config['split']=='dev', 'Only development evidence is accepted by this helper')
    verify_saved_rows(config, rows, tasks)


def verify(run=ROOT/'outputs/followup-heldout-qwen3'):
    run = Path(run)
    publication = json.loads((ROOT/'public_checkpoint/manifest.json').read_text())
    freeze_path = ROOT/'outputs/followup-freeze.json'
    frozen = json.loads(freeze_path.read_text())
    require(digest(freeze_path)==publication['freeze_sha256'], 'Freeze commitment mismatch')
    config, rows = replay(run)
    require(config['split']=='heldout' and config['backend']=='mlx', 'Expected held-out model evidence')
    require(config['inputs']==frozen['inputs']==publication['published_frozen_inputs'], 'Frozen input set mismatch')
    for name, expected in frozen['inputs'].items():
        require(digest(run/'source-snapshot'/name)==expected, 'Snapshot input mismatch: '+name)
    require(config['freeze_sha256']==digest(freeze_path), 'Run/freeze commitment mismatch')
    require(config['model_files']==frozen['models'][config['model_label']], 'Recorded model identity mismatch')
    require(config['runtime']==frozen['runtime'], 'Recorded runtime identity mismatch')
    require(all(config[k]==v for k,v in frozen['run_parameters'].items()), 'Frozen parameter mismatch')
    require(config['conditions']==list(CONDITIONS), 'Condition assignment mismatch')
    tasks = {task['id']:task for task in load_tasks('heldout')}
    require(set(config['task_ids'])==set(tasks), 'Full held-out assignment required')
    require(len(rows)==publication['heldout_trials'], 'Publication trial count mismatch')
    require(digest(run/'trajectories.jsonl')==publication['heldout_trajectories_sha256'], 'Trajectory commitment mismatch')
    unsuccessful = sum(not r['metrics']['authorized_success'] for r in rows)
    require(unsuccessful==publication['heldout_unsuccessful_trials'], 'Failure count mismatch')

    manifest = json.loads((run/'analysis-manifest.json').read_text())
    require(manifest['freeze_sha256']==digest(freeze_path), 'Analysis/freeze commitment mismatch')
    require(digest(ROOT/manifest['report'])==manifest['report_sha256'], 'Original report changed')
    for name, expected in manifest['artifacts'].items():
        require(digest(ROOT/name)==expected, 'Recorded artifact mismatch: '+name)
    summary = json.loads((run/'summary.json').read_text())
    conditions = {c:summarize([r for r in rows if r['condition']==c]) for c in CONDITIONS}
    variants = {v:{c:summarize([r for r in rows if r['variant']==v and r['condition']==c])
                   for c in CONDITIONS} for v in ('clean','injected','revoked')}
    comparisons = {f'{a}_minus_{b}':paired(rows,a,b)
                   for a,b in [('recovery','permissions'),('permissions','baseline')]}
    comparisons['recovery_minus_permissions_revoked'] = paired(
        [r for r in rows if r['variant']=='revoked'],'recovery','permissions')
    require(summary==dict(backend=config['backend'],split=config['split'],conditions=conditions,
                         variants=variants,paired_authorized_success=comparisons), 'Primary summary mismatch')
    audit = json.loads((run/'heldout-review.json').read_text())
    for key, path in [('freeze_sha256',freeze_path),('config_sha256',run/'config.json'),
                      ('trajectories_sha256',run/'trajectories.jsonl'),('summary_sha256',run/'summary.json')]:
        require(audit['provenance'][key]==digest(path), 'Supplemental provenance mismatch: '+key)
    for name, expected in audit['provenance']['supplemental_analysis_sources'].items():
        require(digest(ROOT/name)==expected, 'Supplemental analysis source changed: '+name)
    diagnosed = [diagnose(tasks[r['task_id']],r) for r in rows]
    require(diagnosed==audit['diagnostics'], 'Failure diagnosis mismatch')
    recomputed = build_review(config,rows,tasks,diagnosed)
    for key, value in recomputed.items():
        require(audit[key]==value, 'Supplemental summary mismatch: '+key)
    sessions = [json.loads(line) for line in (run/'sessions.jsonl').read_text().splitlines()]
    require(audit['sessions']==sessions and audit['sessions_count']==len(sessions), 'Session summary mismatch')
    expected_sections = [f'## {r["task_id"]} / {r["condition"]} / repeat {r["repeat"]}'
                         for r in rows if not r['metrics']['authorized_success']]
    actual_sections = [line for line in (run/'failure-traces.md').read_text().splitlines() if line.startswith('## ')]
    require(actual_sections==expected_sections, 'Failure trace missing, duplicated or reordered')

    _, development_rows, receipt = replay_development_transition(
        ROOT/'outputs/followup-dev-v2-repeats3', ROOT/'outputs/followup-verification-transition.json')
    require(receipt==frozen['development_transition'], 'Frozen development-transition receipt mismatch')
    boundary = json.loads((ROOT/'outputs/followup-verification-fix-boundary.json').read_text())
    for name, expected in boundary['preserved_evidence'].items():
        require(digest(ROOT/name)==expected, 'Earlier evidence changed: '+name)
    return {
        'status':'complete frozen-study publication verified',
        'heldout_trajectories':len(rows), 'heldout_unsuccessful_trajectories':unsuccessful,
        'failure_trace_sections':len(actual_sections), 'frozen_inputs_and_snapshots_verified':len(frozen['inputs']),
        'development_trajectories_replayed':len(development_rows),
        'earlier_evidence_files_preserved':len(boundary['preserved_evidence']),
        'authorized_success':{c:{'success':s['authorized_success'],'n':s['n']} for c,s in conditions.items()},
        'primary_comparison':comparisons['recovery_minus_permissions'],
        'limits':'Software, evidence and summary consistency only. Model weights and live inference environment are not independently verified or rerun.',
    }


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',nargs='?',type=Path,default=ROOT/'outputs/followup-heldout-qwen3')
    print(json.dumps(verify(parser.parse_args().run),indent=2))
