# Table — Combined Component Ablation — configurations × metrics

*Source: `experiments/combined_ablation/combined_ablation.json` — produced by `experiment_combined_ablation.py` from runtime execution.*

| Configuration | Disabled | BlindAcc | URR | BFR | Replay | Latency(ms) | Evidence | Recall | RevocComp | HashChain | Ledger | RIS | Overall Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_full_LDREA | — | 0.956 | 0.519 | 0.036 | 1.000 | 0.8290 | 1.000 | 0.481 | 1.000 | 1.000 | 1.000 | 1.000 | BASELINE (full L-DREA) |
| remove_PE | PE | 0.982 | 1.000 | 0.000 | 1.000 | 0.3611 | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.833 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_RV | RV | 0.956 | 0.519 | 0.036 | 1.000 | 0.7135 | 1.000 | 0.481 | 0.000 | 1.000 | 1.000 | 0.833 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_EQ | EQ | 0.956 | 0.519 | 0.036 | 0.000 | 0.6893 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_LG | LG | 0.956 | 0.519 | 0.036 | 0.000 | 0.8636 | 1.000 | 0.481 | 1.000 | n/a | n/a | 0.500 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_HC | HC | 0.956 | 0.519 | 0.036 | 0.000 | 0.9092 | 1.000 | 0.481 | 1.000 | 0.014 | 0.000 | 0.502 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_PE+RV | PE+RV | 0.982 | 1.000 | 0.000 | 1.000 | 0.2229 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 | 0.667 | SECURITY-DEGRADED (authorization/enforcement weakened) |
| remove_EQ+PE | EQ+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.1908 | 0.000 | 0.000 | 1.000 | n/a | n/a | 0.167 | CRITICAL (security AND audit both degraded) |
| remove_LG+PE | LG+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.3621 | 1.000 | 0.000 | 1.000 | n/a | n/a | 0.333 | CRITICAL (security AND audit both degraded) |
| remove_HC+PE | HC+PE | 0.982 | 1.000 | 0.000 | 0.000 | 0.3682 | 1.000 | 0.000 | 1.000 | 0.014 | 0.000 | 0.336 | CRITICAL (security AND audit both degraded) |
| remove_EQ+RV | EQ+RV | 0.956 | 0.519 | 0.036 | 0.000 | 0.5833 | 0.000 | 0.481 | 0.000 | n/a | n/a | 0.167 | CRITICAL (security AND audit both degraded) |
| remove_LG+RV | LG+RV | 0.956 | 0.519 | 0.036 | 0.000 | 0.7607 | 1.000 | 0.481 | 0.000 | n/a | n/a | 0.333 | CRITICAL (security AND audit both degraded) |
| remove_HC+RV | HC+RV | 0.956 | 0.519 | 0.036 | 0.000 | 0.7602 | 1.000 | 0.481 | 0.000 | 0.014 | 0.000 | 0.336 | CRITICAL (security AND audit both degraded) |
| remove_EQ+LG | EQ+LG | 0.956 | 0.519 | 0.036 | 0.000 | 0.7409 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+HC | EQ+HC | 0.956 | 0.519 | 0.036 | 0.000 | 0.7624 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_HC+LG | HC+LG | 0.956 | 0.519 | 0.036 | 0.000 | 0.9386 | 1.000 | 0.481 | 1.000 | n/a | n/a | 0.500 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+PE+RV | EQ+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.0455 | 0.000 | 0.000 | 0.000 | n/a | n/a | 0.000 | CRITICAL (security AND audit both degraded) |
| remove_EQ+HC+LG | EQ+HC+LG | 0.956 | 0.519 | 0.036 | 0.000 | 0.7211 | 0.000 | 0.481 | 1.000 | n/a | n/a | 0.333 | AUDIT-DEGRADED (evidence/ledger integrity lost; authorization intact) |
| remove_EQ+HC+LG+PE+RV | EQ+HC+LG+PE+RV | 0.982 | 1.000 | 0.000 | 0.000 | 0.0328 | 0.000 | 0.000 | 0.000 | n/a | n/a | 0.000 | CRITICAL (security AND audit both degraded) |

> **NOTE — URR is not the False Permit Rate.**
> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`
>
> This metric measures the fraction of malicious events that remain **undetected during blind runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization soundness** and remains unchanged.
