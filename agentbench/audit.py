"""Replay logged actions and verify scores, final states, and input provenance."""
import argparse
import json
from pathlib import Path

from .build_tasks import build
from .core import Environment
from .run import digest

ROOT = Path(__file__).resolve().parents[1]


def audit(run):
    config = json.loads((run/'config.json').read_text())
    if digest(ROOT/'data/tasks.json') != config['task_sha256']:
        raise ValueError('Task hash mismatch')
    for name, expected in config['source_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError(f'Run source changed: {name}')
    tasks = json.loads((ROOT/'data/tasks.json').read_text())
    if tasks != build():
        raise ValueError('Task generator differs from committed data')
    lookup = {t['id']: t for t in tasks}
    rows = [json.loads(line) for line in (run/'trajectories.jsonl').read_text().splitlines()]
    for row in rows:
        env = Environment(lookup[row['task_id']], row['condition'])
        for recorded in row['events']:
            env.step(recorded['action'])
            if env.events[-1] != recorded:
                raise ValueError(f'Event mismatch: {row["task_id"]}')
        if env.score() != row['metrics'] or env.state != row['final_state']:
            raise ValueError(f'Score or state mismatch: {row["task_id"]}')
        if sum(c['generation_tokens'] for c in row['calls']) != row['generation_tokens']:
            raise ValueError('Token total mismatch')
    if config['backend'] == 'mlx':
        manifest = json.loads((ROOT/'data/model-manifest.json').read_text())
        for item in manifest['files']:
            if config['model_files_sha256'].get(item['name']) != item['sha256']:
                raise ValueError(f'Model differs from pinned manifest: {item["name"]}')
    result = {'replayed_trajectories': len(rows), 'all_scores_and_states_match': True,
              'source_and_task_hashes_match': True,
              'model_matches_pinned_manifest': config['backend'] == 'mlx'}
    (run/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    print(json.dumps(audit(parser.parse_args().run), indent=2))
