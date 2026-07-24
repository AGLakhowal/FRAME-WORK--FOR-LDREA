# PAPER_NUMBER_AUDIT

Every distinct number appearing in the scope (Tables 10/11/13, their figures/stats/CIs/latencies),
with reproducibility status. 26/26 independent checks PASS.

## Table 11 numbers
| # | Value | Meaning | Reproducible? |
|---|---|---|---|
| 1 | 33 | episodes | ✅ count of trace dirs |
| 2 | 14 | Gamma decisions | ✅ raw event count |
| 3 | 11 | PERMIT | ✅ |
| 4 | 3 | SAFE_STATE | ✅ |
| 5 | 0.786 | permit rate p̂ | ✅ 11/14 |
| 6 | 0.524 | permit CI low | ✅ Wilson |
| 7 | 0.924 | permit CI high | ✅ Wilson |
| 8 | 0.214 | denial rate | ✅ 3/14 |
| 9 | 0.076 / 0.476 | denial CI | ✅ Wilson |
| 10 | 6 | policy classes | ✅ |
| 11 | 0 | class-veto | ✅ |
| 12 | 33/33, 14 | replay consistent / steps | ✅ ReplayEngine |
| 13 | 0.967 | authorization stability | ✅ 0.96667 |
| 14 | 0.0216 | gamma overhead mean (ms) | ✅ 0.021593 |
| 15 | 0.750 | decision entropy (bits) | ✅ 0.74960 |
| 16 | 3 / 33 | utility successes | ✅ |
| 17 | 1 / 33 | security successes | ✅ |
| 18 | 0 | security via EEA | ✅ trace-verified |
| 19 | 19 | frozen files unchanged | ✅ |
| 20 | n=0 | FPR denominator | ✅ honest undefined |
| 21 | 0.000 / 0.434 | FDR + CI upper | ✅ Wilson (0/5) |

## Table 10 numbers
| # | Value | Meaning | Reproducible? |
|---|---|---|---|
| 22–26 | 0.07436 / 0.10182 / 0.01674 / 0.00220 / 0.00169 | per-stage ms/row | ✅ PERFORMANCE_RESULTS.json |
| 27 | 0.010591 (5.91%) | Runtime Context ms/row | ✅ runtime_profile.json |
| 28 | 0.014996 (8.37%) | Replay ms/row | ✅ runtime_profile.json |
| 29 | 0.19681 | core per-row total | ✅ Σ per_stage_ms |

## Table 13 numbers (per thread level ∈ {1,2,4,8,16,32})
| # | Family | Reproducible? |
|---|---|---|
| 30 | throughput 390766…59830 | ✅ n/wall |
| 31 | speedup 1.00…0.15× | ✅ tp_T/tp_1 |
| 32 | scaling eff. 1.00…0.00 | ✅ tp_T/(T·tp_1) |
| 33 | p50/p95/p99 latency | ✅ numpy percentile |
| 34 | queue delay 340…1604 ms | ✅ dequeue−enqueue |
| 35 | CPU util 1.00…1.97 | ✅ os.times |
| 36 | peak RSS 141.3…163.0 MB | ✅ getrusage |
| 37 | auth-correct / 0 FP / 0 FD / ledger ok | ✅ results==reference |

## Text/summary numbers
- decision entropy, stability, overhead, permit/denial rates as above (BENCHMARK_SUMMARY.md ← statistics.json, consistent — verified reproduce).

**Every number in scope is reproducible. 0 non-reproducible numbers.**
