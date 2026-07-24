# DEPLOYMENT POLICY SPECIFICATION — L-DREA Runtime Governance

**Documentation only. No code, no repository modification, no change to GAMMA, no change to `evaluate_decision()`, no invented policy value, no new scientific methodology.** This document defines the **operational policy interface** of L-DREA: everything an operator must **declare** or **confirm** before a deployment becomes executable. It is the operator-facing complement to the now-complete scientific specification (`PREDICATE_BINDING_FINAL_SPECIFICATION.md`), which certified that every remaining open item is **deployment policy** or an **architectural default** — not missing science.

**Roles:** Runtime Governance Architect · IEEE Artifact Engineer · Deployment Specification Author.

**Scope boundary (binding).** This specification defines *the interface* — the names, types, ownership, validation rules, defaults, and downstream implications of each policy input. It does **not** assign any policy *value*. Assigning a value (an amount limit, a θ, a gate-set) is an operator/governance act performed *against* this interface, not within it. Where the corpus already fixes a mechanism or a frozen default, that fact is cited; nothing here overrides a frozen artifact.

---

## 0. Framing — what a "deployment policy" is in L-DREA

The L-DREA paper treats the node-predicate vector `G` as a **"generic policy-bound"** vector: the *predicate definitions* and the *aggregation* (`Γ = maxᵢ dᵢ`, `Π = 1[Γ=0]`, SAFE_STATE fail-closed) are **science — frozen**; *which evidence each gate binds to* and *what limits apply* are **policy — declared per deployment** (RCL §2; `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md` Part 2; `PREDICATE_BINDING_FINAL_SPECIFICATION.md` §1). This document specifies the second half.

Three consequences follow, and they govern every item below:

1. **Policy selects the evidence source and the limit; it never changes the decision function.** `evaluate_decision()` (`gamma_test_runner.py:133`) is frozen. Policy determines *what is fed in*, never *how the verdict is computed*.
2. **Policy is not fit to data and is never `Class`-dependent.** Any limit, threshold, or binding is an operator/governance business input (a risk-budget SLA, a recognized-set, a service binding). Deriving one from the dataset, or making one vary with the ground-truth `Class`, is **forbidden** — `Class` enters only at Ground-Truth Evaluation (EEB §9; RCL §8).
3. **Every declared value is published with the metrics it conditions.** L-DREA's reported FPR/FDR/UER are **policy-conditional**, exactly as any governance engine's are. A metric without its governing policy declaration is not a reportable result (`PREDICATE_BINDING_FINAL_SPECIFICATION.md` §6).

**The executable-deployment invariant.** Absent any declaration, the system is still *safe* — it fail-closes to SAFE_STATE universally (non-default-permit; FULL_SPEC §0.10 / §2.3). It is not *executable* in the operational sense (yielding non-degenerate, publishable PERMIT/SAFE_STATE decisions) until the **Required** items in §2 are declared and the **Governance confirmations** in §11 are signed.

---

## 1. Policy surface — index

| # | Policy item | Class | Required? | Frozen mechanism it is realized through |
|---|---|---|---|---|
| P1 | **ExecutionBinding Manifest** (container) | Policy | **Required** | `interception/execution_binding.py` · `manifests/Execution_Binding_Manifest.json` |
| P2 | **Gate→Plane Bindings** (gate-set) | Policy | **Required** | ExecutionBinding `family_metadata` / `tool_argument_binding` |
| P3 | **Amount limit `L_amt`** (+ its gate) | Policy | Conditional* | ExecutionBinding amount binding · Policy Loader limits |
| P4 | **θ — HARM threshold** | Policy | Optional | frozen Policy Loader / `evaluate_decision(row, θ)` |
| P5 | **HARM proxy admission** | Governance confirmation | **Required (confirm)** | GovernancePort (plane D) |
| P6 | **Risk Budget Parameters** (SLA envelope: `L_amt`, θ, velocity envelope) | Policy | Conditional* | Policy Loader (`ScientificPolicy`) |
| P7 | **Velocity window envelope / scope** | Architecture / data-fact realized by policy | Conditional* | RCL plane-B producer |
| P8 | **Class-veto plane tag (C/D)** | Policy | Optional | ExecutionBinding `__ReasonCodes_CLASS__` slot |
| P9 | **Actuation semantics** | Architecture (owner-confirm) | **Required (confirm)** | Eq. 7 execute term / I5 |
| P10 | **Policy Manifest integrity** (frozen root) | Policy anchor | **Required** | `frozen_policy.ScientificPolicy` (Merkle root) |
| P11 | **Default fail-closed behaviour** | Frozen architecture | N/A (not declarable) | `evaluate_decision` / SAFE_STATE |
| P12 | **Missing-policy behaviour** | Frozen architecture | N/A (not declarable) | non-default-permit / slice posture |

