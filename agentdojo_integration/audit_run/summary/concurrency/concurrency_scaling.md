# Table 13 — Concurrency Scaling (measured)

- Workload: 200000 frozen Gamma decisions (100000 PERMIT / 100000 SAFE_STATE)
- Concurrency model: python threads (GIL-bound reference decision path) · host cpu_count=10
- Authorization correct at every level: **True** · ledger consistent: **True** · false permits: 0 · false denials: 0

| threads | throughput (dec/s) | speedup | scaling eff. | p50 (ms) | p95 (ms) | p99 (ms) | queue delay mean (ms) | CPU util | peak RSS (MB) | auth correct | FP | FD | ledger ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 390766 | 1.00× | 1.00 | 0.00146 | 0.00167 | 0.00196 | 340.0020 | 1.00 | 141.3 | True | 0 | 0 | True |
| 2 | 384099 | 0.98× | 0.49 | 0.00146 | 0.00167 | 0.00196 | 347.0039 | 1.00 | 143.6 | True | 0 | 0 | True |
| 4 | 372103 | 0.95× | 0.24 | 0.00150 | 0.00167 | 0.00221 | 353.1226 | 1.02 | 146.4 | True | 0 | 0 | True |
| 8 | 221655 | 0.57× | 0.07 | 0.00171 | 0.00258 | 0.00354 | 532.6937 | 1.36 | 148.6 | True | 0 | 0 | True |
| 16 | 74525 | 0.19× | 0.01 | 0.00187 | 0.00321 | 0.00492 | 1379.2673 | 1.89 | 153.0 | True | 0 | 0 | True |
| 32 | 59830 | 0.15× | 0.00 | 0.00208 | 0.00308 | 0.00400 | 1604.6645 | 1.97 | 163.0 | True | 0 | 0 | True |

> Note: the reference decision path is pure-Python and GIL-bound, so thread throughput does not scale linearly; the scientifically load-bearing result is that **authorization correctness, ledger consistency, and replay consistency hold at every thread count with zero false permits/denials**. Process-level parallelism is the route to CPU-parallel throughput and is noted as future work.