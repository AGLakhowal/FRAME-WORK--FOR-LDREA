# NEXT-COMMIT IMPLEMENTATION BLOCKER — Commit 5.1

**Status: BLOCKED. No code written, no file modified, nothing implemented.** During fast-track implementation of the next roadmap commit (**5.1**), I discovered an architectural conflict / hidden assumption between the roadmap's 5.1 acceptance criterion and the explicitly-gated scientific rulings. Per the stop condition ("Do NOT invent a solution"), I halted and produced this document instead of guessing a predicate binding.

**Next commit identified:** Commit 5.1 — `feat(pipeline): add Class-blind evidence-only trace generation (flag OFF, parallel)` (`ENGINEERING_MIGRATION_ROADMAP.md:165-173`).

---

## 1. The ambiguity / architectural conflict

Roadmap 5.1 states two things that cannot both be satisfied without the gated rulings:

> **Purpose:** new generation path producing an **evidence-only trace** (plane-A from the interpreter, plane-B from RCL, **C/D evidence-absent**), **letting the engine compute decisions via 4.1**.
> **Tests required:** Class-blindness; determinism; **the produced trace feeds 4.1 and yields engine-computed decisions**.

The conflict is with the authoritative traceability spec, which **blocks the predicate binding** that "yields engine-computed decisions":

> `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md` Part 10: *"the RCL/EEB transport scaffolding — YES; the credit-card predicate **binding** — NO, pending a small, explicit set of scientific/policy rulings … the five enumerated rulings above must be decided (by their named owners) before the credit-card **predicate binding** (S6/S8) is implemented — and until then **no predicate, threshold, decision, or metric is created** by any destination in this plan."*

The five gated rulings (roadmap `:180`; traceability §10 / EEB spec §10) include exactly the mappings needed to turn an evidence-only trace into engine inputs: **gate→plane binding**, **HARM_RISK proxy + Class-blind θ rationale**, **class-veto plane**, **global-vs-per-subject windows**, **actuation timing**.

## 2. Why implementation cannot safely continue

The frozen engine consumes a **decision schema of finished predicate values**, not raw evidence. Verified against the code:

- **The engine requires boolean gate columns.** `gamma_test_runner.py:915-916`: `for c in NODE_GATE_COLS: deficits[c] = (~df[c]).astype(int)`. A raw-evidence value (`Amount` float) or an evidence-absent `None` in a gate column makes `~df[c]` fail — the engine cannot consume raw evidence.
- **The 4.1 adapter is a PURE REMAP, not a predicate generator.** `eeb_to_engine.py:46`: `out[g] = p.node_predicate_vector[i].value` — it extracts already-computed gate booleans verbatim; it does not (and, by its frozen contract, must not) compute a gate from `Amount`/velocity/freshness.
- **No Predicate Generator exists.** `runtime_context/` contains only 2.1–2.5 + 4.1 (contract, ports, RCL objects, interpreter, assembler, EEB→engine adapter). There is **no** module that maps evidence (plane-A `Amount`/features, plane-B freshness deltas / velocity aggregates, C/D absent) → the engine's `NODE_GATE_COLS` booleans + thresholded `StaleContext`/`TelemetryFresh` + `HARM_RISK`.

Therefore, for 5.1's trace to "feed 4.1 and yield engine-computed decisions," **something must generate the predicate values from evidence**, which requires deciding — for the credit-card arm — at minimum:

| Needed mapping | Gated ruling it depends on |
|---|---|
| `Amount` → amount-limit gate boolean (needs limit `L_amt`) | HARM/θ/limit rationale (ruling 4) + gate→plane binding (ruling 3) |
| velocity/ordering aggregate → velocity gate boolean (needs envelope) | gate→plane binding (ruling 3); global-vs-per-subject windows (ruling 5) |
| freshness **delta** → `StaleContext`/`TelemetryFresh` boolean (needs θ_fresh) | Class-blind θ rationale (ruling 4) |
| features `V1..V28` → `HARM_RISK` (a plane-D score) | **HARM_RISK proxy acceptance** (ruling 4) — traceability §10.4 flags this as inadmissible without a disclosed, Class-blind rationale |
| authority gates absent (C/D) → gate boolean (fail-closed direction) | class-veto plane + gate→plane binding (rulings 2, 3) |

