# Experiment 5b — Combined Component Ablation (interaction effects)

Status: **EXECUTED** · 120.551s · 19 configurations · n=6000/config · baseline RIS 1.0

Interaction classes measured: Redundant: 2, Additive: 7, Critical Dependency: 4.

| config | disabled | Blind Decision Accuracy | URR | BFR | Blind Detection Recall | Evidence | RIS | Verdict |
|--|--|--:|--:|--:|--:|--:|--:|--|
| baseline_full_LDREA | — | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 1.000 | BASELINE |
| remove_PE | PE | 0.982 | 1.000 | 0.000 | 0.000 | 1.000 | 0.833 | SECURITY-DEGRADED |
| remove_RV | RV | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.833 | SECURITY-DEGRADED |
| remove_EQ | EQ | 0.956 | 0.519 | 0.036 | 0.481 | 0.000 | 0.333 | AUDIT-DEGRADED |
| remove_LG | LG | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.500 | AUDIT-DEGRADED |
| remove_HC | HC | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.502 | AUDIT-DEGRADED |
| remove_PE+RV | PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 1.000 | 0.667 | SECURITY-DEGRADED |
| remove_EQ+PE | EQ+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.000 | 0.167 | CRITICAL |
| remove_LG+PE | LG+PE | 0.982 | 1.000 | 0.000 | 0.000 | 1.000 | 0.333 | CRITICAL |
| remove_HC+PE | HC+PE | 0.982 | 1.000 | 0.000 | 0.000 | 1.000 | 0.336 | CRITICAL |
| remove_EQ+RV | EQ+RV | 0.956 | 0.519 | 0.036 | 0.481 | 0.000 | 0.167 | CRITICAL |
| remove_LG+RV | LG+RV | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.333 | CRITICAL |
| remove_HC+RV | HC+RV | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.336 | CRITICAL |
| remove_EQ+LG | EQ+LG | 0.956 | 0.519 | 0.036 | 0.481 | 0.000 | 0.333 | AUDIT-DEGRADED |
| remove_EQ+HC | EQ+HC | 0.956 | 0.519 | 0.036 | 0.481 | 0.000 | 0.333 | AUDIT-DEGRADED |
| remove_HC+LG | HC+LG | 0.956 | 0.519 | 0.036 | 0.481 | 1.000 | 0.500 | AUDIT-DEGRADED |
| remove_EQ+PE+RV | EQ+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | CRITICAL |
| remove_EQ+HC+LG | EQ+HC+LG | 0.956 | 0.519 | 0.036 | 0.481 | 0.000 | 0.333 | AUDIT-DEGRADED |
| remove_EQ+HC+LG+PE+RV | EQ+HC+LG+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | CRITICAL |

> **NOTE — URR is not the False Permit Rate.**
> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`
>
> This metric measures the fraction of malicious events that remain **undetected during blind runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization soundness** and remains unchanged.

**Reviewer R6-ext (interaction effects) resolved.** Every value is produced by executing the full L-DREA runtime; nothing is analytically estimated. See `COMBINED_ABLATION_ANALYSIS.md`.

Reproduce: `./.venv/bin/python experiment_combined_ablation.py`
