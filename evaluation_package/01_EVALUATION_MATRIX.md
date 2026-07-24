# L-DREA Evaluation Matrix — architectural property × evidence

Maps each of the six architectural properties the paper claims to the experiments that validate it,
with the fresh result and the honest status. **CLOSED** = at least one executed experiment with fresh
generated evidence supports the property *at Tier-S*. **CLOSED (bounded)** = supported but with a
sample-size/scope caveat vs. the paper's Tier-H number. **BLOCKED** = requires a dependency absent on
this host (named in `08_THREATS_TO_VALIDITY.md`).

| # | Property | Experiments | Fresh result | Status |
|---|----------|-------------|--------------|--------|
| 1 | **Correct** (authorization sound; no unauthorized externalization within scope) | A1, A6, B3, D1 | UER 0/284,807; boundary FPR 0/62 foreign targets; verifier IDENTICAL over 2¹⁶ | **CLOSED (Tier-S)** |
| 2 | **Deterministic** (bitwise-replayable decisions) | A1 (RDR), A6 (replay verifier), C1 (per-thread replay), E1 (per-config replay) | RDR 100.0000%; 284,807/284,807 manifest records verify; replay-consistent at every thread level & every ablation config | **CLOSED** |
| 3 | **Safe / fail-closed** (Γ>0 ⇒ SAFE_STATE; deny-on-uncertainty) | A1 (class-veto 492/492), A4 (FCR 1.0, 0 fail-open), A3 (stress fail-closed), C1 (0 false permits under load) | class-veto effectiveness 1.0; FCR 1.0; 0 false permits at 1–64 threads | **CLOSED** |
| 4 | **Reproducible** (same inputs → same outputs; third-party auditable) | A1 re-run vs. prior artifact, A6, D1 re-run, PROVENANCE hashes | correctness/formal results reproduce **exactly** (0 FP/0 FD, 0 mismatches, RDR 100%); timing differs by host (documented) | **CLOSED** |
| 5 | **Scalable** (holds under concurrency) | C1 (1→64 threads), C2 (per-stage profile) | safety invariants hold at all 7 levels; **throughput degrades (GIL-bound), does not scale up** | **CLOSED for safety; NEGATIVE for throughput (honestly reported)** |
| 6 | **Domain-independent** (same engine governs finance rows *and* autonomous agents) | A1 (ULB credit-card), B3 (AgentDojo tool calls), E1 | same frozen `evaluate_decision` + manifests adjudicate both a 284,807-row financial corpus and 4 AgentDojo agent suites with 0 foreign-target false permits | **CLOSED (2 domains)** |

## Metric coverage vs. task brief (Categories A–E)

| Requested metric | Experiment | Present in fresh artifact? |
|---|---|---|
| authorization correctness | A1, D1 | ✅ `gamma_lab_v1_report.json`, `independent_verifier_report.json` |
| fail closed | A1, A4, A3 | ✅ class_veto_effectiveness, FCR, stress fail_closed_ok |
| class veto | A1, E1 | ✅ 492/492; ablation leak 15,000 when removed |
| replay determinism | A1, A6, C1 | ✅ RDR 100%; manifest verify PASS; per-thread replay_consistent |
| execution integrity | A6 | ✅ hash-chain adjacency + ledger-bind 0 failures |
| permit / deny | B1, B3 | ✅ statistics.json; boundary rows.jsonl |
| Gamma decisions | B1 | ✅ gamma_global / pi / deficit_count |
| episode utility | B4 | ⛔ BLOCKED (needs Ollama) |
| security success (TASR) | B4 | ⛔ BLOCKED (needs Ollama) |
| decision entropy | B1 | ✅ predicate/tool frequency (entropy derivable); authorization_stability 0.967 |
| authorization stability | B1 | ✅ 0.9667 |
| runtime overhead | B1, C2 | ✅ Γ-decision overhead 0.0216 ms; RCL/replay per-stage |
| replay consistency (agent) | B1 | ✅ recorded replay_validation present |
| latency / throughput | A1, C1 | ✅ full latency dist + 7-level throughput |
| CPU / memory / queue delay | C1 | ✅ cpu_utilization, peak_rss_bytes, queue_delay_ms |
| false permits / false denials (scaling) | C1 | ✅ 0 / 0 at every level |
| ledger consistency | C1 | ✅ all_ledger_consistent true |
| state-space verification | D1 | ✅ 2¹⁶ IDENTICAL |
| TLA+ (if exists) | D2 | see `06_FORMAL_VERIFICATION_REPORT.md` |
| per-component ablation | E1 | ✅ class-veto / Γ / auth-layer leak counts |
| FPR ablation (paper Table 4) | E1 (analogue) | ⚠️ Tier-S leak-count analogue; Tier-H FPR BLOCKED (no 360 k generator) |
