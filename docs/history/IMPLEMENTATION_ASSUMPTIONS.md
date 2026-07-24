# IMPLEMENTATION_ASSUMPTIONS.md

**Phase 3 — Part G: search for hidden assumptions, magic constants, implicit defaults, fallbacks,
special cases, and hidden mappings.** For each: *where it is · why · does it affect correctness*.

Search method: read the decision core, the interception layers, and the manifest loaders; grep for
literals and default-return branches. All findings below are cited to source. Nothing was changed.

---

## A1. AgentDojo routes every tool call through `run_function` (foundational assumption)

- **Where:** implicit — `GammaGovernedRuntime` is injected via AgentDojo's `runtime_class` and overrides `FunctionsRuntime.run_function` ([governed_runtime.py:31,50](agentdojo_integration/interception/governed_runtime.py#L31-L50)).
- **Why:** the reference monitor mediates only what passes through that method; AgentDojo's own dispatcher must call it for every tool invocation.
- **Affects correctness?** **Yes — it is the root assumption of complete mediation (P5) and non-bypassability (P7).** If AgentDojo ever executed a tool without `run_function`, mediation would be bypassed. This is an external contract, **assumed, not proven here.** Unknown-tool fail-closed handling (A4) mitigates *new* tools but not a routing bypass.

## A2. Frozen roots are hardcoded constants (intentional commitments, not magic numbers)

