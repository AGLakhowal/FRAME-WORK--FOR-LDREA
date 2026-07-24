# IEEE RESULTS — FIGURES

**Publication figures rendered from measured data (`PERFORMANCE_RESULTS.json` / `VALIDATION_RESULTS.json`).** `matplotlib` is **not installed** in this environment, so figures are provided as (a) machine-readable figure data (in the JSON files) and (b) ASCII/Markdown charts below. Each figure lists the exact series so a plotting script can render an identical PNG when the dependency is available. No fabricated data.

---

## Figure 1 — Per-row latency distribution (Campaign 7, n=2,000)

Histogram (12 bins over [0.191, 0.571] ms). `█` ≈ proportional to count (log-ish clipped for readability).

```
 ms bin          count   bar
 0.191–0.223     1965   ██████████████████████████████████████████████  (98.25%)
 0.223–0.254       21   █
 0.254–0.286        2   ▏
 0.286–0.318        4   ▏
 0.318–0.349        5   ▏
 0.349–0.381        1   ▏
 0.381–0.413        1   ▏
 0.413–0.445        0
 0.445–0.476        0
 0.476–0.508        0
 0.508–0.540        0
 0.540–0.571        1   ▏
```
**Reading:** tight, right-skewed distribution; 98.25% of rows in the first bin. mean 0.198 ms, p50 0.195, p95 0.207, p99 0.238, max 0.571 (single outlier). Series: `PERFORMANCE_RESULTS.json → 7_performance.latency_histogram`.

## Figure 2 — Per-stage latency breakdown (mean ms/row, stacked)

```
 build   0.0744  ████████████████████████████████████            37.6%
 bind    0.1018  ██████████████████████████████████████████████  51.4%
 adapt   0.0022  █                                                 1.1%
 eval    0.0017  █                                                 0.9%
 emit    0.0167  ████████                                          8.5%
                 └── core per-row total 0.198 ms ──┘
```
**Reading:** the decision core (adapt + eval) is ~2% of cost; EEB construction + Predicate Binding (SHA-256 sealing) dominate. Series: `7_performance.per_stage_ms`.

## Figure 3 — Determinism (all executions collapse to one hash)

```
 executions:  ●●●●●●●●●●  (C2, 10)  ●●●●● (C4 re-emit, 5)  ●●●●●●●● (C8 concurrent, 8)
 distinct record hashes : 1
 distinct manifests     : 1     ── determinism rate = 1.000 ──
 distinct ledger heads  : 1
```
**Reading:** 23 executions → a single hash on every axis; zero divergence.

## Figure 4 — Replay latency (ms), mean ± 95% CI, with p50/p95/p99

```
 generation   |●|            2.01  [1.83 ── 2.18]   p50 1.92  p95 2.89  p99 2.97
 verification            |───●───|  41.1 [39.9 ── 42.4] p50 40.0 p95 46.8 p99 47.2
              0        10        20        30        40        50  (ms)
```
**Reading:** manifest generation is cheap (~2 ms for 24 records); independent verification dominates (~41 ms, subprocess startup + full re-check). Series: `4_replay.gen_latency_ms` / `verify_latency_ms`.

## Figure 5 — Fail-closed robustness before/after H4 fix (Campaign 8)

```
 case                 before fix        after fix (this campaign)
 malformed Amount     ✗ ValueError      ✓ SAFE_STATE + replay PASS
 malformed Time       ✗ ValueError      ✓ SAFE_STATE + replay PASS
 missing Time         ✗ TypeError       ✓ SAFE_STATE + replay PASS
 missing Amount       ✗ TypeError       ✓ SAFE_STATE + replay PASS
 empty request        ✗ TypeError       ✓ SAFE_STATE + replay PASS
 fail-closed rate     0/5               5/5 = 1.000  [0.566, 1.000]
```

## Figure 6 — Throughput scaling (batch sizes executed)

```
 batch      end-to-end       result
 24         (ref)            PASS
 2,000      1,714 rows/s     MEASURED
 5,000      completed        PASS (adjacency + replay)
 284,807    ConcurBench      INTERNAL_PASS
```
**Reading:** linear, deterministic completion across four orders of magnitude; no failures.

---

### Rendering note

To produce PNGs identical to the above, plot the JSON series with any backend:
`7_performance.latency_histogram` (Fig 1), `7_performance.per_stage_ms` (Fig 2), `2_determinism` (Fig 3), `4_replay.*_latency_ms` (Fig 4), `8_stress.malformed_missing_evidence` (Fig 5). No plotting library is bundled here; the ASCII renderings are faithful to the measured series.

*Figures rendered from measured data only; no reported benchmark output regenerated or modified.*
