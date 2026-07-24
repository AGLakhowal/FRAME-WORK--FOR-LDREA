# COMMIT 5.2 — ACTIVATION BLOCKER

**No code, no repository modification, no activation, no flip, no rebaseline.** During implementation of Commit 5.2 (activate the Class-blind runtime pipeline), the prompt's own **STOP CONDITION** fired: activation as specified cannot be performed without doing something the prompt's **ABSOLUTE PROHIBITIONS** forbid and its **VERIFICATION** requires to stay unchanged. Per "If any of these appear necessary, STOP. Document the blocker. Do NOT implement it," I halted and produced this document instead of guessing.

**Roles:** Principal Runtime Systems Engineer · IEEE Artifact Engineer · Runtime Governance Architect · Software Verification Engineer.

---

## 1. Executive Summary

Commit 5.2, as defined by the Engineering Migration Roadmap, means **"flip the *reported* credit-card arm to the Class-blind pipeline and retire `gamma_map_raw` label authoring."** That is, by the roadmap's own words, a **deliberate methodology change: "FPR/FDR/UER become genuine measurements … This commit changes reported results and MUST NOT be treated as neutral."**

This prompt, however, instructs the opposite for the same commit:
- **ABSOLUTE PROHIBITIONS:** *Do NOT modify benchmarks · Do NOT modify metrics · Do NOT modify policy · Do NOT modify evidence generation.*
- **VERIFICATION requires:** *Benchmark parity · Regression parity · Existing tests remain green · No behavioural change.*

**These two mandates are mutually exclusive**, and the conflict is now demonstrated with the actual numbers:

| | Reported credit-card arm today (`gamma_map_raw`) | After Class-blind activation (no declared policy) |
|---|---|---|
| PERMIT | **284,315** | **0** |
| SAFE_STATE | **492** | **≈284,807** |
| FPR / FDR / UER | 0 / 0 / 0 (tautology) | degenerate all-deny (full-vector fail-closed) |
| `gamma_summary.json` | frozen baseline | **completely different** |

Flipping the reported arm therefore **rewrites `gamma_summary.json`**, which the **regression parity gate compares byte-for-byte to the frozen baseline** — so **"Regression parity," "Benchmark parity," and "Existing tests remain green" would all FAIL**, and **"Do NOT modify metrics/benchmarks/evidence generation" would be violated**. This is not avoidable by better engineering; it is the intended effect of the flip.

Moreover, the flip's two governing **owner/governance acts remain unprovided** (they are not engineering, so "all prerequisite engineering work is frozen" does not supply them): the **signed metric-change ruling + baseline rebaseline**, and the **declared credit-card deployment policy** (Gap-3 slice choice + Deployment Contract §16 C1–C6). Without a declared gate-set/SLA, activation reports the **degenerate all-deny**, which is itself a signed, reportable methodology decision — not a neutral wiring.

**Verdict: IMPLEMENTATION BLOCKED.** The neutral "wiring only" activation the prompt describes and the metric-changing flip the roadmap defines cannot both be true; the metric-changing flip is prohibited here and ungoverned. I implemented nothing.

---

## 2. The contradiction, precisely

**Roadmap Commit 5.2** (`ENGINEERING_MIGRATION_ROADMAP.md`): *"flip the default to the Class-blind pipeline (5.1) as the **reported** credit-card arm and retire the label-authoring branch … **Scientific impact: YES — this is the methodology change.** FPR/FDR/UER become genuine measurements (may be non-zero); the tautology is removed. **This commit changes reported results and MUST NOT be treated as neutral.** PRECONDITION (blocking): sign-off on the five rulings …"*

**This prompt** requires the same commit to be **strictly neutral**: benchmark parity, regression parity, existing tests green, and no modification to benchmarks/metrics/policy/evidence generation.

A commit cannot simultaneously (a) change the reported credit-card metrics (roadmap definition) and (b) preserve benchmark/regression parity (this prompt). The instruction set is internally inconsistent for this specific commit.

---

## 3. Factual grounding

1. **The reported arm is `gamma_map_raw`-authored and `Class`-derived.** `run_all.py`/`gamma_test_runner.py` read `GAMMA_G0_CREDITCARD_FULL_mapped.csv`, produced by `gamma_map_raw.py`, which authors the decision from the label (`is_fraud = Class==1` → SAFE_STATE; else PERMITTED). Current summary: **284,315 PERMIT / 492 SAFE_STATE**, FPR/FDR/UER = 0.
2. **The Class-blind pipeline yields the degenerate all-deny.** With no declared credit-card `ExecutionBinding` gate-set / SLA and C/D absent, `predicate_binding` fail-closes the full vector; the frozen engine returns SAFE_STATE for **every** row (verified by the 5.1-B tests). Reported arm would become ≈**284,807 SAFE_STATE / 0 PERMIT**.
3. **The regression parity gate compares `gamma_summary.json` to the frozen baseline** (normalizing only `input_file`) — `tests/test_regression_parity.py`. A flipped arm changes every metric in that file → the gate **fails**.
4. **Nothing in the reported path currently consumes the Class-blind components** (`predicate_binding` / `evidence_trace_builder` / `reported_artifact_emitter`) — confirmed by grep. Activation therefore genuinely requires wiring them into the reported path **and** retiring `gamma_map_raw`, which is the metric change.

---

## 4. Which prohibitions / verifications the flip would violate

