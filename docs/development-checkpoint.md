# Amended development checkpoint — November 13, 2026

This branch publishes the recommended amendments and all 432 genuine development
trajectories: 36 cases × four conditions × three prespecified repeats. It is not a
frozen design, preregistration, or final held-out result. The earlier 144-trial
study and its negative recovery finding remain unaltered. The original pilot on
main remains unchanged by this branch.

## Included

- The development dataset: 12 workflow families, 36 cases.
- Amended common tool instructions, schema feedback, development task wording,
  and harmless-intermediate-draft scoring, specified before the new inference.
- All 432 trajectories, configuration, source commitments, summaries, failure
  analysis, repeat stability review, and limitations.
- Earlier development and smoke evidence, retained without modification.
- Development tests and a verifier that works with this public export.

## Withheld until evaluation is complete

The reserved dataset, its original generator, and all copies of both are omitted.
The earlier private dataset manifest is also omitted from the amendment archive
because it identifies reserved families. The public dataset manifest keeps only
reserved counts and the SHA-256 commitment. The unmodified model-run configuration
retains the original generator hash.

`followup/tasks.py` in this branch is an explicitly labeled path shim. It contains
no cases and cannot generate a dataset. Its bytes do not match the original
generator commitment. The publication manifest records these omissions and
presentation adaptations. No held-out inference or design freeze was performed.
The copied amendment boundary record describes analysis completion before
publication; its `new_results_pushed_to_github=false` field is historical.

## Verify the published development evidence

From the repository root, with Python 3.10 or later:

```sh
python3 -B -m public_checkpoint.verify
python3 -B -m unittest public_checkpoint.test_verify study_analysis.test_development_audit study_analysis.test_repeated_development_review -v
python3 -B -m unittest discover -s tests -v
```

The verifier hashes the eight available original source/data/protocol inputs and
their snapshots, replays all 432 event histories, checks assignments, seeds,
transcripts, states and scores, and reproduces per-trajectory diagnoses, condition
and variant summaries, paired comparisons, and repeat stability/accounting.
The two withheld input hashes are commitments that cannot be independently
verified from this checkout. The verifier never runs a model or opens reserved cases.

The full private-fixture test module and two amendment tests that need the private
generator or complete private input set are deliberately skipped. All other public
tests run normally. Historical private-workspace test counts describe a different
test surface.

The unchanged full-input commands (`followup.run`, `followup.analyze`,
`followup.freeze`, and the diagnostic/repeat-review CLIs) require private inputs.
They remain available for source review and later reproduction; use the public
verifier for this incomplete export. Replay establishes software consistency,
not independent model reproducibility.

To verify the earlier 144-trial checkpoint, use a separate checkout of commit
`8beb10e95f852d6a6ee7f0cbd9c08e36f1040019` and its public verifier. The current
implementation and verifier target the amended study, not the earlier rubric.

## Findings and next decisions

Authorized success is 54/108 for instructions only and 102/108 for each gated arm.
All three repeats have the same per-case success outcomes. Recovery guidance adds
no observed benefit over basic permissions; this null result does not establish
equivalence. The remaining gated failures concern budget reasoning and required
ledger evidence. Zero covered violations in the gated arms does not establish
production safety.

The [amended development review](followup-amended-development-review.md) explains
the failures, the descriptive before/after comparison, and the recommendation for
focused external review before freezing. Publishing this checkpoint does not
freeze the design or authorize tuning on reserved cases. The held-out dataset is
unchanged and unevaluated.
