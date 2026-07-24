# L-DREA DEPLOYMENT PROFILE CONTRACT

**Operational contract only. No code, no implementation, no repository modification, no new scientific methodology, no architectural redesign, no invented value.** This is the **deployment profile contract**: the complete, frozen set of inputs a deployment of L-DREA must supply, and the conditions each must satisfy, for the deployment to be correct, replayable, and reportable. It is the artifact another research lab uses to instantiate L-DREA correctly.

**Roles:** Principal Runtime Governance Architect · IEEE Artifact Evaluator · Deployment Architecture Engineer · Reproducibility Engineer.

**Authoritative frozen sources (this contract adds nothing to them; it composes them into a deployment checklist):**
`RUNTIME_EVIDENCE_ARCHITECTURE.md` · `RUNTIME_CONTEXT_LAYER_SPECIFICATION.md` · `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md` · `PREDICATE_BINDING_FINAL_SPECIFICATION.md` · `DEPLOYMENT_POLICY_SPECIFICATION.md` · `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md`.

---

## 0. Contract scope and invariants

This contract is **composition, not invention.** It enumerates deployment inputs already defined by the frozen corpus and states, per input, exactly what a deployment must provide and how the system behaves. Four invariants govern the whole contract; every input inherits them:

- **I-1 · Frozen decision function.** `evaluate_decision()` (`gamma_test_runner.py:133`), `Γ = maxᵢ dᵢ`, `Π = 1[Γ=0 ∧ class=0]`, and SAFE_STATE are **frozen**. No deployment input may alter them; inputs only determine *what is fed in*.
- **I-2 · No fitting, no `Class` at decision time.** No input may be derived from the dataset or from the ground-truth `Class`. `Class` enters **only** at Ground-Truth Evaluation (EEB §9; RCL §8).
- **I-3 · Non-default-permit.** Every absent/degraded/unknown input resolves to **SAFE_STATE** (FULL_SPEC §0.10 / §2.3; EEB §6). Safety is the default; permit is earned.
- **I-4 · Policy-conditional reporting.** Every reported metric is published together with the full deployment profile that produced it (`PREDICATE_BINDING_FINAL_SPECIFICATION.md §6`).

**Two absences (used throughout — opposite meanings):** *out-of-slice* = a gate not bound → not evaluated, no deficit (slice posture, `RUNTIME_EVIDENCE_ARCH §6`). *Bound-but-absent* = a gate bound whose evidence is unavailable → fail-closed deficit → SAFE_STATE (EEB §6).

---

## 1. Deployment input index

| # | Input | Group | Required? | Class |
|---|---|---|---|---|
| D1 | Scientific Policy Manifest | Anchors | **Required** | Frozen anchor |
| D2 | ExecutionBinding Manifest | Anchors | **Required** | Policy container |
| D3 | Execution Evidence Bundle (EEB) | Evidence substrate | **Required** | Frozen contract |
| D4 | Runtime Context (RCL) | Evidence substrate | **Required** | Frozen substrate |
| D5 | Evidence Producers | Evidence substrate | **Required** | Frozen producers |
| D6 | Authority Port (plane C) | Evidence substrate | **Required** (may be absent-valued) | Frozen port |
| D7 | Governance Port (plane D) | Evidence substrate | **Required** (may be absent-valued) | Frozen port |
| D8 | Policy Port | Evidence substrate | **Required** | Frozen port |
| D9 | Gate→Plane Bindings | Policy parameters | **Required** | Policy |
| D10 | Risk Budget Parameters (envelope) | Policy parameters | Conditional | Policy |
| D11 | Amount Limit `L_amt` | Policy parameters | Conditional | Policy |
| D12 | θ (HARM threshold) | Policy parameters | Optional | Policy |
| D13 | Velocity Window | Policy parameters | Conditional | Policy / data-fact |
| D14 | Governance Confirmations | Confirmations | **Required** | Sign-off |
| D15 | Runtime Semantics Confirmation | Confirmations | **Required** | Sign-off |
| D16 | Replay Manifest | Reproducibility | **Required** | Frozen artifact |
| D17 | Hydra Ledger linkage | Reproducibility | **Required** | Frozen artifact |
| D18 | Evidence Quad linkage | Reproducibility | **Required** | Frozen artifact |

