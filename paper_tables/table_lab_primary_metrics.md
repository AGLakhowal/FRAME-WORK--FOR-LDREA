# Table — LAB v1.0 Primary Metrics (source: gamma_lab_v1_report.json)

| Metric | Adverse | n | Rate | Wilson95↑ (cc) | Re-derived point | Prov |
|---|---:|---:|---:|---:|---:|:--:|
| False Permit Rate (should-deny) | 0 | 492 | 0.0 | 1.312e-02 | 0.0 | ✅ |
| False Denial Rate (should-permit) | 0 | 284315 | 0.0 | 2.297e-05 | 0.0 | ✅ |
| Replay Determinism Rate | 0 | 284807 | 1.0 | 2.293e-05 | 1.0 | ✅ |
| Revocation Compliance | 0 | 284807 | 1.0 | 2.293e-05 | 1.0 | ✅ |
| TOCTOU Violation Rate | 0 | 284807 | 0.0 | 2.293e-05 | 0.0 | ✅ |
| Class-Veto Effectiveness | 0 | 492 | 1.0 | 1.312e-02 | 1.0 | ✅ |

**UER (Eq.7):** 0 events / 284,807 rows → rate 0.0; naive Wilson95↑ (engine, 0/284,807) = 1.349e-05
