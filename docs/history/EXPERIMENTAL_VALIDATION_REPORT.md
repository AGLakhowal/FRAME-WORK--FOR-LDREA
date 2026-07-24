# EXPERIMENTAL VALIDATION REPORT — Complete Scientific Campaign (post-H4)

**Scientific evidence generation only. No redesign, no architecture/methodology change, no engineering refactoring, no reported-benchmark regeneration, no IEEE-paper edit.** Every number is produced by executing the frozen components; raw evidence is in `VALIDATION_RESULTS.json` and `PERFORMANCE_RESULTS.json`. Companion artifacts: `IEEE_RESULTS_TABLES.md`, `IEEE_RESULTS_FIGURES.md`, `PERFORMANCE_REPORT.md`, `REPRODUCIBILITY_REPORT.md`.

**Roles:** Principal AI Systems Research Scientist · IEEE Access Reviewer · Artifact Evaluation Committee Member · Experimental Validation Lead · Runtime Governance Researcher.

**Neutrality guard (verified post-run):** benchmarks executed with `write=False`; all manifests written to temp dirs; `concurbench_full_report.json` / `gamma_summary.json` mtimes unchanged; regression parity 6/6; `evaluate_decision` + `NODE_GATE_COLS` byte-identical to HEAD. **No reported artifact or frozen component was modified.**

---

## 1. Executive Summary

The complete campaign was executed against the frozen runtime substrate (post the H4 robustness fix). **All executable campaigns pass; no implementation defect was detected.** One campaign (6 — genuine AgentDojo) is **not executable** in this environment (package absent; synthetic prohibited) and is documented as an environment limitation, not a defect.

| # | Campaign | Result | Headline |
|---|---|---|---|
| 1 | Runtime Validation | ✅ PASS | end-to-end correct; fail-closed 24/24; EEB+binding integrity; replay correct |
| 2 | Determinism | ✅ PASS | 10/10 executions byte-identical (records, manifests, ledger heads, decisions) |
| 3 | Class-Blind | ✅ PASS | Class 0 / 1 / absent → byte-identical records + manifests |
| 4 | Replay | ✅ PASS | verifier PASS; deterministic; gen 2.01 ms, verify 41.1 ms |
| 5 | ConcurBench | ✅ PASS | INTERNAL_PASS; content matches committed baseline (L4 PARTIAL, pre-existing) |
| 6 | Genuine AgentDojo | ⚠️ NOT EXECUTABLE | `agentdojo` not installed; no synthetic substitute; no fabrication |
| 7 | Performance | ✅ MEASURED | 0.198 ms/row core; ~1,714 rows/s end-to-end; 2.6 KB/row peak |
| 8 | Stress | ✅ PASS | 5,000-row batch; 8-thread concurrent; **malformed/missing now fail-closed 5/5** |
| 9 | Ablation | ✅ OBSERVED | all five components confirmed load-bearing |

**Final certification: SCIENTIFIC VALIDATION COMPLETE** (with the documented AgentDojo environment limitation).

---

## 2. Campaign 1 — Runtime Validation

| Property | Result |
|---|---|
| End-to-end execution (24 requests) | ✅ |
| Runtime activation (orchestrator) | ✅ |
| Authorization correctness (fail-closed) | 24/24 SAFE_STATE — rate 1.000, Wilson 95% CI **[0.862, 1.000]** |
| Evidence generation correctness (EEB `verify_integrity`+`validate_structure`) | ✅ |
| Predicate Binding integrity (bound-EEB seal verifies) | ✅ |
| Provenance preservation (EEB id/digest on every record) | ✅ |
| Replay correctness (frozen verifier RESULT: PASS) | ✅ |

**Status: PASS.** The all-SAFE_STATE distribution is the expected neutral-phase behaviour (no declared deployment policy → full-vector fail-closed, Gap-3(a)); it is not a defect.

## 3. Campaign 2 — Determinism

10 repeated executions of the same batch: **1** distinct record hash, **1** manifest SHA, **1** ledger head, **1** decision vector. Determinism rate 1.000 (Wilson 95% CI **[0.722, 1.000]**). **Status: PASS** — the pipeline is a pure function of its inputs (no wall clock, no randomness).

## 4. Campaign 3 — Class-Blind Verification

| Injection | Record SHA-256 | Manifest SHA-256 | Decision |
|---|---|---|---|
| Class absent | `ae97aa24…` | `522e14f1…` | SAFE_STATE |
| Class = 0 | `ae97aa24…` | `522e14f1…` | SAFE_STATE |
| Class = 1 | `ae97aa24…` | `522e14f1…` | SAFE_STATE |

