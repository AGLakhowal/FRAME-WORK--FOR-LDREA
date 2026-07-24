# IMPLEMENTATION_TRACEABILITY.md

**Phase 3 — Formal Specification Verification, Part A**
**Scope:** read-only. No implementation was modified. Every row below was confirmed by reading the cited source at the cited lines and, where noted, by executing the code.
**Date:** 2026-07-09

---

## 0. What "the spec" physically is (honest scoping note)

The master prompt refers to `FULL_SPEC.md`. **There is no file named `FULL_SPEC.md` in this repository.** The specification content is distributed across:

- **Paper prose** — cited throughout the code as "IEEE Access, 2026", A. Gill-Lakhowal (not checked into the repo as a file).
- **`README.md`** — embeds the operative equations (§7 "decision logic", §8 "benchmark rules") and clause-level FULL_SPEC references (§7.1 bands, §0.10, §2.3).
- **`full_spec_conformance.py`** — the executable encoding of the "FULL_SPEC" clauses (§7.1 acceptance bands, AIS sub-signals, 3-signal closure, SVR/FFC). Emits `full_spec_conformance_report.json`.
- **Seven frozen JSON manifests** under `agentdojo_integration/manifests/` (Merkle root `ce8c8467…`) — the machine-readable scientific pre-registration.

Wherever this package says "FULL_SPEC" it means the union of those artifacts. This is recorded as an **observation**, not a defect (see `SCIENTIFIC_CORRECTNESS_CERTIFICATE.md`).

---

## 1. Canonical authorization core

### 1.1 `evaluate_decision()` — the single Law-of-Concurrence decision engine