| Prompt clause | Effect of the reported flip |
|---|---|
| *Do NOT modify metrics* | ❌ reported FPR/FDR/UER change (tautology → degenerate all-deny) |
| *Do NOT modify benchmarks* | ❌ `gamma_summary.json` / LAB benchmark output rewritten |
| *Do NOT modify evidence generation* | ❌ retiring `gamma_map_raw` replaces the reported generator |
| *Do NOT modify policy* | ❌ reporting the degenerate slice is the undeclared Gap-3 policy choice |
| VERIFY: *Benchmark parity* | ❌ fails against frozen baseline |
| VERIFY: *Regression parity* | ❌ `test_regression_parity` LAB gate fails |
| VERIFY: *Existing tests remain green* | ❌ the parity gate goes red |
| VERIFY: *No behavioural change* | ❌ the reported decision distribution changes wholesale |

Per the STOP CONDITION, each of these makes the flip impermissible here.

---

## 5. Missing governance acts (not engineering; still unprovided)

From `COMMIT_5_2_PRE_IMPLEMENTATION_REVIEW.md` (approved), unchanged and still outstanding:

1. **Signed, reviewed metric-change ruling + baseline rebaseline** — the roadmap's blocking precondition and Deployment Contract I-4. Rebaselining `gamma_summary.json` to the Class-blind result requires this signature; without it, changing the metric is forbidden and the parity gate cannot be legitimately updated.
2. **Declared credit-card deployment policy** — the Gap-3 slice choice (report the degenerate full-vector all-deny **or** a declared A-slice with an `ExecutionBinding` gate-set + risk-budget SLA) plus Deployment Contract §16 **C1–C6** confirmations. No gate-set/SLA is declared, so the only result activation can produce is the degenerate all-deny — a reportable methodology decision that must be signed, not defaulted.

"All prerequisite **engineering** work is frozen" is true and sufficient for the *pipeline*; it does **not** supply these **governance** acts, which are the actual gate on a *reported* flip.

---

## 6. What is neutral-and-possible now vs. what is blocked

- **Neutral and possible (not done here without scope confirmation):** a **flag-gated / parallel** end-to-end activation that wires Runtime Observation → EEB → Predicate Binding → 4.1 → frozen engine → Reported Artifact Emitter → Replay Manifest → Hydra Ledger as an **available, opt-in** runtime path, while the **reported** default remains `gamma_map_raw`. This preserves benchmark/regression parity and violates no prohibition — but it is **not** the roadmap's reported flip and does **not** "retire `gamma_map_raw`" (doing so would change the reported arm). It also does not, by itself, satisfy "the runtime path must *become*" the reported chain.
- **Blocked:** the reported flip + `gamma_map_raw` retirement (§2–§5) — prohibited here and ungoverned.

I have **not** implemented either, because (a) the reported flip is blocked, and (b) the neutral opt-in path only partially satisfies the commit and its scope (flag-gated vs. "become the path"; keep vs. "remove glue") must be confirmed by the owner rather than guessed.

---

## 7. Resolution options (owner to choose — I resolve none)

1. **Re-scope 5.2 to a neutral, parity-preserving end-to-end activation** (flag-gated/parallel; reported arm unchanged; `gamma_map_raw` retained). I can implement this immediately; it keeps every parity/verification requirement green. Explicitly defers the reported flip.
2. **Authorize the true reported flip** by supplying the two governance acts: the **signed metric-change ruling + rebaselined LAB baseline**, and the **declared credit-card deployment policy** (Gap-3 slice + C1–C6). Then the flip becomes implementable, with the parity gate re-pointed at the signed new baseline — but this **is** the non-neutral metric change and cannot be reconciled with this prompt's "no metric change / benchmark parity" clauses, which would need to be lifted.
3. **Split the commit:** land option 1 now (neutral activation), and schedule the reported flip as its own explicitly-non-neutral, signed commit once the governance acts exist.

---

## 8. What I did NOT do

I did **not** flip the reported generator, retire or edit `gamma_map_raw`, wire any Class-blind component into the reported path, rebaseline any fixture, modify `evaluate_decision`/Γ/Predicate Binding/serialization/replay/benchmarks/metrics/policy, or introduce any threshold/heuristic/Class-dependence/authorization logic. No file was modified; only this blocker document was added.

---

## 9. Scientific / neutrality status (of the halt)

Because nothing was implemented, all frozen components remain byte-identical and all reported artifacts unchanged: no scientific methodology, authorization, Γ, Predicate Binding, replay, benchmark, or metric changed. The halt is itself neutral.

---

# IMPLEMENTATION BLOCKED

**Single sentence:** Commit 5.2's roadmap meaning (flip the reported credit-card arm to the Class-blind pipeline, changing FPR/FDR/UER from the tautology to the degenerate all-deny) is **directly forbidden** by this prompt's "no metric/benchmark change + benchmark/regression parity" clauses and is **ungoverned** (no signed metric-change ruling, no declared deployment policy / C1–C6), so activation cannot proceed without either re-scoping to a neutral parallel wiring (option 1) or supplying the governance acts and lifting the parity clauses (option 2) — I implemented nothing and await the owner's resolution.

---

*Activation blocker only. No code, no modification, no flip, no rebaseline, no methodology change. The contradiction is grounded in the actual reported summary (284,315 PERMIT / 492 SAFE_STATE), the degenerate Class-blind result, and the regression parity gate. Awaiting owner resolution before any Commit 5.2 implementation. Experiments, the IEEE paper, and AgentDojo evaluation remain untouched, per the stop condition.*
