# Table IV — Runtime Predicate Coverage & Single-Deficit Isolation (Exp 9)

Deterministic synthetic suite over the frozen `evaluate_decision`. Each case falsifies exactly ONE predicate while every other predicate concurs.

Predicate coverage: **13/13 (100.0%)** · uncovered: none

Single-deficit denial (per-predicate I3): **13/13** · false permits **0** · Wilson95 [0.7719, 1.0000]

Class-veto isolation (I4): **2/2** deny with Gamma_G = 0 · ISB conjuncts driving ISB to 0: **4/4**

| Case | Category | Predicate | Mutation | Decision | deficits | G_G | G_class | ISB | Unauth | Result |
|------|----------|-----------|----------|----------|---------:|----:|--------:|----:|:------:|:------:|
| C001 | control | `(none)` | all predicates concur | PERMIT | 0 | 0 | 0 | 1 | N | PASS |
| C002 | node_gate | `Gate_A1` | Gate_A1 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C003 | node_gate | `Gate_A2` | Gate_A2 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C004 | node_gate | `Gate_A3` | Gate_A3 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C005 | node_gate | `Gate_A4` | Gate_A4 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C006 | node_gate | `Gate_A5` | Gate_A5 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C007 | node_gate | `Gate_A6` | Gate_A6 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C008 | node_gate | `Gate_A7` | Gate_A7 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C009 | node_gate | `Lambda_G` | Lambda_G = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C010 | node_gate | `TOKEN_VALID` | TOKEN_VALID = FALSE | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C011 | node_gate | `AuthoritySignatureValid` | AuthoritySignatureValid = FALSE | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C012 | derived_deficit | `HARM_RISK_THETA` | HARM_RISK > theta | SAFE_STATE | 1 | 1 | 0 | 1 | N | PASS |
| C013 | derived_deficit | `STALE_CONTEXT` | StaleContext == TRUE | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C014 | derived_deficit | `TELEMETRY_STALE` | TelemetryFresh == FALSE | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C015 | class_veto | `Gamma_class::CLASS_1` | ReasonCodes contains CLASS_1 (all node gates TRUE) | SAFE_STATE | 0 | 0 | 1 | 1 | N | PASS |
| C016 | class_veto | `Gamma_class::GOODHART` | ReasonCodes contains GOODHART (all node gates TRUE) | SAFE_STATE | 0 | 0 | 1 | 1 | N | PASS |
| C017 | isb_conjunct | `ISB::TOKEN_VALID` | TOKEN_VALID = False | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C018 | isb_conjunct | `ISB::AuthoritySignatureValid` | AuthoritySignatureValid = False | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C019 | isb_conjunct | `ISB::TelemetryFresh` | TelemetryFresh = False | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C020 | isb_conjunct | `ISB::StaleContext` | StaleContext = True | SAFE_STATE | 1 | 1 | 0 | 0 | N | PASS |
| C021 | unauthorized_eq7 | `Eq7::deficit_while_actuated` | Actuated with Gate_A1 = FALSE | SAFE_STATE | 1 | 1 | 0 | 1 | Y | PASS |
| C022 | unauthorized_eq7 | `Eq7::class_veto_while_actuated` | Actuated with class veto raised | SAFE_STATE | 0 | 0 | 1 | 1 | Y | PASS |
| C023 | unauthorized_eq7 | `Eq7::clean_actuated_control` | Actuated, all predicates concur | PERMIT | 0 | 0 | 0 | 1 | N | PASS |

**Control.** The clean proposal (C001) PERMITs. Without it, an engine that denied everything would score 100% coverage.

**Scope.** Synthetic and deterministic. Establishes that every predicate is correctly wired into the decision and that each alone denies. Does NOT claim the ULB corpus exercises them; that limitation of E1 remains separately disclosed.
