# COMMIT 3.1 — FINAL ENGINEERING REVIEW

**Engineering cleanup review only. No implementation, no file modified, no scientific/behavioural change proposed.** Reviews the *implementation* of Commit 3.1 (the ConcurBench Level-1 delegation to `evaluate_decision`) for engineering improvements that would produce **byte-identical** outputs. `evaluate_decision`, Gamma, predicates, metrics, replay, and benchmark semantics are frozen and untouched throughout.

**Roles:** Senior Software Architect · Runtime-Governance Engineer · IEEE Artifact Engineer · Software-Performance Engineer.

---

## 1. Findings

### CHECK 1 — `df.apply(lambda ...)` in `level1()`

Current (`concurbench_full.py:120-122`):
```python
yhat_permit = df.apply(
    lambda r: evaluate_decision(row_dict(r), 0.5)["pi"] == 1, axis=1
)
```

**Finding: KEEP AS-IS — the inline lambda is load-bearing, not incidental.** Three independent reasons:

1. **Guardrail contract requires the `evaluate_decision(...)` call to be *inside* the assignment's RHS.** The single-engine guardrail flags any assignment to a watched name (`yhat_permit`) whose RHS does **not** contain an `evaluate_decision` call (`check_single_engine.py:100-148`, `_rhs_reduces_to_engine_call` walks the RHS AST for the call). Extracting the lambda into a named helper — `df.apply(_engine_permit, axis=1)` — would remove the literal call from the RHS and **re-introduce the exact `auth_output_assignment` finding that Commit 3.1 cleared**. The inline form is therefore the *correct* form, not a stylistic accident.
2. **Outputs are identical and correct** — proven by byte-parity + SHA-256 (CHECK 5). Any "cleaner" rewrite must clear this bar; the current form already does.
3. **Performance is acceptable** — the full L1 pass over 284,807 rows runs in ~14s; the benchmark already spends comparable time reading the corpus. This is not a hot authorization path (it is an offline benchmark stage), so per-row Python is not a concern worth trading complexity for.

**Alternatives considered and rejected for *now*:**
- *Named-helper extraction* → **rejected**: breaks the guardrail RHS contract (above).
- *`itertuples`/list-comprehension* → no meaningful gain; same per-row cost; less readable than `df.apply`.
- *Distinct-input-tuple memoisation* (compute the decision once per unique gate/harm/stale/fresh/veto combination, map back) → produces **identical** outputs, still routes through `evaluate_decision`, and could be much faster — **but** it adds a grouping/mapping abstraction the roadmap explicitly discourages ("avoid premature abstraction") and is unwarranted at 14s. It is the documented escape hatch **only if** L1 runtime ever becomes unacceptable; not needed today.

**Verdict: retain the current implementation (justified).** No change.

### CHECK 2 — do the new equivalence tests duplicate authorization logic?

**Finding: YES — deliberately, in one isolated place, and legitimately.** `tests/test_concurbench_l1_equivalence.py:52-60` defines `_old_inline_permit(r)`, a verbatim restatement of the *pre-refactor* Level-1 rule, used as the **independent oracle** the roadmap mandates ("an explicit equivalence test asserting L1 == `evaluate_decision` on a sample"). Characteristics that make this benign:
- It lives under `tests/`, which the guardrail **excludes** (`EXCLUDE_PARTS` includes `tests`) — it is not a competing engine and cannot trip the single-engine check.
- Its purpose is precisely to be a *second, independent* derivation: an equivalence test with no independent oracle proves nothing. It anchors "the engine still makes the pre-3.1 decisions."

**Smallest change that reduces duplicated *logic* without weakening verification** (if the owner wants it): replace the live `_old_inline_permit()` **implementation** with a **frozen golden-expectation table** — a small list of `(row, expected_permit)` pairs computed once from the historical rule and pinned as data. This removes the duplicated *rule code* while asserting the identical decisions. Trade-off: a golden table is less self-documenting than the transparent rule, and the **report-level byte-parity + SHA-256 already provides a frozen-output anchor**, so the marginal benefit is small.

**Verdict: acceptable as-is; golden-table substitution is a lateral OPTIONAL refinement, not an improvement that clearly dominates.** Either form is defensible; neither changes behaviour.

### CHECK 3 — threshold handling: literal `0.5` vs a frozen constant

**Finding: NO frozen constant exists to reuse; the literal MUST be retained.** A repo-wide search found **no** module-level named θ constant. `0.5` appears only as scattered literals and a *mutable* CLI default:
- `gamma_test_runner.py:217` — `argparse ... default=0.5` (a **CLI-mutable** default; the Commit 3.1 binding rule explicitly forbids L1 reading it).
- `gamma_test_runner.py:133` — `evaluate_decision(row, harm_threshold)` takes θ as a **parameter** (no module constant).
- `full_spec_conformance.py:98` — `df["HARM_RISK"] > 0.5` (bare literal; a separate policy layer).
- `concurbench_full.py:485` — `if b["HARM_RISK"] > 0.5` (bare literal; the L2 section, out of 3.1 scope).
- `agentdojo_integration/interception/gamma_bridge.py:30` — `harm_threshold: float = 0.5` (default param).
- (`gamma_map_raw.py:48` `HARM_FRAUD = 0.8` is a *different* value for a different purpose — not θ.)

Since (a) **no frozen constant exists**, (b) reusing the argparse default is **forbidden** (mutable/CLI — the binding rule), and (c) **inventing a new constant is forbidden** (CHECK 3 instruction), the literal `0.5` is the only compliant choice. It is also **consistent with the repository's existing style** for θ in the benchmark layers (`full_spec_conformance.py:98` uses the same bare literal). The L1 comment already documents the pin.

