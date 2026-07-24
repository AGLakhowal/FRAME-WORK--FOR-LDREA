# IMPLEMENTATION TRACEABILITY SPECIFICATION

**The implementation blueprint. No code, no pseudocode, no redesign, no optimization, no implementation yet. No modification to Gamma / L-DREA / FULL_SPEC / IEEE paper / RCL spec / EEB spec / predicates / Γ / SAFE_STATE / LAB / ConcurBench / AgentDojo.**

**Reviewer roles adopted:** IEEE Access Artifact-Evaluation reviewer · Senior Software Architect · Runtime-Systems Engineer · Software-Verification Engineer.

**The one question this document answers.** *If another engineer were asked to implement the Runtime Context Layer (RCL) and Execution Evidence Bundle (EEB) from scratch, exactly which Python file / class / function is the destination for each architectural component — and which is reuse vs. new vs. obsolete?* This is traceability, not design. The RCL/EEB semantics are frozen by the prior specifications; here we only bind them to filesystem destinations.

---

## PART 1 — Current codebase inventory

Non-vendored Python only (`.venv/` excluded). Verified by direct read + symbol grep.

### 1.1 Root — Gamma / LAB core and benchmark runners

| File | Role | Key symbols |
|---|---|---|
| `gamma_test_runner.py` | **LAB v1.0 runner + the frozen Gamma engine** + replay/TLC/Evidence-Quad emission | `evaluate_decision` (:133), vectorized decision (`main` :826, decision block :868-892), `NODE_GATE_COLS` (:119), `wilson_interval` (:354), `verify_tlc` (:491), `write_replay_manifest` (:635), `write_repro_bundle` (:714), `EvidenceQuad` (:1099), `METHOD_VERSION` (:78) |
| `gamma_map_raw.py` | **Current (label-driven) trace generator** — the leakage source | `main` (:92), `derive_harm_risk` (:81), gate/status authoring (:150-181) |
| `gamma_replay_verify.py` | **Independent replay verifier** (no pandas, re-reads manifest) | `main` (:38) |
| `gamma_report_page.py` | **Unified HTML dashboard** | `render` (:260), `build_extra_sections` (:62) |
| `concurbench_full.py` | **ConcurBench L1–L4 + ASB** | `level1`–`level4` (:114/:206/:338/:405), `asb` (:469), `run` (:604) |
| `concurbench_conformance_check.py` | ConcurBench conformance checker | `check`/`cond` (:22/:30) |
| `stress_test.py` | **Financial stress harness** (non-compensatory `gamma_decision`) | `gamma_decision` (:34), `p1..p4` (:60-231), `run` (:269) |
| `fcr_test.py` | **Fail-Closed Rate** over injected uncertainty families | `_fc_block` (:59), `run` (:75) |
| `full_spec_conformance.py` | **FULL_SPEC §7.1 bands + theorem family + TLC attestation** | `enforce` (:90), `tlc` (:314), `theorem_family` (:283), `run` (:359) |
| `run_all.py` | **Suite entry point** (7 steps) | `run_base` (:53), `main` (:62), `print_full_summary` (:128) |

### 1.2 `agentdojo_integration/` — the correct runtime-evidence realization (Phase 3A)

