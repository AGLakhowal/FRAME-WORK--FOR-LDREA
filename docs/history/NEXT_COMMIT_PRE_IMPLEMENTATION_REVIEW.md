# NEXT-COMMIT PRE-IMPLEMENTATION REVIEW — Commit 3.1

**Review only. No code, no file modified, no implementation.** The next unimplemented roadmap commit after 2.5 is **Commit 3.1** (`ENGINEERING_MIGRATION_ROADMAP.md:138-145`, Phase 3). Reviewed in isolation; Phase 4+ not anticipated; no commits merged or skipped.

**Roles:** Lead Runtime-Systems Architect · IEEE Artifact Engineer · Software-Verification Engineer · Repository-Migration Engineer · Runtime-Governance Engineer.

> ### Commit 3.1 — `refactor(concurbench): route Level-1 through shared vectorized decision + equivalence test`
> **Purpose:** eliminate L1's inline copy (`concurbench_full.py:114-124`); source the decision from a single shared primitive already used by the runner, so L1 cannot drift. **Files modified:** `concurbench_full.py` (L1 body only), possibly a small shared import from `gamma_test_runner`. **Scientific impact:** none — output numerically identical by construction (verified vs. 0.1 fixtures). **Tests:** byte-parity of the concurbench L1 block vs. baseline; equivalence test L1 == `evaluate_decision` on a sample. **Rollback:** revert to the inline computation.

**This is the first commit in the migration that touches a live benchmark decision path** (2.1–2.5 were additive, unconsumed). Its neutrality guarantee is therefore not "additive/unconsumed" but **byte-parity** against the frozen 0.1 fixtures.

---

## KEY ARCHITECTURAL FINDING (read first) — the "shared vectorized primitive" is **inline in `main()`**, but a callable oracle already exists

The roadmap points at "a single shared vectorized primitive already used by the runner (`gamma_test_runner.py:868-892`)." Verified: that block is **inline inside `main()`** (`main` begins at `:826`), coupled to `args.harm_threshold`, and mutates the DataFrame with `Derived*` columns — it is **not a callable function**. However, the runner **also** has a standalone, canonical single-row entry point:

- **`evaluate_decision(row: Dict, harm_threshold: float) -> Dict` (`gamma_test_runner.py:133-178`)** — the frozen engine function the guardrail treats as *the* single engine, called by the runner's own timed path (`:1145`). Its permit logic is **provably identical** to L1's inline copy:

| Step | L1 inline (`concurbench_full.py:114-124`) | `evaluate_decision` (`:141-166`) |
|---|---|---|
| node deficits | `deficit |= ~df[g]` over `NODE_GATE_COLS` | `if not row[g]: deficit=1` over `NODE_GATE_COLS` |
| harm | `HARM_RISK > 0.5` (hardcoded) | `HARM_RISK > harm_threshold` (θ) |
| freshness/context | `|= StaleContext ; |= ~TelemetryFresh` | same |
| class veto | `ReasonCodes ~ "CLASS_1|GOODHART"` | `"CLASS_1" in reason or "GOODHART" in reason` |
| permit | `yhat_permit = (~deficit) & (~gamma_class)` | `pi = 1 if (deficit==0 and gamma_class==0)` |

They are the same rule. Both modules **already share** `NODE_GATE_COLS`/`BOOL_COLS` (imported at `concurbench_full.py:41-47`). This yields **two viable implementations of 3.1**, which the owner must choose between:

- **Option A (recommended) — route L1 through the existing `evaluate_decision`.** Add `evaluate_decision` to the *existing* `from gamma_test_runner import (...)`, and in `level1()` compute the permit vector by applying `evaluate_decision(row_dict(r), 0.5)` per row (the `row_dict` helper already exists at `:96`). **`gamma_test_runner.py` is UNMODIFIED.** Guardrail-clean by construction. Byte-parity trivial (θ pinned to 0.5). Cost: per-row Python over the corpus (performance, not correctness).
- **Option B — extract the inline vectorized block (`:868-892`) into a shared function in `gamma_test_runner.py`**, called by both `main()` and L1. Preserves vectorization (speed). **But it modifies the frozen engine file**, which (i) exceeds the roadmap's stated scope ("`concurbench_full.py` (L1 body only)"), (ii) raises the byte-parity obligation to the **LAB report + replay manifest** as well, and (iii) may need registry work to stay guardrail-clean. Larger blast radius.

**Recommendation: Option A.** It honors the ABSOLUTE frozen-engine constraint (no `gamma_test_runner.py` change), reuses the canonical single-engine entry point (which the guardrail explicitly blesses — an assignment whose RHS reduces to an `evaluate_decision(...)` call is treated as *reuse*, not a defect: `check_single_engine.py:100-112`), makes the mandated equivalence test true by construction, and keeps blast radius to one file. The rest of this review assumes **Option A**; Option B is flagged where it would differ.

