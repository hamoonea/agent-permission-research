# Follow-up runbook and completion plan

> Public-checkpoint note: full v2 replay/inference commands below require the
> private fixture files. For the public development-only verifier and scope,
> see [development-checkpoint.md](development-checkpoint.md).

This package is ready for development evaluation. It does not claim a completed
held-out study. Preserve the original pilot results. All tools are simulated and
all data are fictional; no external accounts, messages, or API charges are used.

## What is ready

- 24 workflow families, 72 cases, split by family into 36 development and 36 held-out cases.
- Broader permissions; factual goals independent of scope membership.
- Baseline, permission gate, permission gate with recovery guidance, and perfect
  simulated approval with matched coverage.
- Local MLX model inference, task-free warmup, recorded prompts and tool events,
  sampled repeats, interruption/resume, and per-model frozen evaluation guards.
- Replay validation, complete-assignment checks, failure accounting, variant
  tables, and paired uncertainty that resamples workflows rather than trajectories.
- A reviewer checklist and a study protocol with the remaining limitations.

## 1. Environment

Run commands from the repository root. The scripted tests use Python's standard
library. Genuine inference requires Apple Silicon, Metal access, and MLX.

For a fresh setup:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-mlx-lock.txt
.venv/bin/python -m agentbench.download_model
```

The downloader uses the original pilot's pinned model. Reuse your existing local
model directory if already downloaded. In the current workspace, the usable
Python and model are at `../clinical-ai-research/.venv/bin/python` and
`../clinical-ai-research/models/qwen3-4b`. Substitute these in the commands below
to avoid downloading or installing anything again. Do not run inference while
other heavy workloads are using the GPU; timing is descriptive even with warmup.

## 2. Check the software

```sh
python3 -B -m unittest discover -s tests -v
python3 -B -m followup.run --backend scripted --split dev --fixture attack --output outputs/followup-harness-dev
python3 -B -m followup.analyze outputs/followup-harness-dev
```

The reference/attack/recovery scripted modes know the reference plan. They only
test the environment. Never describe their success rates as learned-model results.
Deterministic software tests may inspect both splits; no model should see held-out
prompts before evaluation. The generated files are already supplied; regenerating
`python3 -B -m followup.tasks` refuses to silently overwrite different fixtures.

## 3. Development inference

For a small pipeline check, add `--limit-families 2` and use a separate output name.
For the complete development run:

```sh
.venv/bin/python -B -m followup.run --backend mlx --model models/qwen3-4b --model-label qwen3-4b --split dev --output outputs/followup-dev-v1
.venv/bin/python -B -m followup.analyze outputs/followup-dev-v1
```

This is 144 trajectories (36 cases x 4 conditions x 1 repeat). Defaults are
temperature 0.2, 12 tool turns, and 256 output tokens per turn. Inspect failures
before changing settings. Any prompt/task/code change requires a new output
directory; do not combine old and new conditions. Keep a short log of each change
and why it was justified. Do not optimize for the held-out fixtures.

If interrupted, use the same command and append `--resume`. Recorded complete
trajectories are replay-checked and skipped, including failures. A partially written
JSON line is rejected rather than silently discarded; preserve it and document any
repair. Model-loading failures can be retried with resume because no trajectory was
recorded. A model error inside a trajectory remains a failure and is not rerun.

Give `results.md`, the protocol, and a sample of development trajectories to
Dr. Sabrina Navid Chaudry if she agrees to review this study. Record her actual
role and comments. No review or recommendation has been requested by this package.

## 4. Freeze before any held-out inference

Resolve implementation defects and record the final design. A full genuine
development run is required; scripted checks or a two-family smoke run cannot
serve as the development evidence. Freeze after the final source/protocol edits.

```sh
.venv/bin/python -B -m followup.freeze --development-run outputs/followup-dev-v1 --model qwen3-4b=models/qwen3-4b --repeats 3 --temperature 0.2 --max-steps 12 --max-tokens 256 --rationale "Replace this with the actual development-based rationale and review status" --output outputs/followup-freeze.json
```

For a prespecified second model, add another `--model label=/local/model/path`
before evaluation begins. Do not download a new model or incur charges merely
to satisfy a model-count target; a rigorous one-model result with limitations is
preferable to rushed breadth. Label the second model as a replication, report it
separately, and preserve its full file hashes.

The freeze is a local record, not external preregistration. Editing a frozen input
causes inference to stop. Hold off on edits to `followup/*.py`, the protocol, or
datasets until the frozen evaluation finishes. If a defect requires changes,
preserve the old freeze and results and document an amendment. Reused test cases
are then exploratory, not fresh confirmation.

## 5. Held-out evaluation

```sh
.venv/bin/python -B -m followup.run --backend mlx --model models/qwen3-4b --model-label qwen3-4b --split heldout --freeze outputs/followup-freeze.json --allow-heldout --output outputs/followup-heldout-qwen3
.venv/bin/python -B -m followup.analyze outputs/followup-heldout-qwen3
```

Frozen parameters override run defaults, and case selection is disabled. This is
432 trajectories per model at three repeats. The runner records one output path
per frozen model. Resume that path with the same command plus `--resume`; do not
delete the `.started.json` claim to cherry-pick a replacement run.

Report every assigned trajectory, including runtime errors and malformed answers.
The report refuses an incomplete or duplicate run. A second model uses its own
label/output and the same freeze. Evaluate all prespecified models, or explicitly
report why a model was unavailable rather than silently dropping it.

## 6. Final deliverable

Write a concise report with:

1. Question, relation to AgentDojo/CaMeL, and what this study adds.
2. Workflow split, conditions, model identities and prospective freeze date.
3. Primary authorized-success comparison plus clean/injected/revoked tables.
4. Representative failure traces, including wrong-but-permitted actions.
5. Recovery denominators, scope violations, termination and repeated-denial counts.
6. Limitations, any amendments, external review status and actual personal contributions.

Do not translate perfect-oracle review counts into human minutes. Do not claim
zero observed violations proves safety. A negative recovery-feedback result is
worth reporting. This package was designed/implemented with AI assistance; the
applicant should review the design, reproduce the analysis, and explain their
own reasoning and contributions accurately.

## Dates and priorities (2026, Pacific Time)

| Due | Deliverable |
|---|---|
| Nov. 15 | Understand the code/protocol; arrange review and confirm recommendation writers |
| Nov. 22 | Complete development run, inspect failures, resolve methodological feedback |
| Nov. 25 | Freeze model(s), budgets, prompts, scoring and workflows |
| Nov. 29 | Complete held-out evaluation; stop adding features |
| Dec. 5 | Finish report, résumé findings and statement-of-purpose research paragraph |
| Dec. 10 | Submit application with a five-day buffer |
| Dec. 15 | Confirm all required supporting materials have arrived |

If time becomes tight, keep one model and the prespecified comparison, and defer
new conditions, external benchmark integration, and human-subject research.