| File | Role | Key symbols |
|---|---|---|
| `interception/governed_runtime.py` | **Execution-boundary interposition** (sole chokepoint; fail-closed) | `GammaGovernedRuntime` (:31), `run_function` (:50), `_deny` (:44) |
| `interception/predicate_evaluation.py` | **Env-state → recognized-set reader** (runtime-context reader pattern) | `PredicateEvaluator` (:116), `evaluate` (:120), env readers (:28-107) |
| `interception/frozen_policy.py` | **Layer-1 policy loader** (7 immutable manifests, Merkle root `ce8c8467…`) | `ScientificPolicy` (:44), `classify` (:74), `PolicyError` (:32) |
| `interception/execution_binding.py` | **Layer-2 binding loader** (family→slot, thresholds, tool bindings) | `ExecutionBinding` (:35), `family_slot`/`family_threshold`/`tool_binding` (:54-63) |
| `interception/gamma_bridge.py` | **Bridge to the frozen engine** (reuses `evaluate_decision`) | `GammaBridge` (:24), `decide` (:30) |
| `manifests/build_preregistration.py` | Builds the 7 frozen scientific manifests | `merkle` (:329), `canon`/`sha256_hex` |
| `manifests/build_execution_binding.py` | Builds the Layer-2 binding manifest | `_recog` (:65) |
| `manifests/*.json` | **Frozen manifests** | `predicate_manifest.json`, `threshold_manifest.json`, `tool_mapping_manifest.json`, `recipient_derivation_manifest.json`, `evaluation_manifest.json`, `version_manifest.json`, `dataset_manifest.json`, `Execution_Binding_Manifest.json`, `merkle_root.json` |
| `tests/test_interception.py` | Interception unit tests | `test_functional`/`test_unknown_tool`/`test_layer1_integrity`/`test_layer2_integrity`/`test_dependency_injection` |

### 1.3 `external_validation/` — the rejected synthetic harness (quarantine candidate)

| File | Role | Key symbols | Note |
|---|---|---|---|
| `agentdojo_adapter.py` | **Separate, non-frozen decision reimplementation** | `build_eea` (:16), `evaluate_action` (:58) | `evaluate_action` computes `gamma_g` locally (:60-64) — **does NOT reuse the frozen engine**; a competing authorization path |
| `agentdojo_report.py` | Emits report with literal `false_permit_rate=0.0` etc. | `generate_report` (:18) | fabricated metrics (audit H13) |
| `agentdojo_dashboard.py` | Renders the toy report | `render` (:12) | |
| `agentdojo_runtime_bridge.py` | `intercept` shim | `intercept` (:11) | |
| `tests/test_agentdojo_validation.py` (root `tests/`) | Tests the toy adapter | `test_build_eea_and_evaluate_action` (:13) | |

### 1.4 Entry points, dashboards, data

- **Entry points:** `run_all.py` (suite), `gamma_test_runner.py` (LAB), `gamma_map_raw.py` (mapper), `concurbench_full.py`, `stress_test.py`, `fcr_test.py`, `full_spec_conformance.py`, `gamma_replay_verify.py`.
- **Dashboards:** `gamma_report_page.py` → `gamma_report.html`; `external_validation/agentdojo_dashboard.py`.
- **Data/artifacts:** `GAMMA_G0_CREDITCARD_FULL_mapped.csv` (mapper output), `gamma_replay_manifest.jsonl`, `gamma_validation_results.csv`, `*_report.json`.

---

## PART 2 — Architecture → code traceability

Format per component: **Existing File · Class · Function · Current Status · Required Changes · Reason.** Status ∈ {REUSE-FROZEN, REUSE-PATTERN, NEW-DESTINATION, OBSOLETE, QUARANTINE}. "Required Changes" describes *destination intent only* — no code.