*Conditional* = required **iff** the corresponding gate is in-slice (see D9); otherwise the gate is out-of-slice and the value is not supplied.

---

## 2. GROUP A — Frozen anchors

### D1 — Scientific Policy Manifest

- **Name:** Scientific Policy Manifest — the seven frozen scientific leaf manifests + `merkle_root.json`, loaded by `frozen_policy.ScientificPolicy`.
- **Purpose:** The immutable scientific root (`ce8c8467…`) beneath every other input; defines the frozen predicate/threshold/tool-mapping science and is the integrity anchor all policy artifacts chain to.
- **Required / Optional:** **Required.**
- **Producing Component:** the frozen seven-manifest set (`agentdojo_integration/manifests/`), Merkle-committed; loaded by `ScientificPolicy` / `default_scientific_policy()`.
- **Consuming Component:** `PolicyPort.merkle_root()` / `is_verified()`; the ExecutionBinding loader (root agreement); every downstream policy consumer.
- **Validation Rules:** all seven leaves present; recomputed Merkle root == recorded `merkle_root.json`; if `expected_root` pinned, it must equal the recorded root (version gate).
- **Replay Requirements:** the verified root is recorded in every run's provenance; a run is replay-valid only against the same root.
- **Gamma Impact:** none (integrity anchor; does not enter the decision function).
- **Evidence Bundle Impact:** the verified root and `policy_hash` are carried into the EEB provenance and the Evidence Quad.
- **IEEE Reporting Requirement:** the verified scientific Merkle root must be published as the provenance seal of every metric.
- **Failure Behaviour:** `PolicyError` at construction (Missing Manifest / Invalid Merkle Root / Version Mismatch) → **hard load-time fail-closed**; deployment does not run.

### D2 — ExecutionBinding Manifest

- **Name:** ExecutionBinding Manifest (`Execution_Binding_Manifest.json`, Layer-2).
- **Purpose:** Realizes the deployment's policy-bound half of the predicate vector — families → gamma slots, tool-argument bindings, recognized sets, env references, and unknown-tool handling. Carries **no** scientific decision (manifest `purpose`).
- **Required / Optional:** **Required.**
- **Producing Component:** `manifests/build_execution_binding.py` — deterministically regenerated from the frozen scientific manifests + public AgentDojo v0.1.35 signatures; **byte-identical** on re-run.
- **Consuming Component:** `interception/execution_binding.py` (`ExecutionBinding`, `:35`; `family_slot`/`family_threshold`/`tool_binding` `:54-63`) → `runtime_context/eeb_to_engine.py` → `evaluate_decision()`.
- **Validation Rules:** `derived_from_scientific_root` == verified D1 root; `validated_against_frozen_tool_mapping` and `validated_against_public_signatures` true; `public_signature_snapshot_sha256` matches; regeneration byte-identical; every `gamma_slot` a real engine slot; `unknown_tool_handling.handling == SAFE_STATE_FAIL_CLOSED`.
- **Replay Requirements:** fixed per deployment, byte-identically regenerable → zero replay nondeterminism; `binding sha` recorded in provenance.
- **Gamma Impact:** none to aggregation; selects which evidence populates each `Gate_Ak`.
- **Evidence Bundle Impact:** defines which predicate slots the EEB must fill; its identity is part of the bundle provenance.
- **IEEE Reporting Requirement:** manifest identity (scientific root + binding sha + AgentDojo signature snapshot) published with metrics; different manifests = different, non-comparable policies.
- **Failure Behaviour:** load/validation failure → deployment not executable; a manifest weakening non-default-permit is rejected.

---

## 3. GROUP B — Evidence architecture (runtime substrate)

### D3 — Execution Evidence Bundle (EEB)

