# COMMIT 2.3 — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no file modified, no implementation.** Reviews Commit 2.3 exactly as defined in `ENGINEERING_MIGRATION_ROADMAP.md:107-114`, in isolation (Commit 2.4 interpreter and 2.5 assembler not anticipated; consumers out of scope).

**Roles:** Lead Runtime-Systems Architect · IEEE Artifact Engineer · Software-Verification Engineer · Repository-Migration Engineer · Runtime-Governance Engineer.

---

## SCOPE CONFIRMATION (read first) — the prompt and the roadmap agree

Unlike Commit 2.2 (whose prompt described the RCL *producer* while the roadmap defined *ports*), the Commit 2.3 request carries **no conflicting "Expected Purpose."** The roadmap is authoritative and unambiguous:

> **Commit 2.3 — `feat(rcl): add Runtime Context Layer plane-B objects`**
> Purpose: the four owned plane-B objects (history window, freshness clock, commit/actuate journal, context record) per `RUNTIME_CONTEXT_LAYER_SPECIFICATION.md §3`. Pure observation, no decision. Files created: `runtime_context/context_objects.py`.

This is the **plane-B evidence producer** the 2.2 review anticipated ("If you intended the RCL producer, that is Commit 2.3"). Prior status confirms 0.1, 0.2, 1.1, 2.1, 2.2 are complete; 2.3 is the next step. **No re-scoping is required.** One internal specification discrepancy about *which* four objects must be reconciled before coding — see the next section.

---

## RECONCILIATION REQUIRED — "four objects" is defined **two different ways** in the spec

The word "four" appears with **two incompatible memberships**, and Commit 2.3 must commit to one:

| Source | "Owned objects" enumerated | Count |
|---|---|---|
| **Roadmap 2.3** (`:108`) | history window, freshness clock, commit/actuate journal, **context record** | 4 |
| **Spec §2 reading** (`RUNTIME_CONTEXT_LAYER_SPECIFICATION.md:61`) | velocity window, freshness clock, commit/actuate journal, **assembled bundle** | 4 |
| **Spec §3 catalogue** (`:69-120`) | 3.1 `ExecutionContextRecord`, 3.2 `ExecutionHistoryWindow`, 3.3 `FreshnessClock`, 3.4 `CommitActuateJournal`, 3.5 `EvidenceBundle` | **5** |

The roadmap's four **include `ExecutionContextRecord` and exclude `EvidenceBundle`**; the spec §2 four **include `EvidenceBundle` and exclude `ExecutionContextRecord`**; the spec §3 catalogue lists **five**. These cannot all be Commit 2.3.

**Resolution (binding to the roadmap, which governs the migration):**

- **Commit 2.3 = §3.1 `ExecutionContextRecord` + §3.2 `ExecutionHistoryWindow` + §3.3 `FreshnessClock` + §3.4 `CommitActuateJournal`.**
- **§3.5 `EvidenceBundle` is NOT in 2.3.** It is the **assembler** — roadmap Commit 2.5 (`feat(rcl): add EEB assembler … → sealed bundle`). The spec §2/§3-minimality prose that groups the bundle into "four" is describing the *whole RCL*, not the 2.3 slice.

This matches the dependency graph (`ENGINEERING_MIGRATION_ROADMAP.md:30`): `2.3 RCL-B ─► 2.4 interpreter ─► 2.5 assembler`. **Do not build `EvidenceBundle`/assembly in 2.3.** If you intended the assembled view in this commit, stop — that is 2.5, and building it here would fold two roadmap commits into one, violating "one logical change per commit" (`:11`).

The remainder reviews the **four objects above** (three producers + one snapshot), unconsumed.

---

## PART 1 — Purpose

**What it accomplishes.** Adds `runtime_context/context_objects.py`: the RCL's **plane-B owned observation objects** — the only evidence the RCL *produces* rather than *exposes* (spec §2 "owner vs mere exposer"):

