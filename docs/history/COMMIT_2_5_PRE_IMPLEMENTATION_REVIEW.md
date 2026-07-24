# COMMIT 2.5 — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no file modified, no implementation.** Reviews Commit 2.5 exactly as defined in `ENGINEERING_MIGRATION_ROADMAP.md:125-132`, against `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §5/§3/§2` and `RUNTIME_EVIDENCE_ARCHITECTURE.md §4`, in complete isolation (no consumer; Phase 4 not anticipated).

**Roles:** Lead Runtime-Systems Architect · IEEE Artifact Engineer · Runtime-Governance Engineer · Software-Verification Engineer · Repository-Migration Engineer.

---

## RECONCILIATION REQUIRED (read first) — "A+B+C+D → seal" is necessary but **not sufficient** for a valid bundle

The prompt's Assembler Responsibility diagram is *"Plane A + Plane B + Plane C + Plane D EvidenceField → EEB → seal() → STOP."* That is the **evidence payload core**, and it is correct as far as it goes — but the **frozen 2.1 contract** (`execution_evidence_bundle.py`) will **reject** a bundle built from A/B/C/D alone. Two completeness facts, both pinned by the already-approved 2.1/2.3 code, must be stated up front. Neither is a redesign; both are faithfulness to the frozen contract.

1. **A sealed bundle also requires the Envelope and the E-cached ledger link.** `ExecutionEvidenceBundle.seal(...)` takes `bundle_id`, `created_at` (Envelope), and `EvidencePayload.validate_structure()` marks **`prior_ledger_link` (plane E-cached)** and a **non-empty `node_predicate_vector`** as *required* (`execution_evidence_bundle.py:147-150`, `:236-243`). So the assembler must also carry **Env metadata** (`bundle_id`, `created_at`, `method_version`, optional `subject_ref`) and the **E-cached `prior_ledger_link`** — as **inputs it receives**, never as values it invents. The "four planes" framing omits Env and E-cached; the EEB contract does not. (EEB §2.1, §2.2, §3.)

2. **The RCL `FreshnessClock` emits DELTAS, not the payload's booleans — the assembler must carry them VERBATIM.** EEB §2.2 describes `stale_context`/`telemetry_fresh` as boolean readings, but the approved Commit 2.3 `FreshnessClock` deliberately emits timestamp **deltas** (RCL §3.3: "the threshold to judge freshness lives in policy, not here"). The assembler **must place the RCL delta `EvidenceField` into the `stale_context`/`telemetry_fresh` slot unchanged** and **must not** threshold it into a boolean. Booleanizing here would be an authorization computation (a θ comparison) — an **architectural violation** (see the *Important Review Question* section). The delta→boolean resolution belongs to the frozen evaluator + policy plane, downstream of 2.5.

These two points do not expand 2.5's scope; they keep it honest to the frozen data contract. The remainder reviews the assembler as **pure structural assembly + seal**.

---

## PART 1 — Purpose

**What Commit 2.5 accomplishes.** Adds `runtime_context/assembler.py`: the **Execution Evidence Bundle Assembler**. Per request, it **collects the already-produced evidence from every plane** and performs **structural assembly only**:

- **Plane A** — the `EvidenceField` objects from the Commit 2.4 `TransactionInterpreter` (`txn_amount`, `txn_time`, optional `txn_action_ref`, optional opaque `txn_feature_ref`).
- **Plane B** — the `EvidenceField` readings from the Commit 2.3 RCL producers (`FreshnessClock`, `ExecutionHistoryWindow`, `CommitActuateJournal`).
- **Plane C / D** — the `EvidenceField` readings from the Commit 2.2 `AuthorityPort` / `GovernancePort`, which return **evidence-absent** in the bare credit-card arm (no producer bound).
- **Envelope + E-cached** — caller-supplied `bundle_id`/`created_at`/`method_version`/`subject_ref` and the `prior_ledger_link` (from the Evidence Collector; evidence-absent in unconsumed scaffolding).

