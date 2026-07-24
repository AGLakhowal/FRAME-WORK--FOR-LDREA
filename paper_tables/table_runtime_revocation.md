# Table — Runtime Revocation

| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |
|---|---|---|---|---|---|---|
| Permits revoked | 120 | count | n/a | 120 | `production_evidence/revocation_report_live.json::permits_revoked` | VI-A |
| Acknowledgements received | 600 | count | n/a | 600 | `production_evidence/revocation_report_live.json::acks_received` | VI-A |
| Acknowledgement rate | 1 | ratio | n/a | 600 | `production_evidence/revocation_report_live.json::acknowledgement_rate` | VI-A |
| Compliance rate | 1 | ratio | n/a | 120 | `production_evidence/revocation_report_live.json::compliance_rate` | VI-A |
| Propagation p50 | 51.42 | ms | n/a | 120 | `production_evidence/revocation_report_live.json::propagation_latency_ms.p50` | VI-A |
| Propagation p95 | 51.93 | ms | n/a | 120 | `production_evidence/revocation_report_live.json::propagation_latency_ms.p95` | VI-A |
| Propagation p99 | 52.04 | ms | n/a | 120 | `production_evidence/revocation_report_live.json::propagation_latency_ms.p99` | VI-A |
| False permits after revocation | 0 | count | n/a | 120 | `production_evidence/revocation_report_live.json::false_permits_after_revocation` | VI-A |
| Revocations/sec | 19.4 | 1/s | n/a | 120 | `production_evidence/revocation_report_live.json::revocations_per_s` | VI-A |
