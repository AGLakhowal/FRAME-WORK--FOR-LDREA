# COMMIT 5.2 — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no implementation, no repository modification, no next roadmap item begun.** An engineering-readiness review of Commit 5.2 (activate the Class-blind pipeline; retire `gamma_map_raw` label authoring) against the frozen corpus. Per the stop condition, where a hidden assumption or blocker is found it is **documented, not resolved**.

**Roles:** Principal Runtime Systems Architect · IEEE Artifact Engineer · Runtime Governance Researcher · Software Verification Engineer.

**Frozen authoritative sources:** FULL_SPEC · IEEE paper · Runtime Evidence Architecture · Runtime Context Layer Spec · Execution Evidence Bundle Spec · Predicate Binding Final Spec · Predicate Binding Invariants · Deployment Policy Spec · L-DREA Deployment Profile Contract · Engineering Migration Roadmap.

---

## 1. Executive Summary

**The component-to-component wiring is READY; the activation is BLOCKED.**

Every pairwise connection in the target pipeline is already implemented, specified, and frozen, and the chain is already proven to run end-to-end (Commit 5.1-B `test_connection_*`): a sealed evidence EEB flows through Predicate Binding → the frozen 4.1 adapter → `evaluate_decision` → Γ → Decision, yielding SAFE_STATE with no new methodology. Connecting the parts introduces no science.

**But Commit 5.2 is not "connect the parts" — it is "make the Class-blind pipeline the *reported* credit-card generator and retire `gamma_map_raw`."** That step is gated by the roadmap itself ("⚠️ GATED — NOT science-neutral") and, on inspection of the code, hits **three blockers the frozen specifications explicitly externalize or do not resolve**:

1. **A signed, reviewed metric-change ruling** (owner decision). Activation changes reported FPR/FDR/UER from the current **Class-authored tautology** to the Class-blind result. The roadmap makes this a **blocking precondition** ("a deliberate diff, reviewed and signed"); the Deployment Contract makes metrics **policy-conditional** (I-4). This is an owner act, not a scientific spec, and is not stated to be signed.
2. **A declared deployment policy + governance confirmations** (Gap 3; Deployment Contract §16 C1–C6). The bare Class-blind binding yields the **degenerate full-vector fail-closed all-deny**; a **non-degenerate** result requires a declared credit-card `ExecutionBinding` gate-set + risk-budget SLA that **does not yet exist**. Which result is reported (all-deny vs a declared A-slice) is an owner/policy decision the corpus reserves.
3. **A hidden engineering gap: there is no Class-blind producer for the full reported / replay / benchmark schema.** The Class-blind pipeline (5.1 + 5.1-B → 4.1 → engine) produces the **decision schema only** (`NODE_GATE_COLS`, `HARM_RISK`, `StaleContext`, `TelemetryFresh`, `ReasonCodes`, Γ/Π/Decision). The many other reported columns (`ProposalID`, `ERTuple_ID`, `PermitTokenID`, timestamps, **HASH chain**, `EnvironmentContext`, ordering/replay flags, ConcurBench inputs) are produced **only** by `gamma_map_raw` — which is **Class-entangled** (template selected by `Class`; hash canon computed over Class-derived `Status`/`Gamma`/`harm`; `EnvironmentContext` embeds `class=…`). It can neither be **kept** (it leaks `Class`, breaking Class-blindness) nor **trivially swapped** (no Class-blind emitter exists). Producing one is new engineering beyond "connection," and its ledger/replay output is a **deliberate, signed rebaseline**.

**Verdict: IMPLEMENTATION BLOCKED** — not on missing science (frozen) and not on the binding (frozen), but on owner/governance acts the specs mandate **and** a Class-blind full-schema emitter that does not yet exist.

---

## 2. Scope

**In scope for Commit 5.2 (per roadmap):** flip the reported credit-card generator to the Class-blind pipeline; retire `gamma_map_raw.py:150-181` (the label-authoring branch). It **shall not** redesign any component and **shall not** introduce scientific methodology.

