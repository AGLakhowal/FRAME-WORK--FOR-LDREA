# Dashboard Completion Report

**Scope.** Surfacing of existing runtime evidence in `SCIENTIFIC_DASHBOARD.html`.
**Date of run.** 2026-07-10 · `python RUN_ALL_EXPERIMENTS.py` → exit 0, 10/10 experiments, 16/16 claims, 11/11 reviewer concerns.

> **This enhancement surfaces existing runtime evidence rather than creating new scientific results. No experimental outcomes, benchmark values, or published claims were modified.**

---

## 1. Existing runtime evidence discovered

The audit (Part 10) found that `stress_test.py` already computes substantially more runtime evidence
than the dashboard displayed. Every value below was **already being computed and serialised** into
`stress_test_report.json`; the dashboard simply discarded it.

| Scenario | Γ adjudications already computed | Where they were stored |
|---|---|---|
| P1 — Ghost Treasury Transfer | 1 | `scenarios[0].decision` (rendered) |
| P2 — Sanctions Drift Cascade | 3 | `scenarios[1].subcases` (**discarded**) |
| P3 — Multi-Agent Liquidity Panic | 4 | `scenarios[2].subcases` (**discarded**) |
| P4 — Sovereign Cascade Edge Case | 1 | `scenarios[3].subcases` (**discarded**) |
| **Total** | **9** | |

Each subcase already carried `gamma`, `class_veto`, `decision` and `failed_predicates`.
`fail_closed_ok` was already computed per scenario by `stress_test._scenario()`.

### Facilities that already existed and were therefore reused, not rebuilt

| Requested capability | Already present in | Action taken |
|---|---|---|
| Terminal purpose / motivation / reviewer output | `experiments/_dashboard.py` | Reused. Not rebuilt. |
| Wilson confidence intervals | `predicate_coverage.json`, `fcr_test_report.json`, `statistics_report.json`, `ablation.json` | Reused. Not recomputed. |
| Throughput + GIL limitation | `experiments/stress/concurrency_scaling.json`; negative result **C9** | Reused. Not re-measured. |
| Claim → experiment → figure → table mapping | `claims_registry.py` (16 claims) | Reused. Not duplicated. |
| Reviewer concerns | `claims_registry.REVIEWER_CONCERNS` (11) | Reused. |
| Per-experiment research interpretation | `dashboard_registry.EXPERIMENTS[*].interpretation` | Reused. |
| Predicate coverage statistics | Experiment 9 | Cross-referenced, not recalculated. |

**No duplicate computation was introduced.** The only new computation in this change is wall-clock
timing (Part 5), which did not previously exist for the stress layer.

---

## 2. Newly exposed information

1. **All 9 runtime Γ decisions**, previously invisible. Per subcase: Γ, decision, class veto,
   failed predicates, expected outcome, observed outcome, match, and scientific interpretation.
2. **Runtime decision rollup** per scenario: total decisions, SAFE_STATE / PERMIT / class-veto
   counts, Γ distribution, decision agreement, fail-closed result, scenario verdict.
3. **Scenario fail-closed result: 4 / 4 (100 %)** — computed by `stress_test._scenario()`, not by
   the dashboard. This replaces the previous, misleading "1 decision evaluated".
4. **Measured latency** for every scenario (new artifact `stress_latency_report.json`).
5. **Measured throughput** with the GIL explained as a scientific limitation.
6. **Predicate coverage statistics** (13/13, both polarities) cross-referenced from Experiment 9.
7. **Claims supported** and **Research interpretation** on all 10 HTML experiment cards.

### The oracle gap is surfaced, not hidden

`P2.case_b_stale_truth` is the **only** runtime decision that returns `PERMIT` (Γ = 0). It is a fresh
sanctions feed carrying stale truth. `stress_test._scenario()` already excludes it from the
fail-closed rule. The dashboard now renders it explicitly as `Out of scope — oracle gap` with the
reason stated in full, rather than scoring it as a failure or omitting it.

### Aggregate, computed at render time (never hardcoded)

| Quantity | Value |
|---|---|
| Scenarios | 4 |
| Scenarios satisfying their fail-closed rule | **4 / 4 (100 %)** |
| Total runtime Γ decisions | **9** |
| SAFE_STATE decisions | 8 |
| PERMIT decisions | 1 (the acknowledged oracle gap) |
| Class-veto decisions | 4 |
| Subcase decisions adjudicated | 7 |
| Subcase decision agreement | **7 / 7** |
| Subcase decision disagreement | **0** |
| Predicate evaluations scored | 9 |
| Predicate matches / mismatches | 9 / **0** |
| Overall verdict | **NO DIVERGENCE** |

---

## 3. New dashboard components

