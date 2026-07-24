| Removed | Role | Security Impact | ΔURR | ΔRIS | ΔEvidence | Interaction | Cross-Dataset | Significant | Interpretation |
|---|---|---|--:|--:|--:|---|:--:|:--:|---|
| PE | Predicate Engine | Critical | +0.481 | −0.167 | 0.000 | Additive | Yes | Yes | Authorization boundary opens |
| RV | Runtime Revocation | High | 0.000 | −0.167 | 0.000 | Additive | Yes | Yes | Revoked permits still execute |
| EQ | Evidence Quad | None | 0.000 | −0.667 | −1.000 | Critical Dependency | Yes | Yes | All provenance lost (upstream of ledger) |
| LG | Runtime Ledger | None | 0.000 | −0.500 | 0.000 | Critical Dependency | Yes | Yes | Ledger, chain and replay anchor lost |
| HC | Hash Chain | None | 0.000 | −0.498 | 0.000 | Critical Dependency | Yes | Yes | Chain linkage broken; tamper-evidence lost |

> **NOTE — URR is not the False Permit Rate.**
> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`
>
> This metric measures the fraction of malicious events that remain **undetected during blind runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization soundness** and remains unchanged.
