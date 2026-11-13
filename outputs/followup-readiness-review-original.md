# Freeze readiness review — November 13, 2026

**Recommendation: retain the scientific design, but close two verification gaps
and clarify the evidence-access claim before the final freeze.** These findings
do not invalidate the completed development results. They concern prospective
reproducibility and how strongly the implementation supports the written claims.
No freeze was created and no held-out inference was performed in this review.

The checkpoint reviewed is the amended 432-trial study published at commit
`824ec954444e7cc990d09f99cc9062b4874599b2`. This review is a local follow-up to
that publication. It does not change the original run, scores, or source snapshot.

## Findings to address before freezing

### 1. Freeze validation does not enforce the runtime environment

`followup/freeze.py` records source/data/protocol hashes, model-file hashes and
sampling parameters, but not the runtime versions or dependency-lock digest.
`followup/evidence.py:validate_freeze` checks only inputs and model identity.
The runner records three package versions in each run configuration and checks
them on resume, but a first held-out run can start with different versions from
development without being rejected by the freeze guard.

**Evidence:** inspection of the freeze creation and validation paths; a disposable
validation check confirmed that a package-version field is ignored. The current
environment itself is consistent: all 12 model files match development, the
recorded MLX/MLX-LM/Transformers versions match, and every entry in
`requirements-mlx-lock.txt` matches the installed environment.

**Recommended closure:** bind the actual inference environment to the prospective
freeze and check it before model loading. Record the Python version, dependency
lock digest and installed versions, including tokenizer/template and inference
dependencies. Reject drift with an actionable error. Use the existing environment;
an upgrade or new model is unnecessary. This is an additional safeguard, not a
claim that dependencies have already changed.

### 2. Private replay does not validate the recorded sampling seed

`followup/evidence.py:replay` validates assignments, events, transcripts, states,
scores and token totals, but not `rng_seed`. In a disposable copy of the development
records, changing the first trajectory's seed metadata still passed this replay.
The published development-only verifier already checks derived seeds; the private
freeze/resume/analysis path should have the same protection.

**Evidence:** all 432 original seed values independently match
`trajectory_seed(config.seed, task_id, repeat)`. The counterexample was confined
to a temporary copy; original evidence was not edited.

**Recommended closure:** verify the derived seed for each record and add a test
that altered seed metadata is rejected. Seed metadata checks establish internal
consistency; they do not independently prove which random state a model used.

### 3. Clarify evidence access without changing the primary rubric

The primary metric explicitly requires a read from the task's
`required_evidence_any` list, which is source/backup for the development budget
task. It does not enforce every read in the reference plan. A development-only
counterexample with the correct update and message, but no ledger read, receives
authorized success. Thus the score verifies the specified outcome and source
access, not complete evidence gathering or faithful reasoning.

**Recommended closure:** use “omitted ledger lookup” as a trace diagnosis; do not
claim that missing the ledger is independently rejected by the scorer. The actual
budget failures also have incorrect outputs and remain failures. Keep the current
outcome-focused rubric and disclose this limitation. Requiring every supporting
read would be a substantive new scoring choice and would need a documented
development amendment, rather than being slipped into freeze preparation.

## External review status

The user confirms that the amended 432-trial study was reviewed with no requested
changes. This resolves the pending review-status question. The reply did not name
the reviewer or provide a review date, so this record does not assign those details
or attribute the review specifically to Dr. Sabrina Navid Chaudry.

The checklist remains an uncompleted template; individual items are not marked
as signed off based on the overall report. No additional human review is being
required here. The two verification findings above still need closure, and the
evidence-access limitation should be accurately described before freezing.

## Checks completed

- All 432 original development records passed private action/event, transcript,
  state and score replay; every original derived seed was checked separately.
- The current ten source/data/protocol input hashes match the recorded run, and
  all ten private input snapshots match their commitments.
- Nineteen amendment, diagnostic and repeat-analysis tests passed.
- Six existing freeze, resume, interruption and replay tests passed with their
  fixture setup restricted to development tasks; no full fixture generation ran.
- Three additional negative entry checks rejected missing freeze/explicit flag
  combinations before task loading or model construction.
- All 12 local model files match development. Runtime: Python 3.13.2,
  MLX 0.32.4, MLX-LM 0.32.2, Transformers 5.22.2; the full lock has no mismatches.
- Zero development runtime errors, turn-limit failures or generation-token-limit
  finishes; at most seven calls per trajectory against a twelve-turn budget.
- No held-out run configuration or freeze file was present in the study outputs.
- The reserved dataset's byte hash remains
  `2730b1b7237af2670dd30e8e41af2d0685cb5565698f92bdf56e39d4493c9e91`.
  Only integrity hashing/private snapshots touched those bytes; reserved cases
  were not parsed, regenerated, displayed, or used for inference during review.

## Design choices to retain

Keep one pinned Qwen3-4B model, four conditions, three repeats, temperature 0.2,
base seed 20261111, twelve turns and 256 output tokens per turn. Keep authorized
success as the primary outcome, recovery minus permissions as the primary
comparison, and workflow family as the uncertainty unit. The reserved experiment
will have 432 trajectories but only twelve workflow families, not 432 independent
workflows.

Retain the 18 unsuccessful gated trials and the null recovery result. The correct
budget answer is available through the development catalog; repeated omission
and unsupported answers do not justify tuning an answer-specific hint into the
shared prompt. No new condition, second model or larger budget is justified by
this review. The policy-feedback length confound, static revocation, perfect
approval oracle, exact-format rubric, small authored task set and lack of an
equivalence claim remain explicit limitations.

## Completing freeze preparation

Close the validation findings with focused development-only checks. Preserve the
published run and its input commitments. The existing private replay requires
the current inputs to exactly match the run: changing a hashed source file will
cause it to refuse the old evidence. Do not repair that by rewriting old hashes
or disabling drift checks. Either add a separately recorded preflight safeguard,
or explicitly validate the original evidence against its archived implementation
and record any infrastructure-only transition in the new freeze workflow.

Purely additive validation does not justify rerunning model trials to obtain new
scores. Any change to model-visible instructions, tool behavior, scoring or tasks
does require a documented development revision before freezing.

Then record the exact model/environment, all settings, development evidence,
review status and rationale in the prospective freeze. Before evaluation, verify
that record and use one assigned output directory; interrupted work resumes there
and retains failed trials. Do not inspect interim held-out scores to tune the
design. A defect discovered after inference must preserve the original evaluation
and be reported as an amendment.
