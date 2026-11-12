# Development checkpoint — November 12, 2026

This branch preserves preliminary development work before the recommended design
amendments. It is not a frozen design, preregistration, or final held-out result.
The original 144 development trajectories, scores, run configuration, model hashes,
failure audit, and negative recovery finding are published without alteration.
The original pilot on main remains unchanged by this branch.

## Included

- The development dataset: 12 workflow families, 36 cases.
- Environment, scoring, runner, analyzer, freeze guard, and audit implementation.
- All 144 genuine development trajectories plus the earlier smoke evidence, with
  failures retained. Overlapping smoke trials are not independent observations.
- Protocol, failure review, reviewer checklist, and completion schedule.
- Development-only diagnostic tests and a public evidence verifier.

## Withheld until evaluation is complete

The reserved dataset and its original generator contain the held-out cases.
They are omitted from the public tree and every source snapshot. The dataset
manifest keeps only held-out counts and its SHA-256 commitment. The original
generator's SHA-256 remains in the unmodified run configuration.

`followup/tasks.py` in this public branch is an explicitly labeled path shim. It
does not contain cases, build a dataset, or match the original generator hash.
All original local experiment files remain unchanged. The publication manifest
records the omissions and presentation adaptations. No held-out inference or
design freeze was performed for publication.

## Verify the published development evidence

From the repository root, with Python 3.10 or later:

```sh
python3 -B -m public_checkpoint.verify
python3 -B -m unittest public_checkpoint.test_verify study_analysis.test_development_audit -v
python3 -B -m unittest discover -s tests -v
```

The public verifier hashes the eight available original source/data/protocol
inputs and their snapshots, replays all 144 event histories, checks states,
transcripts and scores, and reproduces the per-trajectory failure diagnoses. It
explicitly reports that the two withheld input hashes cannot be independently
verified from this checkout. It never runs a model or opens reserved cases.

The full private-fixture test module is intentionally skipped in a public checkout;
the original pilot tests and the ten public replay/diagnostic tests are runnable.
Earlier counts such as 30 tests and 864 scripted checks describe the original
private workspace, not the smaller public test surface.

The unchanged full-input commands (`followup.run`, `followup.analyze`,
`followup.freeze`, and the diagnostic audit CLI) require the original private
generator and reserved dataset. They are preserved for source review and later
reproduction; do not present them as runnable from this incomplete public export.
Use `public_checkpoint.verify` for the development evidence now. Replaying saved
evidence checks software consistency, not independent model reproducibility.

## Findings and next decisions

Authorized success was 12/36 for instructions only, 24/36 for basic permissions,
21/36 for recovery guidance, and 24/36 for perfect simulated approval. The gate
prevented covered scope violations, but this does not establish production safety.
The exploratory recovery result is negative and remains visible.

Before freezing, clarify common tool instructions, resolve the harmless-draft
scoring ambiguity, clarify development task wording, and rerun the amended design
with prespecified sampled repeats. Seek actual external feedback and accurately
disclose AI assistance. See the [full review](followup-full-development-review.md).

Publishing this checkpoint does not implement those research amendments or permit
inspection of reserved cases for tuning. The held-out dataset remains unchanged.