| Architecture component | Existing file | Class / function | Current status | Required changes (destination intent) | Reason |
|---|---|---|---|---|---|
| **Transaction Interpreter** | `gamma_map_raw.py` (partial) | `main` / `derive_harm_risk` | **OBSOLETE (label-driven)** | destination = **NEW module** (e.g. `runtime_context/transaction_interpreter.py`); reads `Amount`/`Time`/features into plane-A EEB fields only; the label-authoring branch (:150-181) is retired | must stop authoring predicates from `Class`; Interpreter owns plane A only |
| **Runtime Context Layer (RCL)** | — (pattern only) | `predicate_evaluation.py:PredicateEvaluator` shows the env-reader pattern | **NEW-DESTINATION** | new package `runtime_context/` owning the four plane-B objects (history window, freshness clock, commit/actuate journal, context record) per RCL spec §3 | no plane-B producer exists for the credit-card arm |
| **Execution Evidence Bundle (EEB)** | — | — | **NEW-DESTINATION** | new module `runtime_context/execution_evidence_bundle.py` = immutable data contract per EEB spec §2; assembled+sealed by RCL | the transport contract has no current home |
| **Authority Port** | `predicate_evaluation.py` (env-derived, AgentDojo only) | `PredicateEvaluator.evaluate` | **REUSE-PATTERN / NEW-DESTINATION** | new read-only `AuthorityPort` interface in `runtime_context/`; for credit-card arm returns **evidence-absent** (no Authority Service) | plane-C evidence absent in credit-card arm; present only in AgentDojo/FCR |
| **Governance Port** | — | — | **NEW-DESTINATION** | new read-only `GovernancePort` in `runtime_context/`; surfaces `HARM_RISK` from a risk-service producer (or evidence-absent) | plane-D score is a service output, not a column |
| **Evidence Collector** | `gamma_test_runner.py` | `write_replay_manifest` (:635) | **REUSE-FROZEN** | none to the emitter; RCL/EEB feed it the sealed bundle | ledger writer already correct |
| **Predicate Evaluator (frozen)** | `gamma_test_runner.py` | `evaluate_decision` (:133); vectorized (:868-892); `NODE_GATE_COLS` (:119) | **REUSE-FROZEN** | consume EEB fields instead of authored CSV columns; **no change to logic** | the evaluator is frozen; only its input *source* changes |
| **Gamma** | `gamma_test_runner.py` | decision block (:876-892) | **REUSE-FROZEN** | none | frozen engine |
| **Replay** | `gamma_replay_verify.py`; `gamma_test_runner.py:write_replay_manifest` | `main` (:38) | **REUSE-FROZEN** | none; EEB replay contract (spec §7) aligns to it | independent verifier is the strongest existing evidence |
| **Evidence Quad** | `gamma_test_runner.py` | `EvidenceQuad` (:1099-1107) | **REUSE-FROZEN** | none | already emitted per decision |
| **Hydra Ledger** | `gamma_test_runner.py` | hash chain (:908-911) + `write_replay_manifest` | **REUSE-FROZEN** | none; note: today hashes are authored by the mapper — under RCL the ledger link becomes an EEB `prior_ledger_link` field | append-only chain already exists |
| **AgentDojo Runtime** | `agentdojo_integration/interception/governed_runtime.py` | `GammaGovernedRuntime` (:31) | **REUSE-FROZEN** | none | already the correct interposition |
| **LAB** | `gamma_test_runner.py` | `main` (:826) | **REUSE-FROZEN** | consumes EEB-fed inputs; no metric change | LAB runner unchanged |
| **ConcurBench** | `concurbench_full.py` | `run` (:604) | **REUSE-FROZEN** (+ audit fixes out of scope here) | none for RCL/EEB | benchmark frozen |
| **Policy Loader** | `agentdojo_integration/interception/frozen_policy.py` | `ScientificPolicy` (:44) | **REUSE-FROZEN** | reused by `GovernancePort`/`PolicyPort` to source θ/limits | policy plane already exists, Merkle-committed |
| **Manifest Loader** | `agentdojo_integration/interception/execution_binding.py`; `manifests/build_*.py` | `ExecutionBinding` (:35) | **REUSE-FROZEN** | reused for gate→plane bindings if the credit-card arm adopts manifest-driven bindings | binding loader already exists |

---

## PART 3 — File ownership

Per file: **Purpose · Scientific owner · Engineering owner · Paper § · FULL_SPEC § · Depends on · Used by · Modifiable? (YES/NO/CONDITIONAL) + why.**

