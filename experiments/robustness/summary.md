# Experiment 8 — Runtime Robustness

Status: **EXECUTED** · 1.4s

Control (clean proposal permits): True · total false permits across ALL faults: **0** · safety holds 16/16 families.

| Fault family | Mech | Trials | Outcome | Safety |
|--|--|--:|--|:--:|
| missing_predicate | A | 10 | fp=0 | ✓ |
| delayed_predicate | A | 3 | fp=0 | ✓ |
| corrupted_predicate | A | 10 | fp=0 | ✓ |
| conflicting_predicate | A | 4 | fp=0 | ✓ |
| stale_context | A | 2 | fp=0 | ✓ |
| missing_authorization_context | A | 2 | fp=0 | ✓ |
| authorization_timeout | A | 3 | fp=0 | ✓ |
| network_delay | A | 1 | fp=0 | ✓ |
| partial_system_failure | A | 5 | fp=0 | ✓ |
| predicate_race_condition | A | 3 | fp=0 | ✓ |
| clock_skew | C | 3 | fp=0 | ✓ |
| replay_corruption | B | 1 | detected=True | ✓ |
| ledger_corruption | B | 1 | detected=True | ✓ |
| partial_ledger_loss | B | 1 | detected=True | ✓ |
| event_reordering | B | 1 | detected=True | ✓ |
| duplicate_events | B | 1 | detected=True | ✓ |

Faults are injected only into the harness; the frozen engine and stable replay verifier are unchanged.

Reproduce: `./.venv/bin/python experiment_robustness.py`