- **Name:** Execution Evidence Bundle — the immutable, sealed evidence contract (`runtime_context/execution_evidence_bundle.py`, Commit 2.1).
- **Purpose:** The single sealed object carrying all decision-consumed evidence (bound predicate vector, `HARM_RISK`, `StaleContext`, `TelemetryFresh`, veto, provenance) from producers to the frozen engine; the immutable interface between runtime and decision.
- **Required / Optional:** **Required** (the decision's only admissible input path).
- **Producing Component:** the EEB Assembler (`runtime_context/assembler.py`, Commit 2.5), sealing producer outputs (D5) and ports (D6–D8).
- **Consuming Component:** `runtime_context/eeb_to_engine.decision_inputs_from_eeb()` (pure remap, `:45-57`) → `evaluate_decision()`.
- **Validation Rules:** every field carries a `ProvenanceDescriptor` (origin plane, producer id, evidence quality, observed_at, verification method, trust level); provenance-completeness check passes; absent evidence recorded as `EvidenceQuality.ABSENT`, never fabricated; bundle immutable once sealed.
- **Replay Requirements:** the bundle is the replay unit — DET1/DET4 (EEB §7); given the same sealed bundle the decision is bit-identical.
- **Gamma Impact:** supplies every deficit term; aggregation frozen.
- **Evidence Bundle Impact:** this **is** the bundle.
- **IEEE Reporting Requirement:** the EEB schema/version is disclosed; per-decision bundles underpin the replay manifest.
- **Failure Behaviour:** an incomplete/ill-provenanced bundle is rejected; missing evidence → ABSENT → fail-closed (I-3).

### D4 — Runtime Context (RCL)

- **Name:** Runtime Context Layer — plane-B context objects and the evidence-only trace assembler (`runtime_context/context_objects.py`, `evidence_trace_builder.py`, Commits 2.3 / 5.1).
- **Purpose:** Produces the plane-B observables (freshness deltas, velocity/ordering aggregates, ledger linkage inputs) and assembles the Class-blind evidence-only trace.
- **Required / Optional:** **Required** for any deployment evaluating plane-B gates; otherwise the plane-B slice is empty.
- **Producing Component:** RCL producers (Commit 2.3); `evidence_trace_builder` (Commit 5.1, transport only).
- **Consuming Component:** the EEB Assembler (D3), which seals RCL outputs into the bundle.
- **Validation Rules:** Class-blind and deterministic (tested); producers emit **verbatim** observables, **no thresholds** (thresholding is the frozen predicate's job, not the producer's); global-only velocity where no subject key exists (D13).
- **Replay Requirements:** deterministic given fixed input ordering; recorded in the bundle.
- **Gamma Impact:** none directly; supplies plane-B evidence values that the bound predicates convert to deficits.
- **Evidence Bundle Impact:** plane-B fields of the EEB originate here.
- **IEEE Reporting Requirement:** the RCL observables in-slice (freshness, velocity scope) are disclosed.
- **Failure Behaviour:** unavailable RCL producer → plane-B fields ABSENT → bound-but-absent gates fail-closed.

### D5 — Evidence Producers

- **Name:** Evidence Producers — plane-A `TransactionInterpreter` (Commit 2.4), plane-B RCL producers (Commit 2.3), plane-C/D ports (Commit 2.2).
- **Purpose:** The only admissible sources of raw evidence: plane-A transaction observables (amount, time, opaque feature ref), plane-B context, plane-C authority, plane-D governance.
- **Required / Optional:** **Required** for every plane the deployment declares in-slice; unbound planes report absent.
- **Producing Component:** `transaction_interpreter.py` (A); RCL producers (B); `ports.py` (C/D).
- **Consuming Component:** the EEB Assembler (D3).
- **Validation Rules:** each producer emits native-plane evidence only (no cross-plane relocation — e.g. no `V1..V28`→D proxy, `RUNTIME_EVIDENCE_ARCH §2.3`); values verbatim; absence honest.
- **Replay Requirements:** deterministic per fixed input; producer id recorded in provenance.
- **Gamma Impact:** none directly; produce the evidence the bound predicates consume.
- **Evidence Bundle Impact:** populate the EEB's plane-tagged fields.
- **IEEE Reporting Requirement:** the set of bound producers (and which planes are absent) is disclosed.
- **Failure Behaviour:** producer failure → ABSENT field → fail-closed (I-3); an unclassified tool → SAFE_STATE (manifest `unknown_tool_handling`).

### D6 — Authority Port (plane C)

- **Name:** `AuthorityPort` (`runtime_context/ports.py`) — read-only plane-C evidence exposure.
- **Purpose:** Exposes authority-infrastructure evidence (`token_valid`, `authority_signature_valid`, `authority_concurrence`); **evidence-absent by default** (no token store / HSM / approval producer bound in the credit-card arm).
- **Required / Optional:** **Required as a port** (may be absent-valued).
- **Producing Component:** a bound authority service if present; otherwise the port returns `EvidenceQuality.ABSENT`.
- **Consuming Component:** EEB Assembler (D3) → `TOKEN_VALID` / `AuthoritySignatureValid` fields.
- **Validation Rules:** never fabricates a value; absence is recorded as ABSENT; read-only (no authorize/evaluate).
- **Replay Requirements:** absent-by-default is deterministic; a bound service must itself be deterministic/recorded.
- **Gamma Impact:** if a bound C gate is in-slice and absent → fail-closed deficit; if out-of-slice → none.
- **Evidence Bundle Impact:** fills plane-C EEB fields (or records absence).
- **IEEE Reporting Requirement:** state plane-C absent (or the bound authority service) for the arm.
- **Failure Behaviour:** unavailable authority service on a bound gate → fail-closed.

### D7 — Governance Port (plane D)

- **Name:** `GovernancePort` (`runtime_context/ports.py`) — read-only plane-D evidence exposure.
- **Purpose:** Exposes governance evidence (`harm_risk_score`, `sanctions_clear`); **evidence-absent by default** (no risk/AML/sanctions producer bound in the credit-card arm).
- **Required / Optional:** **Required as a port** (absent-valued in this arm — HARM proxy rejected, D14/C3).
- **Producing Component:** a bound governance/risk service if present; otherwise ABSENT.
- **Consuming Component:** EEB Assembler (D3) → `HARM_RISK` field.
- **Validation Rules:** `harm_risk_score` must report ABSENT unless a **real** risk service is bound; a `V1..V28` proxy is inadmissible unless explicitly admitted by a separate out-of-scope scientific review (not taken).
- **Replay Requirements:** absent-by-default deterministic; a bound service must be deterministic/recorded.
- **Gamma Impact:** HARM absent → contributes via the frozen fail-closed-on-absent-D path; θ (D12) moot.
- **Evidence Bundle Impact:** fills the `HARM_RISK` EEB field (or records absence).
- **IEEE Reporting Requirement:** state HARM **absent (proxy rejected)** for the arm.
- **Failure Behaviour:** unavailable governance service on a bound gate → fail-closed.

### D8 — Policy Port

- **Name:** `PolicyPort` (`runtime_context/ports.py`) — read-only view over the frozen `ScientificPolicy`.
- **Purpose:** Surfaces the verified policy root and the θ/limit policy plane to the runtime without re-verifying or mutating it.
- **Required / Optional:** **Required.**
- **Producing Component:** frozen `ScientificPolicy` (D1).
- **Consuming Component:** the runtime / assembler; `merkle_root()` and `is_verified()` gate executability.
- **Validation Rules:** no writes; no duplicate Merkle bypass; `is_verified()` must be `true` before the deployment is executable.
- **Replay Requirements:** the read root is part of provenance; identical across replays.
- **Gamma Impact:** none (exposes θ/limits; does not aggregate).
- **Evidence Bundle Impact:** contributes `policy_hash` / verified root to provenance.
- **IEEE Reporting Requirement:** the verified root exposed here is published with metrics.
- **Failure Behaviour:** `is_verified() == false` → deployment not executable.

---

## 4. GROUP C — Policy parameters (declared per deployment)

*(These are the interface defined in `DEPLOYMENT_POLICY_SPECIFICATION.md`; the contract restates them as deployment inputs. No value is supplied here.)*

### D9 — Gate→Plane Bindings

- **Name:** Gate→Plane binding table (a subset of D2).
- **Purpose:** Declares, per bound `Gate_Ak`, the evidence plane (A/B/C/D) that feeds it, or out-of-slice. The operator input the corpus externalizes (RCL §2).
- **Required / Optional:** **Required** (at least one gate bound for a non-degenerate deployment).
- **Producing Component:** operator declaration encoded in ExecutionBinding `family_metadata` / `tool_argument_binding`.
- **Consuming Component:** `ExecutionBinding.family_slot` → bound vector → `eeb_to_engine` (ordinal remap) → `NODE_GATE_COLS`.
- **Validation Rules:** each bound gate names a plane whose evidence the EEB carries; Class-blind; Tier-S exclusions explicit; recognized sets / env refs resolve.
- **Replay Requirements:** fixed per deployment; part of provenance.
- **Gamma Impact:** selects the source of each `dᵢ`; no aggregation change.
- **Evidence Bundle Impact:** determines which EEB slots must be populated.
- **IEEE Reporting Requirement:** the active gate-set / slice disclosed (defines the measured slice).
- **Failure Behaviour:** unbound gate → out-of-slice (excluded); bound-but-absent → fail-closed.

### D10 — Risk Budget Parameters (envelope)

- **Name:** Risk Budget envelope `{ L_amt, θ, velocity window }`.
- **Purpose:** The operator's declared risk posture; each member a risk-budget SLA, **not fit to `Class`** (traceability §10.4).
- **Required / Optional:** **Conditional** (each member required iff its gate in-slice).
- **Producing Component:** frozen Policy Loader (`ScientificPolicy` policy plane); operator SLA declaration.
- **Consuming Component:** the respective predicate terms via the bound vector.
- **Validation Rules:** declared through the policy plane; anti-fitting; Class-blind; consistent with the gate-set (D9); integrity-anchored to D1.
- **Replay Requirements:** fixed values recorded in the run manifest.
- **Gamma Impact:** sets values of individual deficit terms; no aggregation change.
- **Evidence Bundle Impact:** limits applied when predicates convert evidence to deficits.
- **IEEE Reporting Requirement:** the entire envelope published with metrics (policy-conditional, I-4).
- **Failure Behaviour:** undeclared member → its gate out-of-slice; never silently fitted.

### D11 — Amount Limit `L_amt`

- **Name:** Amount limit `L_amt` and its gate (ruling 4c).
- **Purpose:** The value in the frozen `Amount ≤ L_amt` predicate; a risk-budget SLA.
- **Required / Optional:** **Conditional** (iff the amount gate — `Gate_A2` in the reference binding — is in-slice).
- **Producing Component:** operator SLA via the Policy Loader, or an env reference in the ExecutionBinding amount binding (reference arm: `env_upper_bound`, `bank_account.balance`, `le`).
- **Consuming Component:** the amount predicate → `Gate_A2` → `evaluate_decision()`.
- **Validation Rules:** operator-declared or env-referenced; **not** derived from data/`Class`; well-typed non-negative bound; operator direction matches the frozen predicate.
- **Replay Requirements:** fixed scalar or deterministic env read; env snapshot recorded if env-derived.
- **Gamma Impact:** sets the value at which `Gate_A2` deficits; no aggregation change.
- **Evidence Bundle Impact:** applied to the plane-A amount observable.
- **IEEE Reporting Requirement:** `L_amt` (or the env-bound rule) published with amount-gate metrics.
- **Failure Behaviour:** undeclared → amount gate out-of-slice; never fitted.

### D12 — θ (HARM threshold)

- **Name:** θ, the value in the frozen `HARM_RISK > θ` predicate (`gamma_test_runner.py:146`).
- **Purpose:** Policy value of an existing externalized engine parameter (`evaluate_decision(row, θ)`; `args.harm_threshold`).
- **Required / Optional:** **Optional** — moot in the credit-card arm (HARM absent, D7).
- **Producing Component:** frozen Policy Loader (θ from the policy plane).
- **Consuming Component:** `evaluate_decision(row, harm_threshold)` — the HARM deficit term.
- **Validation Rules:** within the predicate's valid range; not tuned to data/`Class`; if HARM absent, recorded as **declared-but-moot**.
- **Replay Requirements:** fixed policy scalar; already emitted in the run manifest (`harm_threshold`).
- **Gamma Impact:** controls the HARM deficit term only; moot while HARM absent.
- **Evidence Bundle Impact:** applied to the `HARM_RISK` field (absent here).
- **IEEE Reporting Requirement:** published when HARM in-slice; else state HARM absent / θ moot.
- **Failure Behaviour:** omitted → existing frozen engine default (`0.5`) applies; effect nil while HARM absent.

### D13 — Velocity Window

- **Name:** Velocity/ordering window scope and envelope (ruling 5).
- **Purpose:** Scope of the plane-B velocity predicate; **global-only** in this arm (no subject key, RCL §5); per-subject **must not be faked**.
- **Required / Optional:** **Conditional** (iff velocity in-slice); else velocity out of scope.
- **Producing Component:** RCL plane-B producer (global-only aggregates, verbatim); envelope declared in the policy plane.
- **Consuming Component:** the velocity predicate → its bound gate → `evaluate_decision()`.
- **Validation Rules:** **per-subject prohibited** (no subject key) — a declared per-subject window is a validation failure; global-only scope disclosed as a limitation; Class-blind.
- **Replay Requirements:** deterministic over fixed input ordering; recorded.
- **Gamma Impact:** if in-slice, one deficit term; no aggregation change.
- **Evidence Bundle Impact:** velocity aggregate carried in plane-B fields.
- **IEEE Reporting Requirement:** velocity scope (global-only / out-of-scope) disclosed; no per-subject claims.
- **Failure Behaviour:** undeclared → velocity out-of-slice; fabricated per-subject window → rejected.

---

## 5. GROUP D — Confirmations (owner sign-offs, not new science)

### D14 — Governance Confirmations

- **Name:** Governance confirmation set (per `DEPLOYMENT_POLICY_SPECIFICATION.md §16`, C1–C4/C6).
- **Purpose:** Ratifies the deployment's policy posture: gate-set declaration, Risk-Budget declaration/omission, **HARM proxy rejection** (→ HARM absent), **slice-evaluation posture** (bound-but-absent → fail-closed; out-of-slice excluded), and Policy-Manifest integrity.
- **Required / Optional:** **Required** (deployment not executable unsigned).
- **Producing Component:** named owners (policy / governance / science).
- **Consuming Component:** the deployment gate (executability precondition); recorded in deployment metadata.
- **Validation Rules:** each confirmation signed by its named owner; none introduces a threshold/proxy/feature/algorithm/fit/`Class`-dependency (declarations or ratifications of frozen defaults only).
- **Replay Requirements:** the signed confirmation set is part of the deployment package provenance.
- **Gamma Impact:** none (confirmations ratify posture; they do not compute).
- **Evidence Bundle Impact:** none directly; establishes that ports (D6/D7) are legitimately absent-valued.
- **IEEE Reporting Requirement:** the confirmation set (esp. HARM-absent, slice posture) published with results.
- **Failure Behaviour:** unsigned → not executable.

### D15 — Runtime Semantics Confirmation

- **Name:** Runtime semantics confirmation (actuation, ruling 1; `DEPLOYMENT_POLICY_SPECIFICATION.md §11 / §16 C5`).
- **Purpose:** Ratifies the frozen **post-actuation** reading of the Eq. 7 execute term (Eq. 7 + I5) and the counterfactual UER timing; the execute term (`gamma_test_runner.py:166`) feeds the `unauthorized` audit flag only, **not** `Π`.
- **Required / Optional:** **Required** (owner confirmation).
- **Producing Component:** runtime-semantics owner.
- **Consuming Component:** the `execute`/`unauthorized` audit computation; UER interpretation.
- **Validation Rules:** signed by the runtime-semantics owner; UER timed post-actuation; the term not repurposed into the permit decision.
- **Replay Requirements:** post-actuation observation deterministic given the recorded actuation event; recorded in the bundle.
- **Gamma Impact:** **none** to `Γ`/`Π` (audit flag only).
- **Evidence Bundle Impact:** `Actuated`/`ACT_PERMIT` recorded in the bundle.
- **IEEE Reporting Requirement:** actuation semantics stated so UER is read consistently (counterfactual, post-actuation).
- **Failure Behaviour:** unsigned → not executable.

---

## 6. GROUP E — Reproducibility artifacts

### D16 — Replay Manifest

- **Name:** ERTuple Replay Manifest (`write_replay_manifest`, `gamma_test_runner.py:635`; JSONL; verified by `gamma_replay_verify.py`).
- **Purpose:** The self-describing per-decision evidence record a third party replays without the original runner: header (`kind: gamma_g0_ertuple_replay_manifest`, `method_version`, `n_records`, `genesis_anchor`, `chain_algorithm`) + one record per decision (`proposal_id`, `ertuple_id`, `policy_hash`, `hash_prev`, `hash_current`, `adjacency_ok`, `decision`, `gamma_g`, `gamma_class`, `pi`, `chain_linked`, `unauthorized`, embedded `evidence_quad`).
- **Required / Optional:** **Required** for a reportable run.
- **Producing Component:** `write_replay_manifest` (LAB runner emitter, REUSE-FROZEN).
- **Consuming Component:** `gamma_replay_verify.py` (independent verifier).
- **Validation Rules:** genesis anchored; adjacency `hash_prev[i] == hash_current[i-1]` for all i; `manifest_sha256` reproducible; DET1/DET4 hold (replay-determinism rate == 1).
- **Replay Requirements:** **is** the replay artifact; independent re-check must reproduce every decision + hash chain.
- **Gamma Impact:** records `gamma_g`/`gamma_class`/`pi`; does not compute them.
- **Evidence Bundle Impact:** each record derives from a sealed EEB decision.
- **IEEE Reporting Requirement:** the manifest (path + `manifest_sha256` + `verify_with`) published; replay-determinism rate reported.
- **Failure Behaviour:** any adjacency/determinism break → replay fails → run not reportable.

### D17 — Hydra Ledger linkage

- **Name:** Hydra Ledger — the genesis-anchored append-only hash chain (`gamma_test_runner.py:908-911`; `HASH_prev`/`HASH_current`; EEB `prior_ledger_link`).
- **Purpose:** Tamper-evident ordering of decisions: each decision links to its predecessor; breaking the chain is detectable.
- **Required / Optional:** **Required.**
- **Producing Component:** the hash-chain emitter (REUSE-FROZEN); under RCL the ledger link becomes an EEB `prior_ledger_link` field.
- **Consuming Component:** the replay manifest (D16) adjacency check; `gamma_replay_verify.py`.
- **Validation Rules:** genesis anchor ∈ {GENESIS,0,NONE,""}; every adjacency link valid; append-only (no rewrite).
- **Replay Requirements:** the chain must re-verify independently; `ledger_hash` feeds the Evidence Quad.
- **Gamma Impact:** none (integrity/ordering, not decision).
- **Evidence Bundle Impact:** `prior_ledger_link` / `hash_current` carried per bundle.
- **IEEE Reporting Requirement:** chain adjacency result (all-links-ok) reported.
- **Failure Behaviour:** broken link → tamper detected → run not reportable.

### D18 — Evidence Quad linkage

- **Name:** Evidence Quad — `{ decision, method_version, policy_hash, ledger_hash }` (emitted per decision, `gamma_test_runner.py:1099-1107`; embedded in each replay record).
- **Purpose:** Binds each decision to (a) its outcome, (b) the frozen method version, (c) the verified policy hash, and (d) its ledger position — the minimal self-certifying tuple.
- **Required / Optional:** **Required** (one per decision).
- **Producing Component:** the LAB runner (REUSE-FROZEN).
- **Consuming Component:** `gamma_replay_verify.py`; auditors linking a decision to its policy + ledger.
- **Validation Rules:** `policy_hash` == verified D1 root/policy; `ledger_hash` == the decision's `hash_current`; `method_version` == frozen `METHOD_VERSION`; `decision` ∈ {PERMIT, SAFE_STATE}.
- **Replay Requirements:** reproduced identically in independent verification.
- **Gamma Impact:** records the outcome; does not compute it.
- **Evidence Bundle Impact:** the per-decision certificate derived from the sealed EEB.
- **IEEE Reporting Requirement:** the quad is the citable per-decision provenance unit backing every reported metric.
- **Failure Behaviour:** mismatch (policy/ledger/method) → decision not certifiable → run not reportable.

---

## 7. Deployment Package Template

*Structural template only. No values populated — this shows what a deployment package consists of.*

```
Deployment/
├── ExecutionBinding_Manifest/         # D2 — family→slot, tool bindings, recognized sets, env refs
│   └── Execution_Binding_Manifest.json
├── Scientific_Policy_Manifest/        # D1 — seven frozen leaves + Merkle root
│   ├── <seven frozen scientific leaf manifests>
│   └── merkle_root.json
├── Runtime_Configuration/             # D4–D13 declarations (no values here in the template)
│   ├── gate_plane_bindings            # D9
│   ├── risk_budget_parameters         # D10 (envelope: amount_limit, theta, velocity_window)
│   ├── amount_limit                   # D11
│   ├── theta                          # D12
│   ├── velocity_window                # D13
│   ├── authority_port_binding         # D6 (bound service | absent)
│   ├── governance_port_binding        # D7 (bound service | absent)
│   └── evidence_producer_bindings     # D5 (plane-A / plane-B producers)
├── Governance_Confirmation/           # D14 — signed sign-off set (gate-set, risk-budget,
│   └── governance_confirmations       #        HARM-proxy reject, slice posture, integrity)
├── Runtime_Semantics_Confirmation/    # D15 — signed actuation = post-observation
│   └── runtime_semantics_confirmation
├── Replay_Configuration/              # D16 — replay manifest settings + verifier reference
│   └── replay_manifest_config
├── Evidence_Bundle_Schema/            # D3 — EEB schema/version the deployment seals to
│   └── execution_evidence_bundle_schema
├── Ledger/                            # D17/D18 — Hydra ledger + Evidence Quad linkage config
│   ├── hydra_ledger_config
│   └── evidence_quad_config
└── Deployment_Metadata/               # provenance: roots, shas, owners, versions
    └── deployment_metadata
```

---

## 8. Deployment Readiness Checklist

*An operator completes this before running L-DREA. Each item maps to a contract input.*

```
□ Scientific Policy Manifest verified — seven leaves present, Merkle root recomputed == recorded   (D1)
□ Merkle Root matches pinned expected_root (version gate)                                            (D1)
□ ExecutionBinding verified — derived_from_scientific_root == verified root; byte-identical regen    (D2)
□ ExecutionBinding validated against frozen tool mapping + public AgentDojo signatures               (D2)
□ Execution Evidence Bundle schema validated; provenance-completeness enforced                       (D3)
□ Runtime Context active — RCL producers deterministic + Class-blind                                 (D4)
□ Evidence Producers bound (plane-A / plane-B) or planes declared absent                             (D5)
□ Authority Port bound or honestly absent-valued (plane C)                                           (D6)
□ Governance Port bound or honestly absent-valued (plane D); HARM proxy NOT admitted                 (D7)
□ Policy Port is_verified() == true                                                                  (D8)
□ Gate→Plane bindings declared; slice (in-slice / Tier-S / out-of-slice) fixed                       (D9)
□ Risk Budget parameters declared for every in-slice limit-bearing gate (or gate out-of-slice)       (D10)
□ Amount Limit declared or amount gate out-of-slice; not fit to data/Class                           (D11)
□ θ declared or defaulted (frozen 0.5); recorded moot if HARM absent                                 (D12)
□ Velocity Window global-only (per-subject prohibited) or velocity out-of-scope                       (D13)
□ Governance confirmations signed (gate-set, risk-budget, HARM-reject, slice posture, integrity)     (D14)
□ Runtime Semantics confirmation signed (actuation = post-observation)                               (D15)
□ Replay enabled — ERTuple manifest emitted; independent gamma_replay_verify.py check passes          (D16)
□ Hydra Ledger active — genesis anchored; all adjacency links verified                               (D17)
□ Evidence Quad emitted per decision — policy_hash + ledger_hash + method_version consistent          (D18)
□ Frozen Engine unchanged — evaluate_decision / Γ = maxᵢ dᵢ / Π = 1[Γ=0] / SAFE_STATE untouched      (I-1)
□ No fitting, no Class at decision time; metrics published with full deployment profile               (I-2/I-4)
□ Non-default-permit posture intact (all absent/degraded/unknown → SAFE_STATE)                         (I-3)
```

---

## 9. Final certification

Every deployment input required to instantiate L-DREA (D1–D18) is now **fully specified as an operational contract**: for each, its name, purpose, required/optional status, producing and consuming components, validation rules, replay requirements, Gamma impact, evidence-bundle impact, IEEE reporting requirement, and failure behaviour are stated and grounded in the frozen corpus. The Deployment Package Template and the Deployment Readiness Checklist give another lab a complete, value-free structure and a pre-run gate. No algorithm, threshold, feature, policy value, dataset, implementation, optimization, benchmark logic, or architecture is invented here; the frozen science, the frozen engine (`evaluate_decision`), and GAMMA are unmodified. A deployment that satisfies every checklist item and supplies every input under its stated validation rules is correct, replayable, and reportable by construction.

# READY FOR IMPLEMENTATION

---

*Deployment profile contract only. No code, no implementation, no repository modification beyond authoring this document, no new scientific methodology, no architectural redesign, no invented value. Every input is derived from and cited to the frozen corpus (Runtime Evidence Architecture, RCL, EEB, Predicate Binding Final, Deployment Policy, Implementation Traceability) and the actual components (`frozen_policy.ScientificPolicy`, `execution_binding.py`, `runtime_context/*`, `gamma_test_runner.py`). Awaiting independent review.*