| File | Purpose | Sci owner | Eng owner | Paper § | FULL_SPEC § | Depends on | Used by | Modifiable? |
|---|---|---|---|---|---|---|---|---|
| `gamma_test_runner.py` | frozen engine + LAB runner | Gamma/LAB | runtime eng | §IV-B, §V, §VI-B, App. A | 2.3, 7.1, App. A | pandas, corpus | run_all, gamma_bridge | **CONDITIONAL** — input *source* may change to EEB; **decision logic NO** |
| `gamma_map_raw.py` | label-driven trace generator | (leakage) | data eng | — | — | corpus, template | LAB input | **CONDITIONAL** — label-authoring branch is to be superseded by the Transaction Interpreter; do not extend it |
| `gamma_replay_verify.py` | independent replay verifier | replay/App. A | verification eng | App. A | App. A | manifest | audit/CI | **NO** — frozen evidence path |
| `gamma_report_page.py` | dashboard | reporting | frontend eng | — | 7.1 (display) | report JSON | run_all | **CONDITIONAL** — display only; no metric authoring |
| `concurbench_full.py` | ConcurBench | ConcurBench | benchmark eng | §IX | — | corpus, manifest | run_all | **NO** (frozen; separate audit tracks its fixes) |
| `stress_test.py` | stress harness | stress | benchmark eng | — | — | none | run_all | **NO** (frozen here) |
| `fcr_test.py` | fail-closed rate | FCR | benchmark eng | §V (fail-closed) | 2.3/0.10 | corpus | run_all | **NO** |
| `full_spec_conformance.py` | FULL_SPEC bands + TLC attestation | conformance | benchmark eng | §VI | 7.1, 10 | LAB report | run_all | **NO** |
| `run_all.py` | suite entry | orchestration | build eng | — | — | all runners | operator | **CONDITIONAL** — step wiring only (e.g. step-4 quarantine) |
| `agentdojo_integration/interception/*.py` | runtime-evidence realization | Def. 1/2/4 | runtime eng | §IV-B | 2.3/0.10 | agentdojo, manifests, frozen engine | AgentDojo arm | **NO** — Phase 3A frozen/clean |
| `agentdojo_integration/manifests/*` | frozen pre-registration | pre-registration | manifest eng | — | Verification Pt 5 | — | policy/binding loaders | **NO** — frozen at Merkle root |
| `external_validation/*.py` | rejected synthetic harness | (rejected) | — | — | — | own adapter | run_all step-4 | **CONDITIONAL** — **quarantine/unwire**, do not build upon |
| `tests/*`, `agentdojo_integration/tests/*` | tests | verification | test eng | — | — | targets | CI | **YES** — tests expand freely (no science) |

---

## PART 4 — Implementation plan (destination intent only; no code)

| Architecture item | Create new? | Modify existing? | Delete? | Refactor? | Move logic? | Reuse? |
|---|---|---|---|---|---|---|
| Transaction Interpreter | **YES** (`runtime_context/transaction_interpreter.py`) | — | — | — | plane-A read moves out of `gamma_map_raw.py` | reuse `Amount`/`Time` read |
| RCL plane-B objects | **YES** (`runtime_context/` — history/freshness/journal/context) | — | — | — | — | reuse env-reader *pattern* from `predicate_evaluation.py` |
| EEB data contract | **YES** (`runtime_context/execution_evidence_bundle.py`) | — | — | — | — | mirror Evidence-Quad field discipline |
| Authority/Governance/Policy ports | **YES** (`runtime_context/ports.py`) | — | — | — | — | reuse `ScientificPolicy`/`ExecutionBinding` as PolicyPort backing |
| Predicate Evaluator input adapter | — | **CONDITIONAL** (`gamma_test_runner.py` input source only) | — | — | — | **reuse frozen `evaluate_decision`** |
| Evidence Collector / Quad / Ledger / Replay | — | — | — | — | — | **reuse frozen** |
| `gamma_map_raw.py` label branch | — | — | **retire** (superseded, once Interpreter exists) | — | — | — |
| `external_validation/` | — | **unwire from `run_all.py` step 4** | quarantine package | — | — | — |

**Governing rule:** every "NEW" destination is an **evidence transporter or reader**; none contains a predicate, threshold, or decision. Every decision path is **reuse-frozen**.

---

## PART 5 — No-Science certification (per planned change)

For each destination: does it introduce a new theorem / predicate / authorization logic / policy / metric / runtime semantics / benchmark behaviour? **A YES rejects the change.**

