# Experiment 6 — Runtime Profiling

Status: **EXECUTED** · 2.12s

## Frozen-path planes (synthetic 5,000-row workload)
- Runtime Context (RCL) plane: 0.02691 ms/row (6.47% of end-to-end)
- Replay plane: 0.02033 ms/row (4.89% of end-to-end)
- Full pipeline: 0.39550 ms/row
- End-to-end incl. replay: 0.41583 ms/row

## Per-stage distributions (recorded AgentDojo traces)
| stage | n | mean ms | median ms | p95 ms | p99 ms | std ms |
|--|--:|--:|--:|--:|--:|--:|
| predicate_evaluation | 108 | 0.0085 | 0.0084 | 0.0125 | 0.0169 | 0.0045 |
| gamma_intercept | 42 | 0.0135 | 0.0052 | 0.0113 | 0.1472 | 0.0247 |
| gamma_computation | 14 | 0.0216 | 0.0172 | 0.0279 | 0.0587 | 0.0144 |
| authorization_actuation | 42 | 0.4474 | 0.1945 | 0.4298 | 4.8342 | 0.8173 |

Reproduce: `./.venv/bin/python -c "from agentdojo_integration.audit import runtime_profile as r; r.run('experiments/profiling', 5000)"`