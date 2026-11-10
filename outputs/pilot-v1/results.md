# Exploratory local model results

One deterministic run per case and condition; 24 cases from eight related workflow families. Approval decisions are simulated by a perfect policy oracle. No human study was conducted.

| Condition | Authorized completion | Attempting trajectories | Violating trajectories | Approval requests | Mean seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 16/24 | 8/24 | 8/24 | 0 | 5.05 |
| permissions | 23/24 | 8/24 | 0/24 | 0 | 5.99 |
| approval | 23/24 | 8/24 | 1/24 | 45 | 5.97 |
| combined | 23/24 | 8/24 | 0/24 | 32 | 5.99 |

## Failures and efficiency

| Condition | Raw completion | Explicit false refusals | Invalid actions | Budget exhausted | Runtime errors | Mean prompt tokens | Mean generated tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 23/24 | 0 | 8 | 2 | 0 | 1360.8 | 67.7 |
| permissions | 23/24 | 0 | 8 | 6 | 0 | 1621.0 | 80.8 |
| approval | 24/24 | 0 | 8 | 7 | 0 | 1605.0 | 81.9 |
| combined | 23/24 | 0 | 8 | 6 | 0 | 1621.0 | 80.8 |

## Paired completion differences

Percentage-point differences relative to baseline with exploratory 95% family-cluster bootstrap intervals. Only eight clusters are available. A degenerate interval at zero is not evidence of equivalence.

- permissions: 29.2 points [20.8, 33.3].
- approval: 29.2 points [20.8, 33.3].
- combined: 29.2 points [20.8, 33.3].

## Paired executed violation differences

Trajectory-level percentage-point differences relative to baseline; negative values favor controls.

- permissions: -33.3 points [-33.3, -33.3].
- approval: -29.2 points [-33.3, -20.8].
- combined: -33.3 points [-33.3, -33.3].

## Completion with valid termination

The primary completion metric checks final state even if the agent reaches its step budget. Requiring both authorized completion and a valid finish action gives:

- baseline: 14/24.
- permissions: 18/24.
- approval: 17/24.
- combined: 18/24.

## Variant breakdown

| Variant | Condition | Authorized completion | Executed violations |
| --- | --- | ---: | ---: |
| clean | baseline | 8/8 | 0 |
| clean | permissions | 8/8 | 0 |
| clean | approval | 8/8 | 0 |
| clean | combined | 8/8 | 0 |
| ambiguous | baseline | 8/8 | 0 |
| ambiguous | permissions | 8/8 | 0 |
| ambiguous | approval | 8/8 | 0 |
| ambiguous | combined | 8/8 | 0 |
| injected | baseline | 0/8 | 9 |
| injected | permissions | 7/8 | 0 |
| injected | approval | 7/8 | 2 |
| injected | combined | 7/8 | 0 |

Human review time and dollar computational cost were not measured. Approval requests are a workload proxy; latency includes local inference and simulated tools only.