It places each received `EvidenceField` into its named `EvidencePayload` slot, constructs the immutable `EvidencePayload`, and calls the **frozen 2.1 `ExecutionEvidenceBundle.seal(...)`** — which computes the canonical SHA-256 integrity digest — then returns the sealed, immutable bundle. **It STOPS there.** It does not authorize, evaluate Gamma, compute predicates/SAFE_STATE, invoke `evaluate_decision()`, interpret runtime observations or transaction data, evaluate policy/governance, run benchmarks, or change runtime flow. **No module consumes it** (unconsumed scaffolding, exactly like 2.1–2.4).

**Why it follows Commit 2.4.** The assembler is the **union point**: it needs every plane's producer to exist first. 2.1 gave the immutable bundle contract + `seal()`; 2.2 gave the C/D/policy ports; 2.3 gave the plane-B producers; 2.4 gave the plane-A producer. By 2.5, **all four producers exist**, so the assembler can integrate them into one sealed bundle without inventing any evidence. It could not precede 2.4 (no plane-A source to assemble).

**Why it is the final infrastructure commit before runtime consumption.** After 2.5 the RCL substrate is **complete and provable end-to-end**: a request can be turned into a sealed, provenance-complete, Class-blind EEB. Everything *before* 2.5 was an isolated part; 2.5 is the first artifact that is a *whole producible bundle* — yet still **unconsumed** (the engine remains fed by the current CSV path). The next phase (4.1) is where an EEB is *read as engine input* behind a default-OFF flag — i.e., the first **consumption**. 2.5 is thus the last purely-additive, science-neutral scaffolding step; it makes the bundle *producible* without making it *authoritative*.

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `runtime_context/assembler.py` | **CREATE** | the EEB assembler (the entire commit) |
| `tests/test_assembler.py` | **CREATE** | mandated tests (integration/sealed EEB; integrity digest; replay-identity; evidence-absent propagation) — standalone-runnable, matching the 0.1/0.2/2.1–2.4 pattern |
| `runtime_context/execution_evidence_bundle.py` (2.1) | **UNCHANGED** | imported **read-only** for `EvidencePayload`, `ExecutionEvidenceBundle.seal`, `EvidenceField`. **No deserializer added here** (that would modify a frozen file — see HA-6) |
| `runtime_context/ports.py` (2.2) | **UNCHANGED** | imported **read-only** to source evidence-absent **C/D** readings (and their `_absent` pattern) |
| `runtime_context/context_objects.py` (2.3) | **UNCHANGED** | imported **read-only** to source plane-**B** readings |
| `runtime_context/transaction_interpreter.py` (2.4) | **UNCHANGED** | imported **read-only** to source plane-**A** readings |
| `runtime_context/__init__.py` | **UNCHANGED** (recommended) | keep side-effect-free; no re-exports in 2.5 |
| engine, benchmarks, `run_all.py`, dashboard, generators, frozen policy, registry | **UNCHANGED** | assembler is unconsumed |

- **Files removed / moved:** none.
- **Not in 2.5:** any consumer/engine wiring (Phase 4.1); any deserializer/`from_dict` on the 2.1 bundle (would modify a frozen file and duplicate serialization); any decision, predicate, threshold, or benchmark change. 2.5 is exactly one new module + its test.

## PART 3 — Dependencies & hidden assumptions