- **Where:** `SCIENTIFIC_ROOT = "ce8c8467…"` ([frozen_policy.py:22](agentdojo_integration/interception/frozen_policy.py#L22)); `BINDING_SHA = "a3861927…"` ([execution_binding.py:24](agentdojo_integration/interception/execution_binding.py#L24)).
- **Why:** these are the pre-registration commitments; any manifest drift must trip a load-time error.
- **Affects correctness?** **Beneficial.** They are *checked*, not *assumed*: `_verify()` recomputes the Merkle root and raises on mismatch (executed: tamper → `Version Mismatch`). They are constants-as-integrity-anchors, not silent magic.

## A3. Class-veto token set `{CLASS_1, GOODHART}` is hardcoded

- **Where:** [gamma_test_runner.py:157](gamma_test_runner.py#L157) (single-row) and [:929-932](gamma_test_runner.py#L929-L932) (vectorized).
- **Why:** operationalizes the paper's class-level veto (fraud / Goodhart) as an uppercase substring test on `ReasonCodes`.
- **Affects correctness?** **Bounded.** Any ReasonCodes NOT containing these tokens yields Γ_class=0. This is exactly the specified veto vocabulary (README §8). A row whose adversarial nature is encoded under a *different* token would not trigger the class veto — but would still be denied if any node deficit exists (the corpus shows all 492 fraud rows also fail Γ_G). Assumption: the veto vocabulary is complete for the evaluated dataset. Documented, not a defect for this corpus.

## A4. Unknown tool → SAFE_STATE (fail-closed default)

- **Where:** `classify()` returns `(True, _UNKNOWN_CLASS, [], False)` for unmapped tools ([frozen_policy.py:78](agentdojo_integration/interception/frozen_policy.py#L78)); runtime denies ([governed_runtime.py:55-59](agentdojo_integration/interception/governed_runtime.py#L55-L59)); `unknown_tool_handling` = `SAFE_STATE_FAIL_CLOSED`.
- **Why:** Definition 2(i) complete mediation resolved to §0.10 non-default-permit.
- **Affects correctness?** **Beneficial and correct** — the safe direction. A tool absent from the frozen map is denied, never silently permitted. Verified by execution.

## A5. `GammaBridge.decide` starts from an all-clean baseline row

- **Where:** [gamma_bridge.py:31-36](agentdojo_integration/interception/gamma_bridge.py#L31-L36): all `NODE_GATE_COLS=True`, `HARM_RISK=0.0`, `StaleContext=False`, `TelemetryFresh=True`, `ReasonCodes="NONE"`, `Actuated=False`, `ACT_PERMIT=False`, `TOKEN_VALID=True`, `AuthoritySignatureValid=True`; then flips a slot only for families with `deficit == 1` ([:37-50](agentdojo_integration/interception/gamma_bridge.py#L37-L50)).
- **Why:** the bridge translates a *sparse deficit vector* into the engine's dense row; unlisted/clean families contribute no deficit.
- **Affects correctness?** **Scope-critical, and the key honest caveat.** A predicate family that is **not evaluated** (status `EXCLUDED_BY_POLICY_TIER_S`, or simply absent from `deficits`) defaults to **no deficit → clean → contributes toward PERMIT.** This is the Tier-S structural-only posture: only families the manifest marks `APPLICABLE_ENV_DERIVED` (recipient/identity/destination/resource recognition, amount limit) actually gate the decision from env; the rest are declared excluded, not silently passed (`PredicateEvaluator` reports `EXCLUDED_BY_POLICY`). **Consequence for reviewers:** authorization strength is exactly the strength of the *env-derived* families; excluded families are out of scope by design, not by accident. This is documented behavior, but it means "PERMIT" asserts "no *evaluated* deficit", not "no *conceivable* deficit". Surfaced explicitly.

## A6. Single-row Eq. 7 omits the hash-chain disjunct (special case)

- **Where:** [gamma_test_runner.py:166-169](gamma_test_runner.py#L166-L169) (4 disjuncts) vs vectorized [:985](gamma_test_runner.py#L985) (5th disjunct `~DerivedChainLinked`).
- **Why:** a single decision row has no cross-row `HASH_prev/HASH_current` context.
- **Affects correctness?** **No effect on any decision (Π).** Only the `unauthorized` diagnostic differs, and only in a state the single-row API cannot represent. Fully analyzed in `EQUATION_CONFORMANCE.md` §C7.

## A7. GENESIS anchor accepts a set of sentinels

- **Where:** [gamma_test_runner.py:669,684,956](gamma_test_runner.py#L956) — first `HASH_prev` accepted if uppercase ∈ `{GENESIS, 0, NONE, ""}`.
- **Why:** tolerate different genesis encodings across trace producers.
- **Affects correctness?** **Bounded.** Broadens the accepted anchor; a genuinely broken first link encoded as one of these sentinels would be treated as genesis. Low risk for the controlled corpus; noted.

## A8. Threshold θ default = 0.5; design effect default = 1.7; compensatory τ = 0.15

- **Where:** θ `default=0.5` ([:217](gamma_test_runner.py#L217)); DE `default=1.7` ([:235](gamma_test_runner.py#L235)); `tau = 0.15` ([:1057](gamma_test_runner.py#L1057)).
- **Why:** θ is the HARM admissibility threshold (paper §8, overridable CLI); DE is the cluster-correction design effect (paper IX-G); τ is the *negative-control* compensatory permit threshold (Corollary 2 probe only).
- **Affects correctness?** θ and DE are **documented parameters**, not hidden — θ is passed explicitly to `evaluate_decision`. τ affects **only** the negative-control demonstration, never the LLC decision. No hidden effect on authorization.

## A9. Loader default fallbacks (structural / passthrough)

- **Where:** `family_threshold` default `{"kind":"structural","deficit":0}` ([execution_binding.py:61](agentdojo_integration/interception/execution_binding.py#L61)); `tool_binding` default `{"recognition":None,"structural_only":True}` ([:64](agentdojo_integration/interception/execution_binding.py#L64)).
- **Why:** families/tools without an env-derived directive are structural (no runtime deficit computed).
- **Affects correctness?** **Consistent with A5** — an unspecified family is structural → no deficit. Same scope caveat; reported, not silent (status surfaced as `EXCLUDED_BY_POLICY`).

## A10. Amount comparison swallows type errors → no deficit

- **Where:** [predicate_evaluation.py:158-160](agentdojo_integration/interception/predicate_evaluation.py#L158-L160) — `except (TypeError, ValueError): deficits[fam]=0; status="EVALUATED_PASS"`.
- **Why:** a non-numeric amount cannot be threshold-compared.
- **Affects correctness?** **Minor fail-open in one predicate:** a malformed amount is treated as PASS (no deficit) rather than SAFE_STATE. This is a *local* fail-open contrary to the global fail-closed posture (A4). For the evaluated corpus amounts are numeric, so unobserved — but flagged as the one place the code defaults toward permit on bad input. **Reported (per rules, NOT fixed).**

---

## G-Summary

| # | Assumption / constant | Affects correctness? |
|---|---|---|
| A1 | AgentDojo routes all calls via run_function | **Yes — foundational, assumed not proven** |
| A2 | Hardcoded frozen roots | No (checked, beneficial) |
| A3 | `{CLASS_1,GOODHART}` veto vocabulary | Bounded (complete for corpus) |
| A4 | Unknown tool → SAFE_STATE | No (safe direction) |
| A5 | All-clean bridge baseline / excluded-family default-clean | **Yes — scopes PERMIT to evaluated families** |
| A6 | Single-row Eq.7 minus chain term | No (decision unaffected) |
| A7 | GENESIS sentinel set | Bounded |
| A8 | θ=0.5, DE=1.7, τ=0.15 | No (documented params / control-only) |
| A9 | Structural/passthrough loader defaults | Scope caveat (same as A5) |
| A10 | Amount TypeError → PASS | **Local fail-open (reported, unobserved on corpus)** |

**Two items warrant reviewer attention:** **A5** (PERMIT means "no *evaluated* deficit", i.e.
Tier-S structural-only scope — by design and documented) and **A10** (a single local fail-open on
malformed amount input, contrary to the otherwise fail-closed posture). **A1** is the standing
external assumption underlying complete mediation. None of these are *hidden* in the sense of
undocumented — each is traceable to source and, for A4/A5/A10, to an explicit status/handling
declaration — but they are the assumptions a reviewer must accept for the safety claims to be total.
