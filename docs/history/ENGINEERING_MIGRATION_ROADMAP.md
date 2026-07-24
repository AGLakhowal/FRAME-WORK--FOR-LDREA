# ENGINEERING MIGRATION ROADMAP

**A Git implementation plan — not architecture. No code, no implementation, no file modification.** Ordered, atomic, reversible commits to migrate the repository from its current state to the final architecture (RCL + EEB, single Gamma engine), while every non-gated commit preserves functionality, loads/imports cleanly, passes tests, and introduces no scientific change.

**Roles:** Runtime-Systems Engineer · Software-Verification Engineer · Release Engineer.

---

## 0. Principles binding every commit

1. **One logical change per commit.** No unrelated work combined.
2. **Independently loadable.** After each commit, every module imports and `run_all.py` completes.
3. **Green tests.** Each commit ships with the tests that prove it.
4. **Science-neutral by default.** No commit changes a predicate, threshold, decision, or reported metric — **except** the single explicitly **GATED** commit (5.2), which is a methodology change requiring scientific sign-off and is *not* claimed neutral.
5. **Reversible.** Every commit has a stated rollback (revert-safe; new code is additive and flag-gated until proven).
6. **Safest-first.** Build unconsumed scaffolding before touching any decision path; make the irreversible methodology flip last and gated.

**The gated boundary.** Commits 0.1 → 5.1 and 6.x are pure engineering and may proceed now. Commit **5.2** (activate the Class-blind pipeline / retire label authoring) is the *only* step that changes reported results; it is blocked on the five owner rulings enumerated in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10` and is flagged accordingly.

---

## 1. Commit dependency graph

```
0.1 baseline fixtures ─┐
0.2 guardrail (warn)   │
                       ▼
1.1 quarantine C-1 ────┐
                       │
2.1 EEB contract ─► 2.2 ports ─► 2.3 RCL-B ─► 2.4 interpreter ─► 2.5 assembler
                       │                                              │
3.1 concurbench L1 ────┤ (independent of 2.x)                        │
                       │                                              ▼
                       └──────────────────────────────► 4.1 evaluator EEB-input (flag OFF)
                                                              │
                                              5.1 Class-blind pipeline (flag OFF, parallel)
                                                              │
                                        ══════ GATED BOUNDARY (scientific sign-off) ══════
                                                              │
                                                    5.2 activate + retire label authoring
                                                              │
6.1 docs C-2 ─ 6.2 docs C-3 ─ 6.3 regression gates ─ 6.4 guardrail (enforce) ─ 6.5 artifacts
   (6.x are neutral; 6.3/6.4 should run against whichever pipeline is active)
