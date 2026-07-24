# Table — Runtime Watchdog

| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |
|---|---|---|---|---|---|---|
| Heartbeats | 311 | count | n/a | 311 | `production_evidence/watchdog_summary.json::heartbeats` | VI-B |
| Heartbeat latency mean | 3.165 | ms | n/a | 311 | `production_evidence/watchdog_summary.json::heartbeat_latency_ms.mean` | VI-B |
| Stall threshold | 250 | ms | n/a | 1 | `production_evidence/watchdog_summary.json::stall_threshold_ms` | VI-B |
| Injected stalls detected | 1 | count | n/a | 1 | `production_evidence/watchdog_summary.json::stalls_detected_on_injected_worker` | VI-B |
| Detection rate | 1 | ratio | n/a | 1 | `production_evidence/watchdog_summary.json::detection_rate` | VI-B |
| False triggers | 0 | count | n/a | 311 | `production_evidence/watchdog_summary.json::false_triggers` | VI-B |
| Recovery latency p95 | 209.6 | ms | n/a | 1 | `production_evidence/watchdog_summary.json::recovery_latency_ms.p95` | VI-B |
