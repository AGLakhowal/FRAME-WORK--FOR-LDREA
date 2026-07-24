# Table 13 — Concurrency Scaling (measured)

- Workload: 200000 frozen Gamma decisions (100000 PERMIT / 100000 SAFE_STATE)
- Concurrency model: python threads (GIL-bound reference decision path) · host cpu_count=10
- Authorization correct at every level: **True** · ledger consistent: **True** · false permits: 0 · false denials: 0

| threads | throughput (dec/s) | speedup | scaling eff. | p50 (ms) | p95 (ms) | p99 (ms) | queue delay mean (ms) | CPU util | peak RSS (MB) | auth correct | FP | FD | ledger ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 227771 | 1.00× | 1.00 | 0.00237 | 0.00263 | 0.00279 | 587.8247 | 1.00 | 155.9 | True | 0 | 0 | True |
| 2 | 224981 | 0.99× | 0.49 | 0.00238 | 0.00263 | 0.00300 | 604.4907 | 0.99 | 158.7 | True | 0 | 0 | True |
| 4 | 216123 | 0.95× | 0.24 | 0.00233 | 0.00258 | 0.00342 | 618.0540 | 1.04 | 160.8 | True | 0 | 0 | True |
| 8 | 59496 | 0.26× | 0.03 | 0.00313 | 0.00446 | 0.00517 | 1831.0591 | 1.61 | 163.3 | True | 0 | 0 | True |
| 16 | 51313 | 0.23× | 0.01 | 0.00333 | 0.00467 | 0.00554 | 2069.7141 | 1.64 | 168.9 | True | 0 | 0 | True |
| 32 | 49004 | 0.22× | 0.01 | 0.00346 | 0.00475 | 0.00563 | 2149.5869 | 1.64 | 178.8 | True | 0 | 0 | True |
| 64 | 48867 | 0.21× | 0.00 | 0.00342 | 0.00462 | 0.00558 | 2125.6820 | 1.65 | 190.8 | True | 0 | 0 | True |

> Note: the reference decision path is pure-Python and GIL-bound, so thread throughput does not scale linearly; the scientifically load-bearing result is that **authorization correctness, ledger consistency, and replay consistency hold at every thread count with zero false permits/denials**. Process-level parallelism is the route to CPU-parallel throughput and is noted as future work.