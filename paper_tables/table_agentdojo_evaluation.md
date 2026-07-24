# Table — AgentDojo External Evaluation (Table 11)
_Source: audit_run/summary/{statistics,replay_validation,fpr_fdr}.json; permit-rate CI RE-DERIVED by metrics_engine and cross-checked against the stored Wilson._

| Metric | Value | Provenance |
|---|---|:--:|
| episodes | 33 | ✅ |
| gamma_decisions | 14 | ✅ |
| permit | 11 | ✅ |
| safe_state | 3 | ✅ |
| permit_rate | 0.786 [0.524, 0.924] | ✅ |
| permit_wilson_low | 0.524107694133997 | ✅ |
| permit_wilson_high | 0.9242861328730683 | ✅ |
| gamma_per_episode | 0.42424242424242425 | ✅ |
| overhead_mean_ms | 0.021592857142857143 | ✅ |
| replay_consistent_traces | 33 | ✅ |
| replay_auth_steps | 14 | ✅ |
| decision_entropy_bits | 0.74959525725948 | ✅ |
| authorization_stability | 0.9666666666666668 | ✅ |
| utility_true | 3 | ✅ |
| security_true | 1 | ✅ |
| false_permit_rate | undefined (n=0) | ✅ |
| false_deny_rate | 0.0 | ✅ |