\* *Conditional* = required **only if** the corresponding gate is in-slice for the deployment (e.g. the amount gate is bound, or velocity is declared in-slice). If the gate is not bound, the item is out-of-slice and needs no value (see P12).

**Two distinct "absences" — do not conflate (they have opposite meanings):**

- **Out-of-slice** — a gate the ExecutionBinding manifest does **not** bind. It is not evaluated at all (slice posture, `RUNTIME_EVIDENCE_ARCH §6`). Contributes **no** deficit.
- **Bound-but-absent** — a gate the manifest **does** bind, whose evidence is unavailable at runtime. It **fail-closes**: the missing evidence yields a deficit → SAFE_STATE (EEB §6; FULL_SPEC §2.3/§0.10).

This distinction is load-bearing for every item's "Default behaviour if omitted" and "Gamma implications" fields.

---

## 2. Executable-deployment precondition (checklist)

A deployment is **executable** when, and only when, all of the following hold:

1. A validated **ExecutionBinding Manifest** (P1) is present and loads under `ExecutionBinding` without error.
2. Its **Gate→Plane bindings** (P2) name, for every bound `Gate_Ak`, an evidence plane whose producer exists in the deployment (or is deliberately left bound-but-absent → fail-closed).
3. For every **in-slice** gate requiring a limit (amount, velocity), the corresponding **Risk-Budget parameter** (P3/P6/P7) is declared in the Policy Loader plane, **or** the operator accepts that gate as out-of-slice.
4. The **Policy Manifest integrity anchor** (P10) verifies: the seven frozen scientific manifests reproduce the recorded Merkle root, and (if `expected_root` is pinned) match it.
5. The **Governance confirmations** (§11) are signed: HARM-proxy rejection (P5), slice posture, and actuation semantics (P9).

If any item 1–5 is unmet, the deployment is **not executable**; it remains *safe* (fail-closed to SAFE_STATE) but must not be run for publishable metrics.

---

## 3. P1 — ExecutionBinding Manifest

- **Name:** ExecutionBinding Manifest (`Execution_Binding_Manifest.json`, Layer-2 IMPLEMENTATION artifact).
- **Purpose:** The single container that realizes the deployment's *policy-bound* half of the predicate vector: it maps predicate **families** → engine **gamma slots** (`Gate_A1..A7`, ISB/veto channels), binds **tool arguments** to the evidence read for each gate, names the **recognized sets** and **env field references** each gate consults, and declares **unknown-tool handling**. It carries **no scientific decision** — "NO scientific decision, predicate, threshold, authorization logic, benchmark configuration, or theorem change" (manifest `purpose`).
- **Required or Optional:** **Required.** Without it, no gate is bound; the deployment is degenerate-fail-closed (P12).
- **Default behaviour if omitted:** No gate bound → every mediated action resolves to SAFE_STATE by non-default-permit. Safe, but not executable.
- **Producing component:** `manifests/build_execution_binding.py` — deterministically regenerates the manifest from the seven **frozen** scientific manifests (root `ce8c8467…`) plus the **public** AgentDojo v0.1.35 tool signatures. Re-run is **byte-identical** (sorted keys, constant date).
- **Consuming component:** `interception/execution_binding.py` (`ExecutionBinding`, loader `:35`; `family_slot`/`family_threshold`/`tool_binding` `:54-63`) → feeds the bound predicate vector to the frozen adapter (`runtime_context/eeb_to_engine.py`) → `evaluate_decision()`.
- **Validation rules:**
  - Must declare `derived_from_scientific_root` equal to the frozen scientific root; the loader must **not** admit a manifest whose root disagrees with the Policy Manifest (P10).
  - `validated_against_frozen_tool_mapping` and `validated_against_public_signatures` must be `true`; the `public_signature_snapshot_sha256` must match the pinned AgentDojo signature snapshot.
  - Regeneration must be byte-identical (determinism gate); any drift is a validation failure.
  - Every `gamma_slot` used must be a real engine slot (`Gate_A1..A7`, `__TOKEN_VALID__`, `__StaleContext__`, `__ReasonCodes_CLASS__`, `__aggregator__`); unknown slots are rejected.
  - `unknown_tool_handling.handling` must be `SAFE_STATE_FAIL_CLOSED` (frozen; not an operator choice).
- **Replay implications:** The manifest is fixed per deployment and byte-identically regenerable → contributes **zero** replay nondeterminism (DET1/DET4, EEB §7). Its `binding sha` / scientific root are part of the replayed provenance and must be recorded in the run's evidence bundle.
- **Gamma implications:** **None to the aggregation.** The manifest selects *which evidence populates each `Gate_Ak`*; `Γ = maxᵢ dᵢ` is unchanged. It changes the *composition* of the deficit vector, never the deficit function.
- **IEEE reporting implications:** The manifest identity (scientific root + binding sha + AgentDojo signature snapshot) must be published alongside any reported metric; two deployments with different manifests are different policies and their metrics are not directly comparable.

