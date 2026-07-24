# COMMIT 2.1 — PRE-IMPLEMENTATION REVIEW

**Review only. No code written, no file modified, no implementation.** Reviews Commit 2.1 (`feat(rcl): add Execution Evidence Bundle data contract (no consumer)`) exactly as written in `ENGINEERING_MIGRATION_ROADMAP.md` (Phase 2), in complete isolation — Commits 2.2–2.5 are **not** anticipated.

**Roles:** Lead Runtime-Systems Architect · Software-Verification Engineer · IEEE Artifact Engineer · Repository-Migration Engineer.

**Verified preconditions:** `runtime_context/` does not exist; **nothing** imports `runtime_context`/`execution_evidence_bundle` (no consumer); the interpreter is Python 3.9.6 (stdlib `dataclasses`/`enum`/`hashlib`/`json` available); the EEB spec §2 field set is the authoritative, frozen contract.

---

## 1. Purpose

Add the **immutable Execution Evidence Bundle (EEB) data-contract type** as a new, **unconsumed** module, per `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §2`. It declares the bundle's three field regions — Envelope, Evidence payload (planes A/B/C/D), and the per-field Provenance descriptor — plus the transport surface the spec mandates: **seal (immutable-after-creation), structural validation, canonical serialization, and an integrity digest**. It carries **no decision logic, no authorization, no Γ, no thresholds**. It exists solely to give later commits (2.5 assembler, 4.1 evaluator input) a type to build on. It is the root of the Phase-2 scaffolding chain: nothing depends on 2.1 *within* 2.1, and 2.1 depends on nothing.

## 2. Files created

| File | Purpose | Notes |
|---|---|---|
| `runtime_context/execution_evidence_bundle.py` | the EEB data-contract type (fields per spec §2 + seal/validate/canonical/digest/version) | stdlib only; no `pandas`; no import of Gamma |
| `runtime_context/__init__.py` | marks `runtime_context` an importable package | **recommend empty** (or a single re-export line) — minimal |
| `tests/test_execution_evidence_bundle.py` | the mandated self-test (field types, immutability-after-seal, canonical determinism, digest recompute, version fields) | standalone-runnable (`python3 …`), pytest-compatible — matches the 0.1/0.2 pattern (pytest is installed in no repo env) |

**Note on the test file:** the roadmap's "Files created" line names the module + `__init__.py`, and its "Tests required" line mandates the five checks. The test file is therefore in-scope for this commit (it realizes the required tests), not scope creep — flagged for transparency, exactly as in Commits 0.1/0.2.

## 3. Files modified

**None.** No existing file is edited. In particular: `run_all.py`, `gamma_test_runner.py`, all benchmark runners, `gamma_report_page.py`, `tools/authorization_registry.json`, and `agentdojo_integration/**` are **untouched**. The 0.2 registry is **not** updated (the EEB module is a pure data contract; it computes no authorization and therefore needs no registry entry — provided it stays guardrail-clean, see §5/§7).

## 4. Dependencies

| Depends on | Verdict |
|---|---|
| Commit 0.1 | **No** — fixtures unrelated |
| Commit 0.2 | **No functional dependency**; one **interaction** to verify — the guardrail will *scan* the new module (`runtime_context` is not in `EXCLUDE_PARTS`), so the module must remain clean (0 unregistered warnings). This is a verification step, not a dependency. |
| Commit 1.1 | **No** |
| Commits 2.2–2.5 / later | **No** — 2.1 is the root of the chain; those depend on *it*, never the reverse. |

**Decoupling from the five open scientific rulings:** `EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §10` lists five unresolved items (actuation-timing/`ACT_PERMIT` collision, `class_veto_evidence` plane, gate→plane binding, HARM_RISK proxy + θ rationale, per-subject vs global windows). **None blocks 2.1.** Every one is a *consumption*- or *generation*-time decision; 2.1 only **declares** the fields (with their spec-mandated provenance descriptors and any open-question noted in a docstring) and resolves no semantics. A no-consumer data contract can name a field without deciding how a future consumer interprets it. This is why 2.1 is safely science-neutral.

