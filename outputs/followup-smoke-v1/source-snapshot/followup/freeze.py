"""Freeze a prospective held-out evaluation after development is complete."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from .evidence import digest,inputs,load_tasks,model_identity,positive_int,replay


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--development-run',type=Path,required=True)
    p.add_argument('--model',action='append',required=True,metavar='LABEL=LOCAL_PATH')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=positive_int,default=3)
    p.add_argument('--temperature',type=float,default=0.2)
    p.add_argument('--max-steps',type=positive_int,default=12)
    p.add_argument('--max-tokens',type=positive_int,default=256)
    p.add_argument('--seed',type=int,default=20261111)
    p.add_argument('--rationale',required=True,help='Why these settings were selected on development data')
    args=p.parse_args()
    if args.output.exists(): p.error('Freeze file already exists; preserve the original')
    if not 0<args.temperature<=2: p.error('Use positive temperature for sampled repeats')
    config,rows=replay(args.development_run)
    if config['backend']!='mlx' or config['split']!='dev': p.error('A genuine development model run is required')
    if set(config['task_ids'])!={t['id'] for t in load_tasks('dev')}:
        p.error('Run all development families before freezing; a smoke test is insufficient')
    if any(r['error'] for r in rows): p.error('Resolve development runtime errors before freezing')
    models={}
    for entry in args.model:
        label,sep,path=entry.partition('=')
        if not sep or not re.fullmatch('[a-zA-Z0-9_-]+',label) or label in models:
            p.error('Use unique safe labels: --model qwen3-4b=/path/to/model')
        models[label]=model_identity(path)
    freeze=dict(created_at=datetime.now(timezone.utc).isoformat(),inputs=inputs(),models=models,
                run_parameters={k:getattr(args,k) for k in ('repeats','temperature','max_steps','max_tokens','seed')},
                development_config_sha256=digest(args.development_run/'config.json'),
                development_trajectories_sha256=digest(args.development_run/'trajectories.jsonl'),
                rationale=args.rationale,
                status='Local prospective freeze, not externally preregistered or designer-blind')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f: f.write(json.dumps(freeze,indent=2)+'\n')
    print('Frozen. Do not tune on held-out results; preserve amendments and any failed evaluation.')


if __name__=='__main__': main()