| Component | Source of every value |
|---|---|
| Runtime decisions table (per scenario) | `stress_test_report.json → subcases` |
| Runtime decision rollup | counted from the above at render time |
| Stages-not-executed card | static statement of fact + links to Experiment 2 |
| Latency (measured) | `stress_latency_report.json` (new) |
| Throughput (measured) | `experiments/stress/concurrency_scaling.json` (existing) |
| Predicate statistics | `experiments/predicate_coverage/predicate_coverage.json` (existing) |
| Claims supported / Research interpretation | `claims_registry.py`, `dashboard_registry.py` |

### Replay / Evidence Quad / Independent verifier — not fabricated

The stress layer is `C-2`, an illustrative scenario layer. It executes predicate evaluation, Γ
computation and the authorization decision. It **never invokes** replay, the Evidence Quad, or the
independent verifier. The dashboard therefore renders, for each of those three stages:

> **Not executed in this experiment** — evaluated independently in **Experiment 2**.

with a working cross-reference to the Experiment 2 card. `Replay agreement`, `Evidence agreement`
and `Verifier agreement` in the stress summary read **Not applicable**, linked to Experiment 2. No
replay hash, evidence hash, or verifier verdict is invented for the stress scenarios.

---

## 4. Cross-references added

* Every experiment card now lists **Claims supported** (hover shows the claim statement),
  **Reviewer concern**, **Figures produced**, **Tables produced**, **Generated files** — or
  `Not applicable` where the registry declares none.
* Every experiment card carries a collapsible **Research interpretation** (purpose, scientific
  motivation, why it exists, and — where the registry records one — what it does *not* demonstrate).
* Stress section links to `#E2` (replay/evidence/verifier) and `#E9` (predicate coverage).
* Internal-link audit: **45 anchors, 44 internal links, 0 broken.**

---

## 5. New artifact

`stress_latency_report.json` — produced by `experiments/profile_stress_scenarios.py`, an **external
wrapper** that imports `stress_test.py` through its public entry points and times them with
`time.perf_counter()`. It does not modify `stress_test.py` and does not modify
`stress_test_report.json`.

Measured (2000 invocations per scenario), as recorded by the `RUN_ALL_EXPERIMENTS.py` run above.
These are wall-clock measurements and will differ on the next run; they are not frozen constants.