---

## 4. P2 — Gate→Plane Bindings (the credit-card gate-set)

- **Name:** Gate→Plane binding table (ruling 3 in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10.3`; classified **POLICY** in `PREDICATE_BINDING_FINAL_SPECIFICATION.md §4`).
- **Purpose:** Declares, for each concrete `Gate_Ak` the deployment intends to evaluate, which **evidence plane** feeds it — plane A (interpreter observables: amount, time, features), plane B (RCL objects: freshness, velocity/ordering), plane C (authority), plane D (governance) — or **out-of-slice**. This is the operator input the corpus already externalizes: "the binding of a specific gate index to a specific evidence plane is a **deployment policy** already externalised (the AgentDojo `ExecutionBinding`, Layer 2)" (RCL §2).
- **Required or Optional:** **Required** (a subset of P1). At least one gate must be bound for a non-degenerate deployment.
- **Default behaviour if omitted:** A gate not named in the binding is **out-of-slice** — not evaluated, contributes no deficit (slice posture, `RUNTIME_EVIDENCE_ARCH §6`). A gate named but whose plane has no producer is **bound-but-absent** → fail-closed (EEB §6).
- **Producing component:** operator declaration, encoded in the ExecutionBinding `family_metadata` (family → `gamma_slot`) and `tool_argument_binding` (tool arg → family + recognized set / env ref). Reference realization (AgentDojo arm): `GATE_recipient/identity/destination/resource_recognition → Gate_A1` (membership over recognized sets); `GATE_amount_limit → Gate_A2` (env upper bound). Tier-S gates (`GATE_scope→Gate_A3`, `GATE_ownership→Gate_A4`, `TRACE→Gate_A6`, `INTERLOCK→Gate_A7`, etc.) are marked `EXCLUDED_BY_POLICY_TIER_S` (structural deficit 0).
- **Consuming component:** `ExecutionBinding.family_slot` / `tool_binding` → the bound predicate vector → `eeb_to_engine.decision_inputs_from_eeb()` (`:45-46`, pure remap by ordinal) → `NODE_GATE_COLS` in `evaluate_decision()`.
- **Validation rules:**
  - Every bound gate must name a plane whose evidence field the EEB actually carries (A/B present; C/D → must be explicitly ABSENT via the ports, not fabricated).
  - The binding must be **Class-blind**: no gate's plane or recognized-set may depend on the ground-truth `Class`.
  - A gate may be `EXCLUDED_BY_POLICY_TIER_S` (structural, deficit 0) **only** by explicit policy tier declaration, not silently.
  - The recognized-set catalog referenced by a gate must exist in `recognized_set_catalog`; its `env_field_references` must resolve.
- **Replay implications:** Bindings are fixed per deployment → deterministic. The realized binding table is part of replayed provenance.
- **Gamma implications:** Selects the *source* of each `dᵢ`; **no effect on aggregation**. Out-of-slice gates are absent from the vector (no deficit); bound-but-absent gates contribute a deficit (fail-closed).
- **IEEE reporting implications:** The active gate-set (which slots in-slice, which Tier-S excluded, which out-of-slice) **must be disclosed** with results — it defines the slice on which FPR/FDR/UER are measured (`RUNTIME_EVIDENCE_ARCH §6` slice posture).

---

## 5. P3 — Amount limit `L_amt`

- **Name:** Amount limit `L_amt` and the gate it binds (ruling 4c; classified **POLICY**).
- **Purpose:** The upper bound the amount gate enforces: the `Amount ≤ L_amt` predicate is **defined** (frozen); `L_amt` is its **policy value**. It is a **risk-budget SLA, not fit to `Class`** (`IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10.4`). Different deployments (bank X vs bank Y) set different limits, all valid.
- **Required or Optional:** **Conditional** — required iff the amount gate (`Gate_A2` in the reference binding) is in-slice; otherwise out-of-slice and unneeded.
- **Default behaviour if omitted (amount gate in-slice):** If no `L_amt` is declared, the amount gate is **out-of-slice** (policy) — it is not evaluated. It is **never** silently defaulted to a fitted or invented number. (The reference AgentDojo binding instead uses an **env-derived** bound — `env_upper_bound`, `env_ref: bank_account.balance`, operator `le` — which is a legitimate alternate realization when the deployment's limit is an environment fact rather than a scalar SLA.)
- **Producing component:** operator SLA, sourced through the frozen **Policy Loader** (`frozen_policy.ScientificPolicy`, "source[s] θ/limits", traceability Part 2), or an env reference declared in the ExecutionBinding amount binding.
- **Consuming component:** the amount predicate feeding `Gate_A2` in the bound vector → `evaluate_decision()`.
- **Validation rules:**
  - `L_amt` must be an operator-declared or env-referenced value; it must **not** be derived from, or correlated with, the dataset or `Class` (anti-fitting rule).
  - Must be a well-typed non-negative bound with an explicit comparison operator (`le`) matching the frozen predicate direction.
  - Provenance must record the declaring owner and the SLA source.
- **Replay implications:** A fixed scalar (or a deterministic env read) → deterministic. If env-derived, the env snapshot must be part of the replayed bundle so the bound is reproducible.
- **Gamma implications:** Sets the *value* at which `Gate_A2` deficits; **no effect on aggregation**. A stricter/looser `L_amt` changes which rows deficit at `Gate_A2`, never how deficits combine.
- **IEEE reporting implications:** `L_amt` (or the env-bound rule) **must be published with the metrics** — FPR/FDR at the amount gate are meaningless without the limit that produced them. Do **not** fit `L_amt` to improve a metric; that would be dataset fitting (forbidden).

---

## 6. P4 — θ (HARM threshold)

- **Name:** θ, the HARM-risk decision threshold (ruling 4b; classified **POLICY**).
- **Purpose:** The value in the frozen `HARM_RISK > θ` predicate (`evaluate_decision`, `gamma_test_runner.py:146`). The predicate is defined and frozen; θ is its **policy value**, an already-externalized engine parameter (`evaluate_decision(row, θ)`; `args.harm_threshold`).
- **Required or Optional:** **Optional.** It is **moot in the credit-card arm** because HARM is plane-D absent there (P5). It becomes live only if a real risk service is bound.
- **Default behaviour if omitted:** The existing engine default parameter value (`0.5`, as used at every frozen call site, e.g. `evaluate_decision(inst, 0.5)`) applies. This is the **established frozen default**, not a value invented here. With HARM absent (credit-card arm), θ has no effect on the decision regardless of its value.
- **Producing component:** frozen **Policy Loader** (θ sourced from the policy plane, traceability Part 2); passed as the `harm_threshold` argument.
- **Consuming component:** `evaluate_decision(row, harm_threshold)` — the `HARM_RISK > θ` deficit term.
- **Validation rules:**
  - θ ∈ the predicate's valid range; declared through the policy plane, not hardcoded per run.
  - θ must **not** be tuned against `Class` or the dataset.
  - If HARM is absent for the arm, θ must be recorded as **declared-but-moot** (documented, not silently dropped).
- **Replay implications:** A fixed policy scalar → deterministic; recorded in the run manifest (`harm_threshold` is already emitted, `gamma_test_runner.py:1278/1433`).
- **Gamma implications:** Controls the `HARM_RISK` deficit term only; **no effect on aggregation**. Moot while HARM absent.
- **IEEE reporting implications:** θ must be published with results whenever HARM is in-slice. In the credit-card arm, results must state HARM absent and θ moot.

---

## 7. P5 — HARM proxy admission (governance confirmation)

- **Name:** HARM proxy admissibility (ruling 4a). Classified **ARCHITECTURE (default reject)**; the admit path is **optional, out-of-scope Science, explicitly not taken**.
- **Purpose:** Decides whether a label-free statistical proxy over features (`V1..V28`) may stand in for a real plane-D `HARM_RISK` service. The architecture states `HARM_RISK` is a **governance-service output** (plane D); a feature proxy is "defensible **only** as an explicitly-labelled proxy, never as the architecture's intended source" (`RUNTIME_EVIDENCE_ARCH §2.3`), and the credit-card arm has **no** risk service → HARM **absent** (§5).
- **Required or Optional:** **Required as a governance confirmation** — governance signs the **rejection** (a sign-off, *not* new science). Admitting a proxy would require **inventing a hazard model** (feature engineering) — new science, forbidden here and **not required to proceed**.
- **Default behaviour if omitted:** **Reject** → HARM native-plane absent → frozen fail-closed on the D-signal. This is the architectural default; no action needed to obtain it beyond the sign-off.
- **Producing component:** `GovernancePort` (plane D, `runtime_context/ports.py`) — returns `harm_risk_score` as **evidence-absent** by default (no producer bound). A real risk service, if later deployed, would bind here.
- **Consuming component:** the `HARM_RISK` field of the EEB → `eeb_to_engine` → `evaluate_decision`.
- **Validation rules:**
  - Default path: `GovernancePort.harm_risk_score` **must** report `EvidenceQuality.ABSENT` (no fabricated value).
  - The rejection must be **signed** by the governance owner (§11).
  - Admission (if ever taken) requires an explicitly-labelled proxy, a disclosed Class-blind derivation + θ, and a separate scientific review — **out of scope for this deployment**.
- **Replay implications:** Absent-by-default is deterministic. (An admitted proxy would add a derived D-signal whose determinism would need its own DET proof — not applicable here.)
- **Gamma implications:** Under reject, HARM contributes via the existing fail-closed-on-absent-D path; **no new deficit source**, no aggregation change.
- **IEEE reporting implications:** Results must state that HARM is **absent (proxy rejected)** for this arm. Publishing a HARM-based metric would misrepresent the deployment.

---

## 8. P6 — Risk Budget Parameters (SLA envelope)

- **Name:** Risk Budget Parameters — the operator's risk-budget SLA envelope: `{ L_amt (P3), θ (P4), velocity envelope (P7) }` taken as a set.
- **Purpose:** Groups the operator business inputs that express *how much risk this deployment tolerates*. Each is a **risk-budget SLA, not fit to `Class`** (traceability §10.4). The envelope is the operator's declared risk posture, published with the metrics it conditions.
- **Required or Optional:** **Conditional** — each member is required iff its gate is in-slice (see P3/P4/P7). The envelope as a whole is required for any deployment that evaluates a limit-bearing gate.
- **Default behaviour if omitted:** Each undeclared member renders its gate out-of-slice (not evaluated), never silently defaulted to a fitted value. θ retains the frozen engine default but is moot when HARM absent.
- **Producing component:** frozen **Policy Loader** (`ScientificPolicy`) — the Merkle-committed policy plane that sources θ/limits; operator declares SLA values into this plane.
- **Consuming component:** the respective predicate terms in `evaluate_decision()` via the bound vector.
- **Validation rules:**
  - Every member declared through the policy plane, owner-attributed, and **anti-fitting** (no dataset/`Class` derivation).
  - The envelope must be internally consistent with the gate-set (P2): a declared `L_amt` requires the amount gate in-slice, etc.
  - The envelope must be integrity-anchored to the Policy Manifest root (P10).
- **Replay implications:** Fixed SLA values → deterministic; the full envelope is recorded in the run manifest for reproduction.
- **Gamma implications:** Sets values of individual deficit terms; **no effect on aggregation**.
- **IEEE reporting implications:** The **entire envelope** is published with results. Metrics are **policy-conditional**: FPR/FDR/UER are reported *for this envelope*, and re-declaring the envelope defines a different (non-comparable) operating point.

---

## 9. P7 — Velocity window envelope / scope

- **Name:** Velocity/ordering window scope (ruling 5). Classified **ARCHITECTURE / data-fact**, realized by policy for the envelope value.
- **Purpose:** Fixes the scope of the plane-B velocity/ordering predicate. Because the credit-card dataset has **no subject key** (RCL §5), only a **global** window is a real observable; a **per-subject** window "must not be faked." The envelope value (window size, if velocity is in-slice) is a policy declaration.
- **Required or Optional:** **Conditional** — required iff velocity is declared in-slice; otherwise velocity is **out of scope** for the arm (a legitimate declaration).
- **Default behaviour if omitted:** Velocity **out-of-slice** — not evaluated (data-fact: no subject key precludes per-subject; operator may decline global too). No deficit contributed.
- **Producing component:** RCL plane-B producer (velocity/ordering aggregates, computed **global-only**, verbatim, no threshold at the producer). The envelope (window) is an operator declaration in the policy plane.
- **Consuming component:** the velocity predicate feeding its bound gate → `evaluate_decision()`.
- **Validation rules:**
  - **Per-subject windows are prohibited** in this arm (no subject key) — declaring one is a validation failure (would be fabrication).
  - If in-slice, the window envelope is declared through the policy plane and is Class-blind.
  - The global-only scope must be disclosed as a limitation.
- **Replay implications:** Global-window aggregates are deterministic over the fixed input ordering; recorded in the bundle.
- **Gamma implications:** If in-slice, contributes one deficit term; **no effect on aggregation**. If out-of-slice, no contribution.
- **IEEE reporting implications:** The velocity scope (global-only, or declared out-of-scope) **must be disclosed**; per-subject velocity claims are not supportable for this arm and must not be reported.

---

## 10. P8 — Class-veto plane tag (C/D)

- **Name:** Class-veto producing-plane tag (ruling 2; classified **POLICY**).
- **Purpose:** Tags the origin plane of the non-`Class` class-level veto channel (`__ReasonCodes_CLASS__` slot) as authority (C) or governance (D). **Its value is ABSENT either way in this arm**, so the tag has **no material effect** on the decision; the architecture recommends **D** (`RUNTIME_EVIDENCE_ARCH §2.3`).
- **Required or Optional:** **Optional** (absent-valued; recommend D for consistency).
- **Default behaviour if omitted:** Veto channel **absent** → no class-level veto contributed at runtime (the ground-truth `Class` enters only at Ground-Truth Evaluation, never at decision time). The legacy `ReasonCodes`-string veto path in `eeb_to_engine.py:57` is an explicitly-temporary **Commit-4.1 equivalence carrier only**, not a runtime evidence source, and must not be built upon.
- **Producing component:** `GovernancePort` (recommended plane D) — absent by default.
- **Consuming component:** the veto channel read by `evaluate_decision` (`gamma_class` from `ReasonCodes`); absent in this arm.
- **Validation rules:** The tag, if declared, must name C or D; the runtime value **must** be ABSENT for the credit-card arm (no genuine non-`Class` veto producer); it must **never** be sourced from the ground-truth `Class`.
- **Replay implications:** Absent-valued → deterministic; nothing to reproduce beyond the recorded absence.
- **Gamma implications:** **None** (absent-valued; no deficit contributed).
- **IEEE reporting implications:** Results must state the veto channel is **absent** for this arm; the C/D tag is a documentation attribute with no metric effect.

---

## 11. P9 — Actuation semantics (owner confirmation)

- **Name:** Actuation / execute-term semantics (ruling 1). Classified **ARCHITECTURE** (owner-confirmable, non-material to Γ).
- **Purpose:** Fixes whether the Eq. 7 execute term is a pre-decision **intent** or a **post-actuation observation**, and how counterfactual UER is timed. The architecture resolves this: **Eq. 7 + invariant I5 ⇒ post-actuation observation**. In the engine the execute term is `bool(row["Actuated"] or row["ACT_PERMIT"])` (`gamma_test_runner.py:166`), used only for the `unauthorized` audit flag — **not** for `Π`.
- **Required or Optional:** **Required as an owner confirmation** (runtime-semantics owner signs the post-actuation reading). Not a value to declare — a semantics to confirm.
- **Default behaviour if omitted:** The frozen post-actuation reading (Eq. 7 / I5) already governs; confirmation records the owner's ratification.
- **Producing component:** runtime actuation observation (post-actuation), surfaced as `Actuated`/`ACT_PERMIT`.
- **Consuming component:** the `execute` / `unauthorized` computation in `evaluate_decision` (audit only; does **not** enter `Π = 1[Γ=0 ∧ class=0]`).
- **Validation rules:** Confirmation must be signed by the runtime-semantics owner; UER timing must follow the post-actuation reading; the term must not be repurposed into the permit decision.
- **Replay implications:** Post-actuation observation is deterministic given the recorded actuation event; recorded in the bundle.
- **Gamma implications:** **None to `Γ`/`Π`** — the execute term feeds the `unauthorized` audit flag only (non-material to the permit decision).
- **IEEE reporting implications:** The actuation semantics must be stated so UER is interpreted consistently (counterfactual, post-actuation). No metric value changes from the confirmation.

---

## 12. P10 — Policy Manifest (integrity anchor)

- **Name:** Policy Manifest — the frozen scientific policy plane (`frozen_policy.ScientificPolicy`) and its Merkle root.
- **Purpose:** The integrity anchor beneath every policy declaration. The seven frozen scientific manifests (root `ce8c8467…`) define the immutable science; `ScientificPolicy` verifies them (per-leaf SHA → Merkle root) at construction and exposes the verified root. Every policy artifact (ExecutionBinding P1, Risk-Budget envelope P6) must chain to this root.
- **Required or Optional:** **Required** — no deployment is executable without a verified policy manifest.
- **Default behaviour if omitted / on failure:** `PolicyError` at construction (Missing Manifest / Invalid Merkle Root / Version Mismatch). The system does **not** proceed — this is a **hard fail-closed at load time**, prior to any decision.
- **Producing component:** the frozen seven-manifest set + `merkle_root.json`; loaded by `frozen_policy.ScientificPolicy` (`default_scientific_policy()`), exposed read-only via `PolicyPort` (`runtime_context/ports.py`).
- **Consuming component:** `PolicyPort.merkle_root()` / `is_verified()`; the ExecutionBinding loader (must agree on the scientific root); every downstream policy consumer.
- **Validation rules:**
  - All seven leaf manifests present; recomputed Merkle root **must** equal `merkle_root.json`.
  - If `expected_root` is pinned, it **must** equal the recorded root (version gate) — mismatch is a hard error.
  - No writes; no duplicate verification bypass. `PolicyPort.is_verified()` must return `true` before the deployment is considered executable.
- **Replay implications:** The verified root is part of every run's provenance; a run is only replay-valid against the same root. Tampering breaks the hash chain and the run is rejected.
- **Gamma implications:** **None** — the manifest anchors integrity; it does not enter the decision function.
- **IEEE reporting implications:** The verified scientific Merkle root (and the ExecutionBinding `derived_from_scientific_root`) **must be published** with results as the provenance seal binding metrics to a specific frozen science + declared policy.

---

## 13. P11 — Default fail-closed behaviour (frozen; not declarable)

- **Name:** Default fail-closed / non-default-permit.
- **Purpose:** The frozen safety posture: any deficit, any bound-but-absent evidence, any degraded/unavailable service, and any unknown/unclassified tool resolves to **SAFE_STATE** (deny, not actuated). "non-default-permit" — FULL_SPEC §0.10 / §2.3; EEB §6; realized in `evaluate_decision` (`Π = 1[Γ=0 ∧ class=0]`, else SAFE_STATE) and in the ExecutionBinding `unknown_tool_handling: SAFE_STATE_FAIL_CLOSED` (derived from Definition 2(i) complete mediation).
- **Required or Optional:** **Not declarable.** It is a frozen architectural invariant. Operators do **not** turn it off; there is no permit-by-default mode.
- **Default behaviour if omitted:** N/A — it *is* the default and cannot be omitted.
- **Producing component:** frozen engine + assembler (absent evidence → ABSENT fields → deficit).
- **Consuming component:** `evaluate_decision` / SAFE_STATE resolution.
- **Validation rules:** No policy declaration may weaken it. A manifest attempting a permit-on-absent or default-permit posture is invalid and must be rejected.
- **Replay implications:** Deterministic (DET3: `Γ>0 → SAFE_STATE`).
- **Gamma implications:** It **is** the interpretation of `Γ` (`Π = 1[Γ=0]`); any non-zero deficit → SAFE_STATE.
- **IEEE reporting implications:** Reported UER/FCR presuppose fail-closed; the posture must be stated as the frozen baseline of every result.

---

## 14. P12 — Missing-policy behaviour (frozen; not declarable)

- **Name:** Missing-policy resolution.
- **Purpose:** Defines what happens when a policy input is **not** declared, distinguishing the two absences (§1):
  - **No gate bound / gate out-of-slice** → the gate is **not evaluated** (slice posture, `RUNTIME_EVIDENCE_ARCH §6`); it contributes no deficit and is excluded from the reported slice.
  - **Gate bound but evidence/limit absent** → **fail-closed** deficit → SAFE_STATE (EEB §6).
  - **No ExecutionBinding / no verified Policy Manifest** → deployment **not executable**; load-time hard fail (P10) or degenerate universal SAFE_STATE (P1). Safe, not runnable-for-metrics.
- **Required or Optional:** **Not declarable** — it is the frozen consequence of complete mediation + non-default-permit.
- **Default behaviour if omitted:** As above; the system never "guesses" a missing limit, θ, or binding, and never fits one from data.
- **Producing component:** the ports (absent evidence) + the assembler (ABSENT fields) + the loader (integrity failure).
- **Consuming component:** `evaluate_decision` (deficit → SAFE_STATE) / slice selection (out-of-slice exclusion).
- **Validation rules:** A missing **Required** item (§2) must **block executability**, not be silently defaulted to a fitted value. A missing **Conditional** item must render its gate out-of-slice, disclosed as such.
- **Replay implications:** Deterministic — absence is recorded, not invented; reproduces identically.
- **Gamma implications:** Out-of-slice → no term; bound-but-absent → deficit term. Never a fabricated permit.
- **IEEE reporting implications:** Any out-of-slice gate and any absent evidence **must be disclosed**; a metric silently computed over a narrowed slice (without disclosing what was excluded) is not a valid L-DREA result.

---

## 15. Cross-cutting summary — Replay, Gamma, IEEE

| Concern | Invariant across all policy items |
|---|---|
| **Replay** | Every policy input is a **fixed, deterministically-recorded** value/binding per deployment (scalar SLA, byte-identical manifest, verified root, or deterministic env read). No policy input introduces nondeterminism; all are captured in the run's evidence bundle for DET1/DET4 reproduction. |
| **Gamma** | **No policy input changes the aggregation.** `Γ = maxᵢ dᵢ`, `Π = 1[Γ=0 ∧ class=0]`, SAFE_STATE are frozen. Policy selects *which evidence populates each deficit term* and *at what limit a term deficits* — never *how terms combine*. |
| **IEEE reporting** | Every reported metric (FPR/FDR/UER/FCR) is **policy-conditional** and must be **published together with**: the ExecutionBinding identity (scientific root + binding sha + AgentDojo signature snapshot), the active gate-set/slice, the Risk-Budget envelope (`L_amt`, θ, velocity scope), the HARM-absent (proxy-rejected) statement, and the actuation semantics. A metric detached from its declared policy is not a reportable L-DREA result. |

---

## 16. Governance confirmations required (sign-off block)

These are **policy acts / confirmations — not new science** (`PREDICATE_BINDING_FINAL_SPECIFICATION.md §5-6`). Each must be signed by its named owner before the deployment is executable.

| # | Confirmation | Owner | Nature | Effect if unsigned |
|---|---|---|---|---|
| C1 | **Declare the credit-card ExecutionBinding gate-set** (P1/P2) | policy / binding | Declaration | Not executable (degenerate fail-closed) |
| C2 | **Declare / omit `L_amt`, θ, velocity envelope** via the frozen policy manifest (P3/P4/P6/P7) | governance | Declaration | Corresponding gate out-of-slice |
| C3 | **Confirm reject-proxy** for HARM (P5) → HARM absent | governance / science | Confirmation | Not executable (posture unratified) |
| C4 | **Confirm slice-evaluation posture** (bound-but-absent → fail-closed; out-of-slice excluded) (P2/P12) | governance | Confirmation | Not executable (posture unratified) |
| C5 | **Confirm actuation = post-observation** (P9; Eq. 7 / I5) | runtime semantics | Confirmation | Not executable (semantics unratified) |
| C6 | **Verify Policy Manifest integrity** (P10) — recorded root, pinned expected root | policy | Verification | Hard load-time fail |
| — | *(Optional, out-of-scope) admit a HARM proxy — the only new-science path, explicitly **not taken*** | governance / science | Would require new science | N/A (not part of this deployment) |

No confirmation above introduces a threshold, proxy, feature, algorithm, dataset fit, or `Class`-dependent behaviour. C1/C2 are declarations against an existing mechanism; C3–C6 ratify frozen architectural defaults.

---

## 17. Validation / conformance checklist (operator)

1. `ScientificPolicy` constructs without `PolicyError`; `PolicyPort.is_verified()` is `true`; recorded root = pinned `expected_root`. *(P10/C6)*
2. `ExecutionBinding` loads; `derived_from_scientific_root` = verified root; `validated_against_frozen_tool_mapping` and `validated_against_public_signatures` are `true`; `public_signature_snapshot_sha256` matches; regeneration is byte-identical. *(P1)*
3. Every bound `Gate_Ak` names an existing plane/producer or is deliberately bound-but-absent; Tier-S exclusions are explicit; recognized sets and env references resolve. *(P2)*
4. Each in-slice limit-bearing gate has a declared, anti-fitting, Class-blind Risk-Budget value; each undeclared one is disclosed as out-of-slice. *(P3/P6/P7)*
5. `GovernancePort.harm_risk_score` reports ABSENT (proxy rejected); veto channel absent. *(P5/P8)*
6. All governance confirmations C1–C6 signed. *(§16)*
7. The full policy set (manifest identity, gate-set/slice, Risk-Budget envelope, HARM-absent statement, actuation semantics) is bundled for publication with any metric. *(§15)*

If all seven hold, the deployment satisfies the executable-deployment precondition (§2) and every implementation input is formally specified.

---

## 18. Certification

Every input that Commit 5.1-B (the predicate binding) and Commit 5.2 (activation) require is now **formally specified as a policy interface**, with — for each item — its name, purpose, required/optional status, omission default, producing and consuming components, validation rules, and replay / Gamma / IEEE-reporting implications. No item introduces new scientific methodology; the single new-science path (admitting a HARM proxy) is explicitly **out of scope and not taken**. No policy *value* is invented herein — this document defines only the interface against which an operator declares values and governance signs confirmations. The frozen science, the frozen engine (`evaluate_decision`), and GAMMA are unmodified.

The predicate binding can therefore be implemented as **pure engineering, parameterized by declared policy** — reading the gate→plane binding from the ExecutionBinding manifest and any θ / `L_amt` / velocity envelope from the frozen Policy Loader, with fail-closed and slice posture as frozen defaults — once the §16 confirmations are signed.

# READY FOR IMPLEMENTATION

---

*Deployment policy specification only. No code, no repository modification beyond authoring this document, no change to GAMMA or `evaluate_decision()`, no invented policy value, no new scientific methodology. Every item is grounded in the authoritative in-repo corpus (ExecutionBinding manifest, `frozen_policy.ScientificPolicy`, `runtime_context/ports.py`, `eeb_to_engine.py`, `gamma_test_runner.py`, the EEB / RCL / Runtime-Evidence-Architecture / Traceability specs, and `PREDICATE_BINDING_FINAL_SPECIFICATION.md`) and cited accordingly. Awaiting independent review.*
