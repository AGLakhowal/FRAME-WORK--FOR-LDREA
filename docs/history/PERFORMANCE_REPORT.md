# PERFORMANCE REPORT — Class-blind Runtime Pipeline (post-H4)

**Measurement only. No optimisation, no redesign, no methodology change.** All numbers from executing the frozen components; raw data in `PERFORMANCE_RESULTS.json`. Single host, Python 3.9 venv (pandas/numpy; no matplotlib/scipy).

**Method:** per-stage and per-row latency instrumented over **n = 2,000** well-formed requests through the exact operations the Phase-A orchestrator performs (`build_evidence_bundle` → `PredicateBinding.bind` → `decision_inputs_from_eeb` → frozen `evaluate_decision` → `ReportedArtifactEmitter.emit`); end-to-end throughput and peak memory measured over a full `run_pipeline`; replay costs over n = 20. `time.perf_counter`; `tracemalloc` for memory.

---

## 1. Latency

| Metric | Value |
|---|---|
| Core per-row latency (mean) | **0.198 ms** |
| 95% CI on the mean | [0.19717, 0.19841] ms |
| Std. dev | 0.0141 ms |
| p50 / p90 / p95 / p99 | 0.195 / 0.203 / 0.207 / 0.238 ms |
| min / max | 0.191 / 0.571 ms |

Distribution is tight and right-skewed (98.25% of rows in [0.191, 0.223] ms; a single 0.571 ms outlier) — see `IEEE_RESULTS_FIGURES.md` Fig 1.

## 2. Per-stage cost (mean ms/row)

| Stage | ms/row | Share |
|---|---|---|
| build_evidence_bundle (Runtime Context → sealed EEB) | 0.0744 | 37.6% |
| Predicate Binding (bind → bound EEB) | 0.1018 | 51.4% |
| EEB→Engine Adapter | 0.0022 | 1.1% |
| evaluate_decision (frozen engine) | 0.0017 | 0.9% |
| Reported Artifact Emitter (serialization) | 0.0167 | 8.5% |
| **Core total** | **0.198** | 100% |

**Observation (no action taken):** the authorization core (adapter + engine) is ~0.004 ms/row (2% of cost). Cost is dominated by evidence-bundle sealing and predicate binding, both SHA-256 canonicalization over the payload. This is inherent to the tamper-evidence design, not a hotspot to optimise here.

## 3. Throughput & orchestration

| Metric | Value |
|---|---|
| End-to-end throughput (`run_pipeline`, 2,000 rows) | **1,714 rows/s** |
| End-to-end per-row | 0.583 ms/row |
| Orchestration overhead (end-to-end − core-stage sum) | 0.387 ms/row |
| Replay manifest generation | 0.0137 ms/row |

**Note:** the orchestration overhead (per-call `dict(req)` copy, deterministic envelope-label formatting, `_observable` indirection, and object allocation/GC) exceeds the instrumented core-stage sum; it is reported as measured, not tuned. Timing varies run-to-run (a prior run measured 1,206 rows/s); absolute throughput is indicative, not a competitive claim (see Threats to Validity in the main report).

## 4. Memory

| Metric | Value |
|---|---|
| Peak (tracemalloc, 2,000-row `run_pipeline`) | 5,126 KB |
| Peak per row | ~2,624 B |

Memory scales linearly and modestly with batch size (records + sealed EEBs held transiently per row).

## 5. Replay cost (n = 20)

| Operation | mean (ms) | 95% CI | p50 | p95 | p99 |
|---|---|---|---|---|---|
| Manifest generation (24 records) | 2.01 | [1.83, 2.18] | 1.92 | 2.89 | 2.97 |
| Independent verification (subprocess) | 41.1 | [39.9, 42.4] | 40.0 | 46.8 | 47.2 |

Verification cost is dominated by Python subprocess startup + a full independent re-check; generation is cheap.

## 6. Scaling

| Batch | Result | Note |
|---|---|---|
| 2,000 | 1,714 rows/s | performance sample |
| 5,000 | PASS | large-batch stress; adjacency + replay PASS |
| 284,807 | INTERNAL_PASS | ConcurBench full run (~15 s) |

Deterministic linear completion across scales; no failures, no memory blow-up.

## 7. Summary

The pipeline sustains ~1.7k rows/s end-to-end with ~0.2 ms core per-row latency and ~2.6 KB/row peak memory; the decision core is negligible and cost is dominated by cryptographic sealing/binding (by design). Replay generation is ~2 ms; independent verification ~41 ms (subprocess-bound). **Measurement only — no optimisation performed.**

---

*Performance report only. No optimisation, no reported-output change. Raw data in `PERFORMANCE_RESULTS.json`.*