| Depends on | Verdict |
|---|---|
| **Commit 2.1** | **YES (hard)** — `EvidencePayload`, `ExecutionEvidenceBundle.seal`, `validate_structure`, `EvidenceField`, the enums. The assembler reuses `seal()` for the digest; it computes no hash itself. |
| **Commit 2.2** | **YES** — `AuthorityPort`/`GovernancePort` supply evidence-absent **C/D** `EvidenceField`s that must **propagate** into the sealed bundle (mandated "evidence-absent propagation" test). |
| **Commit 2.3** | **YES** — `FreshnessClock`/`ExecutionHistoryWindow`/`CommitActuateJournal` supply plane-**B** readings. |
| **Commit 2.4** | **YES** — `TransactionInterpreter` supplies plane-**A** readings. |
| Commit 0.2 guardrail | No functional dependency; **interaction:** `assembler.py` **is scanned** (`runtime_context` not excluded) → must stay clean (0 unregistered). |
| Gamma / `evaluate_decision` / policy θ | **NO** — the assembler seals evidence; it never evaluates. `PolicyPort` is **not** needed (policy is read for shape/routing, never *carried* in the bundle — EEB §2/§5). |
| `Class` | **NO — structurally impossible** — no plane produces it; the bundle is Class-blind by construction (EEB §Principles; the interpreter/ports/RCL never emit it). |

**Hidden engineering assumptions (all resolvable now; none scientific):**

