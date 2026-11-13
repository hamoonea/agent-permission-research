"""Content-addressed inputs and strict replay of saved evidence."""
import hashlib
import json
from pathlib import Path

from .core import CONDITIONS, Environment, initial_messages
from .tasks import ROOT


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inputs():
    files=[*sorted((ROOT/'followup').glob('*.py')),
           ROOT/'data/followup/dev.json',ROOT/'data/followup/heldout.json',
           ROOT/'docs/followup-protocol.md', ROOT/'requirements-mlx-lock.txt']
    return {str(p.relative_to(ROOT)):digest(p) for p in files}


def model_identity(path):
    path=Path(path)
    if not path.is_dir() or not list(path.glob('*.safetensors')):
        raise ValueError('Model directory must contain local safetensors weights')
    return {p.name:digest(p) for p in sorted(path.iterdir()) if p.is_file()}


def load_tasks(split):
    tasks=json.loads((ROOT/f'data/followup/{split}.json').read_text())
    if any(t['split']!=split for t in tasks): raise ValueError('Mislabeled split')
    if len({t['id'] for t in tasks})!=len(tasks): raise ValueError('Duplicate task IDs')
    return tasks


def read_rows(run):
    p=Path(run)/'trajectories.jsonl'
    if not p.exists(): return []
    return [json.loads(line) for line in p.read_text().splitlines()]


def trajectory_seed(seed,task_id,repeat):
    import hashlib
    # Common seeds across conditions; different workflows/repeats get different seeds.
    return int(hashlib.sha256(f'{seed}:{task_id}:{repeat}'.encode()).hexdigest()[:8],16)


def verify_rows(config, rows, tasks, complete=True):
    if type(config.get('seed')) is not int: raise ValueError('Missing or invalid base sampling seed')
    if len(config['task_ids'])!=len(set(config['task_ids'])): raise ValueError('Duplicate task assignment')
    if not set(config['task_ids'])<=set(tasks): raise ValueError('Unknown task assignment')
    if any(t['split']!=config['split'] for t in tasks.values()): raise ValueError('Mislabeled split')
    expected={(t,c,r) for t in config['task_ids'] for c in CONDITIONS for r in range(config['repeats'])}
    observed=set()
    for row in rows:
        key=(row['task_id'],row['condition'],row['repeat'])
        if key not in expected or key in observed: raise ValueError('Duplicate/unplanned trajectory')
        observed.add(key)
        if type(row.get('rng_seed')) is not int or row['rng_seed']!=trajectory_seed(config['seed'],row['task_id'],row['repeat']):
            raise ValueError('Sampling seed mismatch')
        task=tasks[row['task_id']]
        if row['family']!=task['family'] or row['variant']!=task['variant'] or row['backend']!=config['backend']:
            raise ValueError('Trajectory metadata mismatch')
        env=Environment(task,row['condition'])
        if len(row['calls'])!=len(row['events']): raise ValueError('Call/event mismatch')
        messages=initial_messages(task)
        for call,event in zip(row['calls'],row['events']):
            try: a=json.loads(call['raw'])
            except (ValueError,TypeError): a=None
            if a!=event['action']: raise ValueError('Raw response/action mismatch')
            result=env.step(a)
            if env.events[-1]!=event: raise ValueError('Event replay mismatch')
            messages.extend([{'role':'assistant','content':call['raw']},
                             {'role':'user','content':'Tool result: '+json.dumps(result,sort_keys=True)}])
        if messages!=row['messages']: raise ValueError('Prompt transcript mismatch')
        if env.state!=row['final_state'] or env.score()!=row['metrics']:
            raise ValueError('State/score replay mismatch')
        for token in ('prompt_tokens','generation_tokens'):
            if sum(c[token] for c in row['calls'])!=row[token]: raise ValueError('Token total mismatch')
        if len(row['calls'])>config['max_steps']: raise ValueError('Exceeded step limit')
        exhausted=not env.closed and row['error'] is None
        if row['budget_exhausted']!=exhausted: raise ValueError('Exhaustion mismatch')
        if exhausted and len(row['calls'])!=config['max_steps']: raise ValueError('Premature truncation')
    if complete and observed!=expected: raise ValueError(f'Incomplete run: {len(observed)}/{len(expected)}')


def replay(run, complete=True):
    run=Path(run)
    config=json.loads((run/'config.json').read_text())
    if config['inputs']!=inputs(): raise ValueError('Study inputs changed since this run')
    tasks={t['id']:t for t in load_tasks(config['split'])}
    rows=read_rows(run)
    verify_rows(config,rows,tasks,complete)
    return config,rows


def validate_freeze(freeze, label, identity):
    if freeze['inputs']!=inputs(): raise ValueError('Frozen study inputs have changed')
    if label not in freeze['models'] or freeze['models'][label]!=identity:
        raise ValueError('Model is not the frozen model for this label')
    from .runtime import validate_runtime
    validate_runtime(freeze.get('runtime'))


def positive_int(value):
    value=int(value)
    if value<1: raise ValueError('Positive integer required')
    return value