- **`ExecutionHistoryWindow` (§3.2)** — a bounded rolling view of prior mediated requests, exposing **velocity** and **execution-ordering** aggregates. Append + bounded-eviction. **Global-only** (the transaction source provides no subject key — spec §5 "Honest gap").
- **`FreshnessClock` (§3.3)** — a **pure function of timestamps** exposing context-capture / telemetry-heartbeat **deltas** for the `StaleContext` / `TelemetryFresh` deficit inputs. Read-only derivation.
- **`CommitActuateJournal` (§3.4)** — append-only record of commit-log / actuation-log **event references** exposing the commit-before-actuate ordering fact (Invariant I5).
- **`ExecutionContextRecord` (§3.1)** — the immutable per-request snapshot (request id, decision timestamp, references to the window/freshness/journal readings used). Immutable once sealed (DET4/append-only).

It is a **read model / observation layer only**: it **owns shape and observation, never meaning** (spec §0 Prime Invariant, §10). It **does not** authorize, evaluate, classify, compute predicates, invoke Gamma / SAFE_STATE / `evaluate_decision`, compare against any threshold or limit, read `Class`, or touch any runtime/benchmark path. **No module consumes it** (unconsumed scaffolding, as with 2.1 and 2.2).

**Why it follows 2.1/2.2 and precedes 2.4/2.5.** The three producers generate the plane-B readings that the **2.5 assembler** later seals into an EEB (`EvidencePayload` fields `stale_context`, `telemetry_fresh`, `commit_*`, and the velocity/ordering entries of `node_predicate_vector`). 2.3 is the **producer half** of the split the 2.2 review named; the **assembler half is 2.5**. Nothing here reaches a predicate — the readings terminate at their return value until 2.4/2.5/4.1 wire them.

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `runtime_context/context_objects.py` | **CREATE** | the four plane-B objects (3 producers + 1 snapshot) |
| `tests/test_context_objects.py` | **CREATE** | mandated tests (determinism, window bounding/eviction, timestamp-recomputability) — standalone-runnable, matching the 0.1/0.2/2.1/2.2 pattern |
| `runtime_context/execution_evidence_bundle.py` | **UNCHANGED** | imported read-only **iff** readings are emitted as 2.1 `EvidenceField` (see HA-6) |
| `runtime_context/ports.py` | **UNCHANGED** | **no dependency** — ports expose A/C/D; 2.3 owns B (siblings, not layered) |
| `runtime_context/__init__.py` | **UNCHANGED** (recommended) | keep side-effect-free; do not add re-exports in 2.3 |
| everything else (engine, benchmarks, `run_all.py`, dashboard, registry, frozen policy) | **UNCHANGED** | objects are unconsumed |

**Not in 2.3:** `EvidenceBundle`/assembler (§3.5 → **Commit 2.5**); `TransactionPort`/interpreter (§4/§6 → **Commit 2.4**); any threshold, limit, or fresh/stale/ordering *verdict* (policy/engine-owned, never RCL). 2.3 is exactly four observation objects. Do not add a fifth.

## PART 3 — Dependencies & hidden assumptions

| Depends on | Verdict |
|---|---|
| Commit 0.1 / 1.1 | No |
| Commit 0.2 | No functional dependency; **interaction**: `context_objects.py` **is scanned** by the guardrail (`EXCLUDE_PARTS` excludes `tests`/`tools`/`archive` but **not** `runtime_context`) → must stay clean (0 unregistered) |
| **Commit 2.1** | **Conditional (HA-6)** — hard dependency **iff** readings are emitted as `EvidenceField`/`ProvenanceDescriptor` with `OriginPlane.B`. Recommended for symmetry with the ports. |
| Commit 2.2 | **No** — no import of `ports.py`; the assembler (2.5) is what unites ports + owned objects |
| Gamma / `evaluate_decision` / `PolicyPort` thresholds | **No** — 2.3 produces deltas/aggregates only; it reads **no** threshold (thresholds are policy/engine-owned, spec §3.3/§7) |
| `Class` / dataset labels | **No — and must remain No** (Class-blindness, spec §8) |

**Hidden engineering assumptions (all resolvable now; none scientific):**