| Planned destination | New theorem? | New predicate? | New authz logic? | New policy? | New metric? | New runtime semantics? | New benchmark? | Verdict |
|---|---|---|---|---|---|---|---|---|
| Transaction Interpreter | No | No | No | No | No | No | No | **ACCEPT** (transports plane-A evidence) |
| RCL plane-B objects | No | No | No | No | No | No (exposes freshness/ordering already assumed) | No | **ACCEPT** |
| EEB data contract | No | No | No | No | No | No | No | **ACCEPT** (transport only) |
| Ports (Authority/Governance/Policy) | No | No | No | No (reads frozen policy) | No | No | No | **ACCEPT** (read-only exposure) |
| Predicate Evaluator input adapter | No | No | No (logic unchanged) | No | No | No | No | **ACCEPT** (source swap only) |
| `external_validation` quarantine | No | No | removes a competing path | No | removes fabricated metrics | No | No | **ACCEPT** (removal, not addition) |

Every planned change is certified **science-neutral**: it moves evidence or reuses the frozen engine. Anything that would author a predicate/threshold/decision is out of scope by construction.

---

## PART 6 — Hardcode elimination

Cross-referenced to the verified audit. Each hardcode → its replacement *architecture* (not code).

| ID | File:line | Hardcoded item | Reason it exists | Replacement architecture |
|---|---|---|---|---|
| H1 | `gamma_map_raw.py:150-181` | gates/HARM/ReasonCodes/Status from `Class` | label-driven trace | **Transaction Interpreter (A) + RCL (B) + Ports (C/D)** feed EEB; `Class` removed from generation |
| H2 | `gamma_map_raw.py:184-185` | `TOKEN_VALID=True`, `AuthoritySignatureValid=True` all rows | no authority source | **AuthorityPort** returns evidence-absent for credit-card arm (never a constant `True`) |
| H3 | `full_spec_conformance.py:126` | `ptp_skew=1.0` | no clock source | plane-B **FreshnessClock** reading, or explicit `config_assumption` marker |
| H4 | `full_spec_conformance.py:318` | `distinct_reachable_states=40192` | TLC not run | **TLC attestation** surfaced as tier-0 (unchanged); real check needs `tla2tools.jar` (out of RCL scope) |
| H5 | `concurbench_full.py:341,381-397` | node_count=5, consistencies=1.0, etc. | L3 simulated | out of RCL/EEB scope (ConcurBench L3 is a separate finding) |
| H9 | `stress_test.py:90-231` | confidence/tackled/verdict strings | authored judgement | out of RCL/EEB scope (relabel per audit C-5) |
| H10 | `gamma_report_page.py:106` | "284,807/492/13" literal | dashboard lead | source from report JSON (display fix) |
| H11 | `gamma_report_page.py:696,707` | neg-control `1/13`/`0` bars | dashboard fallback | source from JSON (display fix) |
| H13 | `external_validation/agentdojo_report.py:49-56` | `false_permit_rate=0.0` etc. | fabricated | **quarantine package** (Part 4) |
| H14 | `gamma_test_runner.py:1011` | `tau=0.15` | neg-control threshold | **policy constant** via PolicyPort (disclosed config, not RCL-owned) |

**Directly addressed by RCL/EEB:** H1, H2, H14 (and, structurally, the `TOKEN_VALID/Signature` inertness). **Out of RCL/EEB scope but recorded:** H3-H5, H9-H11, H13 (display/benchmark/quarantine findings tracked separately). No RCL/EEB destination introduces a *new* hardcode — ports return **evidence-absent**, never synthesized values.

---

## PART 7 — Implementation order (sequencing only; no code)