| Scenario | Γ decisions | Mean (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---|---|---|---|---|
| P1 | 1 | 0.0052 | 0.0056 | 0.0057 | 0.0176 |
| P2 | 3 | 0.0059 | 0.0061 | 0.0063 | 0.0201 |
| P3 | 4 | 0.0072 | 0.0075 | 0.0076 | 0.0180 |
| P4 | 1 | 0.0046 | 0.0048 | 0.0049 | 0.0187 |
| All | 9 | 0.0058 | 0.0074 | 0.0075 | 0.0201 |

It measures **predicate evaluation + Γ computation + authorization decision** only. It explicitly
records `not_executed` for replay generation, Evidence-Quad assembly and independent verification.

---

## 6. Throughput and the GIL (disclosed negative result C9)

Reused verbatim from the existing concurrency campaign (200,000 decisions per level):

| Threads | Decisions/s | Speed-up |
|---|---|---|
| 1 | 231,588 | 1.00× |
| 2 | 232,198 | 1.00× |
| 4 | 218,562 | 0.94× |
| 8 | 63,917 | 0.28× |
| 64 | 49,195 | 0.21× |

The bottleneck is **interpreter serialization (CPython GIL)**, not CPU, I/O, or replay. Throughput is
flat to ~4 threads and degrades beyond. This is a limitation of the reference implementation, not of
the architecture, and it is reported as a **negative result**, not a scaling claim. Authorization
correctness holds at every thread count: **0 false permits, 0 false denials.**

---

## 7. No duplicated computations introduced

Confirmed by the Part 10 audit before any code was written:

* Wilson intervals — **read**, not recomputed.
* Throughput — **read**, not re-measured.
* Predicate coverage — **read** from Experiment 9, not re-derived.
* Γ, decisions, class veto, failed predicates, `fail_closed_ok` — **read** from the runtime report.
* Claims, reviewer concerns, figures, tables, interpretations — **read** from the registries.

Dead helpers from earlier iterations were removed; no duplicate HTML or logic remains.

---

## 8. Scientific integrity preserved

`python RUN_ALL_EXPERIMENTS.py` was executed after implementation. All artifacts were hashed before
and after and diffed field-by-field.

**Correctness invariants — all held, exactly:**

| Invariant | Before | After |
|---|---|---|
| E9 predicate coverage rate | 1.0 | 1.0 |
| E9 covered predicates | 13 | 13 |
| E9 single-deficit denial rate | 1.0 | 1.0 |
| E9 cases passed | 23 | 23 |
| E4 total false permits | 0 | 0 |
| E4 total false denials | 0 | 0 |
| E4 all authorization correct | True | True |
| E4 ledger consistent | True | True |
| `stress_test_report.json` | byte-identical | byte-identical |
| `gamma_summary.json` | byte-identical | byte-identical |

**Honest disclosure — `RUN_ALL_EXPERIMENTS.py` is not byte-idempotent.** Re-running it changed 15
substantive fields. Every one is a **wall-clock measurement or a value derived from one**: latency
mean/p95/p99, throughput, thread speed-up, and `replay.pct_of_end_to_end`. Cascading `sha256`/`bytes`
entries in `evidence_manifest.json`, `run_index.json` and `provenance_graph.json` follow from those
re-measured files.

This behaviour **predates this change**: `gamma_bundle/reproducibility/evidence_manifest.json` still
records `pct_of_end_to_end = 4.9567`, the repository root recorded `4.6886`, and this run produced
`4.4617` — three different values from three different runs, the first two written before this task
began. Re-measurement across runs is inherent to timing metrics; it is not caused by these changes,
and it does not touch a single correctness metric.

No engine, predicate, decision path, replay engine, verifier, evidence generator, figure, table or
published claim was modified.

---

## 9. Reproducibility

* `experiments/profile_stress_scenarios.py` and `experiments/generate_predicate_flow_figure.py` are
  wired into `RUN_ALL_EXPERIMENTS.py`, so the whole pipeline remains one command.
* Dashboard structure after the full run: **34/34 sections, tags balanced, 0 broken anchors,
  0 tracebacks, 0 `None` leakage.**
* `RUN_ALL_EXPERIMENTS.py` exit 0 — 10/10 experiments, 16/16 claims, 11/11 reviewer concerns,
  10 figures, 5 tables, 1 disclosed negative result.

---

## 10. Defect found, reported, not silently patched

`experiments/predicate_coverage/predicate_coverage.json` records:

```json
"wilson95": { "low": 1.0, "high": 0.7719046276458016, "n": 13, "successes": 13 }
```

The bounds are **transposed** — `low > high`. Silently swapping them would edit a published metric,
which the rules forbid; silently printing them would display an impossible interval. The dashboard
therefore renders the interval in ascending order **and states that the source record has the fields
transposed, with the values unchanged**.

**This should be fixed at the source** in the Experiment 9 generator (a one-line ordering fix in the
Wilson helper). It is left for the maintainer because correcting it changes a published metric, which
is outside the mandate of this presentation-only task.

---

## 11. Files

**Created**
* `experiments/profile_stress_scenarios.py` — external latency profiler (wrapper; modifies nothing)
* `stress_latency_report.json` — new measurement artifact
* `experiments/generate_predicate_flow_figure.py`, `experiments/figures/fig_predicate_evaluation_flow.{svg,png}`
* `DASHBOARD_COMPLETION_REPORT.md` — this file

**Modified (presentation only)**
* `experiments/dashboard_science.py` — subcase surfacing, rollups, latency/throughput/coverage cards, not-executed card
* `experiments/generate_dashboard_html.py` — claims + research interpretation on experiment cards; badge CSS
* `RUN_ALL_EXPERIMENTS.py` — registers the two new generator steps

**Deleted**
* `specs/STRESS_SCENARIO_PREDICATE_EXPECTATIONS.json` — duplicate specification; single source of
  truth restored to `stress_test.py` + `stress_test_report.json`

**Unmodified, verified**
* Gamma engine, `evaluate_decision()`, authorization logic, predicate evaluation, replay engine,
  Evidence Quad, independent verifier, benchmark logic, paper figures, paper tables, provenance chain.

---

## 12. Remaining limitations

1. `RUN_ALL_EXPERIMENTS.py` is not byte-idempotent for timing metrics (§8). Correctness metrics are.
2. The transposed Wilson interval in `predicate_coverage.json` (§10) is disclosed, not fixed.
3. P2/P3/P4 record subcase Γ decisions but **no per-predicate vector**; `gamma_decision()` returns
   only the failed-predicate names, so the full predicate table exists for P1 only. The dashboard
   states this rather than inferring the missing predicates.
4. Decision correctness at the *scenario* level is 4/4 via each scenario's fail-closed rule. Only P1
   declares a single bare decision token in `expected_outcome`; P2–P4 declare compound free text
   ("MIXED (A/C fail-closed; B oracle gap)"), so they are adjudicated by the fail-closed rule rather
   than by string equality. This is stated in the dashboard.
5. E7 (AgentDojo end-to-end) remains blocked on `ollama + llama3.1:8b`; boundary FPR is measured
   without an LLM. Pre-existing and already disclosed.
