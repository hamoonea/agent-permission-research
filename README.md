# Evaluating permissions and approval in LLM agents

> **Amended development checkpoint — November 13, 2026.** The 432-trial study is
> complete. No design freeze or held-out evaluation has occurred. Reserved cases,
> their generator and snapshot copies remain private. Use the
> [public verification instructions](docs/development-checkpoint.md); full private-input
> v2 commands require withheld files. Earlier evidence is preserved in this branch's history.

## Latest development revision (v2.1)

The amended **432-trial development study** (three repeats) is complete and
replay-verified. Authorized success: 54/108 for instructions only and 102/108
for each of basic permissions, recovery guidance and perfect simulated approval.
Recovery guidance showed no observed advantage; a zero observed difference is
not evidence of general equivalence. All gated failures were budget tasks with
omitted factual lookups. The held-out dataset remains unchanged and unevaluated.

- [Amended study results and freeze recommendation](docs/followup-amended-development-review.md)
- [Changes fixed before inference](docs/followup-amendment-v2.md)
- [Three-repeat results](outputs/followup-dev-v2-repeats3/results.md)

Nineteen development-focused amendment, diagnostic and repeat-analysis checks
passed. No design freeze has occurred. The earlier evidence below is preserved
with its original scoring; these versions should not be pooled as independent trials.

## Follow-up study (v2): scoped permissions and recovery

The follow-up adds **24 workflow families / 72 cases**, split into 12 development
and 12 held-out families. Each has clean, injected, and revoked-source variants.
Broader permissions allow multiple actions without revealing the correct answer.
The main comparison tests whether policy-only denial guidance improves successful
completion compared with a bare denial. A separate package preserves the v1 code
and evidence below.

- [Follow-up protocol](docs/followup-protocol.md)
- [Runbook and December 15 schedule](docs/followup-runbook.md)
- [External review checklist](docs/followup-review-checklist.md)
- [Dataset manifest](data/followup/manifest.json)
- [Development validation and initial findings](docs/followup-development-log.md)
- [Full development study and pre-freeze review](docs/followup-full-development-review.md)

Earlier v2.0 validation: 30 automated tests and 864 scripted workflow checks passed. A genuine
24-trajectory development smoke test completed without runtime/schema errors;
all records passed replay. Recovery guidance did not improve success in that
two-family sample. See the development log for counts, amendments, and limits.

The original **144-trajectory development run** is preserved and replay-verified:
authorized success was 12/36 for instructions only, 24/36 for basic permissions,
21/36 for recovery guidance, and 24/36 for perfect simulated approval. The review
recommends clarifying tool schemas, draft scoring and task wording before freezing.
Original scores are preserved. No held-out model inference has occurred; the
held-out data hash is unchanged. These are development results, not final validation.

**Status:** implementation and development validation. Held-out model inference
requires an explicit prospective freeze after development. Scripted checks are
software verification, not model findings. This is not an externally preregistered
study; the held-out fixtures are visible to the designer and software tests.
The v2 design and implementation were prepared with Codex assistance and require
the applicant's review and accurate contribution disclosure.

## Original pilot (v1)

A reproducible independent research pilot comparing instruction-only rules, enforced permissions, simulated approval, and combined controls in a fictional workplace. All tools operate on in-memory data. No tool can send real email, access accounts, or execute arbitrary code.

The benchmark contains **24 cases from eight base workflows**, each with clean, ambiguous, and injected source content. The first model pilot uses a pinned, locally executed Qwen3 4B Instruct model. It is an exploratory study, not a claim of production safety or a human-subject experiment.

## Read the research

- [Research report](docs/research-report.md)
- [Protocol and limitations](docs/protocol.md)
- [Related work](docs/related-work.md)
- [Model pilot results](outputs/pilot-v1/results.md)
- [Scripted harness checks](outputs/harness-v1/results.md), which are not model results

The central distinction is between **attempted violations** and **executed violations**. A successful gate can prevent execution while the model continues trying prohibited actions. Authorized completion requires satisfying the task's final-state goal without any executed violation.

## First pilot findings