## 5. Hidden engineering assumptions (all resolvable now; none scientific)

- **HA-1 — Guardrail cleanliness (most important).** `runtime_context/` will be scanned by the 0.2 guardrail. The EEB module **must not** contain a bare decision-literal assignment (`X = "PERMIT"` / `"SAFE_STATE"`), a decision-literal `IfExp`, or an assignment to an auth-output name (`gamma_g`/`gamma_class`/`pi`/`permit`/…). Per spec §2 a data contract has **no reason** to — derived-output fields (Status/decision/Γ) are explicitly **absent** from the bundle. **Resolution:** implement the contract with no such constructs; if a validation whitelist of literals is ever needed, express it as a `frozenset({...})` (a `Call`, not a bare `Constant`, and not bound to an auth-output name) so it is not flagged. **Post-commit check:** `python3 tools/check_single_engine.py` must still report **0 unregistered**. A warning here would signal decision logic leaking into the contract — a design error to fix in the module, not to paper over in the registry.
- **HA-2 — Immutability mechanism.** Spec §1 mandates immutable-after-seal; the *mechanism* is an engineering choice. **Resolution:** a frozen `@dataclass(frozen=True)` (or an explicit seal flag that raises on post-seal mutation). Either satisfies the property; recommend frozen dataclass for determinism and simplicity (3.9-compatible).
- **HA-3 — Canonical serialization + digest algorithm.** Spec §7/§10 require *a* deterministic canonical form and *a* digest but leave the choice to engineering. **Resolution:** JSON with `sort_keys=True, separators=(",",":")` + **SHA-256** — consistent with the repo's existing hashing (`gamma_map_raw.py`, `gamma_replay_verify.py`, the manifest). No new dependency; 3.9-compatible.
- **HA-4 — Python/stdlib compatibility.** Target **3.9.6**; use `dataclasses`, `enum`, `hashlib`, `json`, `typing` only. Avoid 3.10+ syntax (`match`, bare `X | Y` runtime unions). **Resolution:** add `from __future__ import annotations` and stdlib-only imports.
- **HA-5 — Provenance-descriptor `evidence_quality` values.** Spec §2.3 fixes the enum (`PRESENT`/`ABSENT`/`DEGRADED`/`EXPIRED`). These are **not** decision literals and are transcribed from the frozen spec — no decision required.

None of these is scientific; each is an implementation detail already pinned by the spec + repo convention.

## 6. Repository impact

| Area | Change? | Why |
|---|---|---|
| Repository structure | **+1 package** (`runtime_context/`) + 1 test file | purely additive |
| Execution flow | **None** | nothing imports the module; `run_all` unchanged |
| Imports | **None rewired** | new module imported by nothing |
| Tests | **+1 self-test**; 0.1/0.2 unaffected | additive |
| Packaging | new package dir (empty `__init__.py`) | isolated |
| Runtime | **None** | no runtime path touched |
| Benchmark pipeline | **None** | LAB/ConcurBench/stress/FCR/FULL_SPEC untouched; 6 reports stay byte-identical |
| Dashboard | **None** | `gamma_report_page.py` untouched |
| Authorization / decision logic | **None** | the contract computes nothing |

**Everything that can remain unchanged, does.** The only additions are the new package and its test.

## 7. Regression risks (engineering only; no scientific risk)

| Risk | Severity | Mitigation |
|---|---|---|
| EEB module trips the 0.2 guardrail (false positive / decision-logic leak) | Low-Med | HA-1 — keep the contract free of decision literals/auth-output names; verify 0 unregistered post-commit |
| Import-time error in the new module | Very Low | unconsumed by `run_all` → cannot break the suite; its own self-test catches it |
| Accidental dependency added (e.g., `pandas`) | Low | stdlib-only mandate (HA-4) |
| Benchmark output drift | **None** | no benchmark code touched → reports byte-identical (re-verify against 0.1 baseline) |
| `__init__.py` accidentally imports a heavy/consuming module | Low | keep `__init__.py` empty (scope-minimization, §10) |

