# CLASS-BLIND REPORTED ARTIFACT EMITTER — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no implementation, no design, no repository modification.** An engineering-readiness review of the new commit (Class-blind Reported Artifact Emitter), scoped to one question: **can it be implemented safely using only the already-frozen scientific specifications?** Per the stop condition, hidden assumptions are **documented, not resolved**.

**Roles:** Principal Runtime Systems Engineer · Software Architect · IEEE Artifact Engineer.

**Frozen authoritative sources:** Runtime Evidence Architecture · Runtime Context Layer · Execution Evidence Bundle · Predicate Binding · Deployment Policy Specification · Deployment Profile Contract · FULL_SPEC · Engineering Migration Roadmap.

---

## 1. Executive Summary

**The emitter's *decision* content is fully specified; its *serialization* conventions are not — and they are not in the frozen scientific corpus at all.**

The emitter is confirmed to be a **serialization-only** component: it computes no authorization, Γ, predicate, or policy, and interprets no evidence. Its decision inputs come entirely from the frozen pipeline (`evidence_trace_builder` → `predicate_binding` → `eeb_to_engine` → `evaluate_decision`). That half is ready.

But the emitter must also **author the reported identity, timestamps, and the Hydra Ledger hash chain** — and these conventions exist **only as implementation code inside the retiring `gamma_map_raw`**, never in a frozen *scientific* specification:

- **Identifier scheme** (`ProposalID`, `PermitTokenID`, `ERTuple_ID`, `SubjectProfileID` via `h12`/`h16` over the row index) — a code convention.
- **Timestamp scheme** (`EPOCH_BASE` + observable `Time` + `commit +10ms` / `actuate +25ms` offsets) — a code convention with magic offsets.
- **Hydra Ledger hash-canon composition** (`{ProposalID}|{Status}|{Gamma}|{harm:.6f}|{PermitTokenID}|{TimestampUTC}`) — a code convention; only the chain *adjacency algorithm* is frozen (via the verifier).
- **Structural template constants** (`PolicyHash`, `SpecVersion`, `NodeID`, `TLC*` hashes) — *copied from a `Class`-selected sample-template row* in `gamma_map_raw`.
- **`EnvironmentContext` provenance string** — **actively embeds `class={…}`** (`gamma_map_raw:~142`), i.e. it **leaks `Class`**, and its Class-blind replacement content is **undefined**.

Because the question is specifically *"using only the frozen scientific specifications,"* the honest answer is **no**: those specifications do not define the serialization/identifier/timestamp/ledger/provenance conventions the emitter must reproduce, one convention leaks `Class` with no defined replacement, and the only place they exist is the module being retired. Implementing without a frozen (or owner-ratified) serialization contract would require **inventing** identifiers, timestamps, ledger canon, and provenance content — exactly what the constraints forbid.

**Verdict: IMPLEMENTATION BLOCKED** — not on science (complete) and not on the decision pipeline (frozen), but on the **absence of a frozen serialization / identifier / timestamp / ledger-canon / provenance specification** (or an owner ratification of the existing `gamma_map_raw` conventions as Class-blind **REUSE-PATTERNS**) that the emitter can build to without invention.

---

## 2. Scope

The emitter's chartered responsibility (from `CLASS_BLIND_EMITTER_ENGINEERING_REVIEW.md`): **serialize** each Class-blind decision + observable evidence into the full reported artifact row and its ledger link, so the frozen LAB runner / replay emitter / Evidence Quad consume it unchanged. It authors **R1 identity/envelope**, **R2 Hydra Ledger chain**, and **carries R3 decision predicates** — the roles `gamma_map_raw` performs Class-dependently today.

**Responsibility verification (serialization only).** The emitter must NOT:

| Must NOT | Confirmed by design intent |
|---|---|
| compute authorization | decision comes from frozen `evaluate_decision` |
| compute Γ | Γ is frozen; emitter carries the result |
| compute predicates | predicates come from `predicate_binding` (frozen) |
| compute policy | no policy value read or derived |
| interpret evidence | evidence carried/serialized, never interpreted |
| change replay semantics | chain *algorithm* frozen (verifier); emitter authors only chain *values* |
| modify the frozen engine | engine untouched |