**This review covers:** each connection in `EEB → Predicate Binding → EEB→Engine Adapter → Frozen Engine → Gamma → Decision`; hidden-assumption analysis; scientific-neutrality analysis; the implementation boundary (allowed/frozen files, active/inactive paths); and the full verification plan.

**Connection-by-connection readiness** (each arrow of the target pipeline):

| Connection | Already implemented? | Already specified? | Needs new methodology? | Needs deployment policy? | Needs owner decision? |
|---|---|---|---|---|---|
| Evidence producers → **EEB** (5.1 `evidence_trace_builder`) | ✅ yes | ✅ RCL/EEB §2–§5 | ❌ no | ❌ no | ❌ no |
| EEB → **Predicate Binding** (5.1-B `predicate_binding`) | ✅ yes (frozen) | ✅ Predicate Binding Final + Invariants | ❌ no | ⚠️ *gate-set/SLA if non-degenerate slice wanted* | ⚠️ *Gap 3 slice choice* |
| Predicate Binding → **EEB→Engine Adapter** (4.1 `eeb_to_engine`) | ✅ yes (frozen) | ✅ EEB §2.2; roadmap 4.1 | ❌ no | ❌ no | ❌ no |
| Adapter → **Frozen Engine** (`evaluate_decision`) | ✅ yes (frozen) | ✅ frozen | ❌ no | ❌ no | ❌ no |
| Engine → **Gamma** (`Γ = maxᵢ dᵢ`) | ✅ yes (frozen) | ✅ frozen | ❌ no | ❌ no | ❌ no |
| Gamma → **Decision** (`Π = 1[Γ=0]`, SAFE_STATE) | ✅ yes (frozen) | ✅ frozen | ❌ no | ❌ no | ❌ no |
| **Activation**: pipeline → *reported* generator (retire `gamma_map_raw`) | ❌ **no producer for full schema** | ⚠️ roadmap flags GATED | ❌ (connection) / ⚠️ (emitter is new eng.) | ✅ **yes** (C1–C6) | ✅ **yes** (signed metric change + rebaseline) |

**Reading:** every *decision* connection is green. The **activation row** carries all the blockers.

---

## 3. Allowed file modifications

If (and only if) the §10 blockers are cleared by their owners, Commit 5.2's modifications are bounded to:

| File | Permitted change | Constraint |
|---|---|---|
| `run_all.py` / generator default | flip the default generator to the Class-blind pipeline | wiring only; no decision logic |
| `gamma_map_raw.py` | archive/remove the **label-authoring branch** (`:150-181`) | the Class→predicate authoring only |
| `archive/` | receive the retired `gamma_map_raw` authoring | move, not edit |
| `tests/fixtures/baseline/*` (credit-card arm) | **signed** rebaseline of the intentionally-changed artifacts | only with the signed metric-change ruling |
| A **new** Class-blind full-schema emitter (if authored) | produce replay/ledger/benchmark columns Class-blind | **new engineering — beyond "connection"; see §6 H-3** |

No other file may be modified. Note that the last row is **not** "connection" and, if required, changes 5.2's character from a wiring commit to an engineering commit — a scope question for the owner.

---

## 4. Frozen files (must NOT be modified)

- `gamma_test_runner.py` — `evaluate_decision` (:133-178), `NODE_GATE_COLS` (:119-130), the vectorized decision block, Γ aggregation, SAFE_STATE, replay emitter (`write_replay_manifest`), Evidence Quad, Hydra Ledger hash chain.
- `runtime_context/predicate_binding.py` (5.1-B, frozen), `eeb_to_engine.py` (4.1, frozen), `execution_evidence_bundle.py` (2.1), `assembler.py` (2.5), `ports.py` (2.2), `context_objects.py` (2.3), `transaction_interpreter.py` (2.4), `evidence_trace_builder.py` (5.1).
- `gamma_replay_verify.py` (independent verifier), `concurbench_full.py`, `fcr_test.py`, `full_spec_conformance.py` (separate arms; not the credit-card generator).
- All frozen scientific manifests + Merkle root; `frozen_policy.ScientificPolicy`; `Execution_Binding_Manifest.json`.
- The entire frozen specification corpus.