| Field | Value |
|---|---|
| **File** | [gamma_test_runner.py](gamma_test_runner.py#L133-L178) |
| **Function** | `evaluate_decision(row: Dict, harm_threshold: float) -> Dict` |
| **Inputs** | `row` keys: 10 node gates `NODE_GATE_COLS` (`Gate_A1…A7`, `Lambda_G`, `TOKEN_VALID`, `AuthoritySignatureValid`), `HARM_RISK: float`, `StaleContext: bool`, `TelemetryFresh: bool`, `ReasonCodes: str`, `Actuated: bool`, `ACT_PERMIT: bool`; scalar `harm_threshold: float` (θ) |
| **Outputs** | dict: `gamma_g ∈{0,1}`, `gamma_class ∈{0,1}`, `deficit_count ∈ℕ`, `pi ∈{0,1}`, `isb ∈{0,1}`, `decision ∈{PERMIT, SAFE_STATE}`, `unauthorized ∈{T,F}` |
| **Paper equation** | Law of Concurrence Γ_G = maxᵢ dᵢ, dᵢ = max(0, mᵢ−θᵢ) [§IV-B]; Π decision rule [§VIII-B]; Eq. 7 Unauthorized Execution [§VIII-C] |
| **FULL_SPEC ref** | README §7 (flowchart), §8 (decision rule `PERMIT iff Π=1`); §2.3 / §0.10 non-default-permit |

### 1.2 `NODE_GATE_COLS` — the node predicate vector G = {g₁…gₙ}

| Field | Value |
|---|---|
| **File** | [gamma_test_runner.py:119-130](gamma_test_runner.py#L119-L130) |
| **Symbol** | `NODE_GATE_COLS` (list[str], n=10) |
| **Paper equation** | Predicate vector G; deficit dᵢ=1 when gᵢ fails [§IV-B] |
| **Verified** | Independent transcription in `independent_verifier.py` `REF_GATES` equals `gamma_test_runner.NODE_GATE_COLS` at runtime (`independent_gate_list_matches_frozen: true`). |

### 1.3 Vectorized (dataset-scale) LLC — the batch twin of `evaluate_decision`

| Field | Value |
|---|---|
| **File** | [gamma_test_runner.py:914-947](gamma_test_runner.py#L914-L947) (Γ_G, Γ_class, Π, decision, ISB); [:977-987](gamma_test_runner.py#L977-L987) (Eq. 7) |
| **Function** | inline in `run_benchmark()` over a pandas DataFrame |
| **Inputs** | full CSV corpus columns (same predicate semantics as §1.1) |
| **Outputs** | `DerivedGammaG`, `DerivedGammaClass`, `DerivedPi`, `DerivedDecision`, `DerivedISB`, `DerivedUnauthorized` |
| **Paper equation** | identical to §1.1 (see `EQUATION_CONFORMANCE.md` for the single-row↔vectorized proof) |

---

## 2. AgentDojo interposition chain (Layer-0 → decision)

### 2.1 `GammaGovernedRuntime` — the sole interception point

| Field | Value |
|---|---|
| **File** | [agentdojo_integration/interception/governed_runtime.py:50-81](agentdojo_integration/interception/governed_runtime.py#L50-L81) |
| **Function** | `run_function(env, function, kwargs, raise_on_error=False)` (overrides `FunctionsRuntime.run_function`) |
| **Inputs** | live AgentDojo `env`, tool `function` name, `kwargs` |
| **Outputs** | tool result (on PERMIT) **or** `GammaSafeState` denial (on SAFE_STATE / unknown tool) |
| **Paper equation** | Definition 1 (externalization boundary), Definition 2 (complete mediation), Definition 4 [§IV] |
| **FULL_SPEC ref** | §2.3 / §0.10 non-default-permit; refactor items 4 (fail-closed), 6 (dependency inversion) |

### 2.2 `GammaBridge` — deficit vector → engine row → REUSED `evaluate_decision`

| Field | Value |
|---|---|
| **File** | [agentdojo_integration/interception/gamma_bridge.py:24-51](agentdojo_integration/interception/gamma_bridge.py#L24-L51); alias at [:19](agentdojo_integration/interception/gamma_bridge.py#L19) |
| **Function** | `GammaBridge.decide(deficits: dict, harm_threshold=0.5) -> dict` |
| **Inputs** | `{frozen_family: deficit∈{0,1}}`; `harm_threshold` |
| **Outputs** | verbatim `evaluate_decision(row, θ)` dict |
| **Key property** | Creates **no** authorization logic; `evaluate_decision = _gamma.evaluate_decision` (imported, not reimplemented, line 19). Family→gamma-slot map is **read** from the Execution Binding Manifest (`self.binding.family_slot`). |
| **Paper equation** | §IV-B LLC (reuse mandate) |

### 2.3 `PredicateEvaluator` — env → per-family deficits

| Field | Value |
|---|---|
| **File** | [agentdojo_integration/interception/predicate_evaluation.py:116-161](agentdojo_integration/interception/predicate_evaluation.py#L116-L161) |
| **Function** | `PredicateEvaluator.evaluate(env, tool, args, families, binding) -> {deficits, status}` |
| **Inputs** | live `env`, tool name, call `args`, applicable `families`, per-tool `binding` |
| **Outputs** | `{'deficits': {family:0/1}, 'status': {family:<status>}}` |
| **Paper equation** | predicate instantiation mᵢ vs θᵢ [§IV-B]; membership / env_upper_bound directives read from manifest |
| **Note** | Holds **no** tool→arg map and **no** threshold constant; both read from Layer-2 (`family_threshold`, `tool_binding`). |

### 2.4 `ScientificPolicy` — Layer-1 frozen manifest loader + Merkle integrity

| Field | Value |
|---|---|
| **File** | [agentdojo_integration/interception/frozen_policy.py:44-83](agentdojo_integration/interception/frozen_policy.py#L44-L83); Merkle verify [:58-72](agentdojo_integration/interception/frozen_policy.py#L58-L72) |
| **Function** | `ScientificPolicy.classify(tool) -> (mediated, eea_class, families, conditional)`; `_verify()` recomputes Merkle root |
| **Inputs** | 7 frozen leaves + `merkle_root.json` |
| **Outputs** | tool classification; frozen root `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618` |
| **Paper ref** | Verification Part 5 (Merkle commitment); Definition 2(i) complete mediation |
| **Verified** | Root recomputes to `ce8c8467…`; wrong `expected_root` raises `PolicyError: Version Mismatch` (executed 2026-07-09). |

### 2.5 `ExecutionBinding` — Layer-2 derived binding loader

| Field | Value |
|---|---|
| **File** | [agentdojo_integration/interception/execution_binding.py:35-71](agentdojo_integration/interception/execution_binding.py#L35-L71) |
| **Function** | `family_slot`, `family_status`, `family_threshold`, `tool_binding`, `unknown_tool_handling` |
| **Inputs** | `Execution_Binding_Manifest.json` |
| **Outputs** | runtime lookups; canonical sha `a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1` |
| **Provenance** | `derived_from_scientific_root` must equal `ce8c8467…` else `PolicyError: Binding Provenance Failure` |
| **Verified** | sha matches at runtime (executed 2026-07-09). |

---

## 3. Family → Gamma-slot binding (read from the frozen manifest at runtime)

Captured by executing `ExecutionBinding.family_slot` over all families (2026-07-09):

| Frozen family | gamma_slot | evaluation_status |
|---|---|---|
| `CTR_ISB` | `__StaleContext__` | EXCLUDED_BY_POLICY_TIER_S |
| `GAMMA` | `__aggregator__` | AGGREGATOR_NOT_A_PREDICATE |
| `GATE_recipient_recognition` | `Gate_A1` | APPLICABLE_ENV_DERIVED |
| `GATE_identity_recognition` | `Gate_A1` | APPLICABLE_ENV_DERIVED |
| `GATE_destination_recognition` | `Gate_A1` | APPLICABLE_ENV_DERIVED |
| `GATE_resource_recognition` | `Gate_A1` | APPLICABLE_ENV_DERIVED |
| `GATE_amount_limit` | `Gate_A2` | APPLICABLE_ENV_DERIVED |
| `GATE_scope` | `Gate_A3` | EXCLUDED_BY_POLICY_TIER_S |
| `GATE_ownership` | `Gate_A4` | EXCLUDED_BY_POLICY_TIER_S |
| `AUTH_TOKEN` | `__TOKEN_VALID__` | EXCLUDED_BY_POLICY_TIER_S |
| `TRACE` | `Gate_A6` | EXCLUDED_BY_POLICY_TIER_S |
| `INTERLOCK` | `Gate_A7` | EXCLUDED_BY_POLICY_TIER_S |
| `CLASS_velocity` | `__ReasonCodes_CLASS__` | EXCLUDED_BY_POLICY_TIER_S |

`unknown_tool_handling` → `SAFE_STATE_FAIL_CLOSED` (Definition 2(i) → §0.10 non-default-permit).

---

## 4. Traceability closure

Every symbol the master prompt enumerates — Γ, Π, decision, authorization, runtime policy, SAFE_STATE, PERMIT — resolves to exactly one authoritative implementation:

| Concept | Authoritative implementation |
|---|---|
| Γ (Γ_G) | `deficit = max(dᵢ)` — [gamma_test_runner.py:140-158](gamma_test_runner.py#L140-L158) |
| Γ_class | `gamma_class` — [gamma_test_runner.py:157](gamma_test_runner.py#L157) |
| Π | `pi = (deficit==0 and gamma_class==0)` — [gamma_test_runner.py:159](gamma_test_runner.py#L159) |
| decision | `"PERMIT" if pi==1 else "SAFE_STATE"` — [gamma_test_runner.py:176](gamma_test_runner.py#L176) |
| SAFE_STATE / PERMIT | same line (176); runtime enforcement [governed_runtime.py:76-81](agentdojo_integration/interception/governed_runtime.py#L76-L81) |
| authorization (runtime) | `GammaGovernedRuntime.run_function` [governed_runtime.py:50-81](agentdojo_integration/interception/governed_runtime.py#L50-L81) |
| runtime policy (frozen) | `ScientificPolicy` + `ExecutionBinding` (manifest-driven; no Python policy) |

**Single-engine invariant:** the tool `tools/check_single_engine.py` exists specifically to statically forbid any assignment of `gamma_g/pi/decision` not routed through `evaluate_decision()`. The bridge imports the engine (line 19) rather than duplicating it. **No second authorization engine exists.**