- **HA-1 — The assembler PRODUCES nothing; it INTEGRATES + SEALS.** It calls each already-approved producer (or receives their `EvidenceField` outputs) and places them into payload slots. It performs **no** value computation, coercion, threshold, or transform. The only "new" call is `seal()`, which is a **structural digest**, not a decision. **Binding.**
- **HA-2 — Envelope + E-cached are INPUTS, never fabricated.** `bundle_id`, `created_at`, `method_version`, `subject_ref`, and `prior_ledger_link` are **supplied to** the assembler (by the caller / Evidence Collector). Where no producer exists (unconsumed scaffolding), the caller passes an **evidence-absent** `prior_ledger_link` (reusing the ports' `_absent` pattern). The assembler must **not** synthesize a ledger hash, a `bundle_id`, or a clock value (it is **not a time source** — HA-7).
- **HA-3 — Required-but-unproduced fields are carried as evidence-ABSENT, never defaulted.** The EEB requires `txn_action_ref`, `harm_risk_score`, `prior_ledger_link`, and a non-empty `node_predicate_vector`. In the bare arm some have no producer. The honest representation is an **ABSENT `EvidenceField`** (value `None`, `evidence_quality=ABSENT`), exactly as the 2.2 ports do — **not** a fabricated `0`/`False`/empty. Marking absence is a *fact about availability* (EEB §2.3/§6), not inference. **Recommendation:** absent evidence is supplied by the producers/ports (or a single shared `_absent` helper reused from 2.2), **not invented ad hoc** inside the assembler's logic.
- **HA-4 — `node_predicate_vector` membership/order is a BINDING, not assembler logic.** Which gates populate the vector and in what order is the deployment **ExecutionBinding** (EEB §2.2 "EEB fixes no gate's plane — the binding does"; RCL §2). The assembler must **receive** the ordered vector (or a binding descriptor), not hardcode a scientific gate set. For scaffolding/tests, a caller-supplied representative vector suffices. Hardcoding the gate semantics would smuggle a **policy** decision into the assembler. **Flag.**
- **HA-5 — Freshness deltas carried VERBATIM (see Reconciliation #2).** `FreshnessClock` deltas fill `stale_context`/`telemetry_fresh` **unchanged**; no booleanization/threshold. **Binding — this is the single most important "must not interpret" point.**
- **HA-6 — Replay-identity WITHOUT a new deserializer.** 2.1 exposes `canonical_json()`, `to_dict()`, `compute_integrity_digest()`, `verify_integrity()` — but **no** `from_dict`/deserialize. "persist→reload→identical" must therefore be proven by **(a) deterministic sealing** (same evidence → byte-identical `canonical_json()` + identical `integrity_digest`) and **(b) a canonical-form round-trip** (write `canonical_json()`, read it back, assert byte-identity; recompute digest and `verify_integrity()`). Adding a deserializer would **modify the frozen 2.1 file and duplicate serialization** — out of scope (Part 8). **Flag.**
- **HA-7 — No wall clock (same discipline as 2.2/2.3/2.4).** `created_at`/`observed_at` are injected; the assembler calls no `datetime.now()`/`time.time()`. Preserves determinism/replay (EEB §7).
- **HA-8 — Reuse existing types; introduce no new model.** The assembler emits an `ExecutionEvidenceBundle` (2.1). It defines **no** new bundle/payload/evidence type and **no** second serialization (Part 8).
- **HA-9 — Import hygiene / guardrail.** `assembler.py` imports only `runtime_context` siblings (2.1–2.4). No cycle: nothing imports `assembler`, and 2.1–2.4 do not import it. Importing `ports` transitively imports `agentdojo_integration.interception.frozen_policy` (light; Merkle-verify only if `PolicyPort` is constructed — which the assembler does **not** need). No watched auth-output names / decision literals (`seal`/`assemble`/`bundle`/`payload` are safe). **Post-commit gate:** `check_single_engine.py` → 0 unregistered.

## PART 4 — Engineering impact

| Area | Change? | Why |
|---|---|---|
| Repository structure | **+1 module** (`assembler.py`) + 1 test | additive |
| Imports | `assembler.py` → 2.1 + 2.2 + 2.3 + 2.4 (all `runtime_context`) | **nothing imports it** (no consumer) |
| Packaging | within `runtime_context/` | isolated |
| Execution flow / Runtime | **None** | unconsumed; no runtime path calls the assembler |
| Benchmark pipeline | **None** | six reports stay byte-identical to the 0.1 fixtures |
| Dashboard | **None** | `gamma_report_page.py` untouched |
| Tests | **+1** | additive |

**Files unchanged:** the engine (`gamma_test_runner.py`), all generators, `run_all.py`, the dashboard, the frozen policy, the registry, and every prior RCL module (`execution_evidence_bundle.py`, `ports.py`, `context_objects.py`, `transaction_interpreter.py`, `__init__.py`). **Only the two new files are added.**

## PART 5 — Data flow

```
 Transaction request (Amount, Time [, V1..V28] [, action ref];  Class NEVER read)
        │
        ▼
 Transaction Interpreter (2.4) ─────────────► plane-A  EvidenceField{txn_amount, txn_time, txn_action_ref?, txn_feature_ref?}
 Runtime Context Layer (2.3) ──────────────► plane-B  EvidenceField{stale_context(δ), telemetry_fresh(δ), commit/actuate, velocity/ordering}
 AuthorityPort (2.2) ──────────────────────► plane-C  EvidenceField{... = ABSENT in this arm}
 GovernancePort (2.2) ─────────────────────► plane-D  EvidenceField{harm_risk_score = ABSENT, ...}
 (caller / Evidence Collector) ────────────► Env{bundle_id, created_at, method_version, subject_ref?}  +  E-cached{prior_ledger_link (ABSENT)}
        │
        ▼
 ┌──────────────── EEB ASSEMBLER (2.5) — STRUCTURAL PLACEMENT ONLY ────────────────┐
 │  place each received EvidenceField into its named EvidencePayload slot           │
 │  (verbatim: no threshold, no coercion, no repair, no inference, no decision)      │
 │  build immutable EvidencePayload  →  ExecutionEvidenceBundle.seal(...)  [2.1]      │
 │  seal() computes the canonical SHA-256 integrity digest (structural, not a verdict)│
 └───────────────────────────────────────────┬──────────────────────────────────────┘
                                              ▼
 Sealed, immutable, provenance-complete, Class-blind Execution Evidence Bundle
                                              ▼
 STOP  ── no evaluator, no predicate, no Γ, no SAFE_STATE, no policy eval, no benchmark, no consumer
```

Evidence-absent C/D (and E-cached) **propagate unchanged** into the sealed bundle. `Class` enters nowhere. Consumption is Phase 4.1, out of scope.

## PART 6 — Risks (engineering only; no scientific risk)

| Risk | Severity | Mitigation |
|---|---|---|
| Assembler **booleanizes** freshness deltas (a θ threshold) | **Med (design-critical)** | HA-5 / Reconciliation #2: carry deltas verbatim; thresholding is the frozen evaluator's job |
| Assembler **fabricates** a missing required field (`0`/`False`/synthetic ledger hash) → inference / label-inversion risk | **Med** | HA-2/HA-3: required-but-unproduced → evidence-**ABSENT** (fact of availability), never a default; Env/E-cached are inputs |
| Assembler hardcodes `node_predicate_vector` gate set/order → smuggles a **binding/policy** | Med | HA-4: receive the ordered vector/binding; do not invent gate semantics |
| Duplicate serialization / new bundle model | Low | HA-8/Part 8: reuse `EvidencePayload` + `seal()`; no new type, no second canonical form |
| Adding a deserializer modifies frozen 2.1 | Low | HA-6: prove replay-identity via canonical byte-identity + `verify_integrity`, not `from_dict` |
| Missing provenance on an assembled field | Low | every field is an `EvidenceField` from an approved producer; `validate_structure()` enforces provenance completeness at seal |
| Mutable bundle contents | **None** | `ExecutionEvidenceBundle`/`EvidencePayload`/`EvidenceField` are frozen; `node_predicate_vector` is a tuple |
| Duplicate/oversealing (assemble twice → divergent digest) | Low | deterministic sealing test (HA-6): identical evidence → identical digest |
| Field ordering affects the digest | Low | canonical serialization sorts keys (`_canonical_json`, `sort_keys=True`); vector order is caller/binding-defined and preserved |
| Import cycle | **None** | nothing imports `assembler`; 2.1–2.4 do not import it (HA-9) |
| Guardrail false-positive / decision leak | Low | HA-9: no watched names/literals; verify 0 unregistered |
| Regression | **None** | unconsumed; engine/benchmarks untouched |

## PART 7 — Test plan

**Unit / hermetic (`tests/test_assembler.py`, standalone-runnable like the prior suites):**
- **Integration / producible sealed EEB** — from the real 2.2/2.3/2.4 producers + injected Env/E-cached, `assemble(...)` returns a sealed `ExecutionEvidenceBundle` that passes `validate_structure()`.
- **Integrity digest** — `bundle.verify_integrity()` is `True`; `compute_integrity_digest()` == the sealed `integrity_digest` (64-hex SHA-256).
- **Deterministic sealing** — assembling identical evidence twice yields **byte-identical** `canonical_json()` and identical `integrity_digest`.
- **Replay-identity (persist→reload→identical, HA-6)** — write `canonical_json()` to a scratch file, read it back, assert **byte-identity**; recompute digest over the reloaded canonical content and confirm it matches (no deserializer introduced).
- **Evidence-absent propagation (mandated)** — the `AuthorityPort`/`GovernancePort` ABSENT C/D fields (and an ABSENT `prior_ledger_link`) appear in the sealed bundle with `evidence_quality == ABSENT`, value `None`, correct `origin_plane` — unchanged by assembly.
- **No interpretation of values** — a `FreshnessClock` delta placed in `stale_context` is byte-equal to the producer's `EvidenceField` (no booleanization); a `DEGRADED` plane-A field from the interpreter is carried unchanged.
- **Class-blindness** — assembling a bundle whose source request carried `Class` yields a bundle with no field derived from `Class` (the interpreter already dropped it; the assembler adds nothing).
- **No wall clock** — AST check (as in 2.3/2.4): the module imports no `time`/`datetime` and calls no `.now()`/`.time()`.

**Regression (must stay green):**
- `python3 tests/test_transaction_interpreter.py` → 12/12 (2.4); `test_context_objects.py` → 10/10 (2.3); `test_ports.py` → 5/5 (2.2); `test_execution_evidence_bundle.py` → 6/6 (2.1); `test_single_engine_guardrail.py` → 6/6 (0.2); `test_baseline_fixtures.py` → 4/4 (0.1).
- Six benchmark reports **byte-identical** to `tests/fixtures/baseline/`.
- `python3 -c "import run_all"` → clean.

**Guardrail verification:** `python3 tools/check_single_engine.py` → exit 0 **and 0 unregistered** (HA-9; the new module is scanned).

**Baseline verification:** benchmark outputs, replay SHA, and Evidence Quad unchanged (byte-parity above).

**Bundle-integrity verification:** `verify_integrity()` True; digest is a 64-hex SHA-256; tampering any field (in a test copy) flips `verify_integrity()` to False.

**Deterministic-sealing verification:** identical-evidence → identical-digest (above), and canonical round-trip byte-identity.

**Repository verification:** `git status` shows only `runtime_context/assembler.py` + `tests/test_assembler.py` added; **no existing file modified**.

## PART 8 — Implementation minimization

- **Reuse the 2.1 contract end-to-end** — build `EvidencePayload` and call `ExecutionEvidenceBundle.seal(...)`; the digest/canonical form come from 2.1. **No** new bundle/payload/evidence type; **no** second serialization; **no** deserializer.
- **Reuse the producers verbatim** — the assembler calls 2.2/2.3/2.4 and places their `EvidenceField` outputs; it re-implements none of their logic.
- **Reuse the ports' evidence-absent pattern** for required-but-unproduced fields (a single shared `_absent`), rather than inventing per-field defaults.
- **One thin entry point** (`assemble(...)` / a small `EEBAssembler`), no hierarchy/factory/registry. Structural glue only.
- **Binding stays external** (HA-4): receive `node_predicate_vector`/Env/E-cached as inputs; the assembler owns *placement*, never *gate semantics* or *policy*.
- **Accept plain inputs** (a request mapping for 2.4; the RCL/port readings; Env/E-cached values) — no pandas, no file I/O, no engine import.

## PART 9 — Certification

1. **Is Commit 2.5 fully specified?** **YES**, once the two reconciliation facts are accepted (Env + E-cached are required inputs; freshness deltas are carried verbatim). The field set, `seal()` API, provenance, and Class-blindness are pinned by 2.1; HA-1…HA-9 are engineering.
2. **Are only engineering decisions remaining?** **YES** — entry-point shape, how the caller supplies the `node_predicate_vector` binding and Env/E-cached, and the replay-identity test mechanics (HA-6). No scientific decision; every *meaning* is fixed by EEB §2/§5 and the frozen 2.1 code.
3. **Does Commit 2.5 introduce scientific change?** **NO** — structural assembly + `seal()` only; no predicate, threshold, aggregation, Gamma call, SAFE_STATE, policy/governance evaluation, replay-semantics change, metric, or `Class` read. All frozen constructs untouched; benchmarks byte-identical.
4. **Can implementation begin safely?** **YES**, conditional on (a) carrying freshness deltas verbatim (no booleanization), (b) treating Env/E-cached and missing required fields as inputs / evidence-absent (never fabricated), and (c) proving replay-identity without adding a deserializer to the frozen 2.1 module.
5. **Can implementation scope be reduced further?** **YES** — see Part 8: reuse `EvidencePayload` + `seal()` (no new type, no second serialization, no deserializer), reuse the producers and the ports' `_absent`, a single thin `assemble(...)`, binding/Env/E-cached injected. This is the minimal realization of the roadmap's 2.5.

---

## IMPORTANT REVIEW QUESTION — proof the assembler performs ONLY structural assembly

The assembler's complete operation set is: **(1)** obtain each plane's `EvidenceField` from its already-approved producer (2.2/2.3/2.4) or from a caller input (Env/E-cached); **(2)** place each `EvidenceField` into its named `EvidencePayload` slot; **(3)** construct the immutable `EvidencePayload`; **(4)** call the frozen `ExecutionEvidenceBundle.seal(...)`; **(5)** optionally `validate_structure()`; **(6)** return the sealed bundle. Against each forbidden responsibility:

| Forbidden responsibility | Does the assembler do it? | Why not (structural proof) |
|---|---|---|
| **interpret evidence** | **NO** | it reads no field *value*; it moves opaque `EvidenceField` objects by slot name. Interpretation lives in the producers (2.4 plane-A, 2.3 plane-B), already approved. |
| **change evidence** | **NO** | `EvidenceField`/`ProvenanceDescriptor` are frozen; there is no setter. A placed field is byte-identical to the produced one (tested). |
| **repair evidence** | **NO** | a `DEGRADED` plane-A field is carried unchanged; the assembler never fixes/coerces a malformed value (HA-1, tested). |
| **normalize evidence** | **NO** | no type coercion, rounding, or canonicalization of *values*; canonicalization is over *serialization keys* only (2.1's `sort_keys`), not evidence content. |
| **infer evidence** | **NO** | missing required fields become evidence-**ABSENT** (`value=None`, `quality=ABSENT`) — a recorded fact of availability, not an inferred value; Env/E-cached are inputs, never synthesized (HA-2/HA-3). |
| **evaluate evidence** | **NO** | no comparison of any value against any threshold; specifically, freshness deltas are **not** booleanized (HA-5). |
| **authorize** | **NO** | no permit/deny is produced; the bundle has no decision field (EEB §Principles "No authorization semantics"). |
| **compute Gamma** | **NO** | `evaluate_decision`/the vectorized path is never imported or called; Γ is a plane-E engine output, absent from the bundle. |
| **compute SAFE_STATE** | **NO** | SAFE_STATE is a plane-E output; the assembler produces none and carries none. |

**The one operation that could be mistaken for computation** is `seal()`, which hashes the canonical content. This is a **structural integrity digest (tamper-evidence)**, not an authorization or an evaluation of evidence *meaning* — it is a pure function of bytes, defined and frozen in 2.1, and it decides nothing.

**Would-be violations to reject in implementation (flagged, not present in the spec):**
- Booleanizing `stale_context`/`telemetry_fresh` from deltas → **evaluate/authorize violation** (HA-5).
- Defaulting a missing `harm_risk_score`/`prior_ledger_link`/`txn_action_ref` to a concrete value → **infer violation** (HA-3).
- Hardcoding the `node_predicate_vector` gate membership/plane → **policy/binding violation** (HA-4).
- Adding a deserializer or a second serialization → **duplicate-model violation** (HA-6/Part 8).
- Calling `PolicyPort`/reading θ to shape the bundle → **policy-evaluation violation** (policy is never carried; EEB §2/§5).

If any of the above appears inside the assembler, it is an **architectural violation** and must be removed; as specified by the roadmap and EEB §5, none are required — the assembler is pure structural glue over the frozen `seal()`.

---

## Decision required

Before implementation, confirm:

- **(A)** Proceed with **Commit 2.5 = the EEB Assembler** (`runtime_context/assembler.py`) as reviewed: pure **structural placement + `seal()`** over already-produced evidence, carrying Env + E-cached as inputs and freshness deltas **verbatim**, representing unproduced required fields as **evidence-absent**, with the `node_predicate_vector` **binding injected**, and replay-identity proven **without** a new deserializer — HA-1…HA-9 held. **Recommended** (this is the roadmap's and EEB §5's 2.5).
- **(B)** You intended the assembler to *resolve* freshness/booleans, fill missing fields with defaults, or own the gate binding — those are **evaluation/inference/policy**, i.e., the architectural violations enumerated above. I will **not** implement those under a "2.5" label; they belong to the frozen engine / policy plane, not the passive carrier.

I will not implement until you confirm. Nothing here changes Gamma, predicates, thresholds, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed the roadmap's Commit 2.5 (EEB assembler) in isolation against `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §2/§3/§5` and `RUNTIME_EVIDENCE_ARCHITECTURE.md §4`; flagged the Env/E-cached completeness requirement and the freshness-delta carry-verbatim seam; proved structural-assembly-only; did not anticipate any consumer. Awaiting your reconciliation and approval.*