Building any of these now = **inventing the gated scientific methodology** (θ, HARM proxy, gate binding, freshness thresholds) that the traceability spec and the roadmap's 5.2 precondition explicitly reserve for owner sign-off. Even though 5.1 is flag-OFF and "not reported," *authoring* these mappings creates predicates/thresholds — which Part 10 forbids until the rulings land. The "flag-OFF" status controls *reporting*, not *whether the scientific mapping has been invented*.

**This is a hidden assumption in the roadmap:** 5.1's "yields engine-computed decisions" silently presupposes a credit-card Predicate Generator whose parameters are the very rulings gated for 5.2. The dependency graph shows the gated boundary *below* 5.1, but 5.1's own acceptance test reaches *across* that boundary.

## 3. What CAN be built now (neutral subset — offered, not assumed)

To avoid crying wolf: the **transport half** of 5.1 is pure engineering and is unblocked — assembling an **evidence-only EEB trace** from components already built and frozen:

- plane-A: `TransactionInterpreter` (2.4) → `txn_amount`/`txn_time`/`txn_feature_ref` (opaque)
- plane-B: RCL producers (2.3) → freshness **deltas**, velocity/ordering aggregates (verbatim, no threshold)
- C/D: `AuthorityPort`/`GovernancePort` (2.2) → **evidence-absent**
- sealed via the assembler (2.5)

This produces a genuine, Class-blind, deterministic **evidence trace** and can be tested for Class-blindness + determinism. **What it cannot do without a ruling** is the last step — "feeds 4.1 and yields engine-computed decisions" — because that step is the gated predicate binding.

## 4. Minimum clarification required (choose one)

1. **Narrow 5.1 to the neutral transport subset (recommended, unblocks immediately):** implement `runtime_context/evidence_trace_builder.py` as an **evidence-only trace assembler** (interpreter + RCL + absent ports → sealed EEB trace), with tests for **Class-blindness + determinism only**. Explicitly **defer** the "feeds 4.1 and yields engine-computed decisions" acceptance criterion to a post-ruling commit (it is the predicate binding, S6/S8, gated). Confirm this scope and I proceed under fast-track.

2. **Provide the gated sign-off now:** rule on the relevant items of `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10` — specifically **gate→plane binding**, **HARM_RISK proxy + Class-blind θ/limit rationale**, **class-veto plane**, and **freshness θ** — by their named owners (governance/science). Then a credit-card Predicate Generator can be built to the ruled spec, and 5.1's full acceptance criterion becomes implementable without invention.

3. **Authorize an explicitly-non-scientific placeholder binding** for the flag-OFF/not-reported path only, naming the owner who accepts that a documented, disclaimed, unratified mapping may exist in the codebase (behind the OFF flag) ahead of the rulings. (I flag this as the weakest option: it puts an un-ruled predicate mapping into the tree, which the traceability spec's Part-10 certification currently forbids.)

## 5. What I did NOT do

I did **not** implement any part of 5.1, did **not** invent a limit/θ/HARM-proxy/gate-binding, did **not** modify any file, and did **not** proceed on a guess. No scientific artifact, predicate, threshold, decision, metric, replay, or benchmark was touched.

---

*Implementation blocker only. The conflict is between roadmap 5.1's acceptance criterion ("yields engine-computed decisions") and the traceability spec's Part-10 gating of the credit-card predicate binding on five owner rulings. Awaiting a scope narrowing (option 1), the gated sign-off (option 2), or an explicit owner authorization (option 3) before implementing Commit 5.1.*