Byte-identical across all three. **Status: PASS** — `Class` has no effect on runtime behaviour, records, or ledger.

## 5. Campaign 4 — Replay Validation

| Property | Value |
|---|---|
| Ledger integrity (genesis-anchored adjacency) | ✅ |
| Reproducibility (independent verifier) | RESULT: PASS |
| Manifest determinism (5×) | 1 distinct SHA |
| Replay generation latency | mean **2.01 ms**, 95% CI [1.83, 2.18], p99 2.97 ms (n=20) |
| Replay verification latency | mean **41.1 ms**, 95% CI [39.9, 42.4], p99 47.2 ms (n=20) |

**Status: PASS.**

## 6. Campaign 5 — ConcurBench Evaluation

Fresh full run (`write=False`), 284,807 instances (492 adversarial):

| Level | Verdict |
|---|---|
| L1 authorization correctness | PASS (FPR=0, UER=0, FDR=0, FCR=1.0, DR=1.0) |
| L2 adversarial robustness | PASS (adaptive fp 0/11,808; contamination/canary PASS) |
| L3 distributed consistency | PASS (5-node, consistency 1.0, partition PASS) |
| L4 replay auditability | PARTIAL (unchanged, pre-existing) |
| Overall | INTERNAL_PASS |

Deterministic content (timing excluded) **matches the committed baseline exactly**. **Status: PASS / no deviation.**

## 7. Campaign 6 — Genuine AgentDojo Evaluation

**NOT EXECUTABLE.** `importlib.util.find_spec('agentdojo') is None` — the genuine package is not installed. The campaign prohibits archived/synthetic validation, so **no substitute was used and no result fabricated**. Interception, authorization, replay, runtime-evidence, and governance-behaviour measurements under the genuine AgentDojo harness **could not be produced** and remain outstanding until the dependency is provisioned. This is an environment limitation, **not** an implementation defect.

## 8. Campaign 7 — Performance (see `PERFORMANCE_REPORT.md`)

Per-row core latency **0.198 ms** (95% CI [0.1972, 0.1984]; p50 0.195, p95 0.207, p99 0.238, max 0.571; n=2,000). End-to-end throughput **~1,714 rows/s**. Per-stage means (ms): build 0.074 · bind 0.102 · adapt 0.0022 · eval 0.0017 · emit 0.0167. Peak memory 5,126 KB for 2,000 rows (~2.6 KB/row). **Status: MEASURED** (no optimisation).

## 9. Campaign 8 — Stress Testing

| Sub-campaign | Result |
|---|---|
| Large batch (5,000 rows) | ✅ PASS — completed; adjacency valid; replay PASS |
| Concurrent (8 threads) | ✅ PASS — no errors; identical ledger head across threads |
| Malformed / missing evidence | ✅ **PASS — fail-closed 5/5** (rate 1.000, Wilson 95% CI [0.566, 1.000]); no exceptions |
| Fail-closed robustness | ✅ every degraded input → SAFE_STATE + valid deterministic artifact + replay PASS |

**Status: PASS.** The H4 fix is confirmed under stress: absent/malformed observables now preserve end-to-end fail-closed behaviour.

## 10. Campaign 9 — Ablation Studies

| Ablated component | Observed architectural consequence |
|---|---|
| Runtime Context (plane-B) | plane-B ABSENT → freshness/velocity unsupported → fail-closed; no crash |
| Execution Evidence Bundle | adapter requires a sealed EEB (`AttributeError`) → **load-bearing** |
| Predicate Binding | evidence-only 3-field vector ≠ 10-gate engine vector (`IndexError`) → **load-bearing** |
| Replay | records + ledger still produced, but no manifest → **loss of independent auditability** |
| Reported Artifact Emitter | no reported artifact / ledger canon → no replay manifest; provenance→report linkage lost → **load-bearing** |

**Status: OBSERVED (5/5).** No redesign performed.

---

## 11. Statistical Analysis (summary)

- **Proportions (Wilson 95% CI):** authorization fail-closed 24/24 = 1.000 [0.862, 1.000]; determinism 10/10 = 1.000 [0.722, 1.000]; stress fail-closed 5/5 = 1.000 [0.566, 1.000]. (Wide lower bounds reflect small n by design — these are correctness demonstrations, not sampling estimates.)
- **Latency (mean ± 95% CI, ms):** core per-row 0.198 ± 0.0006 (n=2,000); replay gen 2.01 ± 0.18; replay verify 41.1 ± 1.25.
- **Determinism:** 1.00 across 10 (Campaign 2) + 5 (Campaign 4) + 8 concurrent (Campaign 8) executions — 0 divergences.
- **Replay:** 0 adjacency / 0 ledger-bind / 0 consistency failures; large-batch (5,000) replay PASS.
- Distributions/histogram: `IEEE_RESULTS_FIGURES.md`; full tables: `IEEE_RESULTS_TABLES.md`.

