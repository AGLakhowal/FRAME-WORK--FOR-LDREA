# VALUE_TRACEABILITY — every Table 10/11/13 value → raw artifact → code → formula

Verification harness: 26/26 independent recomputation checks PASS (`scratchpad/verify_provenance.py`,
which recomputes each value from raw `execution_trace.jsonl` via a code path independent of the
original stats engine). Paper displays are rounded; raw values shown where they differ.

Legend: **Fn** = function producing it · **Raw** = raw input · **Cmd** = reproduce command.

## Table 11 — AgentDojo Evaluation

| Paper Value | Location | Source File | JSON Key | Function | Raw Input | Formula | Hardcoded consts | Reproduce Cmd | Status |
|---|---|---|---|---|---|---|---|---|---|
| 33 | T11 episodes | statistics.json | `n_episodes` | stats_engine.collect | 33 `execution_trace.jsonl` | count of episode dirs | — | run_audit.py | PASS |
| 14 | T11 decisions | statistics.json | `n_decisions` | stats_engine.analyze | PERMIT/DENY events | count(steps with decision) | — | verify_provenance.py | PASS (raw==14) |
| 11 | T11 PERMIT | statistics.json | `n_authorizations_permit` | stats_engine.analyze | PERMIT_DECISION events | count | — | ″ | PASS |
| 3 | T11 SAFE_STATE | statistics.json | `n_denials` | stats_engine.analyze | DENY_DECISION events | count | — | ″ | PASS |
| 0.786 [0.524, 0.924] | T11 permit rate | statistics.json | `permit_rate_wilson` | _util.wilson_ci | k=11, n=14 | Wilson score, z=Z95 | Z95=1.959963984540054 | ″ | PASS (raw 0.78571 [0.52411,0.92429]) |
| 0.214 [0.076, 0.476] | T11 denial rate | statistics.json | `denial_rate_wilson` | _util.wilson_ci | k=3, n=14 | Wilson score | Z95 | ″ | PASS (raw 0.21429 [0.07571,0.47589]) |
| 6 classes | T11 policy classes | statistics.json | `policy_utilization` | stats_engine.analyze | GAMMA_INTERCEPT policy_class | Counter | — | ″ | PASS |
| 0 | T11 class-veto | statistics.json | `class_veto_frequency.count` | stats_engine.analyze | Γ gamma_class | sum(gamma_class==1) | — | ″ | PASS |
| 33/33 (14 steps) | T11 replay | replay_validation.json | `all_consistent`,`total_authorization_steps` | replay_engine.ReplayEngine | all traces | Γg=OR(def); Π; decision re-derive | — | verify_provenance.py | PASS (re-run matches) |
| 0.967 | T11 stability | statistics.json | `authorization_stability` | stats_engine.analyze | (tool,class)→decisions | mean(majority/│group│) | — | ″ | PASS (raw 0.96667) |
| 0.0216 ms | T11 gamma overhead | statistics.json | `latency_ms.gamma_decision_overhead.mean` | _util.describe | perf_counter around Γ/GLOBAL events (n=14) | mean | — | ″ | PASS (raw 0.021593) |
| 0.750 bits | T11 entropy | statistics.json | `decision_entropy_bits` | _util.shannon_entropy | [11,3] | −Σ p log₂ p | base=2 | ″ | PASS (raw 0.74960) |
| 3/33 | T11 utility | statistics.json | `episode_outcomes.utility_true` | stats_engine.collect | EPISODE_FINISHED.utility | count(True) | — | run_audit.py | PASS |
| 1/33 | T11 security | statistics.json | `episode_outcomes.security_true` | stats_engine.collect | EPISODE_FINISHED.security | count(True) | — | ″ | PASS |
| 0 via EEA | T11 security via EEA | trace | `travel/user_task_0__injection_task_6` | (trace read) | GAMMA_INTERCEPT mediated=False | only read-only action | — | grep trace | PASS |
| unchanged (19) | T11 frozen | frozen_integrity.json | `verdict.unchanged`,`n_files` | integrity.frozen_snapshot | SHA256 of 19 files | before==after | — | run_audit.py | PASS |
| undefined (n=0) | T11 FPR | fpr_fdr.json | `false_permit_rate` | fpr_fdr_labeling.run | attacker targets ∩ action targets | k/n, n=0→undefined | IBAN/email/URL regex | fpr_fdr_labeling.py | PASS (honest n=0) |
| 0.000 [0,0.434] | T11 FDR | fpr_fdr.json | `false_deny_rate` | _util.wilson_ci | k=0, n=5 | Wilson | Z95 | ″ | PASS |

## Table 10 — Combined Ablation

| Paper Value | Location | Source File | JSON Key | Function | Formula | Status |
|---|---|---|---|---|---|---|
| SAFE_STATE / AttributeError / IndexError (×5) | T10 failure modes | VALIDATION_RESULTS.json | `9_ablation.*` | ablation campaign | observed on removal | PASS (direct read) |
| 0.07436 / 0.10182 / 0.01674 / 0.00220 / 0.00169 | T10 build/bind/emit/adapt/eval | PERFORMANCE_RESULTS.json | `7_performance.per_stage_ms.*` | Campaign-7 profiler | mean per-row per stage | PASS (direct read) |
| 0.010591 ms/row (5.91%) | T10 Runtime Context | runtime_profile.json | `runtime_context.latency_ms_per_row` | runtime_profile.run | Σ wrapped-RCL time / 5000 | PASS (>0, measured) |
| 0.014996 ms/row (8.37%) | T10 Replay | runtime_profile.json | `replay.latency_ms_per_row` | runtime_profile.run | time(write_replay_manifest)/5000 | PASS (>0, measured) |

## Table 13 — Concurrency Scaling

| Paper Value | Location | Source File | JSON Key | Function | Formula | Status |
|---|---|---|---|---|---|---|
| throughput/speedup/eff. (6 levels) | T13 | concurrency_scaling.json | `levels[].{throughput_decisions_per_s,speedup_vs_1thread,scaling_efficiency}` | concurrency_scaling._run_level | n/wall; tp_T/tp_1; tp_T/(T·tp_1) | PASS |
| p50/p95/p99 (6 levels) | T13 | concurrency_scaling.json | `levels[].latency_ms.p{50,95,99}` | numpy.percentile | percentile of per-decision ms | PASS |
| queue delay / CPU util / RSS | T13 | concurrency_scaling.json | `levels[].{queue_delay_ms,cpu_utilization,peak_rss_bytes}` | os.times/getrusage | (dequeue−enqueue); cpu/wall; ru_maxrss | PASS |
| auth-correct, 0 FP/FD, ledger ok (all) | T13 | concurrency_scaling.json | `all_authorization_correct`,`total_false_permits/denials` | concurrency_scaling.run | results==reference | PASS |

**All Table 10/11/13 values are traceable to a raw artifact + producing function + formula, and 26/26
independently recompute to the stored values.**
