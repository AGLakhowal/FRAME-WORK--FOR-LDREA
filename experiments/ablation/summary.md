# Experiment 5 — Component Ablation

Status: **EXECUTED** · 1.979s · workload 60,000/config

| config | permits | leaked permits | leak rate | throughput | replay |
|--|--:|--:|--:|--:|:--:|
| baseline_full_LDREA | 15,000 | 0 | 0.000 | 1,164,068 | T |
| remove_class_veto | 30,000 | 15,000 | 0.250 | 1,198,663 | T |
| remove_noncompensatory_gamma | 30,000 | 15,000 | 0.250 | 1,364,603 | T |
| remove_authorization_layer | 60,000 | 45,000 | 0.750 | 5,874,050 | T |

**Causal reading:** class-veto and non-compensatory Gamma each convert 15,000 baseline denials to permits when removed; removing the authorization layer leaks 45,000. Replay is an audit/integrity component (not a decision gate): removing it changes 0 authorization decisions but makes execution-integrity verification (Exp 2) impossible — its contribution is provenance, not leakage prevention.

Reproduce: `./.venv/bin/python experiment_ablation.py`
