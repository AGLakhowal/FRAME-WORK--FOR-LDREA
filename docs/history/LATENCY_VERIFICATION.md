# LATENCY_VERIFICATION

All latencies are measured with `time.perf_counter()` deltas recorded at event emission; sample
counts and distribution statistics are recomputed from the raw values.

## Measurement functions
- **Gamma decision overhead (Table 11):** `execution_tracer` wraps the frozen `GammaBridge.decide` /
  Γ-COMPUTATION path; `processing_time_ms` on `Γ COMPUTATION` + `GLOBAL_POLICY_EVALUATION` events.
  Start/end = `perf_counter()` immediately around the frozen call; unit ms.
- **Per-stage core (Table 10):** Campaign-7 harness (`PERFORMANCE_RESULTS.json`), n=2000 rows.
- **Runtime Context / Replay (Table 10):** `runtime_profile.py` timer wrappers, n=5000.
- **Concurrency latency (Table 13):** `concurrency_scaling._run_level` times each `bridge.decide`;
  percentiles via `numpy.percentile`.

## Gamma decision overhead — recomputed from 14 raw samples (verify_provenance.py)
| stat | value (ms) |
|---|---|
| sample count | 14 |
| mean | 0.021593 → **0.0216** (paper) |
| median | 0.0172 |
| min | 0.0079 |
| max | 0.0587 |
| std | 0.014352 |
| q1 / q3 | 0.011625 / 0.027925 |

Recomputed mean (independent) 0.021592857 matches stored `gamma_decision_overhead.mean` (PASS).
*(P95/P99 not part of the Table-11 headline; the full 14-sample vector is in the traces and
`statistics.json`.)*

## Concurrency latency (Table 13) — measured percentiles per level
| threads | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | mean (ms) | samples |
|---|---|---|---|---|---|---|
| 1 | 0.00146 | 0.00167 | 0.00196 | — | measured | 200,000 |
| 8 | 0.00171 | 0.00258 | 0.00354 | — | measured | 200,000 |
| 32 | 0.00208 | 0.00308 | 0.00400 | — | measured | 200,000 |
(full 6-level table in `concurrency_scaling.{json,csv,md}`; percentiles via numpy over 200k samples/level.)

## Measurement overhead
- Logging overhead per event = the recorded `perf_counter` delta only; the wrappers call the original
  and return its unchanged value (observer effect verified null on the deterministic authorization
  layer — see `EXECUTION_TRACE_SYSTEM.md`, traced==clean env-hash identical).
- Concurrency queue delay (enqueue→dequeue) is measured and reported separately per level
  (`queue_delay_ms`), so scheduling wait is not conflated with decision latency.

## Reference latencies (pre-existing artifacts, unchanged, cited not re-run)
- Replay generation/verification (Table IV): `gamma_summary.json` / IEEE_RESULTS_TABLES.md Table IV
  (gen mean 2.01 ms, verify mean 41.1 ms) — earlier campaign, not regenerated (per freeze rule).

**LATENCY VERIFICATION: PASS (means/medians/percentiles recompute from raw samples; counts match).**
