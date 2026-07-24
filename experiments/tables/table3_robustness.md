# Table III — Runtime Robustness under Fault Injection (Exp 8)

Control: a clean actuated proposal PERMITs = True. Faults injected into the harness only; engine unchanged. Total false permits across all faults: **0**. Safety holds in **16/16** families.

| Fault family | Mechanism | Trials | False permits / Detected | Safety holds |
|--------------|-----------|-------:|--------------------------|:------------:|
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