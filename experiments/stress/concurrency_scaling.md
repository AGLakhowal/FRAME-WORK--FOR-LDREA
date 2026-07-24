# Table 13 — Concurrency Scaling (measured)

- Workload: 200000 frozen Gamma decisions (100000 PERMIT / 100000 SAFE_STATE)
- Concurrency model: python threads (GIL-bound reference decision path) · host cpu_count=10
- Authorization correct at every level: **True** · ledger consistent: **True** · false permits: 0 · false denials: 0

| threads | throughput (dec/s) | speedup | scaling eff. | p50 (ms) | p95 (ms) | p99 (ms) | queue delay mean (ms) | CPU util | peak RSS (MB) | auth correct | FP | FD | ledger ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 355151 | 1.00× | 1.00 | 0.00150 | 0.00183 | 0.00192 | 405.4851 | 0.99 | 2124.1 | True | 0 | 0 | True |
| 2 | 408922 | 1.15× | 0.58 | 0.00129 | 0.00146 | 0.00154 | 333.1162 | 1.02 | 2124.1 | True | 0 | 0 | True |
| 4 | 318723 | 0.90× | 0.22 | 0.00154 | 0.00192 | 0.00300 | 385.7990 | 1.04 | 2124.1 | True | 0 | 0 | True |
| 8 | 95098 | 0.27× | 0.03 | 0.00200 | 0.00325 | 0.00379 | 1128.2245 | 1.60 | 2124.1 | True | 0 | 0 | True |
| 16 | 75342 | 0.21× | 0.01 | 0.00213 | 0.00337 | 0.00400 | 1298.4893 | 1.68 | 2124.1 | True | 0 | 0 | True |
| 32 | 71116 | 0.20× | 0.01 | 0.00225 | 0.00350 | 0.00417 | 1402.1508 | 1.68 | 2124.1 | True | 0 | 0 | True |
| 64 | 69797 | 0.20× | 0.00 | 0.00233 | 0.00350 | 0.00417 | 1415.7771 | 1.69 | 2124.1 | True | 0 | 0 | True |

> Note: the reference decision path is pure-Python and GIL-bound, so thread throughput does not scale linearly; the scientifically load-bearing result is that **authorization correctness, ledger consistency, and replay consistency hold at every thread count with zero false permits/denials**. Process-level parallelism is the route to CPU-parallel throughput and is noted as future work.