The emitter is downstream of the decision and upstream of the frozen emitters. **This boundary is clean and specified.** The block (below) is about the *serialization conventions*, not the responsibility.

---

## 3. Allowed modifications

If (and only if) the §6 block is cleared:

| Action | File | Constraint |
|---|---|---|
| **Create** | `runtime_context/<emitter>.py` (name TBD) | serialization only; flag-OFF/parallel; unconsumed scaffolding |
| **Create** | `tests/test_<emitter>.py` | Class-blind / determinism / replay-adjacency / provenance |
| **Modify** | **none** | like 5.1 / 5.1-B, this commit is unconsumed scaffolding — it wires into nothing until 5.2 |

No existing file may be modified by this commit. (`gamma_map_raw` is retired by **5.2**, not here.)

---

## 4. Frozen files (must NOT be modified)

- **Decision pipeline:** `gamma_test_runner.py` (`evaluate_decision`, `NODE_GATE_COLS`, Γ block, SAFE_STATE), `predicate_binding.py` (5.1-B), `eeb_to_engine.py` (4.1), `evidence_trace_builder.py` (5.1), `assembler.py`, `execution_evidence_bundle.py`, `ports.py`, `context_objects.py`, `transaction_interpreter.py`.
- **Replay / ledger:** `write_replay_manifest` (emitter), the chain **adjacency algorithm** (`hash_prev[i] == hash_current[i-1]`, genesis-anchored), `gamma_replay_verify.py`, the manifest record format, the **Evidence Quad** `{decision, method_version, policy_hash, ledger_hash}`.
- **Separate arms:** `concurbench_full.py`, `fcr_test.py`, `full_spec_conformance.py`.
- **Policy/manifests:** frozen scientific manifests + Merkle root, `frozen_policy.ScientificPolicy`, `Execution_Binding_Manifest.json`.
- **`gamma_map_raw.py`** — untouched by this commit (retired by 5.2).
- The frozen specification corpus.

---

## 5. Architecture diagram

```
FROZEN DECISION PIPELINE (upstream)                 EMITTER (this commit, flag-OFF/parallel)
──────────────────────────────────                 ─────────────────────────────────────────
 evidence_trace_builder (5.1)  ─ sealed EEB ──┐
 predicate_binding (5.1-B)      ─ bound EEB ──┤
 eeb_to_engine (4.1)            ─ schema ─────┤       consumes: EEB + decision + injected envelope
 evaluate_decision (FROZEN)     ─ Γ/Π/Decision┘             │
                                                            ▼
                                          ┌──────── serialize (R1 identity, R2 ledger, R3 carry)
                                          │           ▲   ▲   ▲
                                          │        [ID scheme][timestamp scheme][ledger canon]
                                          │        ── all NOT in frozen scientific specs ──
                                          ▼
                                   full reported row + Class-blind HASH chain
                                          │
                                          ▼  (consumed only AFTER 5.2 activation)
                          FROZEN: gamma_test_runner → write_replay_manifest → Evidence Quad → verifier

Owned by emitter:   HASH_prev/HASH_current VALUES (a new Class-blind chain instance); reported row content.
Frozen (not owned): chain ALGORITHM + adjacency; replay manifest format; Evidence Quad; the verifier.
```

**Consumes:** sealed EEB (5.1), bound decision (5.1-B→4.1→engine), injected envelope params (`RunID`, epoch base, ordering, injected times).
**Consumed by:** nothing while flag-OFF; the LAB runner **after** 5.2.
**Replay owned:** the chain *values* (a new instance). **Replay frozen:** the *algorithm*, manifest format, verifier.
**Ledger owned:** the Class-blind chain instance. **Ledger frozen:** the hashing algorithm + genesis-anchoring + adjacency contract.

---

## 6. Hidden assumptions (documented, NOT resolved)

Each is a convention the emitter must reproduce that is **absent from the frozen scientific specifications** and present only as code in the retiring `gamma_map_raw`. Per the stop condition, none is resolved here.

