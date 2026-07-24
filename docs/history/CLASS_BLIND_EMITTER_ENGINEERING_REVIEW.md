# CLASS-BLIND FULL-SCHEMA EMITTER — ENGINEERING SCOPE REVIEW

**Analysis only. No code, no implementation, no design, no repository modification, no invented algorithm / policy / replay semantics / identifier / ledger behaviour.** An architectural-responsibility review of the Class-blind full-schema emitter identified as the one engineering gap in `COMMIT_5_2_PRE_IMPLEMENTATION_REVIEW.md §6 H-3`. The sole question: does the emitter belong **inside** Commit 5.2, or should it be its **own engineering commit before** 5.2?

**Roles:** Principal Software Architect · Runtime Systems Engineer · IEEE Artifact Engineer.

---

## 1. Executive Summary

The Class-blind full-schema emitter is a **substantial, independent, replay/ledger-owning, science-neutral component** — not a wiring change. Commit 5.2 is defined by the roadmap as *"connect the already-implemented components"*; the emitter is **not implemented**, so it is by definition **not part of "connection."** It authors the **Hydra Ledger hash chain** and the full reported row that the frozen replay/Evidence-Quad emitters consume — a distinct responsibility currently discharged (Class-dependently) by `gamma_map_raw`, which cannot remain. Building it can and should be done as **parallel, flag-OFF, unconsumed scaffolding** — exactly the pattern of every prior pipeline layer (2.1–2.5, 4.1, 5.1, 5.1-B) — and verified for Class-blindness / determinism / replay-ledger compatibility **without changing any reported metric**. Bundling it into 5.2 would couple a large neutral engineering artifact to the gated, non-neutral metric flip, enlarging blast radius and complicating review and rollback.

**Recommendation: CREATE A NEW ENGINEERING COMMIT BEFORE 5.2.**

---

## 2. Engineering responsibility

The emitter's single responsibility is **serialization, not decision**: transform each Class-blind decision (produced by the frozen pipeline) plus its Class-blind observable evidence into the **full reported artifact row** and its **ledger link**, so that the frozen LAB runner, replay emitter, Evidence Quad, and dashboard consume it unchanged.

Precisely, three sub-responsibilities that today are entangled inside `gamma_map_raw`:

| # | Responsibility | Today (Class-entangled) | Must become (Class-blind) |
|---|---|---|---|
| R1 | **Identity / envelope** — `ProposalID`, `RunID`, `Step`, `TimestampUTC`, `DatasetID`, `SubjectProfileID`, `EnvironmentContext`, `PermitTokenID`, `ERTuple_ID`, commit/actuate timestamps | generated inside the `Class`-branched loop; `EnvironmentContext` embeds `class=…` | deterministic from Class-blind inputs (row index, injected times, run params); no `Class` |
| R2 | **Hydra Ledger hash chain** — `HASH_prev`, `HASH_current`, `PolicyHash` | canon computed over Class-derived `Status`/`Gamma`/`harm` (`gamma_map_raw:~200`) | canon over the **decision + Class-blind fields only**; a new genesis-anchored chain |
| R3 | **Decision-carry + reported projection** — gates, `HARM_RISK`, `Stale/Fresh`, `ReasonCodes`, `Status`, `DecisionOutcome`, `FirstFailingGate`, flags | authored from `Class` | carried from the frozen pipeline / derived by the frozen runner from the carried predicates |

**Boundary clarification (from the code).** The frozen runner (`gamma_test_runner.write_replay_manifest`) **reads** `HASH_prev`/`HASH_current`/`PolicyHash` from the row and only **derives** `DerivedGammaG/Class/Pi/Decision/ChainLinked/Unauthorized` from the predicate columns. Therefore the emitter must **author** R1 + R2 and **carry** R3's predicate inputs; it must **not** re-implement the Derived* decision fields (frozen runner) or the replay manifest / Evidence Quad (frozen). The emitter is strictly upstream of the frozen emitters and downstream of the frozen decision.

---

## 3. Why the emitter exists

The frozen pipeline (`evidence_trace_builder` 5.1 → `predicate_binding` 5.1-B → `eeb_to_engine` 4.1 → `evaluate_decision`) produces a **decision**, not a **reported artifact**. A decision is `{Γ, Π, Decision}` over a bound schema. The reported/replay/benchmark artifact additionally requires **identity, envelope, timestamps, a tamper-evident ledger link, and the Evidence Quad's `policy_hash`/`ledger_hash`** serialized around each decision. That serialization layer — the "Evidence Collector" role named in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md` Part 2 — exists today **only** inside `gamma_map_raw`, and only in a **Class-authoring** form. The emitter is the missing **Class-blind serialization layer** that lets the frozen engine's genuine decisions be reported and replayed. Without it, the pipeline can *decide* Class-blindly but cannot *report* Class-blindly.

