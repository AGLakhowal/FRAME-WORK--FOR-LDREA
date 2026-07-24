# REVIEWER MAPPING (auto-generated, rebuttal-ready)

For every anticipated reviewer concern: the experiment(s) that answer it, the evidence artifact, the paper section, the figure, and the live-derived resolution status.

| # | Reviewer concern | Experiment(s) | Evidence artifact | Paper § | Figure | Status |
|---|------------------|---------------|-------------------|---------|--------|--------|
| R1 | Where is authorization correctness demonstrated on realistic data? | E1 | gamma_lab_v1_report.json | IX-B | fig_authorization_accuracy.svg | **Resolved** |
| R2 | Where is replay determinism proven? | E1, E10, E2 | replay_report.json | IX (replay) | fig_replay_integrity.svg | **Resolved** |
| R3 | Is the decision logic formally correct, or only tested? | E3, E9 | independent_verifier_report.json | VI / Appendix D | — | **Resolved** |
| R4 | Does the system remain safe under concurrency / load? | E4 | concurrency_scaling.json | IX (scalability) | fig_latency.svg | **Resolved** |
| R5 | Does it actually scale in throughput? | E4 | concurrency_scaling.json | IX (limitation) | fig_throughput.svg | **Resolved (negative result, disclosed)** |
| R6 | Are all components necessary, or is this over-engineered? | E5 | ablation.json | IX (ablation) | fig_component_ablation.svg | **Resolved** |
| R6-ext | Where is the evidence of INTERACTION EFFECTS between runtime components (pairwise / higher-order)? [E5b reports blind-detection metrics — URR/BFR — NOT the authorization FPR of R1/R8] | E5b | combined_ablation.json | IX (combined ablation) | fig_combined_ablation_heatmap.svg | **Resolved** |
| R7 | What is the runtime overhead of the governance layer? | E6 | runtime_profile.json | IX (overhead) | fig_runtime_breakdown.svg | **Resolved** |
| R8 | Does the approach generalize beyond one dataset (agents)? | E7 | boundary_fpr.json | IX-E | fig_false_permit_rate.svg | **Partially resolved** |
| R9 | How does it behave under faults / adversarial runtime conditions? | E8 | robustness.json | IX (Exp 8) | fig_robustness.svg | **Resolved** |
| R10 | Are the zero-event claims statistically justified given sample sizes? | E1, E7 | statistics_report.json | IX (statistics) | — | **Partially resolved** |
| R11 | Are hardware results being over-claimed? | — | — | V-G / XII | — | **Out of scope (not claimed)** |

## Detailed concern → claim → evidence chains

### R1 — Where is authorization correctness demonstrated on realistic data?
- Claim C1 [Supported]: Runtime authorization prevents unauthorized execution on a realistic transaction stream (0 unauthorized externalizations).
    - ✓ `experiments/runtime_correctness/gamma_lab_v1_report.json` ▷ `unauthorized_execution.count` = `0` (needs `==0`)
- Claim C2 [Supported]: The authorization decision is sound: zero false permits on the should-deny population of the ULB stream.
    - ✓ `experiments/runtime_correctness/gamma_lab_v1_report.json` ▷ `primary_metrics.false_permit_rate.adverse_events` = `0` (needs `==0`)

### R2 — Where is replay determinism proven?
- Claim C5 [Supported]: Authorization decisions are deterministically replayable (Replay Determinism Rate = 100%).
    - ✓ `experiments/runtime_correctness/gamma_lab_v1_report.json` ▷ `primary_metrics.replay_determinism_rate.reported_rate` = `1.0` (needs `==1.0`)
- Claim C6 [Supported]: Execution provenance is tamper-evident: every decision record re-verifies (0 hash-chain, ledger-bind, or consistency failures).
    - ✓ `experiments/replay/replay_report.json` ▷ `hash_chain_adjacency_failures` = `0` (needs `==0`)
    - ✓ `experiments/replay/replay_report.json` ▷ `ledger_bind_failures` = `0` (needs `==0`)
    - ✓ `experiments/replay/replay_report.json` ▷ `self_consistency_failures` = `0` (needs `==0`)
    - ✓ `experiments/replay/replay_report.json` ▷ `result` = `PASS` (needs `eq:PASS`)
- Claim C16 [Supported]: Execution evidence is exportable as an independently verifiable audit bundle: every member re-hashes to its recorded digest and the bundle is cryptographically bound to the live ledger, satisfying ConcurBench Level 4.
    - ✓ `experiments/audit_bundle/audit_bundle_report.json` ▷ `verification.status` = `PASS` (needs `eq:PASS`)
    - ✓ `experiments/audit_bundle/audit_bundle_report.json` ▷ `concurbench_level4` = `PASS` (needs `eq:PASS`)
    - ✓ `experiments/runtime_correctness/concurbench_full_report.json` ▷ `replay_and_auditability.audit_packet_export` = `PASS` (needs `eq:PASS`)

### R3 — Is the decision logic formally correct, or only tested?
- Claim C7 [Supported]: The decision logic is mathematically correct: an independent reference implementation is bitwise-equivalent to the engine over the entire 2^16 input space.
    - ✓ `experiments/formal/independent_verifier_report.json` ▷ `total_field_mismatches` = `0` (needs `==0`)
    - ✓ `experiments/formal/independent_verifier_report.json` ▷ `coverage_complete` = `True` (needs `==True`)
    - ✓ `experiments/formal/independent_verifier_report.json` ▷ `verdict` = `IDENTICAL` (needs `eq:IDENTICAL`)
