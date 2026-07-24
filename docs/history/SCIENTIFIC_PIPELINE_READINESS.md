# SCIENTIFIC PIPELINE READINESS

**Assessment only. No code, no implementation, no methodology invented, no Commit 5.2 begun.** Derived solely from the authoritative in-repo specifications (EEB spec, RCL spec, Runtime Evidence Architecture, Implementation Traceability, Engineering Migration Roadmap). `FULL_SPEC.md` and the IEEE paper are cited by these specs but are **not present as files** in the repository; where a claim would require them, it is flagged rather than assumed.

**Roles:** Lead Runtime-Governance Architect · IEEE Artifact Engineer · Runtime-Systems Research Engineer · Software-Verification Engineer.

---

## Task 1 — Does Predicate Binding exist as a complete scientific definition?

**NO.** See `SCIENTIFIC_SPECIFICATION_GAP.md`. The credit-card predicate binding is **explicitly deferred** to five unresolved owner rulings (`IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10`); the only prior binding attempt (`PREDICATE_GENERATION_REDESIGN.md`) was **rejected** as "architecturally wrong" (`RUNTIME_EVIDENCE_ARCHITECTURE.md §6`).

---

## 1. Current scientific pipeline status

Everything from the **runtime producers to the sealed EEB**, and the **frozen engine to the decision**, is defined and implemented. The **one link between them — Predicate Binding — is undefined**.

| Stage | Defined by | Implemented | Status |
|---|---|---|---|
| Runtime producers (A/B/C/D) | RCL spec §3–§7; EEB spec §4 | 2.2, 2.3, 2.4 | ✅ complete |
| Execution Evidence Bundle (immutable contract) | EEB spec §1–§8 | 2.1 | ✅ complete |
| EEB Assembler (producers → sealed EEB) | EEB spec §5; roadmap 2.5 | 2.5 | ✅ complete |
| Evidence-only trace builder (Class-blind) | RCL spec §3–§8; roadmap 5.1 (narrowed) | 5.1 | ✅ complete (transport only) |
| **Predicate Binding (evidence → engine schema)** | **— none — (deferred, §10 rulings)** | **none** | ❌ **SCIENTIFIC GAP** |
| Engine adapter (bound schema → engine columns) | EEB spec §2.2; roadmap 4.1 | 4.1 | ✅ complete (pure remap; consumes a *bound* schema) |
| Frozen engine (`evaluate_decision`, vectorized) | frozen; RCL spec §11; RUNTIME_EVIDENCE_ARCH §2.10 | pre-existing | ✅ frozen |
| Gamma → Decision (Γ=max dᵢ; Π=1[Γ=0]; SAFE_STATE) | frozen; RUNTIME_EVIDENCE_ARCH §2.10 | pre-existing | ✅ frozen |

**Reading:** the substrate is complete and the engine is frozen; the pipeline is **broken only at the Predicate-Binding link**, which no authoritative document specifies for the credit-card arm.

## 2. Predicate Binding readiness

**SCIENTIFIC GAP.** The binding requires five owner-ruled scientific/policy decisions (amount limit `L_amt`, freshness θ, HARM_RISK proxy + θ, gate→plane binding, class-veto plane, actuation timing, velocity-window scope). None is defined; making any is inventing methodology (forbidden). Detail and the minimum required spec are in `SCIENTIFIC_SPECIFICATION_GAP.md §4`.

## 3. Pipeline activation readiness (Task 2 — can Commit 5.2 proceed on existing specs?)

**NO.** Two independent blockers:

1. **Missing prerequisite.** Roadmap 5.2 flips the default to "the Class-blind pipeline (5.1)" that **yields engine-computed decisions**. The narrowed 5.1 produces only evidence traces; the decision-yielding step is the **Predicate Binding (5.1-B)**, which is a SCIENTIFIC GAP. 5.2 cannot run without it.
2. **5.2 is itself gated and non-neutral.** The roadmap marks 5.2 "⚠️ GATED — NOT science-neutral," with **precondition = the five §10 rulings** and a **reviewed, signed metric change** (FPR/FDR/UER become genuine measurements). Existing specs explicitly state "no predicate, threshold, decision, or metric is created" until the rulings land.

Implementing 5.2 on existing specs would require inventing the binding and pre-authorizing a reported-metric change — both forbidden. **5.2 is BLOCKED (on a SCIENTIFIC GAP + owner sign-off).**

## Task 3 — Dependency graph (each arrow → its authoritative document)

```
 Runtime Producers ──①──► Execution Evidence Bundle ──②──► Predicate Binding ──③──► Frozen Engine ──④──► Gamma ──⑤──► Decision
   (A: Interpreter)                                          ✗ UNDEFINED ✗
   (B: RCL objects)
   (C/D: Ports, absent)
```

