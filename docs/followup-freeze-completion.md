# Design freeze completed — November 13, 2026

The verification fixes and scoring clarification are complete. All required
development-only checks passed, and the design was frozen at
**2026-11-13 19:01:54 UTC (11:01:54 Pacific)**. Held-out evaluation has not started.

This is a local prospective freeze, not external preregistration. The user reports
that the amended 432-trial study received external review with no requested
changes. Reviewer identity and date were not supplied, and no specific endorsement
or item-level checklist sign-off is inferred.

## Fixed and verified

- The freeze now records Python implementation/version, platform, dependency-lock
  hash and all 39 installed distribution versions. Frozen evaluation rejects
  drift before loading tasks or initializing the model, including on its first run.
- Private replay now validates each trajectory's sampling seed against its base
  seed, task ID and repeat index, including partial replay before resume.
- The protocol explicitly states that source/backup access is required, but every
  supporting lookup in the reference plan is not independently required. An omitted
  ledger lookup is a trace diagnosis, not a separate scoring penalty. Scores and
  the original budget failures are unchanged.
- An explicit verification transition preserves ordinary source-drift rejection.
  It checks the old snapshots and unchanged experimental behavior, replays the
  original run under its archived implementation, and applies the stronger verifier
  to the same records. No old configuration, score or input commitment was rewritten.

## Validation

| Check | Result |
|---|---:|
| Tests in the inference environment | 65 passed; zero failures/errors |
| Additional scripted development trajectories | 432 replayed and analyzed |
| Scripted gated trajectories achieving authorized success | 324/324 |
| Resume of completed scripted run | No trajectories rerun or changed |
| Original model trajectories verified under archived and current code | 432 |
| Original sampling seeds verified | 432 |
| Previous evidence files preserved byte-for-byte | 68 |
| Frozen source/data/protocol/lock inputs verified | 13 |
| Pinned model files verified | 12 |

The scripted checks are software validation, not additional learned-model findings.
The original full-split generation test was excluded; all other original follow-up
tests ran with development-only setup. Held-out cases were not parsed, generated,
displayed or used for inference. Integrity hashing and private snapshot copying do
not change the reserved dataset.

## Frozen experiment

One pinned Qwen3-4B-Instruct-2507 four-bit model; baseline, permissions, recovery,
and perfect simulated approval; three repeats; temperature 0.2; base seed
20261111; twelve tool turns; 256 output tokens per turn. The planned evaluation
has 36 reserved cases and 432 trajectories. Workflow family remains the uncertainty
unit, with twelve families rather than 432 independent workflows.

Authorized success remains the primary outcome; recovery minus permissions is
the primary comparison. The null development finding, budget failures, limited
scope of enforcement claims, and other protocol limitations remain intact. No
new model inference was needed for these verification-only changes.

## Records

- [Prospective freeze](../outputs/followup-freeze.json)
- [Post-freeze verification](../outputs/followup-freeze-verification.json)
- [Final test record and source hashes](../outputs/followup-verification-checks-final.json)
- [Verified development transition](../outputs/followup-verification-transition.json)
- [Scripted software-check report](../outputs/followup-verification-dev-check/results.md)
- [Protocol and scoring limitation](followup-protocol.md)

Freeze SHA-256:
`2378d1f362a12f375fe5962a21a229f1142a31914119e55e9f1dc888ffd11c62`

Unchanged held-out SHA-256:
`2730b1b7237af2670dd30e8e41af2d0685cb5565698f92bdf56e39d4493c9e91`

The final check confirmed the freeze matches the source, runtime and model, and
that no held-out output configuration or evaluation-start claim exists. The fixes
and freeze are saved locally; the previously published development checkpoint
remains commit `824ec954444e7cc990d09f99cc9062b4874599b2`.
