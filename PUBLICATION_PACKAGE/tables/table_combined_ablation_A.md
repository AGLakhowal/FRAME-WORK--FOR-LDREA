# Table — Combined Component Ablation — configurations × metrics

*Source: `experiments/combined_ablation/combined_ablation.json` — produced by `experiment_combined_ablation.py` from runtime execution.*

| Configuration | Disabled | BlindAcc | URR | BFR | Replay | Latency(ms) | Evidence | Recall | RevocComp | HashChain | Ledger | RIS | Overall Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_full_LDREA | — | 0.956 | 0.519 | 0.036 | 1.000 | 1.5272 | 1.000 | 0.481 | 1.000 | 1.000 | 1.000 | 1.000 | BASELINE (full L-DREA) |
| remove_PE | PE | 0.982 | 1.000 | 0.000 | 1.000 | 0.6285 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.833 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_RV | RV | 0.956 | 0.519 | 0.036 | 1.000 | 1.3176 | 1.000 | 0.481 | 0.000 | 1.000 | 1.000 | 0.833 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_EQ | EQ | 0.956 | 0.519 | 0.036 | 0.000 | 1.2524 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_LG | LG | 0.956 | 0.519 | 0.036 | 0.000 | 1.6892 | 1.000 | 0.481 | 1.000 | n/a | n/a | 0.500 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_HC | HC | 0.956 | 0.519 | 0.036 | 0.000 | 1.6893 | 1.000 | 0.481 | 1.000 | 0.014 | 0.000 | 0.502 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_PE+RV | PE+RV | 0.982 | 1.000 | 0.000 | 1.000 | 0.3594 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.667 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_EQ+PE | EQ+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.3834 | 0.000 | 0.000 | 1.000 | n/a | n/a | 0.167 | CRITICAL (security AND audit both degraded) |
| remove_LG+PE | LG+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.6525 | 1.000 | 0.000 | 1.000 | n/a | n/a | 0.333 | CRITICAL (security AND audit both degraded) |
| remove_HC+PE | HC+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.6314 | 1.000 | 0.000 | 1.000 | 0.014 | 0.000 | 0.336 | CRITICAL (security AND audit both degraded) |
| remove_EQ+RV | EQ+RV | 0.956 | 0.519 | 0.036 | 0.000 | 1.1405 | 0.000 | 0.481 | 0.000 | n/a | n/a | 0.167 | CRITICAL (security AND audit both degraded) |
| remove_LG+RV | LG+RV | 0.956 | 0.519 | 0.036 | 0.000 | 1.3968 | 1.000 | 0.481 | 0.000 | n/a | n/a | 0.333 | CRITICAL (security AND audit both degraded) |
| remove_HC+RV | HC+RV | 0.956 | 0.519 | 0.036 | 0.000 | 1.2787 | 1.000 | 0.481 | 0.000 | 0.014 | 0.000 | 0.336 | CRITICAL (security AND audit both degraded) |
| remove_EQ+LG | EQ+LG | 0.956 | 0.519 | 0.036 | 0.000 | 1.2420 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+HC | EQ+HC | 0.956 | 0.519 | 0.036 | 0.000 | 1.2301 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_HC+LG | HC+LG | 0.956 | 0.519 | 0.036 | 0.000 | 1.5606 | 1.000 | 0.481 | 1.000 | n/a | n/a | 0.500 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+PE+RV | EQ+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.0563 | 0.000 | 0.000 | 0.000 | n/a | n/a | 0.000 | CRITICAL (security AND audit both degraded) |
| remove_EQ+HC+LG | EQ+HC+LG | 0.956 | 0.519 | 0.036 | 0.000 | 1.2425 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+HC+LG+PE+RV | EQ+HC+LG+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.0571 | 0.000 | 0.000 | 0.000 | n/a | n/a | 0.000 | CRITICAL (security AND audit both degraded) |

> **NOTE — URR is not the False Permit Rate.**
> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`
>
> This metric measures the fraction of malicious events that remain **undetected during blind runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization soundness** and remains unchanged.
