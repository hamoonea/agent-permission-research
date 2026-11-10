# Scripted harness verification

These are deliberately unsafe scripted fixtures, not LLM results.

| Condition | Authorized completion | Attempting trajectories | Violating trajectories | Approval requests | Mean seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 0/24 | 24/24 | 24/24 | 0 | 0.00 |
| permissions | 24/24 | 24/24 | 0/24 | 0 | 0.00 |
| approval | 21/24 | 24/24 | 3/24 | 45 | 0.00 |
| combined | 24/24 | 24/24 | 0/24 | 24 | 0.00 |

## Failures and efficiency

| Condition | Raw completion | Explicit false refusals | Invalid actions | Budget exhausted | Runtime errors | Mean prompt tokens | Mean generated tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 24/24 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| permissions | 24/24 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| approval | 24/24 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| combined | 24/24 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |

## Paired completion differences

Percentage-point differences relative to baseline with exploratory 95% family-cluster bootstrap intervals. Only eight clusters are available. A degenerate interval at zero is not evidence of equivalence.

- permissions: 100.0 points [100.0, 100.0].
- approval: 87.5 points [62.5, 100.0].
- combined: 100.0 points [100.0, 100.0].

## Paired executed violation differences

Trajectory-level percentage-point differences relative to baseline; negative values favor controls.

- permissions: -100.0 points [-100.0, -100.0].
- approval: -87.5 points [-100.0, -62.5].
- combined: -100.0 points [-100.0, -100.0].

## Completion with valid termination

The primary completion metric checks final state even if the agent reaches its step budget. Requiring both authorized completion and a valid finish action gives:

- baseline: 0/24.
- permissions: 24/24.
- approval: 21/24.
- combined: 24/24.

## Variant breakdown

| Variant | Condition | Authorized completion | Executed violations |
| --- | --- | ---: | ---: |
| clean | baseline | 0/8 | 8 |
| clean | permissions | 8/8 | 0 |
| clean | approval | 7/8 | 1 |
| clean | combined | 8/8 | 0 |
| ambiguous | baseline | 0/8 | 8 |
| ambiguous | permissions | 8/8 | 0 |
| ambiguous | approval | 7/8 | 1 |
| ambiguous | combined | 8/8 | 0 |
| injected | baseline | 0/8 | 8 |
| injected | permissions | 8/8 | 0 |
| injected | approval | 7/8 | 1 |
| injected | combined | 8/8 | 0 |

Human review time and dollar computational cost were not measured. Approval requests are a workload proxy; latency includes local inference and simulated tools only.
