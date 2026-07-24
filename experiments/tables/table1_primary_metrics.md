# Table I — L-DREA Tier-S Reference Evaluation: Primary Metrics

All values produced by executing the stable engine code; none are hardcoded. CI = 95% confidence (Wilson for rates; bracket = interval, ↑ = one-sided upper bound).

| Metric | Value | 95% CI | N | Exp | Reproduction command |
|--------|-------|--------|---|-----|----------------------|
| False Permit Rate (ULB) | 0/492 | Wilson95↑ 1.312e-02 | 492 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| False Denial Rate (ULB) | 0/284315 | — | 284,315 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Unauthorized Executions (UER) | 0/284807 | — | 284,807 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Replay Determinism Rate | 1.0 | — | 284,807 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Class-Veto Effectiveness | 1.0 | — | 492 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Decision latency mean (ms) | 0.0259 | p95 0.0323 / p99 0.0377 | 284,807 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Authorization Accuracy | 1.000000 | TP 284315/TN 492/FP 0/FN 0 | 284,807 | E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| Replay hash-chain adjacency failures | 0 | — | 284,807 | E2 | `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl` |
| Replay ledger-bind failures | 0 | — | 284,807 | E2 | `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl` |
| Formal state-space coverage | 65536/65536 | complete | 65,536 | E3 | `./.venv/bin/python independent_verifier.py` |
| Decision-equivalence field mismatches | 0 | verdict IDENTICAL | 65,536 | E3 | `./.venv/bin/python independent_verifier.py` |
| Throughput @1 / @64 threads (dec/s) | 355,151 / 69,797 | speedup 0.197× | 200,000 | E4 | `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])"` |
| False permits/denials under load (all levels) | 0/0 | all-correct True | 1,400,000 | E4 | `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])"` |
| Leaked permits: baseline_full_LDREA | 0/60000 | [0.0000, 0.0001] | 60,000 | E5 | `./.venv/bin/python experiment_ablation.py` |
| Leaked permits: remove_class_veto | 15000/60000 | [0.2466, 0.2535] | 60,000 | E5 | `./.venv/bin/python experiment_ablation.py` |
| Leaked permits: remove_noncompensatory_gamma | 15000/60000 | [0.2466, 0.2535] | 60,000 | E5 | `./.venv/bin/python experiment_ablation.py` |
| Leaked permits: remove_authorization_layer | 45000/60000 | [0.7465, 0.7534] | 60,000 | E5 | `./.venv/bin/python experiment_ablation.py` |
| AgentDojo boundary FPR (foreign targets) | 0/62 | Wilson95↑ 5.834e-02 | 62 | E7 | `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py` |
| AgentDojo permit rate (recorded episodes) | 0.786 | [0.524, 0.924] | 14 | E7 | `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py` |
| Robustness: false permits across all faults | 0/51 | safety holds 16/16 families | 51 | E8 | `./.venv/bin/python experiment_robustness.py` |