---

## 4. Why `gamma_map_raw` cannot remain

`gamma_map_raw` is **Class-entangled at every layer**, verified in the code (`gamma_map_raw.py:120-215`):

- **Template selection by `Class`:** `row = dict(fraud_tpl if is_fraud else legit_tpl)` — the entire structural row is chosen by the label.
- **Decision authored from `Class`:** the fraud/legit branches set gates, `Gamma`, `SAFE_STATE`, `ReasonCodes` directly from `is_fraud`.
- **HARM from `Class`:** `harm = HARM_FRAUD if is_fraud else derive_harm_risk(...)`.
- **Provenance leaks `Class`:** `EnvironmentContext` embeds `class={classes[i]}`.
- **Ledger leaks `Class`:** the hash canon is `…|{Status}|{Gamma}|{harm:.6f}|…` — all Class-derived — so `HASH_current` (and the whole chain) is a function of the label.

Consequences (from `COMMIT_5_2_PRE_IMPLEMENTATION_REVIEW.md` H-3):

- **Keeping it** for the "structural" columns **leaks `Class`** into the reported artifact **and the ledger** → violates Class-blindness (EEB §9; RCL §8; Deployment Contract). Impermissible.
- **Retiring it** removes the **only** producer of R1 + R2 → the reported/replay/benchmark schema has no source.

Therefore `gamma_map_raw`'s authoring must be **fully replaced** for the reported credit-card arm by a Class-blind emitter; partial retention is not an option.

---

## 5. Whether the emitter belongs in Commit 5.2

**No.** Four independent reasons:

1. **Definitional.** Roadmap 5.2 = *"activate … connect the already-implemented components; shall NOT redesign any component."* The emitter is **not implemented** and is a **new component** — building it is neither "connect" nor "activate." Including it contradicts 5.2's own charter.
2. **Neutrality separation.** The emitter is **science-neutral** (it serializes; it decides nothing) and can be built + verified with **zero reported-metric change** as parallel scaffolding. Commit 5.2 is **explicitly non-neutral** (the gated metric flip). Bundling a neutral artifact into a gated commit couples it to a governance sign-off it does not need, and makes the signed diff harder to isolate.
3. **Blast radius / verifiability.** The emitter **owns the Hydra Ledger chain** (R2) and the replay inputs — the highest-consequence surface in the system. It deserves **isolated** Class-blind / determinism / replay-adjacency / provenance verification **before** anything is activated, not co-mingled with the activation flip.
4. **Precedent.** Every pipeline layer (2.1–2.5, 4.1, 5.1, 5.1-B) was its own commit, built as **unconsumed scaffolding**, verified, then frozen — before any consumer existed. The emitter fits this pattern exactly; 5.1 having "no consumer until 5.1-B" did not justify merging them, and the same logic applies here.

Keeping it inside 5.2 would convert 5.2 from a one-flag connection into a large engineering + ledger-rebaseline + metric-flip commit — precisely the conflation the phased roadmap avoids.

---

## 6. Recommended roadmap placement

A **new engineering commit immediately before 5.2**, in the pattern of the prior scaffolding commits (the roadmap owner assigns the number; e.g. a **"5.1-C — Class-blind reported-trace emitter (flag OFF, parallel)"** slot between 5.1-B and 5.2):

- **Character:** additive, **unconsumed / flag-OFF**, parallel to `gamma_map_raw`; **science-neutral** (no reported-metric change while OFF).
- **Contract:** produce R1 + R2 + carry R3 Class-blindly; feed the frozen runner/replay/Evidence-Quad emitters unchanged.
- **Exit criteria (must pass before 5.2):** Class-blindness end-to-end (incl. ledger + `EnvironmentContext`), determinism / byte-identical regeneration, replay-adjacency on the new chain, provenance linkage to the sealed EEB.
- **Then** Commit 5.2 becomes a genuine **pure-connection default flip** (retire `gamma_map_raw`, point the reported arm at the emitter) gated only on the owner acts already enumerated (signed metric change + rebaseline + deployment policy C1–C6).

This ordering also cleanly stages the **signed replay rebaseline**: the emitter's new (Class-blind) ledger chain is produced and reviewed in its own commit; 5.2 only *adopts* it.

---

## 7. Required inputs

