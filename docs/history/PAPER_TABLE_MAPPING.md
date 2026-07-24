# PAPER_TABLE_MAPPING.md

**Step 2 — every paper table mapped to metric · formula · experiment · source log/JSON/CSV · code.**
No value in any table is manually editable: `paper_table_generator.py` reads the source JSON (produced
by the experiment from raw logs) and re-derives via `metrics_engine.py`. Regenerate with
`python reproduce_paper.py`.

Legend: **Exp** = `experiment_registry.py` name · **Fn** = `metrics_engine.py` function.

---

## Table — LAB v1.0 Primary Metrics
Exp: `lab_v1_base` → `gamma_test_runner.py` on `GAMMA_G0_CREDITCARD_FULL_mapped.csv`.
Source JSON: `gamma_lab_v1_report.json:primary_metrics`. Generated: `paper_tables/table_lab_primary_metrics.{md,csv}`.

| Metric | Formula | Fn | Source key |
|---|---|---|---|
| False Permit Rate | permits_of_should_deny / N_should_deny | `compute_false_permit_rate` | `false_permit_rate.{adverse_events,n}` |
| False Denial Rate | denies_of_should_permit / N_should_permit | `compute_false_deny_rate` | `false_denial_rate.*` |
| UER | unauth_execs / N_all | `compute_zero_event_upper_bound` (0-event UB) | `unauthorized_execution.count` |
| Replay Determinism | 1 − broken_links/N | `compute_replay_rate` | `replay_determinism_rate.*` |
| Class-Veto Effectiveness | held_in_SAFE / N_class1 | `compute_class_veto_rate` | `class_veto_effectiveness.*` |
| Wilson95 upper (cc) | cluster-corrected Wilson, N_eff=N/DE | (`_util.wilson_ci` + DE) | `*.wilson95_clustercorrected_upper` |

## Table — Runtime Invariants
Exp: `lab_v1_base`. Source: `gamma_lab_v1_report.json:runtime_invariants_violations`. Formula: violation_count per invariant (must=0). Code: direct read + assert 0.

## Table — Measured Latency
Exp: `lab_v1_base`. Source: `gamma_lab_v1_report.json:measured_latency`. `compute_latency` (mean), `compute_p95`/`compute_p99` (nearest-rank), `compute_throughput`.

## Table 10 — Combined Ablation / Per-Stage Latency
Exp: `runtime_profile` (RCL + Replay planes) + Campaign-7 `PERFORMANCE_RESULTS.json:7_performance`.
Source: `runtime_profile.json` + `PERFORMANCE_RESULTS.json`. Fn: `compute_latency`, `compute_runtime_overhead`. Generated: `paper_tables/table_combined_ablation.*`.

## Table 11 — AgentDojo External Evaluation
Exp: `agentdojo_eval` (metrics re-derived from `audit_run/trace/**/execution_trace.jsonl`) + `agentdojo_fpr_fdr`.
Source: `statistics.json`, `replay_validation.json`, `fpr_fdr/fpr_fdr.json`. Generated: `paper_tables/table_agentdojo_evaluation.*`.

| Metric | Formula | Fn | Source key |
|---|---|---|---|
| Permit rate | n_permit / n_decisions | `compute_permit_rate` (Wilson) | `statistics.json:{n_authorizations_permit,n_decisions}` |
| SAFE_STATE rate | n_deny / n_decisions | `compute_safe_state_rate` | `statistics.json:n_denials` |
| Decisions/episode | n_decisions / n_episodes | `compute_gamma_decision_rate` | `statistics.json:{n_decisions,n_episodes}` |
| Overhead (ms) | mean(gamma_decision_overhead) | `compute_runtime_overhead` | `statistics.json:latency_ms.gamma_decision_overhead.mean` |
| Replay consistency | consistent_traces / total | `compute_replay_rate` | `replay_validation.json:n_traces` |
| **False Permit Rate** | malicious_permitted / malicious | `compute_false_permit_rate` | `fpr_fdr.json:counts` → **undefined (n=0)** |
| False Deny Rate | legit_denied / legit | `compute_false_deny_rate` | `fpr_fdr.json:counts` (n=5) |

> FPR is reported **undefined (n=0)** by the engine because `malicious_actions=0` — an honest n=0, not a fabricated 0. This is the load-bearing external-soundness gap flagged in `FINAL_SCIENTIFIC_AUDIT_COMMITTEE_REPORT.md` (B1).

## Table 13 — Concurrency Scaling
Exp: `concurrency_scaling` (frozen path, 200k decisions/level, no LLM).
Source: `concurrency_scaling.json:levels`. Fn: `compute_throughput` (re-derived n/wall), `compute_p95`/`compute_p99`, `compute_queue_delay`. Generated: `paper_tables/table_concurrency_scaling.*`.

| Column | Formula | Source |
|---|---|---|
| throughput | n_decisions / wall_time_s | re-derived + `throughput_decisions_per_s` |
| speedup | tput(t) / tput(1) | `speedup_vs_1thread` |
| scaling eff. | speedup / t | `scaling_efficiency` |
| p50/p95/p99 | percentile(latency) | `latency_ms.*` |
| queue delay | mean(enqueue→service) | `queue_delay_ms.mean` |
| FP / FD | count | `false_permits` / `false_denials` |

## Table — FULL_SPEC Metrics & Verdict
Exp: `full_spec_conformance`. Source: `full_spec_conformance_report.json:{metrics_11_1,full_spec_verdict}`. Direct read (rates computed inside the conformance run).

## Table — Formal State-Space Verification
Exp: `decision_state_space` → `independent_verifier.py`. Source: `independent_verifier_report.json`. Values: `total_states_enumerated`, `coverage_complete`, `total_field_mismatches`, `permit_states`, `verdict`.

---

## Anti-manual-edit guarantee
- `paper_table_generator.py` contains **no numeric metric literal**; every cell is read from JSON or
  recomputed by `metrics_engine`. Grep confirms values enter only via `_load(...)` and `ME.*`.
- Each re-derived cell is cross-checked against its stored artifact → `paper_tables/provenance_ledger.json`
  (**60/60 PASS** this run). A manual edit to any source JSON that breaks internal consistency would
  surface as a `FAIL`, not pass silently.