---

## 1. Purpose

Eliminate the **C-4 defect**: `concurbench_full.py`'s Level-1 authorization scoring re-implements the Law-of-Concurrence decision inline (`:114-124`), a second copy that can silently drift from the frozen engine. 3.1 routes L1's permit computation through the **single canonical `evaluate_decision`**, so L1 is, by construction, whatever the engine says — no independent decision code remains in the benchmark. The registry confirms this is the intended fix: `concurbench_full.py` is classified `MIXED_REUSE_AND_C4_DEFECT / PENDING_REFACTOR_COMMIT_3_1` (`tools/authorization_registry.json:68-72`).

## 2. Files created

| File | Why |
|---|---|
| `tests/test_concurbench_l1_equivalence.py` (or equivalent) | the mandated **equivalence test** (L1 permit path == `evaluate_decision` on a sample) + an **L1 byte-parity assertion** vs. the 0.1 baseline fixture. Standalone-runnable, matching the existing `tests/` pattern. |

## 3. Files modified

| File | Change | Why |
|---|---|---|
| `concurbench_full.py` | **L1 body only** (`level1()`, `:110-165`): delete the inline deficit loop + `gamma_class` + dead `permit` line; compute the permit vector via `evaluate_decision(row_dict(r), 0.5)`. Add `evaluate_decision` to the **existing** `gamma_test_runner` import (`:41`). | remove the C-4 duplicate; single source. The import already exists — this *is* the roadmap's "small shared import from `gamma_test_runner`." |
| `tools/authorization_registry.json` | **(decision — see §6/§10)** optionally **downgrade** the `concurbench_full.py` entry once the L1 findings clear. | the L1 auth-output assignments disappear; but a residual non-L1 finding remains (`:360`, see §6) — so the entry cannot simply be deleted. |

## 4. Files removed / 5. Files moved

**None.** No file is deleted or moved.

## 5. Dependencies

| Depends on | Verdict |
|---|---|
| `gamma_test_runner.evaluate_decision` (`:133`) | **YES** — the reused single-row oracle. Already importable; no engine change (Option A). |
| `gamma_test_runner.NODE_GATE_COLS` / `BOOL_COLS` | already imported (`concurbench_full.py:41-47`) |
| `concurbench_full.row_dict` (`:96`) | **YES** — already builds exactly the fields `evaluate_decision` reads; reused as-is |
| 0.1 baseline fixture `tests/fixtures/baseline/concurbench_full_report.json` | **YES** — the byte-parity oracle (verified present, 74,634 bytes) |
| Commits 2.1–2.5 (RCL/EEB) | **NO** — Phase 3 is independent of Phase 2 (roadmap graph `:30-34`); the EEB is not involved |
| Guardrail (0.2) | interaction only — 3.1 is expected to clear the L1 findings (see §6/§10) |

## 6. Hidden engineering assumptions

- **HA-1 — θ must be pinned to 0.5 for byte-parity.** L1's inline copy hardcodes `HARM_RISK > 0.5`; the runner's vectorized path uses `args.harm_threshold` (default 0.5). L1's call must pass `harm_threshold=0.5` **explicitly** (never read a mutable CLI arg), or the fixture parity breaks under a non-default runner invocation. **Binding.**
- **HA-2 — `evaluate_decision`'s `pi` equals L1's `yhat_permit` exactly.** Proven in the table above (same gates, same θ=0.5, same `CLASS_1|GOODHART` veto, same `pi=(deficit==0 ∧ gamma_class==0)`). Type handling matches (L1 pre-coerces `BOOL_COLS`/`HARM_RISK`; `row_dict` casts `bool`/`float`). ⇒ identical `tp/tn/fp/fn` ⇒ identical L1 metrics ⇒ **whole `concurbench_full_report.json` byte-identical**.
- **HA-3 — Guardrail-cleanliness requires the engine call in the RHS.** To clear the flags at `:116/:123/:124`, the permit assignment's RHS must *contain* the `evaluate_decision(...)` call (e.g. `... = df.apply(lambda r: evaluate_decision(row_dict(r), 0.5)["pi"] == 1, axis=1)`), so `_rhs_reduces_to_engine_call` returns True. Splitting into `dec = df.apply(evaluate_decision...)` then `yhat_permit = dec.map(...)` would leave `yhat_permit`'s RHS **without** an engine call and **stay flagged**. The intermediate `gamma_class`/dead `permit` lines must be **deleted**, not renamed.
- **HA-4 — SCOPE BOUNDARY: `concurbench_full.py:360` is NOT L1 and is NOT in 3.1's scope.** The guardrail flags a **fourth** construct — `stale_decision = "SAFE_STATE"` at `:360`, inside the **Level-3 desync/fleet simulation** (`:355-362`), scenario data, not a competing engine. It is outside `level1()`. **3.1 (L1 body only) must not touch it** (that would be scope creep / merging work). Consequence: after 3.1, `concurbench_full.py` is **not fully guardrail-clean** — the `:360` finding persists. The registry entry can be **downgraded** (L1 defect resolved) but **not removed**; final clearance of `:360` (a label/scenario annotation, akin to the C-2/C-3 handling) is a **separate** matter for Phase 6 (6.4 guardrail→enforce), not 3.1. **Must be flagged, not silently resolved.**
- **HA-5 — Performance (Option A).** `level1()` scores the full corpus (`GAMMA_G0_CREDITCARD_FULL_mapped.csv`, ~284,807 rows). Per-row `df.apply(evaluate_decision...)` replaces a fast vectorized boolean path → a real slowdown of the L1 stage (seconds→tens of seconds). Correctness unaffected. **Mitigation if unacceptable:** compute the decision on the *distinct* decision-input tuples and map back (still single-source, still byte-identical), or adopt Option B. Keep the simple per-row form unless runtime is proven unacceptable (avoid premature abstraction).
- **HA-6 — No import cycle.** `concurbench_full` already imports `gamma_test_runner`; `gamma_test_runner` does not import `concurbench_full`. Adding `evaluate_decision` to the existing import introduces no new module-load or cycle.

