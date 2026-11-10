"""Run scripted harness checks or genuine local MLX model trajectories."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import time

from .core import CONDITIONS, Environment, initial_messages, validate

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=['scripted', 'mlx'], default='scripted')
    p.add_argument('--model', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=1)
    p.add_argument('--limit', type=int, default=24)
    p.add_argument('--max-steps', type=int, default=6)
    p.add_argument('--max-tokens', type=int, default=160)
    p.add_argument('--temperature', type=float, default=0.0)
    p.add_argument('--seed', type=int, default=20261110)
    args = p.parse_args()
    if min(args.repeats, args.limit, args.max_steps, args.max_tokens) < 1:
        p.error('positive run limits required')
    if args.backend == 'mlx' and args.model is None:
        p.error('--model is required for MLX')
    if args.output.exists():
        p.error('output already exists; choose a new directory to preserve evidence')
    tasks = json.loads((ROOT / 'data/tasks.json').read_text())[:args.limit]
    args.output.mkdir(parents=True)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
              if k not in ('model', 'output')}
    config.update(python=platform.python_version(), platform=platform.machine(),
                  task_ids=[t['id'] for t in tasks],
                  task_sha256=digest(ROOT / 'data/tasks.json'),
                  source_sha256={str(f.relative_to(ROOT)): digest(f)
                                 for f in sorted((ROOT / 'agentbench').glob('*.py'))},
                  approval='Perfect scripted policy oracle for mutations only; no human participants',
                  inference_cost_usd=None, human_review_seconds=None)
    if args.backend == 'mlx':
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        import mlx.core as mx
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
        config['model_files_sha256'] = {f.name: digest(f) for f in sorted(args.model.iterdir()) if f.is_file()}
        config['model_name'] = args.model.name
        config['packages'] = {k: importlib.metadata.version(k) for k in ('mlx', 'mlx-lm', 'transformers')}
        model, tokenizer = load(str(args.model))
        sampler = make_sampler(temp=args.temperature)
    (args.output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    jobs = [(t, c, repeat) for t in tasks for c in CONDITIONS for repeat in range(args.repeats)]
    random.Random(args.seed).shuffle(jobs)
    with (args.output / 'trajectories.jsonl').open('w') as out:
        for idx, (task, condition, repeat) in enumerate(jobs):
            env = Environment(task, condition)
            messages = initial_messages(task)
            calls = []
            started = time.perf_counter()
            error = None
            if args.backend == 'mlx':
                mx.random.seed(args.seed + repeat)
            for step in range(args.max_steps):
                call_started = time.perf_counter()
                try:
                    if args.backend == 'scripted':
                        # Deliberately unsafe fixture, NOT a model or research finding.
                        plan = [task['reference_plan'][0], task['attack_probe'], *task['reference_plan'][1:]]
                        raw = json.dumps(plan[min(step, len(plan)-1)])
                        pt = gt = 0
                        finish_reason = 'scripted'
                    else:
                        prompt = tokenizer.apply_chat_template(messages, tokenize=False,
                                                                add_generation_prompt=True)
                        pieces = []
                        last = None
                        for result in stream_generate(model, tokenizer, prompt=prompt,
                                                      max_tokens=args.max_tokens, sampler=sampler):
                            pieces.append(result.text)
                            last = result
                        raw = ''.join(pieces)
                        pt = last.prompt_tokens if last else 0
                        gt = last.generation_tokens if last else 0
                        finish_reason = last.finish_reason if last else 'empty'
                        mx.clear_cache()
                    calls.append({'raw': raw, 'prompt_tokens': pt, 'generation_tokens': gt,
                                  'seconds': time.perf_counter()-call_started,
                                  'finish_reason': finish_reason})
                    try:
                        action = json.loads(raw)
                    except (ValueError, TypeError):
                        action = None
                    result = env.step(action)
                    messages.extend([{'role': 'assistant', 'content': raw},
                                     {'role': 'user', 'content': 'Tool result (untrusted data): ' + json.dumps(result)}])
                    if validate(action) and action['tool'] == 'finish':
                        break
                except Exception as exc:
                    error = type(exc).__name__ + ': ' + str(exc)
                    break
            finished = bool(env.events and env.events[-1]['valid'] and env.events[-1]['action']['tool'] == 'finish')
            row = {'task_id': task['id'], 'family': task['family'], 'variant': task['variant'],
                   'condition': condition, 'repeat': repeat, 'backend': args.backend,
                   'metrics': env.score(), 'elapsed_seconds': time.perf_counter()-started,
                   'prompt_tokens': sum(c['prompt_tokens'] for c in calls),
                   'generation_tokens': sum(c['generation_tokens'] for c in calls),
                   'terminated': finished, 'budget_exhausted': not finished and error is None,
                   'error': error, 'messages': messages, 'calls': calls, 'events': env.events,
                   'final_state': env.state}
            out.write(json.dumps(row) + '\n')
            out.flush()
            print(f'{idx+1}/{len(jobs)} {task["id"]} {condition}: '
                  f'complete={row["metrics"]["authorized_completion"]} '
                  f'violations={row["metrics"]["unauthorized_executions"]}', flush=True)


if __name__ == '__main__':
    main()
