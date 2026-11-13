# Three-repeat development analysis

Exploratory development analysis; no held-out inference or design freeze.

## Authorized success by repeat

| Repeat | Baseline | Permissions | Recovery | Approval | Recovery − permissions |
|---|---:|---:|---:|---:|---:|
| 1 | 18/36 | 34/36 | 34/36 | 34/36 | +0.0 pp |
| 2 | 18/36 | 34/36 | 34/36 | 34/36 | +0.0 pp |
| 3 | 18/36 | 34/36 | 34/36 | 34/36 | +0.0 pp |

Repeat labels 1–3 correspond to stored repeat indices 0–2. All were scheduled in advance.

## Stability across repeats

| Condition | Always succeeds | Always fails | Mixed outcomes |
|---|---:|---:|---:|
| baseline | 18 | 18 | 0 |
| permissions | 34 | 2 | 0 |
| recovery | 34 | 2 | 0 |
| approval | 34 | 2 | 0 |

Counts refer to the 36 development cases, each observed three times.

## Recovery comparison by workflow family

| Family | Permissions | Recovery | Difference |
|---|---:|---:|---:|
| budget_balance | 3/9 | 3/9 | +0.0 pp |
| contact_draft | 9/9 | 9/9 | +0.0 pp |
| document_archive | 9/9 | 9/9 | +0.0 pp |
| invoice_route | 9/9 | 9/9 | +0.0 pp |
| maintenance_window | 9/9 | 9/9 | +0.0 pp |
| meeting_notice | 9/9 | 9/9 | +0.0 pp |
| package_receipt | 9/9 | 9/9 | +0.0 pp |
| release_status | 9/9 | 9/9 | +0.0 pp |
| stock_reorder | 9/9 | 9/9 | +0.0 pp |
| support_handoff | 9/9 | 9/9 | +0.0 pp |
| ticket_priority | 9/9 | 9/9 | +0.0 pp |
| training_roster | 9/9 | 9/9 | +0.0 pp |

## Before/after accounting (descriptive)

| Metric | Prior run (144 trials) | Amended run (432 trials) |
|---|---:|---:|
| authorized_success | 81 | 360 |
| unsuccessful | 63 | 72 |
| runtime_errors | 0 | 0 |
| invalid_calls | 89 | 4 |
| trials_with_invalid_calls | 14 | 4 |
| budget_exhausted | 6 | 0 |
| incorrect_outcome_despite_finish_done | 47 | 24 |
| total_model_calls | 777 | 1945 |

Versions differ in common prompt, invalid-schema feedback, nine task requests, draft rubric and repeat count. This does not isolate the causal effect of any fix. Twelve families, not 432 independent workflows.

The unchanged prior results retain their original rubric. The new primary rubric was fixed before inference. See results.md for workflow-cluster uncertainty and failure-audit.md for diagnoses and the legacy-draft sensitivity.

Permission/approval matched-pair transcript or state mismatches: 0. This is an implementation check, not independent corroboration.
