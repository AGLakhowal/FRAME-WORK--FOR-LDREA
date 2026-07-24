# COMMIT 2.4 — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no file modified, no implementation.** Reviews Commit 2.4 exactly as defined in `ENGINEERING_MIGRATION_ROADMAP.md:116-123`, in complete isolation (Commit 2.5 not anticipated; no consumer).

**Roles:** Lead Runtime-Systems Architect · IEEE Artifact Engineer · Runtime-Governance Engineer · Software-Verification Engineer · Repository-Migration Engineer.

---

## RECONCILIATION REQUIRED (read first) — the prompt's "reads RCL observations" ≠ the roadmap's Commit 2.4

The prompt's **Expected Purpose / Responsibility** says the interpreter should *"Read Runtime Context Layer observations → Convert them into atomic EvidenceField objects,"* and names it the **"Runtime Interpreter."** **That is not the roadmap's Commit 2.4, and it contradicts the EEB specification.** Per `ENGINEERING_MIGRATION_ROADMAP.md:116-123`:

> **Commit 2.4 — `feat(rcl): add Transaction Interpreter (plane-A only, Class-blind)`**
> Purpose: read `Amount`/`Time`/features into **plane-A** EEB fields; **never** reads `Class`. Files created: `runtime_context/transaction_interpreter.py`.

And `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md:140` (Interface contract §5):

> **Transaction Interpreter** — read **the request**; populate **plane-A** fields + their provenance. **Must NOT:** derive predicates; touch **B**/C/D; read `Class`.

**The correction (binding):**

- Commit 2.4 reads the **transaction request** (plane **A**: `Amount`, `Time`, opaque `V1..V28` features). It does **not** read "Runtime Context Layer observations." Those are plane **B**, produced by the **Commit 2.3** objects (`ExecutionHistoryWindow`/`FreshnessClock`/`CommitActuateJournal`), which are a **separate, parallel producer**.
- The Transaction Interpreter and the RCL plane-B producers are **siblings**, not a chain. The interpreter owns plane A; the RCL owns plane B; the C/D ports (2.2) own their exposure. **Commit 2.5 alone unions all four into a sealed bundle** (EEB §5 "RCL (bundle assembler)").
- Therefore the prompt's data-flow *"Runtime Context Objects → Runtime Interpreter → EvidenceField"* mislabels the input. The correct input is the **transaction request**. I review the **roadmap/EEB Transaction Interpreter (plane A)** and will not build a plane-B re-reader (that would duplicate 2.3 and violate the EEB §5 "Must NOT touch B" rule and RCL §5 anti-mixing).

Naming: the roadmap and EEB call it the **Transaction Interpreter**; the prompt's "Runtime Interpreter" is treated as an alias for the same component. The remainder reviews the **Transaction Interpreter (plane A)**.

---

## PART 1 — Purpose

**What it accomplishes.** Adds `runtime_context/transaction_interpreter.py`: the **plane-A producer**. It performs a **direct read of the observable transaction request** and converts each observable field into an **atomic, immutable Commit 2.1 `EvidenceField`** with plane-A provenance:

- `Amount` → `txn_amount` (number)
- `Time` → `txn_time` (number / arrival)
- `V1..V28` → `txn_feature_ref` (**opaque** embedding; **optional**; a **governance-service input only, NEVER a predicate** — EEB §2.2/§5, RCL §5 anti-mixing)
- (optionally) an action/externalization-target reference → `txn_action_ref`, if the request supplies one

It **stops** at atomic `EvidenceField` objects. It does **not** assemble an EEB, authorize, evaluate Gamma, compute SAFE_STATE, invoke `evaluate_decision()`, evaluate policy/governance, derive any predicate, run benchmarks, or change runtime flow. It **never reads `Class`** and it never touches planes B/C/D. **No module consumes it** (unconsumed scaffolding, exactly like 2.1/2.2/2.3).

**Why it follows Commit 2.3.** This is **sequencing, not coupling.** The roadmap builds the RCL substrate in order (2.1 contract → 2.2 C/D/policy ports → 2.3 plane-B producers → 2.4 plane-A producer → 2.5 assembler). By 2.4, the plane-B producers (2.3) already exist, so the assembler (2.5) will have *all* producers present the moment it lands. But 2.4 imports **nothing** from 2.3 — the two are parallel producers into disjoint planes (see Part 3).

