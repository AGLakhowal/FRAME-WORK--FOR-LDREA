# Experiment 9 — Runtime Predicate Coverage

Status: **EXECUTED** · 0.738s

Predicate coverage: **13/13 (100.0%)** · uncovered: none

Single-deficit denial (I3, per predicate): **13/13** (Wilson95 [0.7719, 1.0000])

Class-veto isolation (I4): 2/2 deny with Gamma_G = 0

| Case | Category | Predicate | Decision | deficits | Γ_class | ISB | Result |
|--|--|--|--|--:|--:|--:|:--:|
| C001 | control | `(none)` | PERMIT | 0 | 0 | 1 | PASS |
| C002 | node_gate | `Gate_A1` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C003 | node_gate | `Gate_A2` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C004 | node_gate | `Gate_A3` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C005 | node_gate | `Gate_A4` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C006 | node_gate | `Gate_A5` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C007 | node_gate | `Gate_A6` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C008 | node_gate | `Gate_A7` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C009 | node_gate | `Lambda_G` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C010 | node_gate | `TOKEN_VALID` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C011 | node_gate | `AuthoritySignatureValid` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C012 | derived_deficit | `HARM_RISK_THETA` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C013 | derived_deficit | `STALE_CONTEXT` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C014 | derived_deficit | `TELEMETRY_STALE` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C015 | class_veto | `Gamma_class::CLASS_1` | SAFE_STATE | 0 | 1 | 1 | PASS |
| C016 | class_veto | `Gamma_class::GOODHART` | SAFE_STATE | 0 | 1 | 1 | PASS |
| C017 | isb_conjunct | `ISB::TOKEN_VALID` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C018 | isb_conjunct | `ISB::AuthoritySignatureValid` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C019 | isb_conjunct | `ISB::TelemetryFresh` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C020 | isb_conjunct | `ISB::StaleContext` | SAFE_STATE | 1 | 0 | 0 | PASS |
| C021 | unauthorized_eq7 | `Eq7::deficit_while_actuated` | SAFE_STATE | 1 | 0 | 1 | PASS |
| C022 | unauthorized_eq7 | `Eq7::class_veto_while_actuated` | SAFE_STATE | 0 | 1 | 1 | PASS |
| C023 | unauthorized_eq7 | `Eq7::clean_actuated_control` | PERMIT | 0 | 0 | 1 | PASS |

**Scope:** synthetic, deterministic, over the frozen engine. Establishes that every predicate is correctly wired and that each alone denies. Does NOT claim the ULB corpus exercises them — that limitation is separate and remains disclosed.

Reproduce: `./.venv/bin/python experiment_predicate_coverage.py`