## 7. Repository impact

One benchmark module's L1 body changes + one new test (+ an optional registry downgrade). No new package, no structural change. `gamma_test_runner.py` and every other module are untouched (Option A).

## 8. Runtime impact

**None to the authorization runtime.** The engine, `evaluate_decision`, replay, and the live pipeline are unchanged. The only runtime effect is the **L1 stage of the ConcurBench benchmark runs slower** (HA-5). No decision, threshold, or output changes.

## 9. Benchmark impact

**Numerically none — byte-parity by construction.** The L1 block (and therefore the whole `concurbench_full_report.json`) is identical to the 0.1 baseline fixture. ConcurBench L2–L4 (adversarial/consistency/replay) are **untouched** and unaffected. What changes is provenance, not values: L1's numbers now come from the engine, not a copy.

## 10. Regression risks

| Risk | Severity | Mitigation |
|---|---|---|
| θ drift breaks fixture parity (HA-1) | Med | pin `harm_threshold=0.5` explicitly in the L1 call |
| Guardrail still flags L1 (RHS lacks engine call, HA-3) | Med | put the `evaluate_decision(...)` call *in* the permit assignment's RHS; delete `gamma_class`/dead `permit` |
| Over-reach onto `:360` / L2–L4 (HA-4) | Med | strictly limit the diff to `level1()`; leave `:360` for Phase 6; registry **downgraded, not deleted** |
| L1 performance regression (HA-5) | Med | acceptable for a benchmark; distinct-tuple mapping or Option B if runtime is unacceptable |
| Byte-parity miss from float/bool coercion | Low | `row_dict` + pre-coercion already match `evaluate_decision`'s expectations; parity test gates it |
| Whole-report drift (L2–L4 seeded RNG) | Low | those paths are untouched; the report-parity test covers the full file |
| Rollback needed | Low | single-file revert (see §12) |

## 11. Test plan

**New (`tests/test_concurbench_l1_equivalence.py`, standalone-runnable):**
- **Equivalence (mandated)** — on a representative sample of corpus rows, L1's permit decision equals `evaluate_decision(row_dict(r), 0.5)["pi"]` for every sampled row (trivially true under Option A; guards against future drift).
- **L1 byte-parity (mandated)** — the `level1()` output dict (and/or the produced `concurbench_full_report.json`) is byte-identical to `tests/fixtures/baseline/concurbench_full_report.json`'s L1 block.
- **θ-pinning** — L1 uses 0.5 regardless of any runner CLI arg.

**Guardrail verification:** `python3 tools/check_single_engine.py` — the L1 findings (`:116/:123/:124`) are **gone**; the file's remaining finding is **only** `:360` (documented residual, HA-4). Net known-pending count reflects the L1 clearance.

**Baseline verification:** all six baseline reports (`stress`, `fcr`, `full_spec`, `gamma_summary`, `gamma_lab_v1`, **`concurbench_full`**) byte-identical to `tests/fixtures/baseline/`; replay manifest SHA unchanged.

**Regression (must stay green):** `tests/test_assembler.py` (10/10), `test_transaction_interpreter.py` (12/12), `test_context_objects.py` (10/10), `test_ports.py` (5/5), `test_execution_evidence_bundle.py` (6/6), `test_single_engine_guardrail.py` (6/6), `test_baseline_fixtures.py` (4/4); `python3 -c "import run_all"` clean.