**Verdict: RETAIN the literal `0.5` (explicitly justified).** No change.

### CHECK 4 — code documentation of the Level-1 delegation

**Finding: current documentation is good but incomplete on one axis.** The existing 4-line comment (`concurbench_full.py:116-119`) explains *why authorization is delegated* and *why `evaluate_decision` is the single source*, and documents the θ pin. It does **not** explicitly state *why duplicate authorization is prohibited* (the C-4 drift hazard / single-engine invariant / guardrail contract). Adding one clause closes that gap.

**Verdict: RECOMMENDED — a documentation-only enhancement** (see §2). No behaviour change.

### CHECK 5 — artifact verification (SHA-256)

**Finding: SHA-256 MATCH — exact.**
```
generated concurbench_full_report.json : 54833f7163dc7b5001a2962f113fb837e0c3175d2ed7f914c9ac612fdf85452e
baseline  fixture (0.1)                : 54833f7163dc7b5001a2962f113fb837e0c3175d2ed7f914c9ac612fdf85452e
                                         MATCH ✓
```
The report regenerated with the refactored L1 is cryptographically identical to the frozen baseline fixture. This strengthens the byte-parity claim (`diff -q` → identical) with a hash witness.

**Verdict: verified. No action.**

### CHECK 6 — guardrail documentation of the residual Level-3 warning

**Finding: the registry entry is now STALE and should be clarified.** After 3.1, `tools/authorization_registry.json` still labels `concurbench_full.py` as `classification: MIXED_REUSE_AND_C4_DEFECT`, `status: PENDING_REFACTOR_COMMIT_3_1` — but the C-4/Level-1 defect is **resolved**. The only remaining guardrail finding is `concurbench_full.py:358` (`stale_decision = "SAFE_STATE"`), a **benign Level-3 desync-simulation label**, not a competing engine (analogous to the documented C-2/C-3 separate-layer literals). The metadata should reflect: *C-4 resolved by Commit 3.1; residual `:358` is an expected L3-simulation SAFE_STATE label*, while keeping the entry **non-exempt** (final enforcement is Commit 6.4).

**Verdict: RECOMMENDED — a documentation/metadata clarification in the registry** (see §2). The guardrail remains warn-only and still reports `:358`; **no behaviour change**.

---

## 2. Recommended changes

| # | Change | Where | Nature |
|---|---|---|---|
| R1 | Add one clause to the L1 comment: *duplicate authorization is prohibited because a second copy can silently drift from the engine (the C-4 defect); the single-engine invariant + guardrail require all authorization to originate from `evaluate_decision`.* | `concurbench_full.py:116-119` (comment only) | Documentation |
| R2 | Update the `concurbench_full.py` registry entry: status → *L1/C-4 resolved by Commit 3.1*; note the residual `:358` as a benign L3-sim SAFE_STATE label; keep `exempt: false` until 6.4. | `tools/authorization_registry.json` (metadata only) | Documentation |
| R3 *(optional)* | Replace the `_old_inline_permit()` live oracle with a frozen golden-expectation table. | `tests/test_concurbench_l1_equivalence.py` | Test hygiene (lateral) |
| — | CHECK 1 (`df.apply`) and CHECK 3 (`0.5` literal): **retain as-is**, justified above. | — | No change |

## 3. Severity of each recommendation

| Rec | Severity | Rationale |
|---|---|---|
| **R1** (L1 comment) | **RECOMMENDED** | Improves auditability of the single-engine intent; the user's CHECK 4 explicitly requests it. Non-blocking. |
| **R2** (registry metadata) | **RECOMMENDED** | Removes stale "PENDING_REFACTOR_COMMIT_3_1" status; needed for clean 6.4 enforcement later. Non-blocking now. |
| **R3** (golden table) | **OPTIONAL** | Reduces duplicated *logic* but trades transparency; byte-parity/SHA already anchor outputs. A lateral trade, not a clear win. |
| CHECK 1 keep | **N/A (no change)** | Inline lambda is required for guardrail cleanliness; outputs identical; 14s acceptable. |
| CHECK 3 keep | **N/A (no change)** | No frozen constant exists; reusing the CLI default is forbidden; inventing one is forbidden. |

**There is no MANDATORY change.**

## 4. Does any recommendation change scientific behaviour?

**No — none.** Every item is documentation (R1, R2) or isolated test hygiene (R3). None touches `evaluate_decision`, Gamma, predicates, Γ aggregation, SAFE_STATE, thresholds, policy, replay, metrics, benchmark semantics, or any produced output. The report's bytes and SHA-256 are unaffected by all three; the guardrail's warn-only behaviour and its `:358` report are unaffected. Zero scientific drift.

## 5. Final certification

**READY TO FREEZE.**

The Commit 3.1 implementation is scientifically correct and engineering-sound as it stands: byte-identical report (SHA-256 `54833f71…5452e` matches baseline), full regression green, `gamma_test_runner.py` untouched, the three Level-1 guardrail findings cleared, and the single documented out-of-scope `:358` residual behaving exactly as reviewed. The `df.apply` form and the `0.5` literal are **correct as-is** (justified in CHECK 1 / CHECK 3 — no change warranted). The three recommendations (R1, R2 documentation; R3 optional test hygiene) are **non-blocking, behaviour-neutral polish** the owner may apply as a follow-up or skip; **none is required to freeze**, and none alters a single output byte.

---

*Final engineering review only. No code changed, no implementation performed, no scientific/behavioural change proposed or made. `evaluate_decision`, Gamma, FULL_SPEC, predicates, Γ aggregation, SAFE_STATE, replay, metrics, benchmark semantics, and the engineering roadmap remain frozen and untouched. Awaiting independent review of these recommendations before any polish is applied.*