| Arrow | Transformation | Authoritative document | Status |
|---|---|---|---|
| **①** Producers → EEB | plane-A read (`Amount/Time/features`); plane-B objects (freshness/window/journal); C/D ports (absent) → sealed EEB | EEB spec §2.2 / §4 / §5; RCL spec §3–§7; roadmap 2.2–2.5 | ✅ defined + implemented |
| **②** EEB → Predicate Binding | evidence values → engine predicate inputs (gate booleans, HARM_RISK, thresholded freshness, veto) for the credit-card arm | **NONE** — deferred to `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10` (5 unresolved rulings); prior attempt `PREDICATE_GENERATION_REDESIGN.md` **rejected** by `RUNTIME_EVIDENCE_ARCH §6` | ❌ **UNDEFINED (the gap)** |
| **③** Bound schema → Frozen Engine | pure field remap of an *already-bound* decision schema → engine columns | EEB spec §2.2; roadmap 4.1; `eeb_to_engine.py` | ✅ defined + implemented (but its input — arrow ② — is undefined) |
| **④** Engine → Gamma | deficit vector → `Γ = max_i d_i` (non-compensatory) | frozen `gamma_test_runner.py:876-892`; RCL spec §11; RUNTIME_EVIDENCE_ARCH §2.10 | ✅ frozen |
| **⑤** Gamma → Decision | `Π = 1[Γ=0]`; SAFE_STATE fail-closed; Evidence Quad; ledger | frozen; RUNTIME_EVIDENCE_ARCH §2.10; RCL spec §8/§11 | ✅ frozen |

**Only arrow ② lacks an authoritative definition.** Arrows ①③④⑤ are each anchored to a specific in-repo spec and are implemented/frozen.

## Task 4 — Implementation readiness assessment

| Task | Classification | Basis |
|---|---|---|
| Runtime producers (2.2–2.4) | **READY** (done) | RCL/EEB specs; implemented + tested |
| EEB contract + assembler (2.1, 2.5) | **READY** (done) | EEB spec; implemented + tested |
| Engine adapter (4.1) | **READY** (done) | roadmap 4.1; implemented + zero-logic-diff verified |
| Evidence-only trace (5.1 narrowed) | **READY** (done) | RCL spec; implemented + Class-blind/deterministic tested |
| Batch-1 engineering (6.1, 6.2, 6.3, 6.5, 6.4-reduced) | **READY** (done) | roadmap 6.x; implemented + parity-gated |
| **Predicate Binding (5.1-B)** | **SCIENTIFIC GAP** | §10 rulings undefined; arrow ② unspecified |
| **Pipeline activation (5.2)** | **BLOCKED** | depends on 5.1-B (gap) + 5 rulings + signed metric change |
| Post-5.2 engineering (6.4-full, 6.3 LAB re-baseline, 6.5 re-run) | **BLOCKED** | depend on 5.2 |

## 5. Remaining scientific gaps

**One gap, five rulings** (the sole scientific blocker to finishing the pipeline):
1. Actuation timing / `ACT_PERMIT` semantics (Ruling 1) — owner: runtime semantics.
2. Class-veto producing plane C vs D (Ruling 2) — owner: policy.
3. Gate-index → evidence-plane binding (Ruling 3) — owner: policy/binding.
4. HARM_RISK proxy admissibility + Class-blind θ and `L_amt` (Ruling 4) — owner: governance/science.
5. Per-subject vs global velocity windows (Ruling 5) — owner: science.

Each is an owner **decision + disclosed Class-blind rationale**, not engineering time. No `FULL_SPEC.md`/paper file exists in-repo to derive them from; they are external/frozen and reserved for owner sign-off.

## 6. Remaining engineering work

- **Blocked-until-rulings:** build the Predicate Binding (5.1-B) to the signed spec, then activate (5.2). Both are Med–High engineering **once** the rulings exist — but **zero** engineering is safe now.
- **Blocked-until-5.2:** 6.4-full guardrail enforce, 6.3 LAB re-baseline (signed), 6.5 Class-blind re-generation.
- **Available now:** none — all remaining pure-engineering (Batch 1) is complete; everything left is gated on arrow ②.

## Recommendation

# SCIENTIFIC SPECIFICATION REQUIRED

The engineering substrate is complete and the engine is frozen; the pipeline is broken at exactly one link — **arrow ② (Predicate Binding)** — which **no authoritative specification defines** for the credit-card arm. It is explicitly deferred to the **five owner rulings** in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10`.

**Do not implement 5.1-B or 5.2.** The single unblocking action is **not engineering** — it is obtaining the five signed rulings (with disclosed, Class-blind rationale) from their named owners. Once signed, the binding becomes pure engineering to the ruled spec and the pipeline can be activated with scientific review of the deliberate metric change. Proceeding without the rulings would require inventing methodology — the exact failure `PREDICATE_GENERATION_REDESIGN.md` was rejected for and that Commit 5.1 correctly stopped on.

---

*Readiness assessment only. No code, no modification, no methodology invented, no Commit 5.2 begun. The pipeline is engineering-complete and frozen-engine-ready; its one missing scientific link is the credit-card Predicate Binding, gated on five owner rulings. Awaiting those rulings before any scientific implementation.*