**Repository verification:** `git status` shows only `concurbench_full.py` (+ new test, + optional registry) changed; `gamma_test_runner.py` **unmodified**.

## 12. Rollback plan

**Single-file `git revert`** of the `concurbench_full.py` L1 change restores the inline computation (the new test and any registry edit are independently revertible). No data migration, no engine state, no fixture change — the refactor is additive-in-reverse and the baseline fixtures are the invariant.

## 13. Can implementation scope be reduced?

**Yes — Option A is already the minimal realization:**
- **Reuse `evaluate_decision`** (no new decision code, no engine extraction, no new module).
- **Reuse `row_dict`** (`:96`) and the **existing** `gamma_test_runner` import (add one name).
- **Touch only `level1()`**; do **not** modify `gamma_test_runner.py`, do **not** touch `:360`/L2–L4, do **not** add abstractions or a vectorized helper.
- Keep the equivalence test small (a sample), letting the 0.1 fixture carry full parity.

---

## CRITICAL ARCHITECTURE CHECK

Does Commit 3.1 change any of the following?

| Concern | Changed? | Basis |
|---|---|---|
| authorization semantics | **NO** | L1's decision becomes *literally* `evaluate_decision`; identical rule (HA-2) |
| predicate semantics | **NO** | same gates, same θ=0.5, same class veto; nothing redefined |
| Gamma | **NO** | `gamma_test_runner.py` unmodified (Option A); engine untouched |
| SAFE_STATE | **NO** | fail-closed semantics unchanged; the `:360` literal is untouched scenario data, not L1 |
| policy evaluation | **NO** | no policy/threshold authored or changed; θ pinned to the existing default |
| benchmark behaviour | **NO (numerically)** | byte-parity vs. the 0.1 fixture; only L1's *source of truth* and *runtime speed* change |
| replay semantics | **NO** | replay manifest/verifier untouched; L1 does not participate in the hash chain |

**No architectural violation.** 3.1 *removes* a competing decision copy and sources the number from the frozen engine — it strengthens the single-engine invariant rather than perturbing it. (Under Option B this check would require re-affirming LAB-report + replay byte-parity because the engine file would change — another reason to prefer Option A.)

---

## CERTIFICATION

1. **Is the next roadmap commit fully specified?** **YES**, once the owner rules Option A vs. B (recommended: A) — the reused oracle, the θ-pinning, the guardrail-clean form, the byte-parity gate, and the scope boundary at `:360` are all pinned. All open items are engineering.
2. **Are only engineering decisions remaining?** **YES** — A vs. B, the L1 performance form (per-row vs. distinct-tuple), and whether to downgrade the registry entry now or in Phase 6. No scientific decision.
3. **Does it introduce scientific change?** **NO** — byte-identical decision and metrics; no predicate, threshold, Gamma, SAFE_STATE, policy, replay, or reported-metric change (roadmap principle 4; verified against the 0.1 fixtures).
4. **Can implementation begin safely?** **YES** (Option A), conditional on: pin θ=0.5; place the `evaluate_decision` call in the permit RHS (guardrail); limit the diff to `level1()`; leave `:360`/L2–L4 untouched; do not modify `gamma_test_runner.py`.
5. **Can implementation scope be reduced?** **YES** — see §13: reuse `evaluate_decision` + `row_dict` + the existing import; one function touched; no engine change; no new abstraction. This is the minimal realization of the roadmap's 3.1.

---

## Decision required

Confirm one before implementation:
- **(A)** Proceed with **Commit 3.1 via Option A** — route L1 through the existing `evaluate_decision` (no `gamma_test_runner.py` change), θ pinned to 0.5, guardrail-clean, byte-parity-gated, `:360`/L2–L4 untouched. **Recommended.**
- **(B)** You require preserved L1 vectorization via a **shared function extracted from `gamma_test_runner.py:868-892`** — this modifies the frozen engine file and enlarges the byte-parity/rollback surface to the LAB report + replay; it exceeds the roadmap's stated "L1 body only" scope and must be sanctioned as such.

I will not implement until you confirm. Nothing here changes Gamma, predicates, thresholds, replay, benchmarks (numerically), or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed exactly one roadmap commit (3.1) in isolation against the actual code (`concurbench_full.py:110-165`, `gamma_test_runner.py:133-178`/`:868-892`), the 0.1 baseline fixtures, and the guardrail registry; surfaced the inline-vs-callable primitive choice, the θ-pinning parity condition, the guardrail-RHS requirement, and the `:360` scope boundary; did not anticipate later commits. Awaiting your reconciliation and approval.*