| Step | Files affected | Depends on | Risk | Regression risk | Verification required | Commit boundary |
|---|---|---|---|---|---|---|
| **S1** Define EEB data contract module | `runtime_context/execution_evidence_bundle.py` (new) | EEB spec §2 | Low | None (no consumer yet) | schema/immutability unit tests | "EEB contract skeleton" |
| **S2** Add read-only Ports (Authority/Governance/Policy) returning evidence-absent by default | `runtime_context/ports.py` (new) | S1; `frozen_policy.py`, `execution_binding.py` | Low | None | port unit tests incl. evidence-absent | "RCL ports" |
| **S3** Add RCL plane-B objects | `runtime_context/` (new) | S1 | Med | None (isolated) | determinism + freshness/ordering unit tests | "RCL context objects" |
| **S4** Add Transaction Interpreter (plane-A only) | `runtime_context/transaction_interpreter.py` (new) | S1 | Low | None | plane-A field tests; **Class-blindness test** | "Transaction interpreter" |
| **S5** Assemble+seal EEB from Interpreter+RCL+Ports | `runtime_context/` assembler | S1-S4 | Med | None (not yet wired to LAB) | integrity-digest + replay-identity tests | "EEB assembly" |
| **S6** Adapt Predicate Evaluator **input source** to accept an EEB (logic untouched) | `gamma_test_runner.py` (input path only) | S5 | **High** | **High** (touches the runner) | full LAB parity vs. current on a controlled arm; **decision-logic diff = zero** | "Evaluator EEB input (no logic change)" |
| **S7** Quarantine `external_validation/`; unwire `run_all.py` step 4 | `run_all.py`, `external_validation/` | independent | Low | Med (dashboard section) | suite runs without step 4; dashboard renders | "Quarantine synthetic harness" |
| **S8** Retire `gamma_map_raw.py` label branch (only after S6 proven) | `gamma_map_raw.py` | S6 | High | High | replay + LAB regression | "Retire label-driven mapper" |

**Safest-first principle:** build the new, unconsumed transport (S1-S5) before touching the runner (S6); quarantine (S7) is independent; the irreversible retirement (S8) is last and gated on S6 proof.

---

## PART 8 — Test plan (per step)

| Test class | What it must assert | Applies to |
|---|---|---|
| **Unit** | each EEB field's type/immutability; each RCL object's determinism; each port's evidence-absent behavior | S1-S5 |
| **Integration** | Interpreter+RCL+Ports → sealed EEB → frozen evaluator produces a decision | S5-S6 |
| **Replay** | persisted EEB replays to **identical** evaluator inputs; digest + adjacency recompute-match (`gamma_replay_verify.py`) | S5-S6, S8 |
| **Determinism** | identical evidence ⇒ byte-identical EEB ⇒ identical Γ/decision (DET1) | S5-S6 |
| **Manifest** | `ScientificPolicy`/`ExecutionBinding` integrity (Merkle root, binding sha) unchanged | S2 |
| **AgentDojo** | `agentdojo_integration/tests/test_interception.py` still passes unchanged | S6-S7 |
| **LAB** | LAB decision-logic output identical pre/post S6 on a controlled arm (zero logic diff) | S6, S8 |
| **ConcurBench** | ConcurBench outputs unchanged (not touched by RCL/EEB) | S6 |
| **Failure** | corrupted/malformed EEB rejected at seal; never reaches evaluator | S1, S5 |
| **Unknown-service** | Authority/Governance service unavailable ⇒ field `ABSENT` ⇒ frozen fail-closed (not a synthesized permit) | S2, S6 |
| **Unknown-evidence** | unknown transaction field dropped from typed payload; not passed as predicate | S4 |
| **Missing-authority** | absent `TOKEN_VALID`/signature ⇒ `ABSENT` ⇒ SAFE_STATE via frozen policy | S2, S6 |
| **Version-mismatch** | incompatible `schema_version`/`method_version` ⇒ bundle rejected/quarantined | S1, S6 |
| **Class-blindness (critical)** | no EEB field is a function of `Class`; `Class` reachable only at scoring; a mutation of `Class` leaves every predicate input unchanged | S4, S5, S6 |

---

## PART 9 — Implementation risk register

