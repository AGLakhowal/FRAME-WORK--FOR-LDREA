# Table — Critical runtime dependencies

*Source: `experiments/combined_ablation/combined_ablation.json` — produced by `experiment_combined_ablation.py` from runtime execution.*

| Component | Dependent Components | Failure Impact (measured single removal) |
|---|---|---|
| Predicate Engine (PE) | EQ+FT+RD | RIS→0.83; FPR 1.000; evidence 1.000; ledger 1.000 |
| Runtime Revocation (RV) | FT+RD | RIS→0.83; FPR 0.519; evidence 1.000; ledger 1.000 |
| Evidence Quad (EQ) | HC+LG | RIS→0.33; FPR 0.519; evidence 0.000; ledger n/a |
| Runtime Ledger (LG) | HC | RIS→0.50; FPR 0.519; evidence 1.000; ledger n/a |
| Hash Chain (HC) | — | RIS→0.50; FPR 0.519; evidence 1.000; ledger 0.000 |
| Runtime Risk Detection (RD) | — | governance stage (not in ablation matrix) |
| Runtime Watchdog (WD) | FT | governance stage (not in ablation matrix) |
| Fleet Telemetry (FT) | — | governance stage (not in ablation matrix) |
| Clock Consistency (single-host PTP) (CK) | — | governance stage (not in ablation matrix) |

> **NOTE — URR is not the False Permit Rate.**
> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`
>
> This metric measures the fraction of malicious events that remain **undetected during blind runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization soundness** and remains unchanged.