*(Analysis of what the emitter must consume — not a design.)*

- **Sealed evidence EEB** (from `evidence_trace_builder`, 5.1) — the Class-blind plane-A/B evidence + provenance.
- **Bound decision** for the row — `{Γ, Π, Decision}` and the bound predicate schema, from `predicate_binding` (5.1-B) → `eeb_to_engine` (4.1) → `evaluate_decision` (frozen).
- **Deterministic envelope parameters** — `RunID`, dataset id, epoch base, and **injected** timestamps / row ordering (the emitter is **not** a time source; no wall clock — consistent with the whole substrate's discipline).
- **Prior ledger link** — the previous row's `HASH_current` (genesis-anchored) for chain adjacency.
- **Policy identity** — the verified scientific Merkle root / `PolicyHash` (from `frozen_policy.ScientificPolicy`), for the Evidence Quad.

**Excluded input (invariant):** `Class`. It must have no field, no read, no derivation anywhere in the emitter — including the ledger canon and `EnvironmentContext`.

---

## 8. Required outputs

*(What the emitter must produce for the frozen consumers — not a design.)*

- **The full reported row set** (the schema the LAB runner + dashboard consume): identity/envelope (R1), the carried decision predicates + reported projections (R3), consumable by the frozen `gamma_test_runner`.
- **The Class-blind Hydra Ledger chain** (R2): `HASH_prev` / `HASH_current` over a Class-blind canon, genesis-anchored, adjacency-valid — the input the frozen `write_replay_manifest` reads.
- **Evidence-Quad inputs**: `policy_hash` and `ledger_hash` per row, so the frozen quad `{decision, method_version, policy_hash, ledger_hash}` is emitted unchanged.
- **Provenance linkage**: each row traceable to its sealed EEB (`prior_ledger_link` / bundle reference), preserving the EEB provenance.

**Non-outputs (frozen, must not be re-implemented):** `evaluate_decision`, Γ aggregation, `DerivedGammaG/Class/Pi/Decision` (runner-derived), the replay manifest itself, the Evidence Quad computation, ConcurBench/FCR/FULL_SPEC (separate arms).

---

## 9. Engineering risk assessment

| Dimension | Assessment | Basis |
|---|---|---|
| **Size / independence** | **Large, independent** | authors R1 + R2 (identity + ledger) — a full serialization layer, not a wiring change |
| **Blast radius** | **High** | owns the Hydra Ledger chain and replay inputs; errors corrupt replay/adjacency/Evidence-Quad |
| **Scientific neutrality** | **Neutral (if flag-OFF/parallel)** | serializes decisions; computes no decision, threshold, or metric |
| **Replay impact** | **New chain = deliberate rebaseline** | Class-blind canon differs from the Class-derived one; must be signed (staged in the emitter commit) |
| **Class-blindness risk** | **The central risk** | must be proven absent in row, provenance, **and ledger canon** — the exact place `gamma_map_raw` leaks |
| **Coupling risk if bundled into 5.2** | **High** | conflates a neutral artifact with the gated metric flip; harder review/rollback |
| **Coupling risk if separated** | **Low** | isolated verification before activation; 5.2 stays a one-flag flip |
| **Verifiability** | **Fully verifiable pre-activation** | Class-blind + determinism + replay-adjacency + provenance tests, no metric change (precedent: 5.1/5.1-B) |

**Net:** high-consequence but well-isolatable; the risk is **minimized by separation** and **amplified by bundling**.

---

## 10. Recommendation

The Class-blind full-schema emitter is a **new, large, ledger-owning, science-neutral serialization component** — categorically distinct from Commit 5.2's chartered "connect the already-implemented components." It should be built and frozen as its **own** parallel, flag-OFF scaffolding commit (in the pattern of 2.1–5.1-B), verified for Class-blindness, determinism, replay-adjacency, and provenance **before** any activation, so that Commit 5.2 remains a genuine pure-connection default flip gated only on the previously-enumerated owner/governance acts. Bundling the emitter into 5.2 would violate 5.2's charter, couple a neutral artifact to a gated non-neutral change, and enlarge the ledger/replay blast radius under a single commit.

# CREATE A NEW ENGINEERING COMMIT BEFORE 5.2

---

*Engineering scope review only. No code, no design, no implementation, no repository modification, no invented algorithm / policy / replay semantics / identifier / ledger behaviour. Responsibilities and boundaries are derived from the frozen corpus and the observed code (`gamma_map_raw.py`, `gamma_test_runner.py`, the `runtime_context/` pipeline). Awaiting independent review before any implementation or roadmap change.*
