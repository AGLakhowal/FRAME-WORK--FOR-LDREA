# Table — Fleet Runtime

| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |
|---|---|---|---|---|---|---|
| Worker processes | 5 | count | n/a | 5 | `production_evidence/fleet_summary.json::nodes` | VI-C |
| Throughput | 2162 | 1/s | n/a | 1500 | `production_evidence/fleet_summary.json::throughput_decisions_per_s` | VI-C |
| Queue delay p95 | 526 | ms | n/a | 1500 | `production_evidence/fleet_summary.json::queue_delay_ms.p95` | VI-C |
| Busy fraction mean | 0.04987 | ratio | n/a | 5 | `production_evidence/fleet_summary.json::utilization.busy_fraction_mean` | VI-C |
| Busy fraction peak | 0.06124 | ratio | n/a | 5 | `production_evidence/fleet_summary.json::utilization.busy_fraction_peak` | VI-C |
| Load imbalance (CV) | 0.4322 | ratio | n/a | 5 | `production_evidence/fleet_summary.json::utilization.load_imbalance_cv` | VI-C |