**Why it must precede Commit 2.5.** The assembler (2.5) unions plane-A (interpreter), plane-B (RCL 2.3), and C/D (ports 2.2) into a sealed bundle. It cannot populate the plane-A payload fields (`txn_amount`, `txn_time`, `txn_action_ref`, `txn_feature_ref`) without the plane-A producer. 2.4 provides exactly that producer and nothing more; 2.5 then assembles. Splitting production (2.4) from assembly (2.5) keeps "one logical change per commit" (`:11`) and keeps the interpreter free of any bundle/decision responsibility.

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `runtime_context/transaction_interpreter.py` | **CREATE** | the plane-A producer (the entire commit) |
| `tests/test_transaction_interpreter.py` | **CREATE** | mandated tests (plane-A population; **Class-blindness**; **unknown-field dropped**) — standalone-runnable, matching the 0.1/0.2/2.1/2.2/2.3 pattern |
| `runtime_context/execution_evidence_bundle.py` | **UNCHANGED** | imported **read-only** for its 2.1 types (`EvidenceField`, `OriginPlane.A`, …) |
| `runtime_context/ports.py` | **UNCHANGED** | **not** imported or modified. A named `TransactionPort` is **not** added here (that would modify an existing file; the roadmap lists **no** modifications for 2.4). See Part 8. |
| `runtime_context/context_objects.py` (2.3) | **UNCHANGED** | **not** imported — plane B is a sibling producer, not an input to 2.4 |
| `runtime_context/__init__.py` | **UNCHANGED** (recommended) | keep side-effect-free; no re-exports in 2.4 |
| engine, benchmarks, `run_all.py`, dashboard, generators, frozen policy, registry | **UNCHANGED** | interpreter is unconsumed |

- **Files removed:** none. **Files moved:** none.
- **Not in 2.4:** any EEB assembly/sealing (Commit 2.5); any plane-B/C/D read; any predicate derivation; any `TransactionPort` facade in `ports.py` (would modify an existing file). 2.4 is exactly one new module + its test.

## PART 3 — Dependencies & hidden assumptions

| Depends on | Verdict |
|---|---|
| **Commit 2.1** | **YES (hard)** — imports `EvidenceField`, `ProvenanceDescriptor`, `OriginPlane` (uses **`A`**), `EvidenceQuality`, `VerificationMethod`, `TrustLevel` to build plane-A readings |
| **Commit 2.2** | **NO** — does not import `ports.py`; does not add/modify `TransactionPort` |
| **Commit 2.3** | **NO** — does not import `context_objects.py`. The interpreter reads the **transaction request (plane A)**, not the RCL **plane-B** objects. The roadmap graph arrow `2.3 → 2.4` is **commit sequencing, not an import dependency.** |
| Commit 0.2 guardrail | No functional dependency; **interaction:** `transaction_interpreter.py` **is scanned** (`runtime_context` is not in `EXCLUDE_PARTS`) → must stay clean (0 unregistered) |
| `Class` / dataset labels | **NO — and must remain NO** (Class-blindness, EEB §Principles / §9; RCL §8) |
| pandas / CSV / `gamma_map_raw` / engine | **NO** — reads a neutral request record; no heavy import, no coupling to the active generator |

**Hidden engineering assumptions (all resolvable now; none scientific):**

