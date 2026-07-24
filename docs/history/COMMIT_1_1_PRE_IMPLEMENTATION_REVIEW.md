# COMMIT 1.1 — PRE-IMPLEMENTATION REVIEW

**Review only. No code written, no file modified, no implementation begun.** Reviews Commit 1.1 (`refactor: archive legacy external_validation harness and unwire from run_all`) against `ENGINEERING_MIGRATION_ROADMAP.md` and `AUTHORIZATION_ENGINE_CLASSIFICATION.md`.

**Roles:** Lead Software Architect · Runtime-Systems Engineer · IEEE Artifact Engineer · Repository-Migration Engineer.

**Evidence base:** repository-wide grep for every `external_validation` reference, direct read of `run_all.py` wiring and `gamma_report_page.py` consumption, and cross-check against the Commit 0.2 guardrail/registry.

---

## PART 1 — Purpose

**What it accomplishes.** Commit 1.1 removes the **C-1 fabricated competing authorization engine** (`external_validation/`) from the live pipeline by (a) **unwiring** it from `run_all.py` and (b) **archiving** the package out of the scanned tree. `external_validation/agentdojo_adapter.py:58-70` computes an independent `gamma_g`/`decision` from a `sensitivity` heuristic — a second authorization engine — and `external_validation/agentdojo_report.py:49-56` emits literal `false_permit_rate=0.0` etc. The suite renders these on the dashboard as "Independent validation — AgentDojo" ([gamma_report_page.py:181](gamma_report_page.py#L181)).

**Why necessary.** Two authoritative documents mandate it: `AUTHORIZATION_ENGINE_CLASSIFICATION.md` classifies C-1 as **Engineering defect → DELETE**, and `FINAL_FORENSIC_AUTHORIZATION_AUDIT.md §5` marks it the single **CRITICAL** competing engine "live on the dashboard." `PROJECT_CONSISTENCY_AUDIT.md` **CR-3** flags the same. Leaving it wired presents non-Gamma decisions as Gamma "independent validation."

**Reviewer concern supported.** Reviewer-2 **construct validity / external validation** (fabricated metrics) and the project's **single-authorization-engine** invariant. The *genuine* external arm — `agentdojo_integration/` (Phase 3A) — is untouched and remains the real AgentDojo integration.

---

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `external_validation/` (entire package: `agentdojo_adapter.py`, `agentdojo_report.py`, `agentdojo_dashboard.py`, `agentdojo_runtime_bridge.py`, `__init__.py`, and its co-located `*.md` design docs) | **ARCHIVE** → `archive/external_validation_legacy/` | quarantine the C-1 defect out of the scanned/imported tree |
| `run_all.py` | **MODIFY** | remove the import (:89), STEP-4 block (:100-102), `AGENTDOJO_DIR` (:46), the `"agentdojo"` key in the `extra` dict (:121), the `print_full_summary` arg (:125), the docstring/output references (:13-17, :210); renumber steps to **six** |
| `tests/test_agentdojo_validation.py` | **MOVE** → `archive/external_validation_legacy/` | it imports `external_validation.agentdojo_adapter` (:10) and `.agentdojo_report` (:30); it tests the toy harness and must travel with it |
| `tools/authorization_registry.json` | **MODIFY** (registry follow-through) | the C-1 entry `external_validation/agentdojo_adapter.py` (status `PENDING_QUARANTINE_COMMIT_1_1`) becomes stale once the file moves; update its `path`+`status` to `QUARANTINED` (or remove) — see HA-3 |
| `gamma_report_page.py` | **REMAIN UNCHANGED** (recommended) | **its AgentDojo section is already guarded** by `agentdojo = extra.get("agentdojo")` (:70) + `if agentdojo:` (:177). Not passing the key hides the section automatically — no edit needed (see HA-1) |
| `gamma_test_runner.py`, `concurbench_full.py`, `stress_test.py`, `fcr_test.py`, `full_spec_conformance.py`, `gamma_replay_verify.py`, `gamma_map_raw.py` | **UNCHANGED** | not referenced by external_validation; frozen benchmark/engine code |
| `agentdojo_integration/**` | **UNCHANGED** | the *real* AgentDojo arm; independent package |
| `tests/test_baseline_fixtures.py`, `tests/test_single_engine_guardrail.py` | **UNCHANGED** | Commit 0.1/0.2 artifacts; neither imports external_validation |
| Root `AGENTDOJO_LDREA_*.md`, `README.md` | **OUT OF SCOPE** | documentation-consistency items (`PROJECT_CONSISTENCY_AUDIT` CR-3/MJ-1), not part of the 1.1 *code* quarantine (see HA-5) |

**Complete reference set to unwire (verified by grep):** `run_all.py` lines 13-17, 46, 89, 100-102, 121, 125, 171-173 (already `if agentdojo:`-guarded), 210; `tests/test_agentdojo_validation.py` lines 10, 30, 38. No other module imports `external_validation`.

---

## PART 3 — Dependencies & hidden assumptions

**Depends on Commit 0.1?** No functional dependency. The 0.1 baseline fixtures are the **six active-pipeline reports** (`gamma_lab_v1`, `gamma_summary`, `concurbench`, `stress`, `fcr`, `full_spec`) — **none from external_validation**. So archiving external_validation cannot alter any 0.1 fixture; 0.1 stays green.

**Depends on Commit 0.2?** **Soft, one-directional:** the 0.2 registry contains a C-1 entry pointing at the file 1.1 moves. This is a *follow-through* (HA-3), not a blocker — the guardrail is warn-only and its `EXCLUDE_PARTS` already contains `"archive"`, so the moved package is simply no longer scanned (the C-1 warning correctly disappears). Updating the registry keeps it accurate.

**Depends on later commits?** No. Independent of 1.2/3.1/5.2.

**Hidden engineering assumptions (all resolvable now; none scientific):**

- **HA-1 — Is `gamma_report_page.py` modification necessary?** **No.** The section is guarded (`extra.get("agentdojo")` → `if agentdojo:`). **Resolution:** leave `gamma_report_page.py` **unchanged**; achieve the hide by having `run_all.py` not pass the `"agentdojo"` key. (Optional cleanliness: the now-unreachable section block :176-191 could be removed later as a *documentation* pass, not in 1.1.) This **narrows** the roadmap's file list by one and lowers risk.
- **HA-2 — Disposition of `tests/test_agentdojo_validation.py`.** **Resolution:** **move** it into `archive/external_validation_legacy/` alongside the package (keep test with subject). Do not delete (preserves provenance); do not leave in `tests/` (its import would break).
- **HA-3 — Registry follow-through.** **Resolution:** update the C-1 entry in `tools/authorization_registry.json` — set `status: "QUARANTINED_COMMIT_1_1"` and `path` to the archive location (or remove the entry). This adds the registry to 1.1's modified set (beyond the roadmap's original list) and keeps 0.2's guardrail accurate. The 0.2 self-test checks *key presence*, not path existence, so it stays green.
- **HA-4 — Move mechanism.** `external_validation/` and `tests/` are **untracked** (`git status: ?? external_validation/`, `?? tests/`). **Resolution:** archive via a plain filesystem `mv` (no `git mv`; no history to preserve). Archive dir = `archive/external_validation_legacy/` (matches guardrail `EXCLUDE_PARTS` "archive").
- **HA-5 — Documentation scope boundary.** **Resolution:** 1.1 quarantines the **code package + its co-located `external_validation/*.md`**. Root-level `AGENTDOJO_LDREA_*.md` and `README.md` external_validation references are **out of scope** (separate documentation-consistency items) to avoid scope creep.

---

## PART 4 — Repository impact

| Subsystem | Affected? | Precise reason |
|---|---|---|
| **Gamma / Γ / SAFE_STATE / LUIPM** | **No** | no engine file touched; C-1 was never the engine |
| **Replay** | **No** | `gamma_replay_verify.py` and the manifest untouched |
| **Benchmarks (LAB, stress, FCR, FULL_SPEC)** | **No** | their code and outputs unchanged; the 6 baseline fixtures unaffected — run_all still runs them, one fewer step |
| **AgentDojo** | **Only the fabricated arm** | `external_validation/` (toy) quarantined; `agentdojo_integration/` (real Phase 3A) untouched |
| **Runtime** | **No** | no runtime file touched |
| **ConcurBench** | **No** | `concurbench_full.py` unchanged |
| **Tests** | **Yes (one)** | `tests/test_agentdojo_validation.py` moves with the package; 0.1/0.2/agentdojo_integration tests unaffected; 0.2 guardrail stops flagging C-1 (correct) |
| **Documentation** | **Co-located only** | `external_validation/*.md` move with the package; root docs/README out of scope (HA-5) |
| **Dashboard** | **Section auto-hides** | `if agentdojo:` guard suppresses the AgentDojo section when the key is absent |

**Net observable change:** `run_all.py` completes with **six** steps instead of seven; `external_validation/agentdojo_report.json` is no longer produced; the dashboard renders without the "Independent validation — AgentDojo" section; the guardrail no longer warns about C-1.

---

## PART 5 — Implementation risks (no scientific risks exist)

| Risk class | Risk | Severity | Mitigation |
|---|---|---|---|
| Engineering | `run_all.py` edits (import/step/dict-key/arg removal, step renumber) introduce a typo/NameError | Low-Med | mechanical edits; `AGENTDOJO_DIR`/`agentdojo_report_obj` fully removed together; import-run `run_all.py --help` and a dry pass |
| Regression | a benchmark output drifts | Low | benchmarks untouched → re-run 0.1 baseline parity (6 fixtures byte-identical) |
| Regression | dashboard errors on missing data | **Very Low** | already guarded (`if agentdojo:`); confirmed by read |
| Packaging | a stale import to `external_validation` remains | Low | grep verified only `run_all.py` + `tests/test_agentdojo_validation.py` import it; both handled |
| Repository | dangling 0.2 registry entry | Low | resolved by HA-3 (update/remove entry) |
| Reproducibility | `run_all` output structure changes | **Intended** | one fewer step is the goal; scientific reports (6) remain reproducible/identical |
| Scientific | — | **None** | C-1 is a fabricated non-artifact; classification is authoritative; real arm untouched |

---

## PART 6 — Test plan

**Must be executed after 1.1:**
- `run_all.py` completes end-to-end (or at minimum imports cleanly and runs its non-benchmark structure) with **no** `external_validation` import and **six** renumbered steps; confirm `external_validation/agentdojo_report.json` is not regenerated; confirm the dashboard renders without the AgentDojo section.
- `python3 tools/check_single_engine.py` → exit 0, and **C-1 no longer appears** (package excluded under `archive/`); no new UNREGISTERED warnings.

**Must remain green (regression):**
- `python3 tests/test_baseline_fixtures.py` → 4/4 (0.1 fixtures untouched).
- **Byte-parity spot-check** (prudent, though the enforced gate is Commit 6.3): re-run the six benchmarks and diff against `tests/fixtures/baseline/` — expect identical.
- `python3 tests/test_single_engine_guardrail.py` → 6/6 (registry still well-formed after HA-3).
- `agentdojo_integration/tests/test_interception.py` → unchanged (real arm intact).

**New tests required?** **None mandatory.** Optionally add a one-line assertion that `run_all` no longer imports `external_validation` (an import-absence guard). The roadmap does not require a new test for 1.1; the effective test is "suite still runs + guardrail no longer flags C-1."

---

## PART 7 — Rollback

Fully reversible:
1. `mv archive/external_validation_legacy/ external_validation/` and move `test_agentdojo_validation.py` back to `tests/`.
2. Restore `run_all.py` to its pre-1.1 content (capture a pre-image/patch before editing; `run_all.py` is tracked, so the 1.1 delta is a reverse-applicable diff — reverse-apply it, **not** `git checkout HEAD` which would also drop the pre-existing working-tree modifications).
3. Revert the `tools/authorization_registry.json` C-1 entry (HA-3).

Because `external_validation/` and `tests/` are untracked, the archive move is a plain `mv` back. No downstream commit depends on 1.1 → isolated rollback. Commits 0.1 and 0.2 are unaffected.

---

## PART 8 — Certification

1. **Is Commit 1.1 completely specified?** **YES** — with HA-1…HA-5 resolved in this review (all engineering). The exact reference set is enumerated (Part 2); the roadmap's `gamma_report_page.py` edit is shown unnecessary (HA-1) and the registry follow-through is added (HA-3).
2. **Are any scientific decisions still required?** **NO.** C-1's DELETE classification is authoritative (`AUTHORIZATION_ENGINE_CLASSIFICATION.md`); the real AgentDojo arm is untouched.
3. **Are only engineering decisions remaining?** **YES** — the five HAs, all resolved (archive naming, test disposition, registry update, move mechanism, doc-scope boundary).
4. **Is Commit 1.1 independent of later commits?** **YES.** No dependency on 1.2/3.1/5.2. Soft, backward-only relation to 0.2 (registry accuracy), not a blocker.
5. **Can implementation begin safely?** **YES**, subject to confirming the recommended resolutions — in particular **HA-1 (leave `gamma_report_page.py` unchanged)** and **HA-3 (update the registry entry)** — and capturing a `run_all.py` pre-image for rollback.

**Recommendation:** proceed to implement Commit 1.1 with the file set of Part 2 as refined (archive the package + its test, edit `run_all.py`, update the registry; leave `gamma_report_page.py` unchanged). Nothing here changes Gamma, predicates, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. All citations are `file:line` from the current working tree. Awaiting approval before implementing Commit 1.1; will not proceed to Commit 1.2.*
