# Table 13 — Concurrency Scaling (measured)

- Workload: 200000 frozen Gamma decisions (100000 PERMIT / 100000 SAFE_STATE)
- Concurrency model: python threads (GIL-bound reference decision path) · host cpu_count=10
- Authorization correct at every level: **True** · ledger consistent: **True** · false permits: 0 · false denials: 0

| threads | throughput (dec/s) | speedup | scaling eff. | p50 (ms) | p95 (ms) | p99 (ms) | queue delay mean (ms) | CPU util | peak RSS (MB) | auth correct | FP | FD | ledger ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 234087 | 1.00× | 1.00 | 0.00229 | 0.00254 | 0.00279 | 575.6304 | 1.01 | 156.6 | True | 0 | 0 | True |
| 2 | 229370 | 0.98× | 0.49 | 0.00233 | 0.00254 | 0.00308 | 576.3146 | 1.01 | 162.6 | True | 0 | 0 | True |
| 4 | 215529 | 0.92× | 0.23 | 0.00233 | 0.00275 | 0.00367 | 600.0380 | 1.06 | 166.8 | True | 0 | 0 | True |
| 8 | 70929 | 0.30× | 0.04 | 0.00262 | 0.00446 | 0.00512 | 1675.5828 | 1.59 | 169.6 | True | 0 | 0 | True |
| 16 | 53768 | 0.23× | 0.01 | 0.00329 | 0.00467 | 0.00554 | 2001.4214 | 1.66 | 172.8 | True | 0 | 0 | True |
| 32 | 48718 | 0.21× | 0.01 | 0.00350 | 0.00475 | 0.00567 | 2161.7320 | 1.67 | 180.9 | True | 0 | 0 | True |
| 64 | 50053 | 0.21× | 0.00 | 0.00342 | 0.00492 | 0.00675 | 1935.8092 | 1.65 | 189.3 | True | 0 | 0 | True |

> Note: the reference decision path is pure-Python and GIL-bound, so thread throughput does not scale linearly; the scientifically load-bearing result is that **authorization correctness, ledger consistency, and replay consistency hold at every thread count with zero false permits/denials**. Process-level parallelism is the route to CPU-parallel throughput and is noted as future work.