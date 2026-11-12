# Development validation log — November 11, 2026

## Implemented and checked

- 72 synthetic cases in 24 workflow families; 12 development / 12 held-out.
- 30 automated tests passed, including the 12 original pilot tests.
- 864 software-only trajectories passed runner, analysis and replay checks:
  both splits, all four conditions, reference/attack/recovery fixtures.
  These temporary scripted runs were discarded after verification; they are not
  model findings. The automated suite retains the corresponding feasibility,
  attack, recovery, scoring, resume, freeze and evidence-integrity tests.
- Original v1 code and results remain separate from followup/.

## Initial model check and amendment

`outputs/followup-smoke-v1` was stopped after four completed development
trajectories, with a fifth interrupted. The small model sometimes emitted bare
finish objects without the tool envelope. The generic system prompt was amended
to show valid read and finish JSON examples. No task answer was added.

During code review, task correctness was also strengthened to reject unsolicited
or duplicate messages even to permitted destinations. Graceful interruption now
records the interrupted trajectory as a failure before stopping. Source snapshots
and library versions are retained for subsequent runs.

The incomplete first run and its exact source snapshot are preserved, with no
aggregate research claim. This was development, not held-out selection.

## Completed development smoke test

`outputs/followup-smoke-v2` contains 24 genuine local-model trajectories:
two development workflow families x three variants x four conditions, one sampled
repeat at temperature 0.2. Model files match the recorded local Qwen3 4B identity.
Twelve turns and 256 tokens per turn were the budgets. Two task-free warmups were
performed. All trajectories passed replay; there were zero runtime errors,
invalid action schemas, or budget exhaustions. All 24 produced valid finish(done),
which does not mean all tasks were correctly completed.

| Condition | Correct raw outcome | Authorized success | Trajectories with executed violations |
|---|---:|---:|---:|
| Baseline | 3/6 | 1/6 | 4/6 |
| Permissions | 3/6 | 3/6 | 0/6 |
| Recovery guidance | 1/6 | 1/6 | 0/6 |
| Perfect simulated approval | 3/6 | 3/6 | 0/6 |

Recovery guidance did not improve success in this tiny development sample. Do not
present these six cases as six independent workflows: there are only two families.
The generic analyzer emits exploratory intervals; intervals with only two families
are not suitable evidence for a substantive treatment claim. The sample verifies
execution and exposes failure modes, not the study's hypothesis.

Observed development failures include incorrect priority classification, changing
a correct field value to an incorrect one, finishing before an update, and joining
two permitted email addresses into one disallowed recipient string. Permissions
and ideal approval produced matching prompt/action paths, as expected from equal
coverage and identical feedback. This is a useful implementation check.

## Decisions identified after the smoke test (historical)

1. Review the task wording and scoring with the applicant and an external reviewer.
   In particular, check whether partial-functionality outages in ticket triage
   are sufficiently unambiguous. Do not simplify cases merely to increase success.
2. Run all 12 development families (144 trajectories at one repeat). Preserve the
   current results and record any justified prompt/budget/task amendments.
3. Decide whether the default model is adequate and whether a second model is
   feasible, using development evidence only.
4. Freeze the final design, then run the reserved evaluation as described in the
   runbook. No held-out model inference or prospective freeze has occurred yet.

These implementation changes were prepared with Codex assistance. The applicant
should personally review the experiment, reproduce key results, discuss the
limitations, and accurately document their intellectual contributions. No external
review, recommendation, publication, or GitHub push was performed in this work.

## Full development run completed — November 11, 2026

The requested full run is saved in `outputs/followup-dev-v1`: all 144 trajectories,
12 families, three variants, four conditions, one sampled repeat. No run settings,
inference code, datasets or primary scoring changed. Zero runtime exceptions;
all records passed replay. Authorized success: baseline 12/36, permissions 24/36,
recovery 21/36, approval 24/36. There were 89 invalid tool calls across 14 trials,
with six turn-limit failures. These model behavior failures remain included.

The new development-only diagnostic audit and six tests are in `study_analysis/`.
The original primary scores are not replaced by the post-hoc sensitivity analysis.
Ignoring harmless intermediate drafts on send tasks adds one success per condition
and leaves the recovery/permissions gap unchanged. Tool-schema errors, draft-only
notifications, ambiguous partial-outage wording, and skipped lookups are documented
in [the full pre-freeze review](followup-full-development-review.md).

The held-out SHA-256 is unchanged; no held-out model run or design freeze occurred.
Next: agree on the justified contract/rubric amendments, rerun development under
the final common interface, examine sampled repeats, and seek actual reviewer
feedback before freezing. Do not tune the treatment to obtain a positive result.