---

## 5. Runtime activation diagram

```
BEFORE 5.2 (active, reported)                    AFTER 5.2 (proposed active, reported)
────────────────────────────                    ─────────────────────────────────────
 raw ULB CSV + Class                              raw ULB request (Class DROPPED at plane A)
        │                                                 │
        ▼  gamma_map_raw.py  ⚠️ CLASS-AUTHORED            ▼  evidence_trace_builder (5.1)   Class-blind
 GAMMA_..._mapped.csv                              sealed evidence-only EEB
   (gates/HARM/ReasonCodes/HASH                            │
    all derived from Class)                                ▼  predicate_binding (5.1-B, frozen)
        │                                          bound EEB (carry / absent→fail-closed)
        ▼  gamma_test_runner (reads CSV)                   │
 evaluate_decision (FROZEN) → Γ → Decision                 ▼  eeb_to_engine (4.1, frozen)
        │                                          decision schema
        ▼                                                  │
 reported FPR/FDR/UER (tautological)                       ▼  evaluate_decision (FROZEN) → Γ → Decision
                                                           │
                                                           ▼  [GAP: no Class-blind producer for
                                                              replay/ledger/benchmark columns]
                                                           ▼
                                                   reported FPR/FDR/UER (Class-blind; CHANGED)

INACTIVE (unchanged by 5.2):
  • --eeb-input flag path (4.1 zero-logic-diff arm)  — remains opt-in, byte-identical
  • ConcurBench / FCR / FULL_SPEC arms               — separate; must remain parity-identical
  • predicate_binding as unconsumed scaffolding      — becomes consumed only after activation
```

**Runtime path that becomes active:** `evidence_trace_builder → predicate_binding → eeb_to_engine → evaluate_decision → Γ → Decision` as the reported credit-card generator.
**Runtime path that becomes inactive:** `gamma_map_raw` label authoring (the Class→predicate branch).
**Paths that stay exactly as-is:** the `--eeb-input` 4.1 arm, ConcurBench, FCR, FULL_SPEC, and the frozen engine.

---

## 6. Hidden assumption analysis

Each item is **documented, not resolved** (stop condition).

- **H-1 · Hidden metric change (surfaced, not hidden by roadmap, but must be signed).** Activation changes the reported credit-card metrics from the Class-authored tautology to the Class-blind result. The roadmap flags this ("NOT science-neutral") and requires a **signed, reviewed diff**. Not a scientific spec; an owner act. **STOP — owner sign-off required.**

- **H-2 · Hidden policy interpretation (Gap 3 slice choice).** The Class-blind binding, with no declared credit-card `ExecutionBinding` gate-set / SLA, yields the **degenerate full-vector fail-closed all-deny** (every row SAFE_STATE). The roadmap's phrase "FPR/FDR/UER become genuine measurements (**may be non-zero**)" **silently presupposes a non-degenerate slice** — i.e., a declared amount/velocity gate-set with an SLA (`L_amt`, θ_fresh). No such declaration exists. Reporting a non-degenerate result would require **declaring policy values**; reporting the all-deny is itself the Gap-3(a) **policy choice**. Either way this is a deployment-policy declaration + governance confirmation (Deployment Contract §16 C1–C4), **not** a connection. **STOP — deployment policy + owner ruling required. Do NOT invent an SLA to make metrics "non-zero."**