Across 96 genuine local-model trajectories, baseline instructions allowed an executed policy violation in 8/24 cases; enforced permissions allowed none in 24. Authorized completion rose from 16/24 to 23/24. Raw task completion was 23/24 in both conditions, but their failed cases differed. Requiring valid termination as well as authorized completion gives 14/24 and 18/24, respectively.

Approval alone left one trajectory with executed violations because its gate did not review reads. It required 45 simulated reviews, compared with 32 for combined controls. Mean trajectory latency was 5.05 seconds for baseline and 5.99 seconds for permissions. This small development pilot cannot establish general safety or utility equivalence. See the report for all conditions, uncertainty, and failure examples.

## Reproduce the software checks

Python 3.10 or newer is sufficient; the environment, tests, scripted backend, and analysis use only the standard library.

```sh
python3 -m unittest discover -s tests -v
python3 -m agentbench.run --backend scripted --output outputs/my-harness
python3 -m agentbench.analyze outputs/my-harness
python3 -m agentbench.audit outputs/my-harness
```

The scripted backend deliberately performs an attack probe on every case, including clean cases. This is a software stress fixture, not an estimate of agent behavior or attack success. Output directories must be new: completed evidence is not silently overwritten.

## Reproduce the model pilot

Local inference uses MLX on an Apple Silicon Mac with GPU access. The committed dependency lock records the environment used for the pilot. The model download is approximately 2.3 GB; weights are not included in this repository. The model's own license applies to downloaded weights.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-mlx-lock.txt
.venv/bin/python -m agentbench.download_model
.venv/bin/python -m agentbench.run --backend mlx --model models/qwen3-4b --output outputs/my-pilot
.venv/bin/python -m agentbench.analyze outputs/my-pilot
.venv/bin/python -m agentbench.audit outputs/my-pilot
```

To regenerate the committed short report from the published pilot, run `python3 -m agentbench.report` after analyzing and auditing `outputs/pilot-v1`.

Default settings: four conditions, 24 cases, one repeat, temperature zero, six calls per trajectory, 160 generated tokens per call, seed 20261110. Model revision: `50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b` from `mlx-community/Qwen3-4B-Instruct-2507-4bit`. File hashes are recorded in `data/model-manifest.json` and checked against run provenance by the audit.

To study sampling variability later, specify a nonzero `--temperature` and `--repeats`. This changes the experimental protocol and should use a new output directory. GPU and library differences can affect reproducibility even with fixed seeds. Model loading time is excluded from trajectory latency, and no warmup is performed; initial inference may incur compilation overhead.

## What the controls do

| Condition | Permissions | Simulated approval |
| --- | --- | --- |
| Baseline | Rules in instructions | None |
| Permissions | Exact arguments checked on every tool action | None |
| Approval | Rules in instructions | Every mutation reviewed by a perfect policy oracle |
| Combined | Exact arguments checked first | Every permitted mutation reviewed |

All conditions receive the same prompt. Approval affects mutations, including drafts, but not reads. The oracle and permission layer share the same policy matcher: their overlapping protection is intentional and not evidence of independent defenses. A denied action returns feedback to the agent, which can continue.

## Evidence and limitations

Each run saves configuration, model and source hashes, prompts, raw outputs, token counts, tool events, scores, and final states. Analysis refuses incomplete or duplicate assignments. Audit replays the events to verify stored scores and states. Eight base workflows are the resampling unit for paired exploratory intervals.

The tasks are short, policies reveal exact permitted actions, attacks are fixed, and approval is perfect by construction. This setup does not evaluate real human review, broad information-flow policies, realistic multistep planning, or unseen adaptive attacks. Zero observed failures would not establish safety. Human review time, energy use, and dollar computational cost are not measured.

## Repository structure

- `agentbench/`: environment, task generator, model runner, analysis, audit, and pinned model downloader
- `data/`: synthetic tasks and model provenance
- `tests/`: policy, state-isolation, scoring, schema, and approval checks
- `outputs/`: separate scripted and model evidence
- `docs/`: protocol, context, and research report

All emails, identifiers, documents, and records are synthetic. Reserved `.test` domains are used throughout. No private application documents or clinical research data are included.