```

---

## PHASE 0 — Safety net

### Commit 0.1 — `test: capture baseline golden outputs as regression fixtures`
- **Purpose:** freeze the current LAB/ConcurBench/FCR/FULL_SPEC/replay outputs as byte-level fixtures so every later commit can prove "no change."
- **Files created:** `tests/fixtures/baseline/*` (copies of current `*_report.json`, `gamma_summary.json`, replay manifest SHA).
- **Files modified:** none. **Archived:** none.
- **Scientific impact:** none (records current state).
- **Engineering risk:** none (additive).
- **Tests required:** a fixture-loader smoke test.
- **Expected output:** fixtures committed; no runtime behavior change.
- **Rollback:** delete fixtures dir.

### Commit 0.2 — `ci: add warn-only guardrail for authorization computed outside the frozen engine`
- **Purpose:** static check flagging any new `gamma_g`/`permit`/`SAFE_STATE` computation outside `evaluate_decision`; **warn-only** initially (existing C-2/C-3 are allowlisted with justification links).
- **Files created:** `tools/check_single_engine.py` (lint helper), CI config entry.
- **Files modified:** CI workflow (warn mode).
- **Scientific impact:** none.
- **Engineering risk:** none (non-blocking).
- **Tests required:** guardrail self-test (detects a planted violation).
- **Expected output:** CI emits warnings only.
- **Rollback:** remove the check step.

---

## PHASE 1 — Quarantine the fabricated engine (C-1, classified: DELETE)

### Commit 1.1 — `refactor: archive legacy external_validation harness and unwire from run_all`
- **Purpose:** remove the competing/fabricated engine (C-1) from the live pipeline.
- **Files archived:** `external_validation/*` → `archive/external_validation_legacy/` (retained for provenance, not imported).
- **Files modified:** `run_all.py` (drop step-4 import/call at :89,101; renumber steps), `gamma_report_page.py` (hide the AgentDojo-external section fed by the toy report), root `tests/test_agentdojo_validation.py` (move to archive or mark skipped).
- **Scientific impact:** **removes fabricated non-evidence**; no legitimate result lost (the real AgentDojo arm is `agentdojo_integration/`, untouched).
- **Engineering risk:** Low-Med (dashboard section + suite step wiring).
- **Tests required:** suite runs without step 4; dashboard renders without the removed section; `agentdojo_integration/tests/test_interception.py` still green.
- **Expected output:** `external_validation/agentdojo_report.json` no longer produced; suite completes with one fewer step.
- **Rollback:** revert the move + re-add the step.

---

## PHASE 2 — Introduce scaffolding (unconsumed; each additive & isolated)

### Commit 2.1 — `feat(rcl): add Execution Evidence Bundle data contract (no consumer)`
- **Purpose:** the immutable EEB type per `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md` §2 (fields + provenance descriptor), with sealing/validation/canonical-serialization surface. **No decision logic.**
- **Files created:** `runtime_context/execution_evidence_bundle.py`, `runtime_context/__init__.py`.
- **Scientific impact:** none (transport type; nothing consumes it).
- **Engineering risk:** none (unconsumed).
- **Tests required:** field types, immutability-after-seal, canonical-form determinism, integrity-digest recompute, version fields.
- **Expected output:** module importable; suite unchanged.
- **Rollback:** delete module.

### Commit 2.2 — `feat(rcl): add read-only Authority/Governance/Policy ports (evidence-absent default)`
- **Purpose:** typed read-only ports (EEB spec §4) that return **evidence-absent** when no producer is bound; PolicyPort reads existing frozen manifests (`frozen_policy.py`) read-only.
- **Files created:** `runtime_context/ports.py`.
- **Files modified:** none (reuses `ScientificPolicy`/`ExecutionBinding` read-only).
- **Scientific impact:** none.
- **Engineering risk:** none (unconsumed; ports default to absent).
- **Tests required:** each port returns `ABSENT` with no producer; PolicyPort integrity read matches Merkle root.
- **Expected output:** importable ports; no behavior change.
- **Rollback:** delete module.

### Commit 2.3 — `feat(rcl): add Runtime Context Layer plane-B objects`
- **Purpose:** the four owned plane-B objects (history window, freshness clock, commit/actuate journal, context record) per `RUNTIME_CONTEXT_LAYER_SPECIFICATION.md` §3. Pure observation, no decision.
- **Files created:** `runtime_context/context_objects.py`.
- **Scientific impact:** none.
- **Engineering risk:** Low (isolated).
- **Tests required:** determinism (identical evidence → identical readings), window bounding/eviction, freshness/ordering derivations recomputable from timestamps.
- **Expected output:** importable; no consumer yet.
- **Rollback:** delete module.

### Commit 2.4 — `feat(rcl): add Transaction Interpreter (plane-A only, Class-blind)`
- **Purpose:** read `Amount`/`Time`/features into plane-A EEB fields; **never** reads `Class`.
- **Files created:** `runtime_context/transaction_interpreter.py`.
- **Scientific impact:** none (reads observable request fields only).
- **Engineering risk:** Low.
- **Tests required:** plane-A field population; **Class-blindness test** (mutating `Class` leaves all outputs unchanged); unknown-field dropped.
- **Expected output:** importable; no consumer yet.
- **Rollback:** delete module.

### Commit 2.5 — `feat(rcl): add EEB assembler (Interpreter + RCL + ports → sealed bundle)`
- **Purpose:** assemble a sealed EEB per request from 2.1–2.4 (EEB spec §5). Passive carrier; no decision.
- **Files created:** `runtime_context/assembler.py`.
- **Scientific impact:** none.
- **Engineering risk:** Low-Med (integration of new parts, still unconsumed by the engine).
- **Tests required:** integration (produce a sealed EEB), integrity digest, **replay-identity** (persist→reload→identical), evidence-absent propagation.
- **Expected output:** a producible EEB object; engine still fed by current CSV path.
- **Rollback:** delete module.

---

## PHASE 3 — De-duplicate ConcurBench Level-1 (C-4, classified: REFACTOR)

### Commit 3.1 — `refactor(concurbench): route Level-1 through shared vectorized decision + equivalence test`
- **Purpose:** eliminate L1's inline copy (`concurbench_full.py:114-124`); source the decision from a single shared vectorized primitive already used by the runner (`gamma_test_runner.py:868-892`), so L1 cannot drift.
- **Files modified:** `concurbench_full.py` (L1 body only), possibly a small shared import from `gamma_test_runner`.
- **Scientific impact:** **none** — output is numerically identical by construction (verified against 0.1 fixtures).
- **Engineering risk:** Med (touches a benchmark headline path).
- **Tests required:** **byte-parity** of `concurbench_full_report.json` L1 block vs. baseline fixture; an explicit equivalence test asserting L1 == `evaluate_decision` on a sample.
- **Expected output:** identical L1 metrics; one fewer copy of the rule.
- **Rollback:** revert to the inline computation.

---

## PHASE 4 — Predicate Evaluator input adaptation (S6; highest neutral risk)

### Commit 4.1 — `feat(engine-io): allow Predicate Evaluator to read an EEB as input source (logic unchanged, flag OFF)`
- **Purpose:** add an **input adapter** so `evaluate_decision` / the vectorized path can be fed from an EEB *instead of* raw CSV columns — **decision logic byte-for-byte unchanged**. Behind a default-OFF flag; default path remains the current CSV.
- **Files modified:** `gamma_test_runner.py` (input marshalling only — the region that reads columns into the decision inputs; **not** :868-892 logic).
- **Files created:** `runtime_context/eeb_to_engine.py` (field-mapping adapter).
- **Scientific impact:** none while flag OFF; when ON, must produce **identical** decisions to the CSV path on the same evidence (this is the whole safety contract of S6).
- **Engineering risk:** **High** (touches the runner).
- **Tests required:** **zero-logic-diff gate** — with flag ON on a controlled arm, every `DerivedDecision`/`Γ`/`π` equals the flag-OFF result; full LAB parity vs. 0.1 fixture with flag OFF; AgentDojo tests green.
- **Expected output:** default run identical to today; opt-in EEB path available for validation.
- **Rollback:** revert; flag and adapter are additive.

---

## PHASE 5 — Class-blind generation (C-5, classified: REPLACE)

### Commit 5.1 — `feat(pipeline): add Class-blind evidence-only trace generation (flag OFF, parallel)`
- **Purpose:** new generation path producing an **evidence-only** trace (plane-A from the interpreter, plane-B from RCL, C/D evidence-absent), letting the **engine** compute decisions via 4.1. **Default OFF**; `gamma_map_raw.py` remains the active generator.
- **Files created:** `runtime_context/evidence_trace_builder.py`.
- **Files modified:** none to the active pipeline (new path is opt-in).
- **Scientific impact:** **none while OFF** (current outputs preserved). The new path is available for review but not reported.
- **Engineering risk:** Med (new pipeline; unconsumed by default).
- **Tests required:** Class-blindness (no `Class` read anywhere in the path); determinism; the produced trace feeds 4.1 and yields engine-computed decisions.
- **Expected output:** an alternate, opt-in evidence-only trace; reported numbers unchanged.
- **Rollback:** delete module.

### Commit 5.2 — `feat(methodology): activate Class-blind pipeline; retire gamma_map_raw label authoring`  ⚠️ **GATED — NOT science-neutral**
- **Purpose:** flip the default to the Class-blind pipeline (5.1) as the **reported** credit-card arm and retire the label-authoring branch (`gamma_map_raw.py:150-181`).
- **Files modified:** `run_all.py` / generator default; `gamma_map_raw.py` label-authoring branch (archived).
- **Files archived:** `gamma_map_raw.py` → `archive/` (or its authoring branch removed) once superseded.
- **Scientific impact:** **YES — this is the methodology change.** FPR/FDR/UER become genuine measurements (may be non-zero); the tautology is removed. **This commit changes reported results and MUST NOT be treated as neutral.**
- **PRECONDITION (blocking):** sign-off on the five rulings in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10` (actuation timing; class-veto plane; gate→plane binding; HARM_RISK proxy + Class-blind θ rationale; global-vs-per-subject windows). **Do not implement 5.2 before these are ruled by their owners.**
- **Engineering risk:** High (irreversible methodology shift; results change).
- **Tests required:** replay determinism on the new trace; Class-blindness end-to-end; documented expected *change* vs. baseline (a deliberate diff, reviewed and signed).
- **Expected output:** reported credit-card metrics reflect genuine engine decisions over observable evidence.
- **Rollback:** re-enable `gamma_map_raw` default (flag flip); the old generator remains in archive.

---

## PHASE 6 — Documentation, validation, artifacts (neutral)

### Commit 6.1 — `docs(stress): label stress_test as scenario-illustration layer (C-2)`
- **Purpose:** per classification, mark `stress_test` outputs as an illustrative non-compensatory scenario layer (metadata/notes only); flag the authored `confidence`/`tackled`/`verdict` as author-assessed (the separately-tracked relabel).
- **Files modified:** `stress_test.py` report metadata strings only; report note fields. **No logic.**
- **Scientific impact:** none (labeling; no numeric change).
- **Engineering risk:** none.
- **Tests required:** report still emits; note fields present.
- **Rollback:** revert notes.

### Commit 6.2 — `docs(fullspec): label enforce() as FULL_SPEC §7.1 separate policy layer (C-3)`
- **Purpose:** annotate `full_spec_conformance` output to state it is the broader §7.1 policy (node ∪ bands ∪ AIS ∪ class-veto), distinct from the LAB engine; optionally note the shared node-gate subset for future drift-proofing.
- **Files modified:** `full_spec_conformance.py` metadata/notes only. **No aggregation change.**
- **Scientific impact:** none (labeling).
- **Engineering risk:** none.
- **Tests required:** report emits; note present.
- **Rollback:** revert notes.

### Commit 6.3 — `test(regression): add LAB/ConcurBench/AgentDojo/replay parity gates`
- **Purpose:** promote the 0.1 fixtures into enforced parity gates covering LAB (`gamma_summary.json`), ConcurBench, FCR, FULL_SPEC, and the replay manifest SHA + `gamma_replay_verify.py` exit code; run `agentdojo_integration/tests/test_interception.py` in CI.
- **Files created/modified:** `tests/test_regression_parity.py`; CI config.
- **Scientific impact:** none (verification only).
- **Engineering risk:** none.
- **Tests required:** the gates themselves (green on the current/active pipeline; note: after 5.2 the LAB baseline is intentionally rebaselined with sign-off).
- **Expected output:** CI blocks accidental drift.
- **Rollback:** remove gates.

### Commit 6.4 — `ci: promote single-engine guardrail from warn to enforce`
- **Purpose:** flip 0.2 to blocking now that C-1/C-4/C-5 defects are handled; allowlist only the documented C-2/C-3 layers.
- **Files modified:** CI config; guardrail allowlist.
- **Scientific impact:** none.
- **Engineering risk:** Low (could block legitimately if allowlist incomplete — hence after 6.1/6.2 documentation).
- **Tests required:** guardrail passes on the tree; fails a planted violation.
- **Rollback:** revert to warn.

### Commit 6.5 — `chore(artifacts): regenerate dashboard/reports from the active pipeline`
- **Purpose:** regenerate `gamma_report.html` and reports so displayed artifacts match the active pipeline (pre-5.2: current methodology; post-5.2: Class-blind results).
- **Files modified:** generated `gamma_report.html`, `*_report.json` (outputs).
- **Scientific impact:** none by itself (regeneration); reflects whatever pipeline is active.
- **Engineering risk:** Low.
- **Tests required:** dashboard renders; every displayed value traces to a report field (addresses the display-literal findings).
- **Rollback:** restore prior artifacts.

---

## 2. Sequencing summary & gate

| Phase | Commits | Neutral? | May start now? |
|---|---|---|---|
| 0 Safety net | 0.1, 0.2 | Yes | Yes |
| 1 Quarantine C-1 | 1.1 | Yes (removes fabrication) | Yes |
| 2 Scaffolding | 2.1–2.5 | Yes | Yes |
| 3 De-dup C-4 | 3.1 | Yes (byte-parity) | Yes |
| 4 Evaluator input | 4.1 | Yes (flag OFF; parity-gated) | Yes |
| 5 Class-blind gen | 5.1 | Yes (flag OFF) | Yes |
| **5 Methodology flip** | **5.2** | **NO — gated** | **Only after the 5 scientific rulings** |
| 6 Docs/validation/artifacts | 6.1–6.5 | Yes | Yes (6.3/6.5 re-run post-5.2) |

**Bottom line.** Every commit except **5.2** is science-neutral, independently loadable, test-gated, and reversible, and can be executed now in the order above. **5.2 is the single methodology-changing commit** and is explicitly blocked on scientific sign-off — it is placed last so the entire engineering substrate (single-engine guarantee, RCL/EEB, parity gates, guardrail) is already proven before the reported results change. No commit combines unrelated work; each is one logical change with a stated rollback.

---

*Engineering migration plan only. No code, no implementation, no file modification. Commit titles, scope, risk, tests, and rollback are specified so another engineer can execute the migration step-by-step; the one non-neutral step is gated, not hidden.*