## 8. Test plan

**New (mandated by the commit):** `tests/test_execution_evidence_bundle.py`, standalone-runnable, asserting exactly the roadmap's five: (a) field **types** present/correct per spec §2 regions; (b) **immutability-after-seal** (mutation attempt rejected); (c) **canonical-form determinism** (same inputs → byte-identical canonical form); (d) **integrity-digest recompute** (recomputed digest == recorded); (e) **version fields** present (`schema_version`/`method_version` per spec §2.1). Hermetic — constructs bundles in-memory; touches no repo artifact.

**Regression (must stay green):**
- `python3 tests/test_baseline_fixtures.py` → 4/4 (0.1 fixtures untouched).
- `python3 tests/test_single_engine_guardrail.py` → 6/6 (0.2 self-test).
- `python3 tools/check_single_engine.py` → exit 0 **and 0 unregistered** (HA-1 gate: the new module is not flagged).
- Six benchmark reports byte-identical to `tests/fixtures/baseline/` (spot-check; nothing was re-run).
- `python3 -c "import run_all"` → still imports cleanly (unaffected).

**Repository verification:** `git status` shows only `runtime_context/` and the new test as additions; no existing file modified.

## 9. Rollback

Fully additive ⇒ `rm -rf runtime_context/ tests/test_execution_evidence_bundle.py`. No tracked file to restore; repository returns to its post-1.1 verified state. No commit depends on 2.1 yet → isolated rollback. Commits 0.1/0.2/1.1 unaffected.

## 10. Can the scope be reduced further?

**Largely no — it is already minimal for what the roadmap defines — with two small tightenings:**

- **Keep `runtime_context/__init__.py` empty** (package marker only). Do not re-export or import the module there — avoids any import-time coupling. (Minor reduction.)
- **Carry only the spec §2 field set + seal/validate/canonical/digest/version.** Add no helpers, no builders, no serialization beyond the canonical form + digest, and **no consumer glue**. The field set itself is frozen by spec §2 and cannot be trimmed (it is the contract).
- **Do not** reduce below the roadmap's stated test surface (canonical-form + digest are explicitly required); trimming them would de-scope the commit and push work onto later commits — the opposite of a clean reduction.

The commit cannot be meaningfully shrunk beyond "one contract module + empty package init + one self-test," which is what the roadmap specifies. The maximal *safe* reduction is ensuring the module is a pure data structure and nothing more.

---

## Certification

- **Fully specified?** **YES** — with HA-1…HA-5 resolved here (all engineering: guardrail-cleanliness, frozen-dataclass immutability, JSON+SHA-256 canonical/digest, 3.9/stdlib, spec-fixed enums). Field set is transcribed from frozen spec §2.
- **Only engineering decisions remaining?** **YES.** The five open EEB-spec-§10 scientific rulings are all consumption/generation-time and **do not block** a no-consumer contract (§4).
- **Introduces any scientific change?** **NO** — declares transport fields per a frozen spec; computes nothing; touches no engine/predicate/benchmark/replay/metric.
- **Can implementation begin safely?** **YES**, subject to the post-commit guardrail-clean check (HA-1) and confirming HA-2/HA-3 choices (frozen dataclass; JSON+SHA-256).
- **No existing code consumes it · no runtime path changes · no imports rewired · no authorization path changes · no benchmark changes · no decision logic changes** — **all CONFIRMED** by inspection (no consumer exists; additive-only).

**Recommendation:** proceed to implement Commit 2.1 as the three-file additive contract above (empty `__init__.py`, spec-§2 fields + seal/canonical/digest/version, hermetic self-test), then verify the 0.2 guardrail still reports 0 unregistered and the 0.1/0.2 suites stay green. Nothing here changes Gamma, predicates, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Commit 2.1 reviewed in isolation; Commits 2.2–2.5 not anticipated. Awaiting approval before implementing; will not proceed to Commit 2.2.*
