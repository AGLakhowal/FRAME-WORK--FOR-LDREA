# Provenance Graph — traceability of every reported value

Chain: **Raw Log → Metric Engine (code) → JSON → CSV → IEEE Table → Figure**. Each node lists its on-disk sha256 (first 12) proving the artifact exists.

> ✅ All chains intact: every experiment has raw log → metric engine → JSON present.

## E1 — Runtime Authorization Correctness
- **raw_log** ✅ `experiments/runtime_correctness/logs/E1.log`  sha256:`681227143f4e`
- **metric_engine** ✅ `gamma_test_runner.py`  sha256:`6c7ca5717240`
- **metric_engine** ✅ `metrics_engine.py`  sha256:`4f858c8fe477`
- **metric_engine** ✅ `full_spec_conformance.py`  sha256:`dfaa826b37f2`
- **json** ✅ `experiments/runtime_correctness/gamma_lab_v1_report.json`  sha256:`faad378d2c2d`
- **json** ✅ `experiments/runtime_correctness/full_spec_conformance_report.json`  sha256:`aaeed075ff56`
- **csv** ✅ `experiments/runtime_correctness/gamma_validation_results.csv`  sha256:`f45ebb23b52b`
- **table** ✅ `experiments/tables/table1_primary_metrics.md`  sha256:`632a57db881f`
- **figure** ✅ `experiments/figures/fig_authorization_accuracy.svg`  sha256:`9e4ca9018a0d`
- **figure** ✅ `experiments/figures/fig_false_permit_rate.svg`  sha256:`6599651c9c85`

## E2 — Runtime Replay Integrity
- **raw_log** ✅ `experiments/replay/logs/E2.log`  sha256:`6d0e2169dd63`
- **metric_engine** ✅ `gamma_replay_verify.py`  sha256:`d1ec4b5e1134`
- **json** ✅ `experiments/replay/replay_report.json`  sha256:`f57b238f785b`
- **csv**: (none)
- **table** ✅ `experiments/tables/table1_primary_metrics.md`  sha256:`632a57db881f`
- **figure** ✅ `experiments/figures/fig_replay_integrity.svg`  sha256:`3073e0f130dc`

## E3 — Formal Verification
- **raw_log** ✅ `experiments/formal/logs/E3.log`  sha256:`1045b35d07a9`
- **metric_engine** ✅ `independent_verifier.py`  sha256:`b540ac9f81d1`
- **metric_engine** ✅ `formal/ExternalizationMonitor.tla`  sha256:`f38ae8da968e`
- **json** ✅ `experiments/formal/independent_verifier_report.json`  sha256:`1d20111a7cec`
- **csv**: (none)
- **table** ✅ `experiments/tables/table1_primary_metrics.md`  sha256:`632a57db881f`
- **figure**: (none)

## E4 — Runtime Stress Evaluation
- **raw_log** ✅ `experiments/stress/logs/E4.log`  sha256:`4b35f287d310`
- **metric_engine** ✅ `agentdojo_integration/audit/concurrency_scaling.py`  sha256:`edcf0c8de0af`
- **metric_engine** ✅ `metrics_engine.py`  sha256:`4f858c8fe477`
- **json** ✅ `experiments/stress/concurrency_scaling.json`  sha256:`e6b2c209c62f`
- **csv** ✅ `experiments/stress/concurrency_scaling.csv`  sha256:`2fc8d389b355`
- **table** ✅ `experiments/tables/table2_concurrency_scaling.md`  sha256:`f886039583bf`
- **figure** ✅ `experiments/figures/fig_latency.svg`  sha256:`05b7d71beeff`
- **figure** ✅ `experiments/figures/fig_throughput.svg`  sha256:`76ac2522a024`

## E5 — Component Ablation
- **raw_log** ✅ `experiments/ablation/logs/E5.log`  sha256:`c23afc70311a`
- **metric_engine** ✅ `experiment_ablation.py`  sha256:`359dfcec374c`
- **json** ✅ `experiments/ablation/ablation.json`  sha256:`63defeb892b9`
- **csv** ✅ `experiments/ablation/ablation.csv`  sha256:`fefee215e380`
- **table** ✅ `experiments/tables/table1_primary_metrics.md`  sha256:`632a57db881f`
- **figure** ✅ `experiments/figures/fig_component_ablation.svg`  sha256:`2e45b70e9866`

## E6 — Runtime Profiling
- **raw_log** ✅ `experiments/profiling/logs/E6.log`  sha256:`4b35f287d310`
- **metric_engine** ✅ `agentdojo_integration/audit/runtime_profile.py`  sha256:`8b9989eecf30`
- **metric_engine** ✅ `agentdojo_integration/audit/stats_engine.py`  sha256:`ced580838fb5`
- **json** ✅ `experiments/profiling/runtime_profile.json`  sha256:`d386ebcb2ee3`
- **json** ✅ `experiments/profiling/stage_distributions.json`  sha256:`854061ca16fd`
- **csv**: (none)
- **table**: (none)
- **figure** ✅ `experiments/figures/fig_runtime_breakdown.svg`  sha256:`7e2c4f619e0f`

## E7 — AgentDojo Runtime Governance
- **raw_log** ✅ `experiments/agentdojo/logs/E7_boundary.log`  sha256:`176cbb29812e`
- **metric_engine** ✅ `experiment_agentdojo_boundary_fpr.py`  sha256:`ba3da6fa4063`
- **metric_engine** ✅ `agentdojo_integration/audit/stats_engine.py`  sha256:`ced580838fb5`
- **json** ✅ `experiments/agentdojo/boundary/boundary_fpr.json`  sha256:`cde16292bdca`
- **json** ✅ `experiments/agentdojo/statistics.json`  sha256:`342cdb222433`
- **csv** ✅ `experiments/agentdojo/decisions.csv`  sha256:`3d0a045f2797`
- **table** ✅ `experiments/tables/table1_primary_metrics.md`  sha256:`632a57db881f`
- **figure** ✅ `experiments/figures/fig_false_permit_rate.svg`  sha256:`6599651c9c85`

## E8 — Runtime Robustness
- **raw_log** ✅ `experiments/robustness/logs/E8.log`  sha256:`68b519a52056`
- **metric_engine** ✅ `experiment_robustness.py`  sha256:`9909f63e410b`
- **metric_engine** ✅ `gamma_test_runner.py`  sha256:`6c7ca5717240`
- **metric_engine** ✅ `gamma_replay_verify.py`  sha256:`d1ec4b5e1134`
- **json** ✅ `experiments/robustness/robustness.json`  sha256:`9f1abfbd7d74`
- **csv** ✅ `experiments/robustness/robustness.csv`  sha256:`19d188eb6677`
- **table** ✅ `experiments/tables/table3_robustness.md`  sha256:`2945c9af2d08`
- **figure** ✅ `experiments/figures/fig_robustness.svg`  sha256:`95f53d562493`