## 12. Confusion Matrices

**Class-blind runtime pipeline (neutral phase) — degenerate by design.** With no declared deployment policy the pipeline fail-closes every row:

| actual \ predicted | PERMIT | SAFE_STATE |
|---|---|---|
| (any input) | 0 | all rows |

A **discriminative** confusion matrix (PERMIT vs SAFE_STATE against ground truth) requires a declared credit-card deployment policy + Ground-Truth Evaluation and is a **Phase-B** artifact — explicitly out of scope here (see Threats to Validity). The reported-arm/ConcurBench frozen baseline (Class-authored, TN=284,315, TP=492, FP=0, FN=0) is reproduced in `IEEE_RESULTS_TABLES.md` **only** as the parity baseline, not as evidence of the Class-blind runtime's discriminative power.

## 13. Threats to Validity

1. **Degenerate discrimination (construct validity).** The neutral Class-blind pipeline reports all-SAFE_STATE because no deployment policy/SLA is declared; it demonstrates *safety and mechanics*, not *fraud-vs-legit discrimination*. Discriminative metrics await Phase B.
2. **Baseline is a tautology (internal validity).** The reported-arm confusion matrix (FPR/FDR=0) derives from `gamma_map_raw`'s Class-authored labels; it is a **parity baseline**, not an independent accuracy result. This is precisely what Phase B replaces.
3. **AgentDojo not executed (external validity).** Cross-domain interception/governance evidence is missing (dependency absent); conclusions are limited to the credit-card arm + ConcurBench.
4. **Small-n correctness proportions.** Fail-closed/determinism proportions use small n (wide Wilson lower bounds); they are demonstrations of invariants, complemented by the 5,000-row and 284,807-row runs.
5. **Timing variance (conclusion validity).** Latency is wall-clock on one host and varies run-to-run (e.g., prior 1,206 vs current 1,714 rows/s); absolute numbers are indicative, not competitive claims.
6. **Determinism scope.** Verified on injected/deterministic inputs; a wall-clock or nondeterministic producer (not present) would need re-verification.

## 14. Artifact Evaluation Summary

- **Available:** the frozen pipeline + orchestrator; deterministic, replayable; independent verifier; two machine-readable results files; reproducibility instructions (`REPRODUCIBILITY_REPORT.md`).
- **Functional:** all executable campaigns pass; determinism 1.00; replay PASS; regression parity 6/6.
- **Reusable:** stdlib + pandas/numpy; Python 3.9; no network; deterministic seeds/labels.
- **Limitation:** AgentDojo (F) requires provisioning the genuine package; Phase-B discriminative metrics require a declared deployment policy.

## 15. Outputs produced

`EXPERIMENTAL_VALIDATION_REPORT.md` · `IEEE_RESULTS_TABLES.md` · `IEEE_RESULTS_FIGURES.md` · `PERFORMANCE_REPORT.md` · `REPRODUCIBILITY_REPORT.md` · `VALIDATION_RESULTS.json` · `PERFORMANCE_RESULTS.json`.

## 16. Scientific Neutrality Certification

No scientific methodology, authorization/Gamma/SAFE_STATE semantics, Predicate Binding, Runtime Context, replay semantics, serialization, reported methodology, benchmarks, metrics, or engineering architecture changed. `gamma_map_raw` untouched; reported outputs untouched (mtimes + parity 6/6). Only **evidence generation** occurred; a statistics-labeling bug in the *analysis harness* (Wilson-tuple order) was corrected in the analysis code only — no frozen component touched. **No implementation defect detected** in this campaign.

---

# SCIENTIFIC VALIDATION COMPLETE

**Single sentence:** across nine campaigns the frozen runtime validates cleanly for correctness, determinism (1.00), Class-blindness, replay/ledger/Evidence-Quad integrity, ConcurBench parity, performance, stress, and post-H4 fail-closed robustness (5/5), with the sole gap being the **genuine AgentDojo evaluation**, which is **not executable** in this environment (documented, not fabricated) — no implementation defect was detected.

---

*Scientific validation report only. No redesign, methodology change, reported-benchmark regeneration, `gamma_map_raw` retirement, or IEEE-paper edit. All results reproduced from the frozen components; raw evidence in the two JSON deliverables. Awaiting independent review; Phase B not begun.*