| # | Where implementation could accidentally… | Location | Safeguard |
|---|---|---|---|
| R1 | **change Gamma** | `gamma_test_runner.py:868-892` | S6 touches *input source only*; CI gate asserting a **zero diff** in the decision block; code-owner sign-off |
| R2 | **change predicates** | `NODE_GATE_COLS` (:119) | freeze the list; EEB maps *into* it, never redefines it; test asserts identical membership |
| R3 | **change authorization semantics** | `evaluate_decision` (:133) | function body untouched; parity test on a controlled arm |
| R4 | **change replay** | `write_replay_manifest` (:635), `gamma_replay_verify.py` | replay contract tests (Part 8); verifier remains byte-oriented and unmodified |
| R5 | **change policy** | `frozen_policy.py`, manifests | manifests are Merkle-frozen; loaders read-only; integrity test |
| R6 | **change metrics** | `metric_block` (:369), report JSON | RCL/EEB emit no metrics; metric functions untouched |
| R7 | **change paper claims** | dashboards / reports | display-only changes; no new numeric source added by RCL/EEB |
| R8 | **reintroduce leakage** | new Transaction Interpreter | Class-blindness test (Part 8) is a hard CI gate; `Class` not importable into `runtime_context/` |
| R9 | **create a competing engine** (as `external_validation` did) | any new module | prohibition: RCL/EEB must call the frozen `evaluate_decision`; no local `gamma_g` computation (lint/review rule) |

---

## PART 10 — Final implementation certification

**Can implementation begin now without further scientific decisions?**

**Qualified answer: the RCL/EEB transport scaffolding — YES; the credit-card predicate *binding* — NO, pending a small, explicit set of scientific/policy rulings.**

- **Purely engineering, may start immediately (S1-S5, S7 and their tests):** the EEB data contract, RCL plane-B objects, read-only ports (evidence-absent by default), the Transaction Interpreter's plane-A read, EEB assembly/replay, and quarantining `external_validation/`. None of these makes a scientific decision; all are transport/reuse.

- **Blocked on scientific/policy rulings (must precede S6/S8 for the credit-card arm) — carried forward from EEB spec §10, unresolved by design:**
  1. **`actuation_observation` vs. `ACT_PERMIT` timing/naming collision** — is the Eq.7 execute term a pre-decision intent or a post-actuation observation, and how is counterfactual UER timed? (Owner: runtime semantics.)
  2. **`class_veto_evidence` producing plane** — governance (D) or authority (C) origin of the non-Class class-level veto. (Owner: policy.)
  3. **Gate-index → evidence-plane binding for the credit-card arm** — which concrete `Gate_Ak` binds to amount (A), which to velocity (B); the remaining authority/sanctions gates resolve to evidence-absent. (Owner: policy/binding.)
  4. **HARM_RISK proxy acceptance** — whether a label-free statistical hazard proxy is an admissible plane-D stand-in for this arm, and the **disclosed, Class-blind** rationale for θ and any amount limit `L_amt` (risk-budget SLA, not fit to `Class`). (Owner: governance/science.)
  5. **Per-subject vs. global plane-B windows** — accept global-only velocity (no subject key in the dataset) or declare velocity out of scope for this arm. (Owner: science.)

- **Everything else is engineering.** Serialization format, hash algorithm, container types, and module layout are implementation choices with no scientific content.

**Certification statement.** This blueprint binds every architectural component to a precise filesystem destination (Parts 2-4), certifies every planned change science-neutral (Part 5), maps every relevant hardcode to a replacement architecture (Part 6), sequences the work safest-first with a zero-logic-diff gate on the one high-risk step (Parts 7, 9), and defines the test surface including a hard Class-blindness gate (Part 8). Implementation of the RCL/EEB **mechanism** may begin now as pure engineering; the five enumerated rulings above must be decided (by their named owners) before the credit-card **predicate binding** (S6/S8) is implemented — and until then no predicate, threshold, decision, or metric is created by any destination in this plan.

---

*Implementation traceability blueprint only. No code, pseudocode, redesign, optimization, or implementation. No modification to Gamma, L-DREA, FULL_SPEC, the IEEE paper, the RCL spec, the EEB spec, the predicates, Γ, SAFE_STATE, LAB, ConcurBench, or AgentDojo. All file/line citations are for destination binding, not modification.*