- **HA-1 · Hidden identifier generation.** `ProposalID`/`PermitTokenID`/`ERTuple_ID`/`SubjectProfileID` derive from the row index via `h12`/`h16` (`gamma_map_raw:69-74, 133-190`). Class-blind and deterministic, **but the scheme is a code convention, not a frozen spec**. The emitter cannot derive it from the scientific corpus; reusing it requires ratifying the scheme as a frozen **REUSE-PATTERN** (lifted verbatim). Inventing a new scheme is forbidden. **STOP.**

- **HA-2 · Hidden timestamp generation.** Timestamps derive from `EPOCH_BASE` + the observable `Time` + fixed **`commit +10ms` / `actuate +25ms`** offsets (`gamma_map_raw:45, 133-142`). Class-blind, but the **offsets are magic constants** and the scheme is a code convention, not a spec. The commit/actuate ordering they encode interacts with **Invariant I5** — so the offsets are not cosmetic. Reuse requires ratification; re-choosing them is invention. **STOP.**

- **HA-3 · Hidden ledger semantics.** The hash-canon **composition** (`{ProposalID}|{Status}|{Gamma}|{harm:.6f}|{PermitTokenID}|{TimestampUTC}`, `gamma_map_raw:~200`) is a code convention. Only the chain **adjacency algorithm** is frozen (the verifier). The emitter's Class-blind chain is a **new instance** whose canon composition must be either (a) reused verbatim (values become engine-derived) or (b) redefined. Its adoption as *reported* is the **signed replay/ledger rebaseline** (scoped to 5.2). The **composition itself is undefined by any frozen spec**; ratification as a REUSE-PATTERN is required before build. **STOP.**

- **HA-4 · Hidden provenance semantics.** `EnvironmentContext` currently **embeds `class={classes[i]}`** (`gamma_map_raw:~142`) — a direct `Class` leak into the reported artifact. It **cannot be reused verbatim** (violates Class-blindness, EEB §9), and its **Class-blind replacement content is undefined** by any frozen spec. What the Class-blind provenance string must contain is an unspecified authoring decision. **STOP.**

- **HA-5 · Hidden benchmark coupling / template-constant `Class` selection.** Structural constants (`PolicyHash`, `SpecVersion`, `NodeID`, `TLC*` hashes) are copied from a **`Class`-selected** template row (`fraud_tpl if is_fraud else legit_tpl`, `gamma_map_raw:107-108, 122`). The emitter must source these from a **single `Class`-independent** origin and confirm the constants are **identical across the two template rows** (else `Class` leaks structurally). Additionally, coupling to ConcurBench/FCR/FULL_SPEC (separate arms) must be confirmed **absent**. Both are **unconfirmed** and unspecified. **STOP.**

- **HA-6 · Hidden decision-authoring carry-over (guardrail).** `gamma_map_raw` authors `HARM` from `Class` (`HARM_FRAUD` / `derive_harm_risk`) and gates/`Status`/`ReasonCodes` from `Class`. The emitter must take **all** decision content from the frozen pipeline and must **not** carry over any of `gamma_map_raw`'s Class-authoring helpers. This is specified (the pipeline owns the decision), but is the highest-risk accidental-invention path and is flagged as a hard guardrail. (Not itself a blocker; the decision half is specified.)

**None of HA-1…HA-5 is missing science.** Each is a missing **serialization specification** (or an unratified reuse of a retiring convention, or — HA-4 — an undefined Class-blind provenance string). They are exactly the items the corpus never froze because, until now, `gamma_map_raw` authored them.

---

## 7. Scientific neutrality

| Property | Status | Note |
|---|---|---|
| Computes no decision/Γ/predicate/policy | ✅ neutral | serialization only |
| Frozen engine/binding/adapter untouched | ✅ | this commit modifies nothing |
| Reported metrics unchanged | ✅ (while flag-OFF) | scaffolding; no consumer until 5.2 |
| Class-blindness | ⚠️ **at risk** | HA-4 (provenance leak), HA-5 (template selection) must be resolved to guarantee it |
| Replay/ledger semantics | ⚠️ **reuse-vs-redefine unratified** | algorithm frozen; canon composition unspecified (HA-3) |
| Requires new science | ❌ no | but requires a **serialization spec / reuse ratification** (not science) |

