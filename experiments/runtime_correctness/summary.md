# Experiment 1 — Runtime Authorization Correctness

Status: **EXECUTED**  ·  duration 12.854s  ·  N = 284,807 transactions

## Confusion matrix (authorization decision vs golden-trace expected outcome)
- True permits (TP): 284,315
- True denials (TN): 492
- False permits (FP): 0
- False denials (FN): 0

## Primary metrics (with Wilson 95% bounds)
- Unauthorized executions (UER): 0 / 284,807
- False Permit Rate: 0 / 492 (cluster-corrected Wilson95↑ 1.312e-02)
- False Denial Rate: 0 / 284315
- Replay Determinism Rate: 1.0
- Class-Veto Effectiveness: 1.0
- TOCTOU violations: 0
- Runtime invariants: 6/6 hold
- Latency mean/p95/p99 (ms): 0.0259 / 0.0323 / 0.0377

Reproduce: `./.venv/bin/python gamma_test_runner.py --no-html --no-open`