- **HA-1 — Input is a neutral request record, not a DataFrame.** To stay stdlib-only, hermetic, and decoupled from the active CSV/pandas path, the interpreter should accept a plain `Mapping[str, Any]` (one request's fields). It must **not** import pandas or read files. **Binding for testability.**
- **HA-2 — Class-blindness by construction (fixed allowlist).** The interpreter reads **only** an explicit plane-A allowlist (`Amount`, `Time`, the `V1..V28` feature keys, and an optional action ref). Every non-allowlisted key — **including `Class`** — is **neither read nor copied**. This single mechanism satisfies *both* mandated tests: Class-blindness (Class is off the allowlist) **and** unknown-field-dropped (anything off the allowlist is dropped). No branch may reference `Class`. **Binding.**
- **HA-3 — `txn_feature_ref` is opaque; never a predicate.** `V1..V28` are carried as a single opaque vector/reference (EEB §2.2: "governance-service input only; NOT a predicate"; RCL §5 anti-mixing). The interpreter must **not** threshold, decompose, or interpret them. Optional field (present only if features are supplied).
- **HA-4 — Plane-A provenance is fixed by §4.** Every produced field uses `origin_plane = A`, `verification_method = FIELD_PRESENCE`, `trust_level = SELF_REPORTED` (payload-sourced), `evidence_quality = PRESENT` for a well-formed value. This deliberately differs from 2.3's plane-B provenance (`TIMESTAMP_DERIVED`/`DERIVED`) and reuses the same 2.1 enums.
- **HA-5 — Malformed value → `DEGRADED`, never a raise/decision (EEB §4/§6).** A present-but-untypeable `Amount`/`Time` is recorded with `evidence_quality = DEGRADED` (value carried as-is or null); the interpreter does **not** reject, repair, or decide — the frozen engine's fail-closed policy interprets `DEGRADED`. A **missing** field is simply not produced (the assembler/engine handles absence). The interpreter records quality; it never judges.
- **HA-6 — `txn_action_ref` sourcing.** The action/externalization-target reference is an **opaque string carrying no authorization meaning** (EEB §2.2). The credit-card dataset has no explicit action column, so 2.4 produces `txn_action_ref` **only if** the request supplies such a reference (or the caller passes one); it must **not** fabricate an authorization-bearing value. Absence is fine at 2.4 (the interpreter produces the plane-A fields it can observe; completeness is the assembler's concern in 2.5).
- **HA-7 — No wall clock (same discipline as 2.2/2.3).** `txn_time` comes from the **request payload** (data), not a clock. Provenance `observed_at` is an injected/deterministically-derived label, never `datetime.now()`/`time.time()`. Keeps determinism/replay (EEB §7).
- **HA-8 — Reuse 2.1 `EvidenceField`; introduce no new type.** Consistent with the **approved Commit 2.3 determination** (no parallel `RuntimeReading`): the interpreter emits atomic `EvidenceField[A]`. No new evidence model, no converter.
- **HA-9 — Guardrail cleanliness.** No assignment to `gamma_g`/`gamma_class`/`pi`/`permit`/`yhat_permit`/`compensatory_permit`; no bare `"PERMIT"`/`"SAFE_STATE"` literal; no decision-literal `IfExp`. Field names (`txn_amount`, `txn_time`, `txn_feature_ref`, `txn_action_ref`) are outside the watched set and safe. **Post-commit gate:** `check_single_engine.py` → 0 unregistered.

## PART 4 — Engineering impact

| Area | Change? | Why |
|---|---|---|
| Repository structure | **+1 module** (`transaction_interpreter.py`) + 1 test | additive |
| Imports | `transaction_interpreter.py` → `runtime_context.execution_evidence_bundle` (2.1) only | **nothing imports it** (no consumer); no import of 2.2/2.3 |
| Packaging | within `runtime_context/` | isolated |
| Execution flow | **None** | unconsumed |
| Runtime | **None** | no runtime path calls the interpreter |
| Benchmark pipeline | **None** | six reports stay byte-identical to the 0.1 fixtures |
| Dashboard | **None** | `gamma_report_page.py` untouched |
| Tests | **+1** | additive |

**Existing files unchanged:** the engine (`gamma_test_runner.py`), all generators (`gamma_map_raw.py`, …), `run_all.py`, the dashboard, the frozen policy, the registry, and the prior RCL modules (`execution_evidence_bundle.py`, `ports.py`, `context_objects.py`, `__init__.py`). **Only the two new files are added.**

## PART 5 — Data flow

```
 Transaction request  (a neutral record / Mapping)
   │   Amount, Time [, V1..V28 features] [, action ref]
   │   (Class may be PRESENT in the record but is OFF the allowlist → never read, never copied)
   ▼
 Transaction Interpreter        [reads ONLY the plane-A allowlist; drops everything else]
   │   Amount        → EvidenceField(txn_amount,      plane A, FIELD_PRESENCE, SELF_REPORTED)
   │   Time          → EvidenceField(txn_time,        plane A, …)
   │   V1..V28       → EvidenceField(txn_feature_ref, plane A, OPAQUE — governance input, not a predicate)
   │   [action ref]  → EvidenceField(txn_action_ref,  plane A, …)   (only if supplied)
   ▼
 Atomic plane-A EvidenceField objects   (immutable; frozen 2.1 type)
   ▼
 STOP  ── no bundle assembly, no plane B/C/D, no predicate, no threshold,
          no Gamma, no SAFE_STATE, no evaluate_decision, no policy/governance,
          no benchmark, no Class
```

The interpreter terminates at atomic `EvidenceField` objects. The 2.3 RCL plane-B producers run **in parallel** (not shown as an input here — they are not consumed by 2.4). Union + seal is **Commit 2.5**, out of scope.

## PART 6 — Risks (engineering only; no scientific risk)

| Risk | Severity | Mitigation |
|---|---|---|
| Interpreter reads/copies `Class` → **label leakage** | **Med (design-critical)** | HA-2: fixed plane-A allowlist; `Class` off-list; Class-blindness test (mutate/remove `Class` → identical outputs) |
| `V1..V28` interpreted as predicates → **plane inversion** (RCL §5) | Med | HA-3: carry as opaque `txn_feature_ref`; never threshold/decompose |
| Incorrect provenance (wrong plane/trust/method) | Low | HA-4: `A` / `FIELD_PRESENCE` / `SELF_REPORTED` per EEB §4; validated via `_check_field` |
| Mutable evidence returned | **None** | frozen 2.1 `EvidenceField` (immutable by construction) |
| Malformed input triggers a raise or a repair (a decision) | Low | HA-5: record `DEGRADED`; never reject/repair/decide |
| pandas/CSV coupling or heavy import | Low | HA-1: accept a plain `Mapping`; stdlib only |
| Import cycle | **None** | imports only 2.1; `execution_evidence_bundle` imports nothing from `runtime_context` consumers |
| Duplicate interpretation / new evidence model | Low | HA-8: reuse `EvidenceField`; single interpreter; no `TransactionPort` facade, no converter |
| Guardrail false-positive / decision-logic leak | Low | HA-9: no watched names/literals; verify 0 unregistered |
| Serialization drift | **None** | interpreter does not serialize; if serialized later, reuses 2.1 canonical form |
| Regression | **None** | unconsumed; engine/benchmarks untouched |

## PART 7 — Test plan

**Unit / hermetic (`tests/test_transaction_interpreter.py`, standalone-runnable like `test_ports.py`/`test_context_objects.py`):**
- **Plane-A population** — `Amount`/`Time` produce `txn_amount`/`txn_time` with correct value and provenance (`origin_plane == A`, `FIELD_PRESENCE`, `SELF_REPORTED`, `PRESENT`).
- **Class-blindness (mandated)** — two requests identical except `Class` (`0` vs `1`, and `Class` absent) yield **byte-identical** interpreter outputs; assert no output field derives from `Class`.
- **Unknown-field dropped (mandated)** — a request carrying extra non-allowlisted keys produces **no** field for them.
- **Feature opacity** — `V1..V28` surface as a single opaque `txn_feature_ref`; assert it is not decomposed into predicates and not thresholded.
- **`DEGRADED` on malformed** — a non-numeric `Amount` yields `evidence_quality == DEGRADED` (no raise, no repair).
- **Immutability** — a returned `EvidenceField` raises `FrozenInstanceError` on mutation.
- **EEB provenance validity** — each produced field passes the 2.1 `_check_field` (complete provenance, `OriginPlane.A`).
- **No wall clock** — AST check (as in `test_context_objects.py`): the module imports no `time`/`datetime` and calls no `.now()`/`.time()`.

**Regression (must stay green):**
- `python3 tests/test_context_objects.py` → 10/10 (2.3).
- `python3 tests/test_ports.py` → 5/5 (2.2).
- `python3 tests/test_execution_evidence_bundle.py` → 6/6 (2.1).
- `python3 tests/test_single_engine_guardrail.py` → 6/6 (0.2).
- `python3 tests/test_baseline_fixtures.py` → 4/4 (0.1).
- Six benchmark reports **byte-identical** to `tests/fixtures/baseline/`.
- `python3 -c "import run_all"` → clean.

**Guardrail verification:** `python3 tools/check_single_engine.py` → exit 0 **and 0 unregistered** (HA-9; the new module is scanned).

**Baseline verification:** benchmark outputs unchanged (byte-parity above); no metric, replay SHA, or Evidence-Quad change.

**Repository verification:** `git status` shows only `runtime_context/transaction_interpreter.py` + `tests/test_transaction_interpreter.py` added; **no existing file modified** (incl. `ports.py`, `context_objects.py`, `execution_evidence_bundle.py`, `__init__.py`).

## PART 8 — Implementation minimization

- **Reuse 2.1 `EvidenceField`** for every reading (HA-8): `origin_plane = A`; **introduce no new evidence/result type**, no `RuntimeReading`, no converter (consistent with the approved 2.3 decision).
- **One class, no hierarchy/factory/registry.** A single `TransactionInterpreter` with a small method set (e.g. `interpret(request) → tuple/dict of plane-A EvidenceFields`, or per-field readers). No abstract base, no plugin.
- **No `TransactionPort` facade.** The interpreter's public read *is* the plane-A exposure; adding a separately-named port in `ports.py` would modify an existing file (roadmap forbids) and duplicate the surface. Defer any port framing to a later commit if ever needed.
- **Allowlist doubles as two guarantees.** A fixed plane-A allowlist gives Class-blindness **and** unknown-field-drop with one mechanism — no separate filtering code.
- **Accept a plain `Mapping`** (HA-1) — no pandas, no file I/O, no engine import; keeps the module hermetic and the tests fast.
- **No bundle, no B/C/D, no predicate, no threshold, no policy** — those are 2.5 / the frozen engine.

## PART 9 — Certification

1. **Is Commit 2.4 fully specified?** **YES**, once the reconciliation is accepted — the interpreter reads the **transaction request (plane A)** per the roadmap and EEB §5, **not** RCL plane-B observations. The field set (`txn_amount`/`txn_time`/`txn_feature_ref`/optional `txn_action_ref`), provenance (§4), and Class-blindness are pinned; HA-1…HA-9 are engineering.
2. **Are only engineering decisions remaining?** **YES** — input record type (Mapping), `txn_action_ref` sourcing (HA-6), `DEGRADED` handling (HA-5), and the exact method surface. No scientific decision; every *meaning* is fixed by EEB §2/§4/§5 and RCL §5/§8.
3. **Does Commit 2.4 introduce scientific change?** **NO** — a direct read of observable request fields into provenance-tagged transport values; no predicate, threshold, aggregation, Gamma call, SAFE_STATE, policy/governance evaluation, replay, metric, or `Class` read. All frozen constructs untouched.
4. **Can implementation begin safely?** **YES**, conditional on (a) accepting the reconciliation (plane A, not plane B; interpreter does **not** consume 2.3), and (b) modifying **no** existing file (no `TransactionPort` in `ports.py`).
5. **Can implementation scope be reduced further?** **YES** — see Part 8: reuse `EvidenceField` (no new type), a single interpreter class, no `TransactionPort` facade, a plain `Mapping` input, and one allowlist mechanism serving both Class-blindness and unknown-field-drop. This is the minimal realization of the roadmap's 2.4.

---

## Decision required

Before implementation, confirm one:

- **(A)** Proceed with **Commit 2.4 = the Transaction Interpreter (plane A)** in `runtime_context/transaction_interpreter.py` — reads the **transaction request** (`Amount`/`Time`/features), emits atomic plane-A `EvidenceField` objects, **never** reads `Class`, **does not** consume the 2.3 RCL plane-B objects, and **does not** assemble a bundle — with HA-1…HA-9 as reviewed. **Recommended** (this is the roadmap's and EEB spec's 2.4).
- **(B)** You genuinely intended a component that **re-reads the 2.3 plane-B RCL observations** (as the prompt's "Runtime Context Layer observations" phrasing suggests). That is **not** the roadmap's 2.4, it **duplicates** the 2.3 producers, and it **violates** EEB §5 ("Transaction Interpreter must NOT touch B") and RCL §5 anti-mixing. I will **not** build that under a "2.4" label; if this is the intent, it needs its own scientific reconciliation first.

I will not implement until you confirm. Nothing here changes Gamma, predicates, thresholds, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed the roadmap's Commit 2.4 (Transaction Interpreter, plane A) in isolation against `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §2/§4/§5` and `RUNTIME_CONTEXT_LAYER_SPECIFICATION.md §5/§8`; corrected the prompt's plane-B mislabel; did not anticipate Commit 2.5 or any consumer. Awaiting your reconciliation and approval.*
