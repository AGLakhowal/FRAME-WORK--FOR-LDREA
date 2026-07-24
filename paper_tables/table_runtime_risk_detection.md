# Table — Runtime Risk Detection (attack injection)

| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |
|---|---|---|---|---|---|---|
| Attack families | 12 | count | n/a | 12 | `production_evidence/runtime_risk_detection_report.json::families` | VII-A |
| Total attacks | 2394 | count | n/a | 2394 | `production_evidence/runtime_risk_detection_report.json::total_attacks` | VII-A |
| Attacks detected | 2394 | count | n/a | 2394 | `production_evidence/runtime_risk_detection_report.json::attacks_detected` | VII-A |
| Detection rate | 1 | ratio | n/a | 2394 | `production_evidence/runtime_risk_detection_report.json::detection_rate` | VII-A |
| Detection precision | 1 | ratio | n/a | 2394 | `production_evidence/runtime_risk_detection_report.json::detection_precision` | VII-A |
| Suite has power (control) | true | bool | n/a | 1 | `production_evidence/runtime_risk_detection_report.json::suite_has_power` | VII-A |
| Response latency p99 | 1.435 | ms | n/a | 2394 | `production_evidence/runtime_risk_detection_report.json::response_latency_ms.p99` | VII-A |
