"""Complete-run, development-only repeat stability and descriptive version comparison."""
import argparse
from collections import Counter
import json
from pathlib import Path

from followup.analyze import paired,summarize
from followup.core import CONDITIONS
from followup.evidence import digest,load_tasks,read_rows,replay


def stability(rows):
    groups={}
    for row in rows:
        key=(row['task_id'],row['condition'])
        groups.setdefault(key,[]).append(row['metrics']['authorized_success'])
    result={}
    for condition in CONDITIONS:
        selected={t:values for (t,c),values in groups.items() if c==condition}
        result[condition]={
            'always_successful_cases':sum(all(values) for values in selected.values()),
            'always_unsuccessful_cases':sum(not any(values) for values in selected.values()),
            'mixed_outcome_cases':sum(any(values) and not all(values) for values in selected.values()),
            'case_success_counts':{t:sum(values) for t,values in sorted(selected.items())},
        }
    return result


def failure_counts(rows):
    return {
        'assigned':len(rows),
        'authorized_success':sum(r['metrics']['authorized_success'] for r in rows),
        'unsuccessful':sum(not r['metrics']['authorized_success'] for r in rows),
        'runtime_errors':sum(r['error'] is not None for r in rows),
        'invalid_calls':sum(r['metrics']['invalid_actions'] for r in rows),
        'trials_with_invalid_calls':sum(r['metrics']['invalid_actions']>0 for r in rows),
        'budget_exhausted':sum(r['budget_exhausted'] for r in rows),
        'incorrect_outcome_despite_finish_done':sum(r['metrics']['valid_done'] and not r['metrics']['raw_completion'] for r in rows),
        'total_model_calls':sum(len(r['calls']) for r in rows),
        'accumulated_trajectory_seconds':sum(r['elapsed_seconds'] for r in rows),
    }


