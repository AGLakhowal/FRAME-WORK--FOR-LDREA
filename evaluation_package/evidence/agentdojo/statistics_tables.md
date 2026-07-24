# Statistical Analysis — publication tables

- Episodes: 33 · Gamma decisions: 14 (PERMIT 11, SAFE_STATE 3)
- Permit rate (Wilson 95%): 0.786 [0.524, 0.924]
- Denial rate (Wilson 95%): 0.214 [0.076, 0.476]
- Class-veto rate (Wilson 95%): 0.000 [0.000, 0.215]
- Decision entropy: 0.7496 bits · Authorization stability: 0.9666666666666668

## Table I — Γ / Π / deficit-count descriptive statistics

| metric | count | mean | median | std | min | max | IQR |
|---|---|---|---|---|---|---|---|
| Γ_global | 14 | 0.2143 | 0.0000 | 0.4258 | 0.0000 | 1.0000 | 0.0000 |
| Π | 14 | 0.7857 | 1.0000 | 0.4258 | 0.0000 | 1.0000 | 0.0000 |
| deficit_count | 14 | 0.2143 | 0.0000 | 0.4258 | 0.0000 | 1.0000 | 0.0000 |

## Table II — Predicate activation & failure (Wilson 95%)

| predicate | activations | failures | failure rate [95% CI] |
|---|---|---|---|
| CTR_ISB | 14 | 0 | 0.000 [0.000, 0.215] |
| GAMMA | 14 | 0 | 0.000 [0.000, 0.215] |
| GATE_scope | 14 | 0 | 0.000 [0.000, 0.215] |
| AUTH_TOKEN | 14 | 0 | 0.000 [0.000, 0.215] |
| TRACE | 14 | 0 | 0.000 [0.000, 0.215] |
| INTERLOCK | 14 | 0 | 0.000 [0.000, 0.215] |
| GATE_recipient_recognition | 7 | 1 | 0.143 [0.026, 0.513] |
| GATE_amount_limit | 4 | 0 | 0.000 [0.000, 0.490] |
| GATE_destination_recognition | 4 | 1 | 0.250 [0.046, 0.699] |
| CLASS_velocity | 3 | 0 | 0.000 [0.000, 0.561] |
| GATE_ownership | 3 | 0 | 0.000 [0.000, 0.561] |
| GATE_identity_recognition | 2 | 1 | 0.500 [0.095, 0.905] |
| GATE_resource_recognition | 1 | 0 | 0.000 [0.000, 0.793] |

## Table III — Per-tool authorization (Wilson 95%)

| tool | n | permit | deny | permit rate [95% CI] |
|---|---|---|---|---|
| post_webpage | 3 | 2 | 1 | 0.667 [0.208, 0.939] |
| send_money | 2 | 2 | 0 | 1.000 [0.342, 1.000] |
| reschedule_calendar_event | 2 | 2 | 0 | 1.000 [0.342, 1.000] |
| schedule_transaction | 1 | 1 | 0 | 1.000 [0.207, 1.000] |
| get_webpage | 1 | 1 | 0 | 1.000 [0.207, 1.000] |
| invite_user_to_slack | 1 | 0 | 1 | 0.000 [0.000, 0.793] |
| send_direct_message | 1 | 1 | 0 | 1.000 [0.207, 1.000] |
| add_user_to_channel | 1 | 1 | 0 | 1.000 [0.207, 1.000] |
| reserve_hotel | 1 | 1 | 0 | 1.000 [0.207, 1.000] |
| add_calendar_event_participants | 1 | 0 | 1 | 0.000 [0.000, 0.793] |

## Table IV — Latency (ms)

| scope | count | mean | median | std | max |
|---|---|---|---|---|---|
| all events | 269 | 3330.2912 | 0.0132 | 10190.5016 | 99887.4366 |
| Gamma decision overhead | 14 | 0.0216 | 0.0172 | 0.0144 | 0.0587 |

Bootstrap 95% CI for mean event latency: 3330.2912 [2265.7300, 4672.3537] (n=269, 2000 resamples, seed 12345).

> false_permit_rate / false_deny_rate require external ground-truth labels of the CORRECT authorization for each action; these are not present in the traces, so they are reported as null rather than fabricated. AgentDojo utility/security are episode-level task/attack outcomes, not per-action authorization ground truth.