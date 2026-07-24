# IEEE RESULTS — TABLES

**Publication-ready tables generated from `VALIDATION_RESULTS.json` / `PERFORMANCE_RESULTS.json` (frozen runtime, post-H4). No methodology or reported-output change.** All figures are measured, not fabricated. AgentDojo (Campaign 6) is not executable in this environment (genuine package absent) and is marked N/A.

---

### Table I — Campaign summary

| # | Campaign | Metric | Result | 95% CI |
|---|---|---|---|---|
| 1 | Runtime validation | authorization fail-closed | 24/24 = 1.000 | [0.862, 1.000] |
| 2 | Determinism | identical executions | 10/10 = 1.000 | [0.722, 1.000] |
| 3 | Class-blind | identical records (Class 0/1/absent) | 3/3 identical | — |
| 4 | Replay | independent verifier | PASS (0 failures) | — |
| 5 | ConcurBench | overall verdict | INTERNAL_PASS | — |
| 6 | AgentDojo | genuine integration | **N/A (env)** | — |
| 7 | Performance | throughput | 1,714 rows/s | — |
| 8 | Stress | fail-closed (malformed/missing) | 5/5 = 1.000 | [0.566, 1.000] |
| 9 | Ablation | components load-bearing | 5/5 | — |

### Table II — Determinism statistics (Campaigns 2, 4, 8)

| Source | Executions | Distinct record hashes | Distinct manifests | Distinct ledger heads | Determinism rate |
|---|---|---|---|---|---|
| Repeated (C2) | 10 | 1 | 1 | 1 | 1.000 |
| Replay re-emit (C4) | 5 | — | 1 | — | 1.000 |
| Concurrent 8-thread (C8) | 8 | — | — | 1 | 1.000 |
| **Total** | **23** | **1** | **1** | **1** | **1.000** |

### Table III — Class-blind verification

| Injection | Record SHA-256 (12) | Manifest SHA-256 (12) | Decision |
|---|---|---|---|
| Class absent | `ae97aa24814d` | `522e14f1e7b6` | SAFE_STATE |
| Class = 0 | `ae97aa24814d` | `522e14f1e7b6` | SAFE_STATE |
| Class = 1 | `ae97aa24814d` | `522e14f1e7b6` | SAFE_STATE |
| **Identical?** | **YES** | **YES** | **YES** |

### Table IV — Replay statistics

| Property | Value |
|---|---|
| Adjacency failures | 0 |
| Ledger-bind failures | 0 |
| Consistency failures | 0 |
| Independent verifier | RESULT: PASS |
| Manifest determinism (5×) | 1 distinct SHA |
| Large-batch (5,000) replay | PASS |
| Generation latency (ms) | mean 2.01, CI [1.83, 2.18], p50 1.92, p95 2.89, p99 2.97 |
| Verification latency (ms) | mean 41.1, CI [39.9, 42.4], p50 40.0, p95 46.8, p99 47.2 |

### Table V — ConcurBench conformance (284,807 instances; 492 adversarial)

| Level | Verdict | Key metric |
|---|---|---|
| L1 authorization correctness | PASS | FPR=0, UER=0, FDR=0, FCR=1.0, DR=1.0 |
| L2 adversarial robustness | PASS | adaptive fp 0/11,808; contamination/canary PASS |
| L3 distributed consistency | PASS | 5-node consistency 1.0; partition PASS |
| L4 replay auditability | PARTIAL | replay rate 1.0; hashchain PASS; verifier PASS |
| Overall | **INTERNAL_PASS** | deterministic content == committed baseline |

### Table VI — Confusion matrix (Class-blind runtime, neutral phase) — *degenerate by design*

| actual \ predicted | PERMIT | SAFE_STATE |
|---|---|---|
| any input | 0 | N (all) |

*No declared deployment policy → full-vector fail-closed. Discriminative matrix is a Phase-B artifact.*

### Table VII — Reference: reported-arm / ConcurBench baseline confusion matrix — *frozen parity baseline only*

| actual \ predicted | PERMIT | SAFE_STATE |
|---|---|---|
| legit (Class 0, n=284,315) | 284,315 (TN) | 0 (FP) |
| fraud (Class 1, n=492) | 0 (FN) | 492 (TP) |

FPR = 0/284,315 = 0 · FDR = 0/… = 0 · UER = 0. **Caveat:** derived from `gamma_map_raw`'s Class-authored labels; a tautological baseline retained for parity, **not** independent accuracy of the Class-blind runtime.

### Table VIII — Per-stage latency (Campaign 7; n=2,000)

| Stage | Mean (ms/row) | Share |
|---|---|---|
| build_evidence_bundle (5.1) | 0.0744 | 37.6% |
| Predicate Binding (5.1-B) | 0.1018 | 51.4% |
| EEB→Engine Adapter (4.1) | 0.0022 | 1.1% |
| evaluate_decision (frozen) | 0.0017 | 0.9% |
| Reported Artifact Emitter | 0.0167 | 8.5% |
| **Core per-row total** | **0.198** | 100% |

### Table IX — End-to-end performance (Campaign 7)

| Metric | Value | 95% CI |
|---|---|---|
| Core per-row latency (ms) | 0.198 | [0.1972, 0.1984] |
| p50 / p95 / p99 / max (ms) | 0.195 / 0.207 / 0.238 / 0.571 | — |
| Throughput (rows/s, end-to-end) | 1,714 | — |
| Replay generation (ms/row) | 0.0137 | — |
| Peak memory (2,000 rows) | 5,126 KB | — |
| Peak memory per row | ~2,624 B | — |

### Table X — Ablation impact

| Component removed | Failure mode | Verdict |
|---|---|---|
| Runtime Context | fail-closed (no crash) | load-bearing (degradation) |
| Execution Evidence Bundle | `AttributeError` | load-bearing (hard) |
| Predicate Binding | `IndexError` (vector mismatch) | load-bearing (hard) |
| Replay | no independent manifest | load-bearing (auditability) |
| Reported Artifact Emitter | no artifact/ledger/manifest | load-bearing (hard) |

---

*Tables generated from measured results; no reported benchmark output regenerated or modified.*