- Claim C15 [Supported]: Every runtime predicate is exercised and each, in isolation, denies: a deterministic synthetic suite drives the frozen engine so that all 13 runtime predicates are observed in both polarities, and a single deficit among nine concurring predicates always yields SAFE_STATE (per-predicate I3).
    - ✓ `experiments/predicate_coverage/predicate_coverage.json` ▷ `predicate_coverage.coverage_rate` = `1.0` (needs `==1.0`)
    - ✓ `experiments/predicate_coverage/predicate_coverage.json` ▷ `single_deficit_isolation.false_permits` = `0` (needs `==0`)
    - ✓ `experiments/predicate_coverage/predicate_coverage.json` ▷ `control.clean_proposal_permits` = `True` (needs `==True`)
    - ✓ `experiments/predicate_coverage/predicate_coverage.json` ▷ `aggregate.all_cases_pass` = `True` (needs `==True`)

### R4 — Does the system remain safe under concurrency / load?
- Claim C8 [Supported]: Runtime safety is preserved under concurrency: 0 false permits and 0 false denials at every thread level (1-64).
    - ✓ `experiments/stress/concurrency_scaling.json` ▷ `total_false_permits` = `0` (needs `==0`)
    - ✓ `experiments/stress/concurrency_scaling.json` ▷ `total_false_denials` = `0` (needs `==0`)
    - ✓ `experiments/stress/concurrency_scaling.json` ▷ `all_authorization_correct` = `True` (needs `==True`)

### R5 — Does it actually scale in throughput?
- Claim C9 [Supported (negative result)]: Throughput does NOT scale with threads on the pure-Python decision path (GIL-bound); this is reported as a limitation, not a scaling claim.
    - ✓ `experiments/stress/concurrency_scaling.json` ▷ `levels.-1.speedup_vs_1thread` = `0.16082781510580463` (needs `le:1.0`)

### R6 — Are all components necessary, or is this over-engineered?
- Claim C10 [Supported]: Each structural component is necessary: removing the authorization layer leaks the entire deniable population (causal contribution to safety).
    - ✓ `experiments/ablation/ablation.json` ▷ `configs.3.leaked_permits_vs_baseline` = `45000` (needs `>0`)
    - ✓ `experiments/ablation/ablation.json` ▷ `configs.0.leaked_permits_vs_baseline` = `0` (needs `==0`)

### R6-ext — Where is the evidence of INTERACTION EFFECTS between runtime components (pairwise / higher-order)? [E5b reports blind-detection metrics — URR/BFR — NOT the authorization FPR of R1/R8]
- Claim C10b [Supported]: Interaction effects between runtime components are measured, not assumed: the combined ablation executes every pairwise and representative higher-order removal through the full runtime and classifies each interaction. NOTE: E5b reports BLIND-detection metrics (Undetected Risk Rate URR = FN/(TP+FN)), which are a DIFFERENT construct from the authorization False Permit Rate of C2/C12 (0/492, 0/62) and never replace it.
    - ✓ `experiments/combined_ablation/combined_ablation.json` ▷ `n_configurations` = `19` (needs `ge:8`)
    - ✓ `experiments/combined_ablation/combined_ablation.json` ▷ `baseline_runtime_integrity_score` = `1.0` (needs `==1.0`)

### R7 — What is the runtime overhead of the governance layer?
- Claim C11 [Supported]: Per-decision runtime overhead is low: the Runtime-Context and Replay planes are a small fraction of end-to-end pipeline time.
    - ✓ `experiments/profiling/runtime_profile.json` ▷ `runtime_context.pct_of_end_to_end` = `6.58520039749739` (needs `le:25`)
    - ✓ `experiments/profiling/runtime_profile.json` ▷ `replay.pct_of_end_to_end` = `3.299271680532196` (needs `le:25`)

### R8 — Does the approach generalize beyond one dataset (agents)?
- Claim C12 [Partially Supported]: AgentDojo integration preserves authorization correctness: 0 false permits on genuinely-foreign attacker targets at the boundary (no LLM).
    - ✓ `experiments/agentdojo/boundary/boundary_fpr.json` ▷ `soundness_foreign_targets.permitted` = `0` (needs `==0`)

### R9 — How does it behave under faults / adversarial runtime conditions?
- Claim C13 [Supported]: Safety properties hold under runtime fault injection: across all fault families there are 0 false permits and every integrity corruption is detected.
    - ✓ `fresh_evidence/robustness/robustness.json` ▷ `aggregate.total_false_permits` = `0` (needs `==0`)
    - ✓ `fresh_evidence/robustness/robustness.json` ▷ `aggregate.all_safety_properties_hold` = `True` (needs `==True`)

### R10 — Are the zero-event claims statistically justified given sample sizes?
- Claim C2 [Supported]: The authorization decision is sound: zero false permits on the should-deny population of the ULB stream.
    - ✓ `experiments/runtime_correctness/gamma_lab_v1_report.json` ▷ `primary_metrics.false_permit_rate.adverse_events` = `0` (needs `==0`)
- Claim C12 [Partially Supported]: AgentDojo integration preserves authorization correctness: 0 false permits on genuinely-foreign attacker targets at the boundary (no LLM).
    - ✓ `experiments/agentdojo/boundary/boundary_fpr.json` ▷ `soundness_foreign_targets.permitted` = `0` (needs `==0`)

### R11 — Are hardware results being over-claimed?
- Claim C14 [Not Claimed]: Hardware (Tier-H FPGA/SGX/HSM) deployment.
