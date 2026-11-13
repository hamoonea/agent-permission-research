"""Run development models or frozen held-out evaluation; never invoke real tools."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import time

from .core import CONDITIONS, Environment, initial_messages
from .evidence import digest, inputs, load_tasks, model_identity, positive_int, replay, validate_freeze


def make_jobs(tasks,repeats,seed):
    jobs=[(t,c,r) for t in tasks for c in CONDITIONS for r in range(repeats)]
    random.Random(seed).shuffle(jobs)
    return jobs


def trajectory_seed(seed,task_id,repeat):
    import hashlib
    # Common seeds across conditions; different workflows/repeats get different seeds.
    return int(hashlib.sha256(f'{seed}:{task_id}:{repeat}'.encode()).hexdigest()[:8],16)


class MLX:
    def __init__(self,path,temperature,max_tokens):
        os.environ['HF_HUB_OFFLINE']='1'
        os.environ['TOKENIZERS_PARALLELISM']='false'
        import mlx.core as mx
        from mlx_lm import load,stream_generate
        from mlx_lm.sample_utils import make_sampler
        self.mx=mx
        self.generate=stream_generate
        self.model,self.tokenizer=load(str(path))
        self.sampler=make_sampler(temp=temperature)
        self.max_tokens=max_tokens
        self.packages={p:importlib.metadata.version(p) for p in ('mlx','mlx-lm','transformers')}
        # No workflow data used in warmup, which is excluded from trajectory timing.
        self.warmup=[]
        for _ in range(2):
            self.warmup.append(self.call([{'role':'user','content':'Return the word ready.'}]))

    def seed(self,value): self.mx.random.seed(value)

    def call(self,messages):
        prompt=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        started=time.perf_counter()
        pieces=[]
        last=None
        for token in self.generate(self.model,self.tokenizer,prompt=prompt,
                                   max_tokens=self.max_tokens,sampler=self.sampler):
            pieces.append(token.text)
            last=token
        self.mx.clear_cache()
        return dict(raw=''.join(pieces),prompt_tokens=last.prompt_tokens if last else 0,
                    generation_tokens=last.generation_tokens if last else 0,
                    finish_reason=last.finish_reason if last else 'empty',seconds=time.perf_counter()-started)


def execute(task,condition,repeat,backend,max_steps,seed,model=None,fixture='recovery'):
    env=Environment(task,condition)
    messages=initial_messages(task)
    calls=[]
    error=None
    rng_seed=trajectory_seed(seed,task['id'],repeat)
    if model: model.seed(rng_seed)
    plan=task['reference_plan']
    if fixture=='attack': plan=[task['attack_probe'],*plan]
    elif fixture=='recovery' and task['variant']=='revoked':
        plan=[{'tool':'read','args':{'id':'source'}},*plan]
    started=time.perf_counter()
    for step in range(max_steps):
        try:
            call=model.call(messages) if model else dict(raw=json.dumps(plan[min(step,len(plan)-1)]),
                prompt_tokens=0,generation_tokens=0,finish_reason='scripted',seconds=0.0)
            try: a=json.loads(call['raw'])
            except (ValueError,TypeError): a=None
            result=env.step(a)
            calls.append(call)
            messages.extend([{'role':'assistant','content':call['raw']},
                             {'role':'user','content':'Tool result: '+json.dumps(result,sort_keys=True)}])
            if env.closed: break
        except (Exception,KeyboardInterrupt) as exc:
            error=type(exc).__name__+': '+str(exc)
            break
    return dict(task_id=task['id'],family=task['family'],variant=task['variant'],
                condition=condition,repeat=repeat,backend=backend,rng_seed=rng_seed,
                metrics=env.score(),events=env.events,final_state=env.state,messages=messages,calls=calls,
                elapsed_seconds=time.perf_counter()-started,error=error,
                budget_exhausted=not env.closed and error is None,
                prompt_tokens=sum(c['prompt_tokens'] for c in calls),
                generation_tokens=sum(c['generation_tokens'] for c in calls))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backend',choices=['scripted','mlx'],default='scripted')
    p.add_argument('--split',choices=['dev','heldout'],default='dev')
    p.add_argument('--model',type=Path)
    p.add_argument('--model-label',default='qwen3-4b')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repeats',type=positive_int,default=1)
    p.add_argument('--max-steps',type=positive_int,default=12)
    p.add_argument('--max-tokens',type=positive_int,default=256)
    p.add_argument('--temperature',type=float,default=0.2)
    p.add_argument('--seed',type=int,default=20261111)
    p.add_argument('--limit-families',type=positive_int)
    p.add_argument('--fixture',choices=['reference','attack','recovery'],default='recovery')
    p.add_argument('--freeze',type=Path)
    p.add_argument('--allow-heldout',action='store_true')
    p.add_argument('--resume',action='store_true')
    args=p.parse_args()
    if not 0<=args.temperature<=2: p.error('Temperature must be between 0 and 2')
    if args.backend=='mlx' and args.model is None: p.error('--model is required')
    identity=model_identity(args.model) if args.backend=='mlx' else None
    freeze=None
    if args.split=='heldout' and args.backend=='mlx':
        if not args.freeze or not args.allow_heldout:
            p.error('Held-out inference requires --freeze and --allow-heldout; finish development first')
        if args.limit_families: p.error('Held-out inference cannot select a subset')
        freeze=json.loads(args.freeze.read_text())
        validate_freeze(freeze,args.model_label,identity)
        # Frozen parameters, rather than mutable CLI defaults, determine evaluation.
        for k,v in freeze['run_parameters'].items(): setattr(args,k,v)
    elif args.freeze or args.allow_heldout:
        p.error('Freeze options are only for held-out MLX inference')
    tasks=load_tasks(args.split)
    if args.limit_families:
        names=list(dict.fromkeys(t['family'] for t in tasks))[:args.limit_families]
        tasks=[t for t in tasks if t['family'] in names]
    config=dict(backend=args.backend,split=args.split,model_label=args.model_label if identity else None,
                model_files=identity,task_ids=[t['id'] for t in tasks],inputs=inputs(),
                fixture=args.fixture if args.backend=='scripted' else None,
                conditions=list(CONDITIONS),freeze_sha256=digest(args.freeze) if freeze else None,
                **{k:getattr(args,k) for k in ('repeats','max_steps','max_tokens','temperature','seed')})
    config['packages']={p:importlib.metadata.version(p) for p in ('mlx','mlx-lm','transformers')} if identity else {}
    done=set()
    if args.resume:
        old,rows=replay(args.output,complete=False)
        if old!=config: p.error('Resume configuration differs; preserve the old run and use a new development directory')
        done={(r['task_id'],r['condition'],r['repeat']) for r in rows}
    elif args.output.exists():
        p.error('Output exists. Use --resume for an interrupted run or a new development directory')
    if freeze:
        # One output per frozen model. This is a local workflow guard, not tamper-proof preregistration.
        claim=args.freeze.with_name(args.freeze.name+'.'+args.model_label+'.started.json')
        claim_content=dict(freeze_sha256=config['freeze_sha256'],output=str(args.output.resolve()))
        if claim.exists():
            if not args.resume or json.loads(claim.read_text())!=claim_content:
                p.error('This frozen model evaluation has already started; resume its recorded output')
        else:
            with claim.open('x') as f: json.dump(claim_content,f,indent=2)
    if not args.resume:
        args.output.mkdir(parents=True)
        (args.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
        from .tasks import ROOT
        for name in config['inputs']:
            destination=args.output/'source-snapshot'/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,destination)
    jobs=make_jobs(tasks,args.repeats,args.seed)
    pending=[job for job in jobs if (job[0]['id'],job[1],job[2]) not in done]
    if not pending:
        print('Run already complete; no inference performed.')
        return
    model=MLX(args.model,args.temperature,args.max_tokens) if args.backend=='mlx' else None
    session=dict(started_at=datetime.now(timezone.utc).isoformat(),resume=args.resume,
                 packages=model.packages if model else {},warmup=model.warmup if model else [])
    with (args.output/'sessions.jsonl').open('a') as f: f.write(json.dumps(session)+'\n')
    with (args.output/'trajectories.jsonl').open('a') as out:
        for i,(task,c,r) in enumerate(pending):
            row=execute(task,c,r,args.backend,args.max_steps,args.seed,model,args.fixture)
            out.write(json.dumps(row)+'\n'); out.flush(); os.fsync(out.fileno())
            print(f'{len(done)+i+1}/{len(jobs)} {task["id"]} {c}: '
                  f'success={row["metrics"]["authorized_success"]} errors={row["error"]}',flush=True)
            if row['error'] and row['error'].startswith('KeyboardInterrupt:'):
                raise KeyboardInterrupt('Interrupted trajectory preserved; resume will skip it')
    replay(args.output)
    print('Complete: saved actions, prompts, state, and scores pass replay.')


if __name__=='__main__': main()
