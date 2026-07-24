# REPRODUCIBILITY AUDIT (auto-generated)

Everything required to reproduce the evaluation, captured from the execution metadata.

## Environment
- Platform: `macOS-26.5.1-arm64-arm-64bit`
- Machine: `arm64` · CPU: `Apple M5` · cores: 10
- Memory: 17.2 GB
- Python: `3.9.6` (`/Users/sukhmangill/Documents/GitHub/Independent Benchmark and Reviewer-Closure Framework for L-DREA/.venv/bin/python`)
- Git HEAD: `264b9ec378a3c0b0984fdf25cdee98c93e024f70` (dirty: True)
- Evaluation seed: `20260709`
- Java/TLC (E3 optional step): Temurin JRE 21 + tla2tools (fetched to ~/.ldrea_tla)

## Execution order, timestamps, runtime, and reproduction commands
| Exp | Status | Started (UTC) | Runtime (s) | Reproduction command |
|-----|--------|---------------|-------------|----------------------|
| E1 | EXECUTED | 2026-07-11T17:36:49Z | 12.854 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| E10 | EXECUTED | 2026-07-11T17:44:56Z | 15.999 | `./.venv/bin/python tools/export_audit_bundle.py && ./.venv/bin/python concurbench_full.py` |
| E11 | EXECUTED | None | 24.75 | `./.venv/bin/python experiments/run_runtime_stack.py --n 8000` |
| E12 | EXECUTED | None | 281.31 | `./.venv/bin/python experiments/run_dataset_eval.py --limit 100000` |
| E2 | EXECUTED | 2026-07-11T17:37:13Z | 1.102 | `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl` |
| E3 | EXECUTED | 2026-07-11T17:37:15Z | 0.467 | `./.venv/bin/python independent_verifier.py` |
| E4 | EXECUTED | 2026-07-11T17:37:17Z | 14.271 | `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress', 200000, [1, 2, 4, 8, 16, 32, 64])"` |
| E5 | EXECUTED | 2026-07-11T17:37:32Z | 1.979 | `./.venv/bin/python experiment_ablation.py` |
| E5b | EXECUTED | 2026-07-11T17:37:34Z | 120.551 | `./.venv/bin/python experiment_combined_ablation.py` |
| E6 | EXECUTED | 2026-07-11T17:39:35Z | 2.12 | `./.venv/bin/python -c "from agentdojo_integration.audit import runtime_profile as r; r.run('experiments/profiling', 5000)"` |
| E7 | EXECUTED | 2026-07-11T17:39:37Z | 10.33 | `agentdojo_integration/.venv/bin/python experiment_agentdojo_metrics.py` |
| E8 | EXECUTED | 2026-07-11T17:39:47Z | 1.4 | `./.venv/bin/python experiment_robustness.py` |
| E9 | EXECUTED | 2026-07-11T17:39:49Z | 0.738 | `./.venv/bin/python experiment_predicate_coverage.py` |

## Artifact checksums (SHA-256)
| Artifact | SHA-256 | bytes |
|----------|---------|-------|
| `experiments/runtime_correctness/gamma_lab_v1_report.json` | `faad378d2c2d3e5b3ab678ba17ea4028…` | 11694 |
| `experiments/runtime_correctness/gamma_summary.json` | `81d10dc03f4b53d9b07c3ccafba9c650…` | 3514 |
| `experiments/runtime_correctness/gamma_validation_results.csv` | `f45ebb23b52be3cc982b6b691edc137f…` | 133854351 |
| `experiments/runtime_correctness/full_spec_conformance_report.json` | `aaeed075ff566fb6daeadb1449e43a71…` | 9789 |
| `experiments/runtime_correctness/fcr_test_report.json` | `f06256d9a3ff8e9425c5b26335d63c84…` | 1805 |
| `experiments/runtime_correctness/stress_test_report.json` | `0930130a271738fc67ca1ca2eee42218…` | 14958 |
| `experiments/runtime_correctness/concurbench_full_report.json` | `9a63489d53f2cbaaa00f10dd6a374ec4…` | 75622 |
| `experiments/audit_bundle/audit_bundle_report.json` | `ca8d22d996ebf613fa84aa3937fa1598…` | 1023 |
| `experiments/replay/replay_report.json` | `f57b238f785b6ea34f67dbd0a6e40349…` | 529 |
| `gamma_replay_manifest.jsonl` | `1ce2a9e8d4330a0583a9d20a398de432…` | 200966760 |
| `experiments/formal/independent_verifier_report.json` | `1d20111a7cec3d293c16ea51b50aaca6…` | 1300 |
| `experiments/stress/concurrency_scaling.json` | `e6b2c209c62f70606f5314161fa3e265…` | 7141 |
| `experiments/stress/concurrency_scaling.csv` | `2fc8d389b35580a99ba6665c7b312eff…` | 1092 |
| `experiments/ablation/ablation.json` | `63defeb892b96a1565f9397e6cc3a948…` | 5844 |
| `experiments/ablation/ablation.csv` | `fefee215e380c94de783b813c301c777…` | 478 |
| `experiments/ablation/ablation_log.jsonl` | `84e25fd4f8a04b2566bdfeb584391503…` | 2270 |
| `experiments/combined_ablation/combined_ablation.json` | `143ef86da1e81a750549ae6033945fd9…` | 166979 |
| `experiments/combined_ablation/combined_ablation.csv` | `29462051776fc69acd377900bb4f048e…` | 2756 |
| `experiments/combined_ablation/combined_ablation_matrix.csv` | `46e7975c4aeaff7e7f3d1d28eec4724e…` | 1072 |
| `experiments/profiling/runtime_profile.json` | `d386ebcb2ee3dde9dddccea2cd063a7a…` | 984 |
| `experiments/profiling/stage_distributions.json` | `854061ca16fd3269a997f0e62f97c719…` | 1258 |
| `experiments/agentdojo/statistics.json` | `342cdb2224332b64dba0ea8417d2d835…` | 10903 |
| `experiments/agentdojo/boundary/boundary_fpr.json` | `cde16292bdcaad813b6c6a1e28505ec6…` | 4365 |
| `experiments/agentdojo/e7_metrics.json` | `5879bd58ad0c51efdf2369368e21f88a…` | 5903 |
| `experiments/robustness/robustness.json` | `9f1abfbd7d74d30a32a25f2b67fbf105…` | 9490 |
| `experiments/robustness/robustness.csv` | `19d188eb6677e4921c4be4958811986c…` | 1606 |
| `experiments/robustness/robustness_log.jsonl` | `b6666020c34b06112c203b19caa0c565…` | 9611 |
| `experiments/predicate_coverage/predicate_coverage.json` | `94315e89052a6d008af335976ea1a341…` | 18050 |
| `experiments/predicate_coverage/predicate_coverage.csv` | `15255956a4c800ec4d18a2378780c4af…` | 2180 |
| `experiments/predicate_coverage/predicate_coverage_log.jsonl` | `cf469e31e3887ddc10d96119a66d7c8a…` | 10563 |

## One-command reproduction
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py        # full suite (E1–E8) + generators
./.venv/bin/python validate_paper_claims.py       # numerical-claim validation
./.venv/bin/python scientific_consistency.py      # consistency + provenance audit
```