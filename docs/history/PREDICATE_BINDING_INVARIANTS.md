# PREDICATE BINDING — GOVERNING INVARIANTS (Commit 5.1-B)

**Documentation only. No code change, no change to Gamma, no change to `evaluate_decision()`, no change to Predicate Binding behaviour.** This document makes explicit two invariants that already govern the implemented binding layer (`runtime_context/predicate_binding.py`, Commit 5.1-B). It adds no methodology and alters no behaviour; it names, precisely, what the layer does and does not do, so that independent review can rely on the boundary in writing.

**Roles:** Principal Runtime Systems Engineer · Runtime Governance Architect · IEEE Artifact Engineer · Software Verification Engineer.

---

## Invariant PB-1 — The binding maps evidence *availability*, not policy *truth*

**Statement.** The Predicate Binding layer `B` maps the **availability** of each evidence item into the frozen engine's input schema. It does **not** determine, assert, or represent **policy truth** — the truth or falsity of the underlying real-world predicate.

**What this means concretely.**

- When an evidence item is **ABSENT**, `B` encodes it into the frozen engine's **fail-closed input representation**. It does this for exactly one reason: **the architecture requires non-default-permit** (FULL_SPEC §2.3 / §0.10; EEB §6). Absence must resolve to a deficit so the frozen engine holds the action in SAFE_STATE rather than permitting on missing evidence.
- This encoding is **not** an assertion that the underlying real-world predicate is **false** or unsatisfied in reality. `B` makes no claim about the world. It records a single fact: *this evidence was not available to the decision*. The provenance carries this honestly — every fail-closed field is tagged `evidence_quality = ABSENT` on its native plane, never `PRESENT`/`false`.
- Example: for the credit-card arm the authority gates resolve to the fail-closed representation. `B` is **not** stating "the authorization token is invalid" (a policy-truth claim). It is stating "no authority service is bound, so token validity is **unavailable**," and the architecture's non-default-permit converts unavailability to a deficit **inside the frozen engine**.

**Where policy interpretation lives.** Policy interpretation — what an input *means* for the decision (deficit vs. no-deficit, `Γ = maxᵢ dᵢ`, `Π = 1[Γ=0]`, PERMIT vs. SAFE_STATE) — remains **exclusively inside the frozen authorization engine** (`evaluate_decision`, `gamma_test_runner.py:133-178`, frozen). `B` supplies provenanced availability; the engine, and only the engine, interprets it. `B` computes no authorization, no Γ, no SAFE_STATE, and never calls the engine (verified: `test_no_engine_coupling`).

**Consequence.** The two concerns are cleanly separated by construction:

| Layer | Owns | Never does |
|---|---|---|
| Predicate Binding `B` | evidence **availability** → schema shape (carry / absent→fail-closed / out-of-slice) | assert policy truth; decide; threshold; read `Class` |
| Frozen engine | **policy interpretation** of the inputs (deficit semantics, Γ, Π, SAFE_STATE) | receive fabricated or interpreted evidence |

---

## Invariant PB-2 — The fail-closed representations are *inherited semantics*, not implementation choices

**Statement.** The specific fail-closed values `B` writes are **derived from the frozen engine's existing deficit interpretation**. They are **not** implementation choices made by the binding layer. They are **inherited semantics**: `B` reads off the direction in which the frozen engine already counts a deficit, and encodes "ABSENT" into exactly that direction.

**Derivation (each value read directly off the frozen `evaluate_decision`).**

| Fail-closed value in `B` | Frozen engine's deficit interpretation it is inherited from | Source |
|---|---|---|
| gate boolean → `False` | `for g in NODE_GATE_COLS: if not row[g]: deficit` — a gate is a deficit when **falsy** | `gamma_test_runner.py:142-145` |
| `StaleContext` → `True` | `if row["StaleContext"]: deficit` — stale context is a deficit when **truthy** | `gamma_test_runner.py:149-151` |
| `TelemetryFresh` → `False` | `if not row["TelemetryFresh"]: deficit` — telemetry is a deficit when **not fresh** | `gamma_test_runner.py:152-154` |
| class-veto → `""` (no veto) | `gamma_class = 1 if CLASS_1/GOODHART in ReasonCodes` — no non-`Class` veto producer in this arm; `Class` is **never read** by `B` | `gamma_test_runner.py:156-157` |
| `HARM_RISK` → `0.0` placeholder (out-of-slice) | `if row["HARM_RISK"] > θ: deficit` — governance service ABSENT and the `V1..V28` proxy is **rejected**, so the HARM predicate is out-of-slice; the numeric slot is unavoidable (the engine unconditionally compares), `0.0` asserts **no hazard**, and the arm's fail-closed is carried by the absent authority gates above | `gamma_test_runner.py:146-148` |

**Why "inherited," not "chosen."** `B` does not define what a deficit is, nor which direction of a field constitutes one. Those semantics are frozen in `evaluate_decision` and predate `B`. `B` performs a mechanical inversion: *given* the engine's frozen deficit direction for a field, the fail-closed encoding of ABSENT is *the value that direction reads as a deficit*. Had the frozen engine defined the opposite direction for any field, `B`'s encoding for that field would necessarily be the opposite too. The binding owns **none** of these semantics; it borrows all of them.

**Consequence.** There is no free parameter and no policy value inside `B`. The fail-closed constants (`runtime_context/predicate_binding.py:_FAILCLOSED_GATE / _FAILCLOSED_STALE / _FAILCLOSED_FRESH / _NO_VETO / _HARM_ABSENT_PLACEHOLDER`) are documentation of the engine's inherited deficit directions, not decisions of the binding layer. Changing them would misrepresent the frozen engine, not re-tune a policy.

---

## Combined reading

PB-1 and PB-2 together fix the layer's boundary precisely: **`B` transports evidence availability into the frozen engine's own inherited deficit representation, and stops.** It asserts no policy truth (PB-1) and originates no deficit semantics (PB-2). Every truth-bearing, policy-interpreting step is the frozen engine's. This is exactly why Commit 5.1-B changes no scientific behaviour, no metric, and no benchmark: it adds an availability-transport layer whose every semantic is inherited from, and interpreted by, the unchanged frozen engine.

---

*Documentation only. No code, Gamma, `evaluate_decision()`, or Predicate Binding behaviour was modified. Both invariants describe the already-implemented, already-verified Commit 5.1-B layer and are grounded in the frozen engine source cited above. Awaiting independent review; Commit 5.2 not begun.*