def review(run,prior):
    config,rows=replay(run)
    if config['split']!='dev' or config['backend']!='mlx' or config['repeats']!=3:
        raise ValueError('A complete three-repeat development model run is required')
    tasks=load_tasks('dev')
    if set(config['task_ids'])!={t['id'] for t in tasks}:
        raise ValueError('All development cases are required')
    audit=json.loads((run/'failure-audit.json').read_text())
    if audit['provenance']['trajectories_sha256']!=digest(run/'trajectories.jsonl'):
        raise ValueError('Failure audit does not match the run')
    old_config=json.loads((prior/'config.json').read_text())
    if old_config['split']!='dev' or old_config['backend']!='mlx':
        raise ValueError('Prior evidence must be development-only model evidence')
    old=read_rows(prior)
    repeat_tables={str(r):{c:summarize([row for row in rows if row['repeat']==r and row['condition']==c])
                           for c in CONDITIONS} for r in range(3)}
    repeat_deltas={r:(s['recovery']['authorized_success']/s['recovery']['n']-
                      s['permissions']['authorized_success']/s['permissions']['n']) for r,s in repeat_tables.items()}
    failure_categories=Counter(reason for a in audit['rows'] for reason in a['reasons'])
    pair_index={(r['task_id'],r['condition'],r['repeat']):r for r in rows}
    mismatch=[]
    for r in rows:
        if r['condition']!='permissions':continue
        other=pair_index[(r['task_id'],'approval',r['repeat'])]
        if r['messages']!=other['messages'] or r['final_state']!=other['final_state']:
            mismatch.append({'task':r['task_id'],'repeat':r['repeat']})
    family_deltas={}
    for family in sorted({r['family'] for r in rows}):
        arm={c:[r for r in rows if r['family']==family and r['condition']==c] for c in ('permissions','recovery')}
        count={c:sum(r['metrics']['authorized_success'] for r in arm[c]) for c in arm}
        family_deltas[family]={'permissions':count['permissions'],'recovery':count['recovery'],
                              'n_per_condition':len(arm['permissions']),
                              'difference':(count['recovery']-count['permissions'])/len(arm['permissions'])}
    result={
        'scope':'Exploratory development analysis; no held-out inference or design freeze.',
        'provenance':{'config_sha256':digest(run/'config.json'),'trajectories_sha256':digest(run/'trajectories.jsonl'),
                      'prior_trajectories_sha256':digest(prior/'trajectories.jsonl'),'analysis_sha256':digest(__file__)},
        'repeat_summary':repeat_tables,'repeat_recovery_minus_permissions':repeat_deltas,
        'case_stability':stability(rows),'family_recovery_minus_permissions':family_deltas,
        'family_cluster_comparison':paired(rows,'recovery','permissions'),
        'failure_accounting':failure_counts(rows),'prior_failure_accounting':failure_counts(old),
        'overlapping_failure_reasons':dict(failure_categories),
        'permission_approval_mismatches':mismatch,
        'legacy_draft_sensitivity':audit['legacy_draft_sensitivity'],
        'descriptive_version_comparison':{
            c:{'old_original':summarize([r for r in old if r['condition']==c]),
               'new_repeat_zero':repeat_tables['0'][c],
               'new_all_repeats':summarize([r for r in rows if r['condition']==c])} for c in CONDITIONS},
        'comparison_limit':'Versions differ in common prompt, invalid-schema feedback, nine task requests, draft rubric and repeat count. This does not isolate the causal effect of any fix. Twelve families, not 432 independent workflows.',
    }
    (run/'repeat-review.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Three-repeat development analysis','',result['scope'],'',
           '## Authorized success by repeat','','| Repeat | Baseline | Permissions | Recovery | Approval | Recovery − permissions |',
           '|---|---:|---:|---:|---:|---:|']
    for rep,s in repeat_tables.items():
        values=[f'{s[c]["authorized_success"]}/{s[c]["n"]}' for c in CONDITIONS]
        lines.append('| '+str(int(rep)+1)+' | '+' | '.join(values)+f' | {100*repeat_deltas[rep]:+.1f} pp |')
    lines+=['','Repeat labels 1–3 correspond to stored repeat indices 0–2. All were scheduled in advance.','',
            '## Stability across repeats','','| Condition | Always succeeds | Always fails | Mixed outcomes |',
            '|---|---:|---:|---:|']
    for c,s in result['case_stability'].items():
        lines.append(f'| {c} | {s["always_successful_cases"]} | {s["always_unsuccessful_cases"]} | {s["mixed_outcome_cases"]} |')
    lines+=['','Counts refer to the 36 development cases, each observed three times.','',
            '## Recovery comparison by workflow family','','| Family | Permissions | Recovery | Difference |',
            '|---|---:|---:|---:|']
    for f,s in family_deltas.items():
        n=s['n_per_condition'];lines.append(f'| {f} | {s["permissions"]}/{n} | {s["recovery"]}/{n} | {100*s["difference"]:+.1f} pp |')
    lines+=['','## Before/after accounting (descriptive)','','| Metric | Prior run (144 trials) | Amended run (432 trials) |','|---|---:|---:|']
    for metric in ('authorized_success','unsuccessful','runtime_errors','invalid_calls','trials_with_invalid_calls','budget_exhausted','incorrect_outcome_despite_finish_done','total_model_calls'):
        lines.append(f'| {metric} | {result["prior_failure_accounting"][metric]} | {result["failure_accounting"][metric]} |')
    lines+=['',result['comparison_limit'],'',
            'The unchanged prior results retain their original rubric. The new primary rubric was fixed before inference. '
            'See results.md for workflow-cluster uncertainty and failure-audit.md for diagnoses and the legacy-draft sensitivity.','',
            f'Permission/approval matched-pair transcript or state mismatches: {len(mismatch)}. This is an implementation check, not independent corroboration.','']
    (run/'repeat-review.md').write_text('\n'.join(lines))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--prior',type=Path,default=Path('outputs/followup-dev-v1'))
    a=p.parse_args();result=review(a.run,a.prior)
    print(json.dumps({k:result[k] for k in ('failure_accounting','repeat_recovery_minus_permissions','family_cluster_comparison')},indent=2))
