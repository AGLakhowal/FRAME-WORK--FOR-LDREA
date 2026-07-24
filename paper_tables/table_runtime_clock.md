# Table — Runtime Clock Consistency (NOT PTP)

| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |
|---|---|---|---|---|---|---|
| Timestamp resolution | 41 | ns | n/a | 20000 | `production_evidence/runtime_clock_consistency_report.json::timestamp_resolution_ns` | VI-D |
| Sampling jitter p95 | 333 | ns | n/a | 20000 | `production_evidence/runtime_clock_consistency_report.json::sampling_jitter_ns.p95` | VI-D |
| Sampling jitter p99 | 417 | ns | n/a | 20000 | `production_evidence/runtime_clock_consistency_report.json::sampling_jitter_ns.p99` | VI-D |
| Monotonic consistency | true | bool | n/a | 20000 | `production_evidence/runtime_clock_consistency_report.json::monotonic_consistency` | VI-D |
| Wall-vs-monotonic drift | -18.18 | ppm | n/a | 1 | `production_evidence/runtime_clock_consistency_report.json::wall_vs_monotonic_drift_ppm` | VI-D |
