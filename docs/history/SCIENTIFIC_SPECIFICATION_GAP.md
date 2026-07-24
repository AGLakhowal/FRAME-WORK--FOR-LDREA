# SCIENTIFIC SPECIFICATION GAP — Runtime Predicate Binding

**Analysis only. No code, no implementation, no methodology invented.** Produced because **Task 1 answered NO**: the Runtime Predicate Binding does **not** exist as a complete scientific definition in the authoritative sources.

---

## 1. Task 1 answer

> Does Predicate Binding already exist as a complete scientific definition?

**NO.**

## 2. The missing definition

The pipeline is fully defined and implemented **up to the sealed Execution Evidence Bundle**, and the **frozen engine** downstream is fully defined. The **single missing link** is the transformation:

```
Execution Evidence Bundle (evidence)  ──►  Frozen engine decision schema (bound predicates)
   Amount, Time, V1..V28 (A)                 NODE_GATE_COLS booleans
   freshness deltas, velocity/ordering (B)   HARM_RISK number, thresholded StaleContext/TelemetryFresh
   Authority/Governance ABSENT (C/D)         ReasonCodes-veto signal
```

The **credit-card Predicate Binding** — how each piece of observable evidence becomes each specific predicate input the frozen `evaluate_decision` reads — is **not specified anywhere** in the authoritative corpus. It is **explicitly deferred**, not merely absent:

> `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md` **Part 10**: *"the credit-card predicate **binding** — NO, pending a small, explicit set of scientific/policy rulings … until then **no predicate, threshold, decision, or metric is created** by any destination in this plan."*

The five **unresolved-by-design** rulings (each owner-assigned) are:

| # | Ruling | Owner | What it fixes |
|---|---|---|---|
| 1 | `actuation_observation` vs `ACT_PERMIT` timing/naming (Eq. 7 execute term: pre-decision intent or post-actuation observation; UER timing) | runtime semantics | the actuation/execute predicate input |
| 2 | `class_veto_evidence` producing plane — governance (D) or authority (C) origin of the non-Class veto | policy | the class-level veto's non-Class source |
| 3 | Gate-index → evidence-plane binding — which `Gate_Ak` binds to amount (A), which to velocity (B); rest → evidence-absent | policy/binding | the `NODE_GATE_COLS` composition |
| 4 | **HARM_RISK proxy acceptance** + disclosed **Class-blind θ and amount limit `L_amt`** (risk-budget SLA, not fit to `Class`) | governance/science | the `HARM_RISK` value and its threshold, plus the amount gate |
| 5 | Per-subject vs global plane-B windows (accept global-only velocity, or declare velocity out of scope) | science | the velocity/ordering predicate scope |

## 3. Why implementation would require inventing science

The frozen engine consumes **finished predicate values**, not raw evidence (verified in code): `gamma_test_runner.py:915-916` computes `deficits[c] = (~df[c]).astype(int)` over boolean gates, and the 4.1 adapter (`eeb_to_engine.py:46`) is a **pure remap** of an already-bound schema — neither derives a predicate from evidence. To bridge evidence → predicates for the credit-card arm, an implementer would have to **choose**, with no authoritative basis:

- an **amount limit `L_amt`** (Ruling 4) — any value is a policy/risk-budget decision;
- a **freshness threshold θ_fresh** (Ruling 4) — converting the RCL's raw deltas to `StaleContext`/`TelemetryFresh` booleans;
- a **HARM_RISK proxy** from `V1..V28` and its **θ** (Ruling 4) — the architecture (`RUNTIME_EVIDENCE_ARCHITECTURE.md §2.3`) explicitly warns this "quietly relocates a **D** signal into **A** … defensible only as an explicitly-labelled proxy, never as the architecture's intended source";
- a **gate→plane binding** (Ruling 3) — which `Gate_Ak` is amount vs velocity;
- a **class-veto plane** (Ruling 2) and **actuation semantics** (Ruling 1);
- a **velocity window scope** (Ruling 5).

Every one of these is a **threshold/decision/metric-determining scientific choice**. Making any of them **is** inventing methodology — precisely what the ABSOLUTE RULE forbids and what `PREDICATE_GENERATION_REDESIGN.md` did (and was **rejected** for by `RUNTIME_EVIDENCE_ARCHITECTURE.md §6` as "architecturally wrong"). There is no `FULL_SPEC.md` or IEEE-paper file in the repository to derive these from; they are external/frozen and cited only by section, and the cited sections define the **generic** predicate vector, not the **credit-card binding**.

## 4. Minimum additional specification required

A **signed Predicate-Binding specification for the credit-card arm** resolving exactly the five rulings, each with a **disclosed, Class-blind rationale**:

1. **Amount gate:** `L_amt` value + source (risk-budget SLA), and which `Gate_Ak` it binds to.
2. **Freshness:** θ_fresh bound(s) converting context/telemetry deltas → `StaleContext`/`TelemetryFresh`.
3. **HARM_RISK:** admit or reject a `V1..V28` proxy; if admitted, the exact derivation + θ, with the Class-blind justification; if rejected, declare `HARM_RISK` evidence-absent for this arm.
4. **Gate→plane binding table:** each `NODE_GATE_COLS` entry → its evidence plane (A/B/C/D) or evidence-absent.
5. **Class-veto plane** (C or D) and **actuation semantics** (Eq. 7 timing); **velocity window** scope (global-only or out-of-scope).

Once these are signed by their named owners, the binding (Commit 5.1-B) becomes pure engineering to the ruled spec, and Commit 5.2 (activation) can follow.

---

*Specification-gap analysis only. No methodology invented, no code written, no file modified. The gap is exactly the five owner rulings enumerated in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10`; until they are signed, the credit-card predicate binding cannot be implemented without inventing science.*