The emitter is **science-neutral by construction** but **not specification-complete**: its neutrality on Class-blindness (HA-4/HA-5) and its replay/ledger reproducibility (HA-3) depend on conventions no frozen scientific spec provides.

---

## 8. Verification plan (for when the block is cleared)

- **Class-blind verification.** AST/string scan: `Class` read nowhere in the emitter; `Class` present/absent/differing → **byte-identical full reported row + ledger** (extends the 5.1/5.1-B Class-blind tests to the *entire* row, catching any HA-4/HA-5 leak — the tripwire).
- **Determinism verification.** Identical inputs → byte-identical reported row + identical `HASH_current`; two runs → identical trace (DET1).
- **Replay verification.** The emitted chain feeds the **frozen** `write_replay_manifest`; `gamma_replay_verify.py` → RESULT: PASS (0 adjacency failures); genesis-anchored; append-only (DET4).
- **Provenance verification.** Every reported row traces to its **sealed EEB**; `prior_ledger_link` links the chain; provenance planes preserved; `EnvironmentContext` carries **no `Class`**.
- **Hydra Ledger verification.** Recompute the chain from the canon → matches emitted `HASH_current`; adjacency valid; the chain **algorithm** is the frozen one (unchanged), only the **instance** is new.
- **Evidence Quad verification.** `{decision, method_version, policy_hash, ledger_hash}` per row: `policy_hash` = verified Merkle root; `ledger_hash` = the row's `HASH_current`; `decision` ∈ {PERMIT, SAFE_STATE}.
- **Regression verification.** While flag-OFF: `tests/test_regression_parity.py` **fully green and unchanged** (LAB/ConcurBench/FCR/FULL_SPEC/replay) — proving the scaffolding changes no reported artifact; ConcurBench/FCR/FULL_SPEC untouched (no benchmark coupling, HA-5).

---

## 9. Rollback

- The commit is additive, flag-OFF, unconsumed. **Rollback = delete the two new files** (`runtime_context/<emitter>.py`, `tests/test_<emitter>.py`); nothing else is affected (no existing file modified, no reported artifact changed).
- No ledger/replay rollback is needed — the emitter's chain is not adopted as reported until 5.2.

---

## 10. Readiness certification

The emitter's **responsibility is correctly bounded** (serialization only) and its **decision inputs are fully specified and frozen**. But it **cannot be implemented using only the frozen scientific specifications**, because those specifications **do not define** the identifier scheme (HA-1), timestamp scheme (HA-2), Hydra Ledger canon composition (HA-3), Class-blind provenance-string content (HA-4), or the Class-independent source of the structural template constants (HA-5). These conventions exist **only** as implementation code in the **retiring** `gamma_map_raw`, one of them (`EnvironmentContext`) **leaks `Class`** with **no defined replacement**, and none may be invented (stop condition).

The unblocking action is **not science and not yet engineering** — it is a **specification/ratification act by the owner**: freeze a **Class-blind serialization / identifier / timestamp / ledger-canon / provenance reuse-pattern specification** (lifting the Class-blind, deterministic conventions from `gamma_map_raw` verbatim, confirming each reads no `Class`, and **defining** the Class-blind `EnvironmentContext` content). Once that specification is frozen, the emitter becomes pure engineering to it, and this readiness review can be re-run to certify it.

# IMPLEMENTATION BLOCKED

**Single sentence:** the decision half is frozen and the responsibility is clean, but the emitter's serialization/identifier/timestamp/ledger/provenance conventions are absent from the frozen scientific specifications and present only in the retiring `gamma_map_raw` (which additionally leaks `Class` via `EnvironmentContext`), so a **frozen serialization reuse-pattern specification** (owner act) is required before implementation can proceed without invention.

---

*Pre-implementation review only. No code, no design, no implementation, no repository modification. Findings documented, not resolved. Conventions and leaks are cited to the observed code (`gamma_map_raw.py`, `gamma_test_runner.py`) and the frozen corpus. Awaiting independent review and the enumerated serialization-specification act before any implementation.*
