# Experiment 4 — Runtime Stress Evaluation

Status: **EXECUTED** · 14.3s · 200,000 decisions/level

| threads | throughput (dec/s) | p50 ms | p95 ms | p99 ms | RSS MB | FP | FD | correct |
|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
| 1 | 355,151 | 0.00150 | 0.00183 | 0.00192 | 2124.1 | 0 | 0 | T |
| 2 | 408,922 | 0.00129 | 0.00146 | 0.00154 | 2124.1 | 0 | 0 | T |
| 4 | 318,723 | 0.00154 | 0.00192 | 0.00300 | 2124.1 | 0 | 0 | T |
| 8 | 95,098 | 0.00200 | 0.00325 | 0.00379 | 2124.1 | 0 | 0 | T |
| 16 | 75,342 | 0.00213 | 0.00337 | 0.00400 | 2124.1 | 0 | 0 | T |
| 32 | 71,116 | 0.00225 | 0.00350 | 0.00417 | 2124.1 | 0 | 0 | T |
| 64 | 69,797 | 0.00233 | 0.00350 | 0.00417 | 2124.1 | 0 | 0 | T |

Global: FP 0 · FD 0 · all-correct True · all-ledger-consistent True

Reproduce: `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress', 200000, [1, 2, 4, 8, 16, 32, 64])"`