- **H-3 · Hidden predicate/emitter generation (the critical engineering gap).** The Class-blind pipeline emits the **decision schema only**. Every other reported column — `ProposalID`, `ERTuple_ID`, `PermitTokenID`, `Commit/ActuateTimestamp`, **`HASH_prev`/`HASH_current`**, `EnvironmentContext`, ordering/replay flags, and the ConcurBench inputs — is produced **only** by `gamma_map_raw`, which is **Class-entangled**: the row template is chosen by `Class` (`fraud_tpl if is_fraud else legit_tpl`), `HARM` is `HARM_FRAUD if is_fraud`, `EnvironmentContext` embeds `class={…}`, and the **ledger hash canon is computed over Class-derived `Status`/`Gamma`/`harm`**. Consequently:
  - **Keeping** `gamma_map_raw` for the "structural" columns **leaks `Class`** into the reported artifact and the ledger → **fails Class-blindness** (Deployment Contract; EEB §9). Not permissible.
  - **Retiring** it leaves **no producer** for those columns; the frozen engine + binding do not emit them.
  - Building a **Class-blind full-schema emitter** is **new engineering**, not "connect the components," and its ledger/replay output is a **new chain** (deliberate, signed replay rebaseline). **STOP — this is unspecified engineering; do NOT author it under a "connection" commit without owner scope approval.**

- **H-4 · Hidden replay change.** Activation produces a **different replay manifest** (new decisions, new hash chain) → the manifest SHA baseline **changes**. This is a legitimate rebaseline *only with the signed metric-change ruling*; silently accepting it would mask the methodology change. **STOP — signed rebaseline required.**

- **H-5 · Hidden benchmark change / parity break.** The regression parity gate (6.3) compares the credit-card LAB summary + replay SHA to the frozen 0.1 baseline. Post-activation these **intentionally diverge** and the gate **fails** unless the baseline is rebaselined **with sign-off**. ConcurBench/FCR/FULL_SPEC are **separate arms** and must remain **byte/numeric-parity**; activation must not touch them (verify in §8). **STOP for the credit-card baseline (signed rebaseline); parity must hold for the other arms.**

- **H-6 · Hidden authorization / Gamma change.** None found. The binding and adapter are frozen and add no decision path; `evaluate_decision` and Γ are untouched. The **single-engine guardrail** (6.4) must confirm no second decision path is introduced by the activation wiring (verify in §8). ✅ no change, guardrail-verifiable.

- **H-7 · Hidden fail-open path.** None found *in the frozen components* (non-default-permit; binding fail-closes; PB-1/PB-2 invariants). **Risk to guard at implementation:** the activation wiring must contain **no permit-on-error / permit-on-absent-EEB fallback** and must not retain a `gamma_map_raw` PERMIT path as a default. Any such fallback would be a fail-open. **Flag for implementation-time verification; none exists today.**

---

## 7. Scientific neutrality analysis

| Property | Status under 5.2 activation | Note |
|---|---|---|
| `evaluate_decision` / Γ / SAFE_STATE frozen | ✅ unchanged | connection only |
| Predicate Binding behaviour frozen | ✅ unchanged | 5.1-B frozen |
| **Reported metrics unchanged** | ❌ **intentionally changed** | the methodology change — **not neutral** (roadmap) |
| Class-blindness end-to-end | ⚠️ **conditional** | holds for the decision pipeline; **fails if `gamma_map_raw` is partially retained** (H-3) |
| Replay determinism | ✅ preserved on the new trace | but manifest SHA rebaselined (H-4) |
| Other arms (ConcurBench/FCR/FULL_SPEC) parity | ✅ must remain parity | verify untouched (§8) |
| No new methodology | ✅ for connection / ❌ if an emitter is authored | H-3 makes emitter authoring non-neutral engineering |

**Conclusion:** 5.2 is **deliberately non-neutral on the reported credit-card metrics** (by design, roadmap) and is **conditionally neutral elsewhere** — neutrality of Class-blindness and of the other arms depends on resolving H-3 (emitter) and not touching the separate arms.

---

## 8. Verification plan (for when the blockers are cleared)