- **HA-1 — No wall-clock; determinism by injected time.** The objects **must not** call `datetime.now()` / `time.time()`. All timestamps (`observed_at`, decision time, commit/actuate times, heartbeat times) are **parameters**, exactly as the 2.2 ports took `observed_at`. This is what makes "identical evidence → identical readings" and "recomputable from timestamps" testable, and what keeps the object out of being a time source. **Binding.**
- **HA-2 — `FreshnessClock` exposes DELTAS, not verdicts (the Prime-Invariant boundary).** Spec §3.3 is explicit: *"the threshold to judge freshness lives in policy, not here."* The clock computes `(decision_time − context_capture_time)` and `(decision_time − heartbeat_time)` as raw magnitudes; it **must not** embed a freshness bound or emit a `fresh/stale` boolean. If a boolean is ever wanted, the bound must be a **passed parameter**, never a literal in this module. Emitting a verdict here would (a) author a decision (Prime-Invariant violation, spec §0) and (b) pin a policy constant into the RCL. **Recommend: deltas only in 2.3.**
- **HA-3 — `ExecutionHistoryWindow` exposes AGGREGATES, not limit comparisons.** It surfaces counts / velocity / ordering aggregates over the window; it **must not** compare them to a velocity/ordering *limit* (that comparison is the gate/policy, spec §3.2). **Global-only** — no per-subject window (spec §5 honest gap); do not synthesise a subject key. Window bound `W` is a **construction parameter**.
- **HA-4 — `CommitActuateJournal` exposes ordering FACTS, not the I5 verdict.** Spec §3.4: *"it does not define the ordering rule (which is frozen)"* (`gamma_test_runner.py:918-924`). Record commit/actuate event references + their timestamps and expose the **observed ordering** (e.g. the two timestamps, or a pure `commit_ts < actuate_ts` observation). **Decision needed:** whether 2.3 emits the derived `commit_before_actuate` boolean (a pure observation over two recorded timestamps — defensible) or leaves booleanisation entirely to the frozen check. **Recommend:** expose the recorded timestamps/refs; if a `commit_before_actuate` convenience is emitted, document it as a *pure ordering observation*, not the I5 verdict, and keep the frozen check the sole authority.
- **HA-5 — Mixed mutability (differs from 2.1's deep-frozen contract).** The producers are **stateful containers**: window = append + bounded-eviction, journal = append-only; `ExecutionContextRecord` = **immutable once sealed**. So 2.3 is *not* uniformly frozen. **Resolution:** the mutable producers must emit **immutable snapshot readings** (frozen dataclass / tuple) so a reading taken now is stable even as the window later evolves — the determinism/eviction tests depend on readings being stable snapshots, not live views.
- **HA-6 — Reading output type: `EvidenceField` vs native reading.** Roadmap 2.3 creates only `context_objects.py`; the **assembler (2.5)** maps readings into the sealed EEB. Two admissible choices: (a) emit 2.1 `EvidenceField` with `OriginPlane.B` provenance now (hard dep on 2.1; symmetric with the ports; 2.5 consumes directly); or (b) emit small native reading dataclasses and let 2.5 provenance-wrap. **Recommend (a)** for symmetry with the 2.2 ports and to make the "readings are immutable" test trivial (reuse the frozen `EvidenceField`). Whichever is chosen, **do not introduce a new evidence/result type** (minimization).
- **HA-7 — Eviction is a pure function of the record stream + `W`.** "Time-bounded" eviction must be driven by the **injected** decision timestamps (HA-1), not real time, so eviction is deterministic and replayable. Decide time- vs count-bounded (spec §3.2 permits either) and make it a construction parameter; the bounding test asserts eviction at the boundary.
- **HA-8 — Guardrail cleanliness.** No assignment to `gamma_g`/`gamma_class`/`pi`/`permit`/`yhat_permit`/`compensatory_permit`; no bare `"PERMIT"`/`"SAFE_STATE"` literal; no decision-literal `IfExp`. Plane-B naming (velocity, ordering, freshness_delta, commit/actuate) is outside the watched set and safe. **Post-commit gate:** `check_single_engine.py` → 0 unregistered.

## PART 4 — Engineering impact

| Area | Change? | Why |
|---|---|---|
| Repository structure | **+1 module** (`context_objects.py`) + 1 test | additive |
| Imports | `context_objects.py` → (optionally) `runtime_context.execution_evidence_bundle` (2.1) only | **nothing imports `context_objects.py`** (no consumer) |
| Runtime / execution flow | **None** | unconsumed |
| Benchmark pipeline | **None** | six reports stay byte-identical to the 0.1 fixtures |
| Dashboard | **None** | `gamma_report_page.py` untouched |
| Frozen policy / engine | **None** | not imported; no threshold read |
| Tests | **+1** | additive |

**Everything except the two new files stays untouched.**

## PART 5 — Data flow

```
 (injected) request id, decision timestamp, capture/heartbeat/commit/actuate timestamps
                    │   (parameters — RCL is NOT a time source; HA-1)
                    ▼
   ExecutionHistoryWindow   → velocity / ordering AGGREGATES (global, bounded W)   [OWNED, plane B]
   FreshnessClock           → capture/heartbeat DELTAS (no threshold, no verdict)  [OWNED, plane B]
   CommitActuateJournal     → recorded commit/actuate event refs + ordering fact    [OWNED, plane B]
   ExecutionContextRecord   → immutable snapshot referencing the readings used      [OWNED, plane B]
                    │  returns immutable reading(s) (EvidenceField[B] or frozen reading)
                    ▼
                  STOP  ── no consumer, no assembler, no port, no Gamma,
                           no threshold, no predicate, no benchmark, no Class
```

No path reaches `evaluate_decision`, Gamma, SAFE_STATE, a threshold/limit, the assembler (2.5), the benchmark pipeline, or the dashboard. `Class` has no input channel here at all (spec §8: the RCL sits inside the Class-blind region).

## PART 6 — Risks (engineering only; no scientific risk)

| Risk | Severity | Mitigation |
|---|---|---|
| Object embeds a threshold / emits a fresh-stale-or-ordering **verdict** → Prime-Invariant / label-boundary breach | **Med (design-critical)** | HA-2/HA-3/HA-4: deltas & aggregates only; verdicts stay in policy/engine; frozen I5 remains sole ordering authority |
| Wall-clock call → non-deterministic, non-replayable | Med | HA-1: inject all timestamps; ban `datetime.now()`/`time.time()` in the module |
| Live-view reading mutates after capture (window evolves) | Med | HA-5: emit frozen snapshot readings, not live references |
| Guardrail false-positive / decision-logic leak | Low | HA-8: no watched names/literals; verify 0 unregistered |
| Per-subject window faked despite no subject key | Low | HA-3: global-only; do not synthesise a key (spec §5) |
| New bespoke evidence type proliferates | Low | HA-6: reuse 2.1 `EvidenceField`; introduce no new type |
| `Class` leaks into a plane-B input | **None** (by construction) | no Class parameter is defined; Class-blindness test guards it |
| Regression in benchmarks/engine | **None** | unconsumed; nothing imports the module |
| Serialization drift | **None** | 2.3 does not serialize; if emitting `EvidenceField`, it reuses 2.1's canonical form |

## PART 7 — Test plan

**New (`tests/test_context_objects.py`, hermetic; standalone-runnable like `test_ports.py`):**
- **Determinism** — feeding an identical timestamped request/event stream twice yields **identical readings** (HA-1).
- **Window bounding / eviction** — appending past `W` evicts the oldest deterministically; aggregates reflect only the in-window set (HA-3/HA-7).
- **Freshness recomputability** — `FreshnessClock` deltas equal the arithmetic difference of the injected timestamps, with **no threshold** applied and **no boolean verdict** emitted (HA-2).
- **Ordering fact** — `CommitActuateJournal` reflects the recorded commit/actuate timestamps; any exposed ordering observation is a pure function of them, not the I5 verdict (HA-4).
- **Reading immutability** — an emitted reading (frozen `EvidenceField` or frozen reading) raises `FrozenInstanceError` on mutation; a later window append does not alter a previously captured reading (HA-5).
- **Class-blindness** — the objects accept no `Class` input; (structural) no dataset-label channel exists in any signature.
- **(If HA-6(a))** an emitted plane-B `EvidenceField` passes the EEB `_check_field` provenance completeness (non-empty `producer_id`/`observed_at`, `OriginPlane.B`).

**Regression (must stay green):**
- `python3 tools/check_single_engine.py` → exit 0 **and 0 unregistered** (HA-8 gate; the new module is scanned).
- `python3 tests/test_ports.py` → 5/5 (2.2).
- `python3 tests/test_execution_evidence_bundle.py` → all pass (2.1).
- `python3 tests/test_single_engine_guardrail.py` → all pass (0.2).
- `python3 tests/test_baseline_fixtures.py` → all pass (0.1).
- Six benchmark reports byte-identical to `tests/fixtures/baseline/`.
- `python3 -c "import run_all"` → clean.
- **Repository verification:** `git status` shows only `runtime_context/context_objects.py` + `tests/test_context_objects.py` added; **no existing file modified** (incl. `__init__.py`, `ports.py`, `execution_evidence_bundle.py`).

## PART 8 — Implementation minimization

- **Reuse 2.1 types** for readings (HA-6(a)): return `EvidenceField`/`ProvenanceDescriptor` with `OriginPlane.B`; **introduce no new evidence/result type.**
- **Four small objects, no hierarchy/factory/registry/plugin.** Three producers + one snapshot record. No abstract base, no dispatch layer.
- **Deltas & aggregates only** — no threshold, no limit, no verdict, no boolean fresh/stale/ordering *decision* (keeps the module trivially guardrail-clean and Prime-Invariant-compliant).
- **Global window only** (spec §5); no subject-keying machinery.
- **No assembler, no ports import, no bound producers, no EEB sealing** (those are 2.4/2.5).
- **Standard library only**, Python 3.9-compatible, side-effect-free import — matching the 2.1/2.2 discipline.

## PART 9 — Certification

1. **Is Commit 2.3 fully specified?** **YES**, once the "four objects" membership is fixed to the roadmap set (`ExecutionContextRecord` + `ExecutionHistoryWindow` + `FreshnessClock` + `CommitActuateJournal`; **`EvidenceBundle`/assembler deferred to 2.5**) and HA-1…HA-8 are resolved as above. All open items are engineering, not scientific.
2. **Are only engineering decisions remaining?** **YES** — reading output type (HA-6), time- vs count-bounded window (HA-7), and whether to emit a pure `commit_before_actuate` observation (HA-4). No scientific decision; every *meaning* is pinned by spec §3/§9.
3. **Does Commit 2.3 introduce scientific change?** **NO** — pure observation; no predicate, threshold, aggregation, Gamma call, SAFE_STATE, replay, metric, or `Class` read. Deltas/aggregates only; verdicts stay frozen.
4. **Can implementation begin safely?** **YES**, conditional on the "four objects" reconciliation above (confirm `EvidenceBundle` is **excluded** and belongs to 2.5) and on holding HA-2 (no embedded threshold/verdict) as binding.
5. **Can scope be reduced further?** **YES** — see Part 8: reuse 2.1 `EvidenceField` (no new type), four flat objects with no hierarchy, deltas/aggregates without verdicts, global-only window, no assembler/ports/producers. This is the minimal realization of the roadmap's 2.3.

---

## Decision required

Before implementation, confirm:

- **(A)** Proceed with **Commit 2.3 = the four plane-B objects** (`ExecutionContextRecord`, `ExecutionHistoryWindow`, `FreshnessClock`, `CommitActuateJournal`) in `runtime_context/context_objects.py`, **excluding** `EvidenceBundle`/assembly (deferred to Commit 2.5), with HA-1…HA-8 resolved as reviewed — **recommended**; or
- **(B)** You intended the **assembled `EvidenceBundle`/EEB view** in this commit — that is **Commit 2.5** (assembler), and pulling it into 2.3 would combine two roadmap commits. If so, say so; I will not silently fold 2.5 into 2.3.

I will not implement until you confirm. Nothing here changes Gamma, predicates, thresholds, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed the roadmap's Commit 2.3 (plane-B objects) in isolation against `RUNTIME_CONTEXT_LAYER_SPECIFICATION.md §3`; flagged the internal "four objects" membership discrepancy and bound it to the roadmap; did not anticipate Commits 2.4–2.5 or any consumer. Awaiting your reconciliation and approval.*
