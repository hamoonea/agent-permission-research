"""Verify a declared infrastructure-only transition from archived development evidence.

Ordinary replay and resume remain strict. This explicit development-only path
checks the archived implementation, then replays identical evidence using the
current scorer. It never loads held-out cases or imports the model runtime.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from .evidence import digest, inputs, load_tasks, read_rows, verify_rows
from .tasks import ROOT

ORIGINAL_INPUTS = {
    'followup/__init__.py', 'followup/analyze.py', 'followup/core.py',
    'followup/evidence.py', 'followup/freeze.py', 'followup/run.py', 'followup/tasks.py',
    'data/followup/dev.json', 'data/followup/heldout.json', 'docs/followup-protocol.md',
}
MUTABLE_INPUTS = {
    'followup/evidence.py', 'followup/freeze.py', 'followup/run.py',
    'docs/followup-protocol.md',
}
ADDED_INPUTS = {'followup/runtime.py', 'followup/transition.py', 'requirements-mlx-lock.txt'}


def definition(path, name):
    tree = ast.parse(path.read_text())
    matches = [node for node in tree.body
               if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name]
    if len(matches) != 1:
        raise ValueError('Missing or duplicate behavior definition: '+name)
    return ast.dump(matches[0], include_attributes=False)


def replay_development_transition(run, manifest_path):
    run, manifest_path = Path(run).resolve(), Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    config = json.loads((run/'config.json').read_text())
    if config['split'] != 'dev' or config['backend'] != 'mlx':
        raise ValueError('Transition is only for genuine development evidence')
    if manifest.get('scope') != 'verification-only; no experimental behavior changes':
        raise ValueError('A declared verification-only transition is required')
    for key, path in [('development_config_sha256', run/'config.json'),
                      ('development_trajectories_sha256', run/'trajectories.jsonl')]:
        if manifest.get(key) != digest(path):
            raise ValueError('Transition evidence commitment mismatch: '+key)
    original, current = config['inputs'], inputs()
    if manifest.get('original_inputs') != original or manifest.get('candidate_inputs') != current:
        raise ValueError('Transition input commitments do not match')
    if set(original) != ORIGINAL_INPUTS or set(current) != ORIGINAL_INPUTS | ADDED_INPUTS:
        raise ValueError('Unplanned transition input set')
    changed = {name for name in original if original[name] != current[name]}
    if not changed <= MUTABLE_INPUTS:
        raise ValueError('Experimental input changed: '+', '.join(sorted(changed-MUTABLE_INPUTS)))
    snapshot = run/'source-snapshot'
    for name, expected in original.items():
        if digest(snapshot/name) != expected:
            raise ValueError('Original snapshot changed: '+name)
    # Exact AST preservation covers model calls, prompts passed to the model,
    # action execution, sampling seed derivation and shuffled assignment order.
    behaviors = ['MLX', 'execute', 'make_jobs', 'trajectory_seed']
    for name in behaviors:
        destination = 'followup/evidence.py' if name == 'trajectory_seed' else 'followup/run.py'
        if definition(snapshot/'followup/run.py', name) != definition(ROOT/destination, name):
            raise ValueError('Experimental behavior changed: '+name)
    # Isolated child uses only the authenticated original local snapshot. Its
    # original replay hashes reserved bytes but loads development tasks only.
    script = ('import sys; from pathlib import Path; '
              'sys.path.insert(0, sys.argv[1]); '
              'from followup.evidence import replay; '
              'config, rows = replay(Path(sys.argv[2])); print(len(rows))')
    archived = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(snapshot), str(run)],
                              check=True, capture_output=True, text=True)
    rows = read_rows(run)
    if archived.stdout.strip() != str(len(rows)):
        raise ValueError('Archived replay count mismatch')
    tasks = {task['id']: task for task in load_tasks('dev')}
    if set(config['task_ids']) != set(tasks):
        raise ValueError('All development cases are required')
    verify_rows(config, rows, tasks)
    receipt = {
        'manifest_sha256': digest(manifest_path),
        'original_inputs': original,
        'changed_inputs': sorted(changed),
        'added_inputs': sorted(ADDED_INPUTS),
        'unchanged_behavior_definitions': behaviors,
        'archived_replay_records': len(rows),
        'current_replay_records': len(rows),
        'sampling_seeds_verified': len(rows),
        'scope': manifest['scope'],
    }
    return config, rows, receipt


def create_transition(run, output, rationale):
    run, output = Path(run), Path(output)
    if output.exists():
        raise ValueError('Transition record already exists; preserve the original')
    config = json.loads((run/'config.json').read_text())
    manifest = {
        'scope': 'verification-only; no experimental behavior changes',
        'development_config_sha256': digest(run/'config.json'),
        'development_trajectories_sha256': digest(run/'trajectories.jsonl'),
        'original_inputs': config['inputs'], 'candidate_inputs': inputs(),
        'rationale': rationale,
    }
    encoded = json.dumps(manifest, indent=2)+'\n'
    with tempfile.TemporaryDirectory() as td:
        temporary = Path(td)/'transition.json'
        temporary.write_text(encoded)
        _, _, receipt = replay_development_transition(run, temporary)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as file:
        file.write(encoded)
    return receipt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rationale', required=True)
    args = parser.parse_args()
    print(json.dumps(create_transition(args.development_run, args.output, args.rationale), indent=2))
