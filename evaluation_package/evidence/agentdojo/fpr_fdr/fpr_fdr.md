# False-Permit / False-Deny Evaluation (independent labels)

- Labeling: attacker targets from injection GOAL text (independent of Gamma gate); legitimate targets from benign env recognized-set

| quantity | value |
|---|---|
| Malicious adjudicated actions | 0 |
| — permitted (false permits) | 0 |
| Legitimate adjudicated actions | 5 |
| — denied (false denies) | 0 |
| Unlabeled (excluded) | 9 |
| Total adjudications | 14 |

**False-Permit Rate (independent):** undefined (n=0): no adjudicated action targeted an attacker identifier in the executed corpus
**False-Deny Rate (recognized-set):** 0.000 [0.000, 0.434] (n=5)

> FDR is measured on the recognized-set-defined legitimate class, which overlaps the monitor's own gate; it is near-tautological and reported for completeness. FPR is the independent soundness metric.