- **Regression.** Run `tests/test_regression_parity.py`. Expect: ConcurBench/FCR/FULL_SPEC **PASS unchanged**; credit-card LAB summary + replay SHA **intentionally change** → update the baseline **only under the signed rebaseline** and re-assert parity against the new signed baseline.
- **Replay.** `gamma_replay_verify.py` on the new manifest → RESULT: PASS (0 adjacency/ledger/consistency failures); assert **determinism** (two runs → byte-identical manifest + digest); record the new manifest SHA as the signed baseline.
- **Parity (unchanged arms).** Byte/numeric-identical: `concurbench_full_report.json`, `fcr_test_report.json`, `full_spec_conformance_report.json`, and the `--eeb-input` 4.1 zero-logic-diff arm.
- **Benchmark stability.** Confirm 5.2 touches **only** the credit-card generator default; ConcurBench/FCR/FULL_SPEC code and outputs unmodified (diffstat + report parity).
- **Byte-identical verification (where applicable).** Flag-OFF `--eeb-input` path and the non-credit-card arms remain byte-identical to pre-5.2; `evaluate_decision` + `NODE_GATE_COLS` byte-identical to HEAD.
- **Guardrail.** Run the single-engine guardrail (`tests/test_single_engine_guardrail.py`; 6.4) → confirm exactly one decision engine; the activation introduces **no second decision path** and no bypass.
- **Provenance verification.** Every reported decision traces to a **sealed EEB** with complete provenance and the binding's plane-tagged fields (PB invariants); the emitter (if any) preserves provenance and the ledger links to the EEB (`prior_ledger_link`).
- **Class-blind verification.** End-to-end: assert `Class` is read **nowhere** in the active path (AST/string scan across `evidence_trace_builder`, `predicate_binding`, adapter, **and any new emitter**); Class present/absent/differing → identical reported artifact (extend the 5.1/5.1-B Class-blind tests to the **full** reported row, catching any `gamma_map_raw`/emitter leak — the H-3 tripwire).

**Acceptance:** all above green **and** the signed metric-change ruling + signed rebaseline + declared deployment policy (C1–C6) on file.

---

## 9. Rollback strategy

- **Primary:** re-enable the `gamma_map_raw` default (single flag flip); the retired authoring remains in `archive/`. Reverts the reported generator to the pre-5.2 state.
- **Baseline:** retain the pre-5.2 signed baseline fixtures; rollback restores them as the parity target.
- **Isolation:** the frozen engine, binding, adapter, and the other arms are untouched, so rollback is a generator-default flip plus a fixture restore — no decision-logic revert needed.
- **New emitter (if authored):** additive and behind the generator default; disabling the default fully deactivates it.

---

## 10. Readiness certification

The **decision pipeline connection is engineering-ready and frozen-safe** — every arrow from EEB through Predicate Binding, the 4.1 adapter, the frozen engine, Γ, and Decision is implemented, specified, and already proven end-to-end without new methodology. **However, Commit 5.2 (activation) cannot proceed on the frozen scientific specifications alone**, because those specifications **themselves externalize** the acts activation requires, and one required producer does not exist:

1. a **signed, reviewed metric-change ruling** + **signed replay/parity rebaseline** (owner decision; H-1/H-4/H-5);
2. a **declared credit-card deployment policy** (Gap-3 slice: all-deny vs a declared A-slice) + **governance confirmations C1–C6** (deployment policy; H-2) — with **no invented SLA**;
3. a **Class-blind producer for the full reported/replay/benchmark schema** — `gamma_map_raw` is Class-entangled and can be **neither kept (Class leak) nor trivially swapped**; building one is **new engineering beyond "connection"** (H-3).

None of these is missing science, and none may be resolved here (stop condition). Until the owner rulings/sign-offs are on file and the Class-blind emitter question is scoped, activation would require either inventing policy (H-2), leaking `Class` (H-3), or silently changing reported science (H-1/H-4/H-5) — each forbidden.

# IMPLEMENTATION BLOCKED

**Single sentence:** the pipeline *wiring* is ready, but 5.2's *activation* is blocked on (a) a signed metric-change ruling + rebaseline, (b) a declared credit-card deployment policy + C1–C6 confirmations, and (c) an unspecified Class-blind full-schema emitter — the first two are owner/governance acts the frozen specs require, the third is engineering not yet in scope.

---

*Pre-implementation review only. No code, no modification, no methodology invented, no next roadmap item begun. Findings documented, not resolved. Awaiting independent review and the enumerated owner/governance acts before any Commit 5.2 implementation.*
