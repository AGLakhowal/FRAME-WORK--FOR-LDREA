# Measurement Provenance Matrix

Every headline number in this repository, traced to the artifact it is read from.
**This file is generated.** Each value is extracted from disk at generation time, so it
cannot drift from the artifacts. A value that cannot be resolved is printed as
`**MISSING**` rather than omitted.

Rows: **44** · unresolved: **0**

| Metric | Value | Computed From | Pointer | Script | Figure | Table | Card | Evidence Level |
|---|---|---|---|---|---|---|---|---|
| Decision agreement (status) | `1` | `experiments/runtime_correctness/gamma_lab_v1_report.json` | `decision_agreement.match_status_rate` | `gamma_test_runner.py` | fig_authorization_accuracy.svg | table1_primary_metrics.md | Authorization | Benchmark Evidence |
| False Permit Rate | `0` | `concurbench_full_report.json` | `authorization_correctness.FPR` | `concurbench_full.py` | fig_false_permit_rate.svg | table1_primary_metrics.md | Authorization | Benchmark Evidence |
| FPR Wilson95 upper (cluster-corrected) | `0.0131179` | `concurbench_full_report.json` | `authorization_correctness.FPR_metric.wilson95_clustercorrected_upper` | `concurbench_full.py` | fig_false_permit_rate.svg | table1_primary_metrics.md | Authorization | Benchmark Evidence |
| FPR should-deny denominator (n) | `492` | `concurbench_full_report.json` | `authorization_correctness.FPR_metric.n` | `concurbench_full.py` | - | table1_primary_metrics.md | Authorization | Benchmark Evidence |
| Replay attempts | `284,807` | `concurbench_full_report.json` | `replay_and_auditability.replay_attempts` | `concurbench_full.py` | fig_replay_integrity.svg | table_replay.md | Replay | Benchmark Evidence |
| Replay consistency rate | `1` | `concurbench_full_report.json` | `replay_and_auditability.replay_consistency_rate` | `concurbench_full.py` | fig_replay_integrity.svg | table_replay.md | Replay | Benchmark Evidence |
| ERTuple count | `284,807` | `concurbench_full_report.json` | `replay_and_auditability.ertuple_count` | `concurbench_full.py` | - | table_evidence.md | Evidence | Derived From Measured |
| Ledger root hash | `1ce2a9e8d4330a0583a9d20a398de43297ea59c404e…` | `concurbench_full_report.json` | `replay_and_auditability.final_ledger_root_hash` | `concurbench_full.py` | - | table_evidence.md | Evidence | Derived From Measured |
| Revocation latency p95 (fleet) | `16.064` | `concurbench_full_report.json` | `distributed_consistency.revocation_latency_p95_ms` | `concurbench_full.py` | - | table_fleet.md | Fleet | Repository Simulation |
| Clock skew bound | `1` | `concurbench_full_report.json` | `distributed_consistency.clock_skew_bound_ms` | `concurbench_full.py` | - | table_fleet.md | Fleet | Repository Simulation |
| Quorum rule | `majority write-quorum 3/5; loss of quorum =…` | `concurbench_full_report.json` | `distributed_consistency.quorum_rule` | `concurbench_full.py` | - | table_fleet.md | Fleet | Repository Simulation |
| Predicate coverage rate | `1` | `experiments/predicate_coverage/predicate_coverage.json` | `predicate_coverage.coverage_rate` | `experiment_predicate_coverage.py` | fig_predicate_coverage.svg | table_predicates.md | Predicates | Benchmark Evidence |
| Single-deficit denial rate | `1` | `experiments/predicate_coverage/predicate_coverage.json` | `single_deficit_isolation.denial_rate` | `experiment_predicate_coverage.py` | fig_predicate_coverage.svg | table_predicates.md | Predicates | Benchmark Evidence |
| Engine latency mean (ms) | `0.025917` | `experiments/runtime_correctness/gamma_lab_v1_report.json` | `measured_latency.mean_ms` | `gamma_test_runner.py` | fig_latency.svg | table_latency.md | Latency | Measured Runtime |
| Engine latency p99 (ms) | `0.03775` | `experiments/runtime_correctness/gamma_lab_v1_report.json` | `measured_latency.p99_ms` | `gamma_test_runner.py` | fig_latency.svg | table_latency.md | Latency | Measured Runtime |
| Full pipeline (ms/row, measured) | `0.395504` | `experiments/profiling/runtime_profile.json` | `full_pipeline_ms_per_row_measured` | `experiments/generate_statistics.py` | fig_latency.svg | table_latency.md | Latency | Measured Runtime |
| Replay share of end-to-end (%) | `4.88887` | `experiments/profiling/runtime_profile.json` | `replay.pct_of_end_to_end` | `experiments/generate_statistics.py` | fig_runtime_breakdown.svg | table_latency.md | Latency | Measured Runtime |
| Throughput @1 thread | `355151` | `experiments/stress/concurrency_scaling.json` | `levels[0].throughput_decisions_per_s` | `concurbench_full.py` | fig_throughput.svg | table_throughput.md | Throughput | Measured Runtime |
| Throughput @64 threads | `69796.5` | `experiments/stress/concurrency_scaling.json` | `levels[6].throughput_decisions_per_s` | `concurbench_full.py` | fig_throughput.svg | table_throughput.md | Throughput | Measured Runtime |
| Total false permits (scaling) | `0` | `experiments/stress/concurrency_scaling.json` | `total_false_permits` | `concurbench_full.py` | - | table_throughput.md | Throughput | Measured Runtime |
| Stress scenarios fail-closed | `true` | `stress_test_report.json` | `aggregate.all_in_scope_denials_fail_closed` | `stress_test.py` | - | table_stress.md | Stress | Benchmark Evidence |
| Stress latency p99 (all) | `0.009708` | `stress_latency_report.json` | `aggregate.latency.p99_ms` | `experiments/profile_stress_scenarios.py` | - | table_stress.md | Stress | Measured Runtime |
| Label-leaking engine inputs | `5` | `label_leakage_audit.json` | `verdict.n_leaking_inputs` | `experiments/audit_label_leakage.py` | - | table_threats.md | Threats | Benchmark Evidence |
| Blind detection status | `BLOCKED` | `runtime_detection_report.json` | `status` | `experiments/experiment_runtime_detection.py` | - | table_runtime_detection.md | Runtime Detection | Not Executed |
| Permits issued | `24,912` | `production_evidence/production_evidence_summary.json` | `counts.permits` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Tokens | Derived From Measured |
| Ed25519 signatures created | `24,912` | `production_evidence/signature_verification_report.json` | `signatures_created` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Signatures | Measured Runtime |
| Signature verification success rate | `1` | `production_evidence/signature_verification_report.json` | `verification_success_rate` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Signatures | Measured Runtime |
| Signature verify latency mean (ms) | `0.834407` | `production_evidence/signature_verification_report.json` | `verification_latency_ms.mean` | `experiments/production_evidence_layer.py` | - | table_latency.md | Signatures | Measured Runtime |
| Negative signature tests rejected | `true` | `production_evidence/signature_verification_report.json` | `all_negative_tests_rejected` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Signatures | Measured Runtime |
| Negative suite positive control | `true` | `production_evidence/signature_verification_report.json` | `negative_suite_has_power` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Signatures | Measured Runtime |
| Single-use enforced | `true` | `production_evidence/permit_lifecycle_report.json` | `single_use_verified` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Tokens | Measured Runtime |
| Double-use rejected | `1,000` | `production_evidence/permit_lifecycle_report.json` | `double_use_rejected` | `experiments/production_evidence_layer.py` | - | table_tokens.md | Tokens | Measured Runtime |
| False permits after revocation | `0` | `production_evidence/revocation_report.json` | `false_permits_after_revocation` | `experiments/production_evidence_layer.py` | - | table_revocation.md | Revocation | Measured Runtime |
| Revocation propagation p99 (ms) | `19.9329` | `production_evidence/revocation_report.json` | `propagation_latency_ms.p99` | `experiments/production_evidence_layer.py` | - | table_revocation.md | Revocation | Repository Simulation |
| TOCTOU window p95 (ms) | `0.326041` | `production_evidence/runtime_timestamps_report.json` | `toctou_window_ms.p95` | `experiments/production_evidence_layer.py` | - | table_latency.md | Timestamps | Measured Runtime |
| Decision latency mean (ms) | `0.0014579` | `production_evidence/runtime_timestamps_report.json` | `decision_latency_ms.mean` | `experiments/production_evidence_layer.py` | - | table_latency.md | Timestamps | Measured Runtime |
| Ledger blocks | `25,000` | `production_evidence/ledger_summary.json` | `blocks` | `experiments/production_evidence_layer.py` | - | table_evidence.md | Ledger | Derived From Measured |
| Ledger hash continuity | `true` | `production_evidence/ledger_summary.json` | `hash_continuity` | `experiments/production_evidence_layer.py` | - | table_evidence.md | Ledger | Derived From Measured |
| Ledger tamper detection | `true` | `production_evidence/ledger_summary.json` | `tamper_detection_verified` | `experiments/production_evidence_layer.py` | - | table_evidence.md | Ledger | Measured Runtime |
| ISB pass rate | `1` | `production_evidence/ctr_report.json` | `isb_pass_rate` | `experiments/production_evidence_layer.py` | - | table_evidence.md | CTR | Derived From Measured |
| CTR invalid schema rejected | `1` | `production_evidence/ctr_report.json` | `invalid_schema_rejected` | `experiments/production_evidence_layer.py` | - | table_evidence.md | CTR | Measured Runtime |
| Watchdog timeouts | `5` | `production_evidence/watchdog_report.json` | `timeouts` | `experiments/production_evidence_layer.py` | - | table_watchdog.md | Watchdog | Repository Simulation |
| Watchdog heartbeat mean (ms) | `0.00268646` | `production_evidence/watchdog_report.json` | `heartbeat_interval_ms.mean` | `experiments/production_evidence_layer.py` | - | table_watchdog.md | Watchdog | Measured Runtime |
| Clock skew max |offset| (ms) | `0.974001` | `production_evidence/clock_skew_report.json` | `max_abs_offset_ms` | `experiments/production_evidence_layer.py` | - | table_fleet.md | Clock | Repository Simulation |

## Evidence-level census

| Evidence level | Rows |
|---|---|
| Measured Runtime | 21 |
| Benchmark Evidence | 10 |
| Derived From Measured | 6 |
| Repository Simulation | 6 |
| Not Executed | 1 |

**Production Evidence: 0 rows.** No value in this repository is production
evidence. **External Validation: 0 rows.**

