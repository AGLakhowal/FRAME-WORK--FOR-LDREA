# TABLE_VERIFICATION

Independent recomputation of every table cell (`verify_provenance.py`, 26/26 PASS). Rounding shown
where paper display ≠ raw.

## Table 10 — Combined Ablation
| Row | Column | Value | Source | Calculation | Verified |
|---|---|---|---|---|---|
| Runtime Context | failure | SAFE_STATE | VALIDATION_RESULTS.json `9_ablation.without_runtime_context.decision` | observed on removal | PASS |
| Evidence Bundle | failure | AttributeError | `9_ablation.without_evidence_bundle.error` | observed | PASS |
| Predicate Binding | failure | IndexError | `9_ablation.without_predicate_binding.error` | observed | PASS |
| Replay | failure | no manifest | `9_ablation.without_replay.consequence` | observed | PASS |
| Emitter | failure | no artifact | `9_ablation.without_emitter.consequence` | observed | PASS |
| Evidence Bundle | latency | 0.07436 | PERFORMANCE_RESULTS.json `per_stage_ms.build` | Campaign-7 mean/row | PASS |
| Predicate Binding | latency | 0.10182 | `per_stage_ms.bind` | mean/row | PASS |
| Emitter | latency | 0.01674 | `per_stage_ms.emit` | mean/row | PASS |
| Adapter/eval (ref) | latency | 0.00220 / 0.00169 | `per_stage_ms.adapt/eval` | mean/row | PASS |
| Runtime Context | latency | 0.010591 | runtime_profile.json `runtime_context.latency_ms_per_row` | Σ RCL-timer / 5000 | PASS (measured>0) |
| Replay | latency | 0.014996 | runtime_profile.json `replay.latency_ms_per_row` | time(write_replay_manifest)/5000 | PASS (measured>0) |

## Table 11 — AgentDojo Evaluation
| Cell | Value (paper) | Raw | Source key | Verified |
|---|---|---|---|---|
| episodes | 33 | 33 | `n_episodes` | PASS |
| decisions | 14 | 14 | `n_decisions` | PASS (raw count) |
| PERMIT | 11 | 11 | `n_authorizations_permit` | PASS |
| SAFE_STATE | 3 | 3 | `n_denials` | PASS |
| permit rate | 0.786 [0.524,0.924] | 0.78571 [0.52411,0.92429] | `permit_rate_wilson` | PASS |
| denial rate | 0.214 [0.076,0.476] | 0.21429 [0.07571,0.47589] | `denial_rate_wilson` | PASS |
| classes | 6 | 6 | `policy_utilization` | PASS |
| class-veto | 0 | 0 | `class_veto_frequency.count` | PASS |
| replay | 33/33, 14 steps | 33/33, 14 | `replay_validation.json` | PASS (re-run) |
| stability | 0.967 | 0.96667 | `authorization_stability` | PASS |
| gamma overhead | 0.0216 ms | 0.021593 | `gamma_decision_overhead.mean` | PASS |
| entropy | 0.750 bits | 0.74960 | `decision_entropy_bits` | PASS |
| utility | 3/33 | 3 | `episode_outcomes.utility_true` | PASS |
| security | 1/33 | 1 | `episode_outcomes.security_true` | PASS |
| security via EEA | 0 | 0 | trace (read-only action only) | PASS |
| frozen | unchanged (19) | True, 19 | `frozen_integrity.unchanged` | PASS |
| FPR | undefined (n=0) | n=0 | `false_permit_rate` | PASS (honest) |
| FDR | 0.000 [0,0.434] | 0.0 [0,0.43448] | `false_deny_rate` | PASS |

## Table 13 — Concurrency Scaling
All 6 rows × 14 columns read from `concurrency_scaling.json` `levels[]`. Cross-checks:
`all_authorization_correct=True`, `total_false_permits=0`, `total_false_denials=0`,
`all_ledger_consistent=True` — **PASS**. Dependencies: frozen `GammaBridge.decide`/`evaluate_decision`.

## Dependencies per table
- T10 ← VALIDATION_RESULTS.json (9_ablation) + PERFORMANCE_RESULTS.json (per_stage_ms) + runtime_profile.json
- T11 ← statistics.json + replay_validation.json + frozen_integrity.json + fpr_fdr.json ← 33 execution_trace.jsonl
- T13 ← concurrency_scaling.json ← frozen decision engine

**TABLE VERIFICATION: PASS (all rows/columns recompute to stored).**
