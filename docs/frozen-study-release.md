# Complete frozen-study release — November 13, 2026

This release publishes the unchanged frozen design and all 432 held-out trials:
36 cases across 12 workflow families, four conditions and three repeats. All 195
unsuccessful trials remain in the raw evidence, summaries and failure traces.
No trial was discarded, replaced or rerun for publication.

The release continues the `development/checkpoint-2026-11-12` branch. The original
pilot on `main` and earlier checkpoint commits remain unchanged. The formerly
reserved synthetic dataset, original generator and source snapshots are now
public because evaluation has finished. Future use of these public cases cannot
be treated as a fresh held-out confirmation of this study.

## Start here

- [Held-out results and limitations](followup-heldout-results.md)
- [Frozen protocol](followup-protocol.md) and [freeze record](../outputs/followup-freeze.json)
- [Complete raw trajectories](../outputs/followup-heldout-qwen3/trajectories.jsonl)
- [All 195 failure traces](../outputs/followup-heldout-qwen3/failure-traces.md)
- [Primary results](../outputs/followup-heldout-qwen3/summary.json) and
  [descriptive failure analysis](../outputs/followup-heldout-qwen3/heldout-review.json)
- [Analysis integrity record](../outputs/followup-heldout-qwen3/analysis-manifest.json)
  and [publication record](../public_checkpoint/manifest.json)

Recovery achieved 69/108 authorized successes versus 63/108 for basic permissions.
The difference was +5.6 percentage points, with a prespecified exploratory 95%
family-cluster bootstrap interval of [0.0, 13.9] points. This includes no benefit.
Three of the six gains improved the final decision; the other three satisfied a
required source read despite identical correct final selections. Three recovery
trials also worsened intermediate task state while both conditions still failed.
These limitations and all failures are retained under the original scoring rules.

## Verify this release without running a model

From the repository root, with Python 3.10 or later, run:

```sh
python3 -B -m public_checkpoint.verify
python3 -B -m unittest discover -s tests
python3 -B -m unittest study_analysis.test_development_audit study_analysis.test_repeated_development_review study_analysis.test_heldout_review public_checkpoint.test_verify public_checkpoint.test_frozen_release
```

These commands use Python's standard library and do not download a model or run
inference. The publication checks passed: 58 repository tests plus 19 analysis
and publication tests, with no skips.

The verifier checks all 13 frozen input files and their held-out snapshots,
replays all 432 held-out event histories and scores, reproduces the frozen
summaries and paired comparisons, recomputes the descriptive diagnoses, and
checks coverage of all 195 failure traces. It also replays the 432 amended
development trials through the recorded verification transition and checks that
68 earlier evidence files retain their committed hashes.

The original freeze and trajectory commitments are:

```text
Freeze:       2378d1f362a12f375fe5962a21a229f1142a31914119e55e9f1dc888ffd11c62
Trajectories: ea97a44c9cea57c15f10be628670ff910c5676a5dfc0ea4a63cce19b7e02a75f
```

Replay establishes consistency of the published software, records and analysis.
It does not independently reproduce the model's outputs or attest the original
live inference environment. Model weights are not included; their file hashes,
the recorded environment and the dependency lock are included. The original
MLX run used Apple Silicon and a pinned local model. Historical inference
commands contain local model paths that must be provisioned on another machine.
The commands above are the portable route for checking the saved results.

## Historical records and publication-only changes

Original evidence and hash-bound reports are copied byte-for-byte. Their status
statements describe when those records were created. In particular,
`published_to_github=false`, “saved locally” and pre-evaluation status notes in
earlier records are historical; the publication record linked above describes
this later release. They were not rewritten to change the historical record.

Publication-only changes are the README banner, this guide, the development
checkpoint pointer, the public verifier and its tests, publication metadata and
the public ignore rules. None changes the frozen design or scores. The preceding
publication manifest is archived under `public_checkpoint/history/`.

Only the per-machine evaluation-start lock and the local operational publication
record are omitted from the follow-up evidence export. Neither contains trial
results. Credentials, local environments and model weights are also excluded.
Every file in the completed held-out results directory, including every original
source snapshot, is included unchanged.

Earlier checkpoints remain available at commits
`824ec954444e7cc990d09f99cc9062b4874599b2` (amended development study) and
`8beb10e95f852d6a6ee7f0cbd9c08e36f1040019` (preliminary development study).
Use a separate checkout of the relevant commit for its historical public verifier.
