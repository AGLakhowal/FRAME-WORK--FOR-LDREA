# AUTHORIZATION-ENGINE CLASSIFICATION

**Objective:** classify each of the five authorization-computing sites (C-1…C-5) as an **engineering defect** or a **scientifically legitimate layer**, and recommend an action — so the scientific contribution is preserved while there is only **one implementation of Gamma**.
**Discipline:** not every duplicate is wrong. A computation that belongs to a *different scientific layer* (e.g. a broader governing policy) is legitimate and must be kept; a redundant or fabricated copy of the *same* semantics is a defect. No file modified; classification only.
**Roles:** IEEE Access Artifact-Evaluation Committee · Software-Verification Engineer · Runtime-Systems Auditor.

**Guiding distinction used throughout.** "Implementing Gamma" means computing the LAB authorization decision — non-compensatory `Γ = max_i d_i` over the **fixed node-predicate vector** (`NODE_GATE_COLS` + HARM/stale/telemetry + class veto) → PERMIT/SAFE_STATE. A site that applies the **same operator to a different or larger predicate set for a different scientific purpose** is a *separate layer*, not a duplicate engine. A site that re-computes the **same** decision over the **same** vector, or authors it by fiat, is a duplicate/defect.

---

## C-1 — `external_validation/agentdojo_adapter.py`

1. **Scientific purpose.** Purported "independent AgentDojo external validation." In reality it maps an action to a `sensitivity` heuristic and derives a decision from that.
2. **Is it implementing Gamma?** **NO.** `gamma_g = 1 if eea["sensitivity"]=="high" else 0` (:63) is a bespoke heuristic, unrelated to the node-predicate vector; it does not evaluate `NODE_GATE_COLS`, HARM, freshness, or the real class veto.
3. **Should it compute authorization?** **NO.** The genuine AgentDojo authorization path already exists and correctly reuses the frozen engine (`agentdojo_integration/interception/gamma_bridge.py:51`).
4. **Should it instead call the frozen engine?** **NO — it should not exist.** The correct external arm is `agentdojo_integration/`, which reads real environment state and calls `evaluate_decision`. C-1 is a parallel, non-frozen path with literal `0.0` metrics (`agentdojo_report.py:49-56`) surfaced as "independent validation."
5. **Would replacing it with the frozen engine alter the scientific contribution?** **NO** — it contributes nothing legitimate; removing it removes fabricated non-evidence. (Replacement is not even the right move; deletion/quarantine is.)
6. **Classification:** **A. Engineering defect** (a competing, fabricated engine live on the dashboard).

---

## C-2 — `stress_test.py` (`gamma_decision`)

1. **Scientific purpose.** Illustrate the non-compensatory principle on four narrative financial-services scenarios (deepfake CFO wire, sanctions drift, liquidity panic, sovereign cascade) using a **bespoke finance predicate vocabulary** (`amount_within_daily_limit`, `entity_sanctions_check`, `dual_control_satisfied`, …).
2. **Is it implementing Gamma?** **PARTIALLY.** It applies the *same operator* (`gamma = #failed in-scope; permit = gamma==0 and not class_veto`, :38-39) but over a **different predicate set** that does not exist in `NODE_GATE_COLS`.
3. **Should it compute authorization?** **YES** — the scenario demonstration is the point; showing a single deficit denies is its scientific content.
4. **Should it instead call the frozen engine?** **NO (directly).** `evaluate_decision` expects the fixed CSV row schema; the finance predicates don't map onto it without forcing an artificial encoding. The *operator* is shared in principle, but the *input vocabulary* is legitimately different.
5. **Would replacing it with the frozen engine alter the scientific contribution?** **NO** for the decision itself (the aggregation result would be identical), and the scenario narrative would be unchanged — but the replacement is awkward and unnecessary. The real defects here are the **authored** `confidence`/`tackled`/`verdict`/"78.4%" strings (a *separate* finding already logged), **not** the aggregation.
6. **Classification:** **C. Benchmark-specific computation** (same operator, bespoke scenario predicate set).

---

## C-3 — `full_spec_conformance.py` (`enforce`)

1. **Scientific purpose.** Evaluate the **FULL_SPEC §7.1 conjunctive acceptance bands** — a *broader governing policy* than LAB: node gates **∪ §7.1 bands** (ICS, PR_LCB, CI_WIDTH, ΔV, C-coherence, PTP, latency, ER) **∪ AIS weakest-link ∪ class veto**.
2. **Is it implementing Gamma?** **PARTIALLY.** It uses the identical non-compensatory operator (`gamma = node_deficit | band_deficit | ais_deficit | class_veto`, :145) but applied to a **superset** predicate vector. It is Gamma's *aggregation principle* applied at a **higher policy tier**.
3. **Should it compute authorization?** **YES** — the §7.1 conformance verdict is a distinct, intended scientific artifact (the runner itself labels §7.1 "the broader governing policy," `gamma_test_runner.py:1397`).
4. **Should it instead call the frozen engine?** **NO for the whole computation** (that would drop bands + AIS). **Conditionally YES for the shared subset:** the node-gate portion could be *sourced from* the frozen engine so the shared predicates cannot drift, with the band/AIS deficits added by the FULL_SPEC layer on top.
5. **Would replacing it with the frozen engine alter the scientific contribution?** **YES.** Replacing `enforce` with `evaluate_decision` would delete the §7.1 band and AIS conformance checks — a real loss. This layer must be **kept**.
6. **Classification:** **D. Separate policy layer** (FULL_SPEC §7.1 broader acceptance policy; same operator, higher tier).

---

## C-4 — `concurbench_full.py` `level1`

1. **Scientific purpose.** ConcurBench Level-1 correctness scoring over the full 284,807-row corpus.
2. **Is it implementing Gamma?** **YES — as an exact inline copy.** The deficit loop + `HARM_RISK>0.5` + `StaleContext` + `~TelemetryFresh` + class veto → `yhat_permit` (:118-124) is **numerically identical** to `evaluate_decision` at θ=0.5. Critically, **the same module already imports and uses `evaluate_decision`** (levels 2/3/ASB), so L1 is an *internally inconsistent* duplicate.
3. **Should it compute authorization?** **YES** (it must score the corpus) — **but not with a private copy.**
4. **Should it instead call the frozen engine?** **YES** — via the shared vectorized decision logic (the runner already vectorizes the identical rule at `gamma_test_runner.py:868-892`). L1 should draw from one source of truth, not re-type the rule.
5. **Would replacing it with the frozen engine alter the scientific contribution?** **NO** — the result is identical by construction; only the drift risk and the internal inconsistency are removed.
6. **Classification:** **A. Engineering defect** (redundant, unguarded duplicate of the same semantics). *(Its performance motive is legitimate, but the runner's shared vectorized path already satisfies it — so this is duplication, not a distinct benchmark computation.)*

---

## C-5 — `gamma_map_raw.py`

1. **Scientific purpose.** Generate the golden-trace CSV from the raw dataset.
2. **Is it implementing Gamma?** **NO — it *authors* the outcomes.** It writes `Gamma`, `SAFE_STATE`, `Status`, `ACT_PERMIT`, `ReasonCodes` directly from `is_fraud` (:150-181); no aggregation occurs. It manufactures the very columns the engine later "re-derives."
3. **Should it compute authorization?** **NO.** A trace generator must emit **observable evidence**, never the decision. Authoring the decision is the root of the tautology.
4. **Should it instead call the frozen engine?** The *generator* should not call the engine either — it should emit Class-blind evidence, and the **engine** (downstream) should compute the decision from that evidence. So: the decision-authoring branch must be removed and superseded by the Class-blind Transaction Interpreter (per the RCL/EEB plan).
5. **Would replacing it with the frozen engine alter the scientific contribution?** **NO legitimate contribution is lost** — the "detection" it appears to demonstrate was never real (tautology). Replacing authoring with engine-computed decisions over real evidence *restores* scientific validity rather than removing a contribution.
6. **Classification:** **A. Engineering defect** (label-driven decision authoring / leakage source).

---

## FINAL DECISION

| Site | Implements Gamma? | Classification | Action | Rationale (one line) |
|---|---|---|---|---|
| **C-1** `external_validation/agentdojo_adapter.py` | NO (heuristic) | **A. Engineering defect** | **DELETE** (quarantine + unwire `run_all.py:101`) | fabricated competing engine on the live dashboard; the real AgentDojo arm already reuses the frozen engine |
| **C-2** `stress_test.py` `gamma_decision` | PARTIALLY (same operator, bespoke vocab) | **C. Benchmark-specific computation** | **DOCUMENT** (keep; label the operator as the shared non-compensatory rule; relabel authored confidence/verdict separately) | legitimate scenario illustration; decision is the same operator on a finance predicate set that doesn't fit the fixed schema |
| **C-3** `full_spec_conformance.py` `enforce` | PARTIALLY (superset policy) | **D. Separate policy layer** | **DOCUMENT / KEEP** (mark as FULL_SPEC §7.1 broader policy; optionally source the shared node-gate deficits from the engine to prevent drift) | broader §7.1 acceptance policy; replacing it would delete real band/AIS conformance |
| **C-4** `concurbench_full.py` `level1` | YES (exact inline copy) | **A. Engineering defect** | **REFACTOR** (single source of truth: draw from the shared vectorized decision + add an equivalence cross-check test) | numerically identical duplicate; same file already reuses the engine elsewhere |
| **C-5** `gamma_map_raw.py` | NO (authors outcomes) | **A. Engineering defect** | **REPLACE** (supersede the label-authoring branch with the Class-blind evidence-only interpreter; let the engine decide) | tautology origin; a generator must emit evidence, not the decision |

**Summary of the eliminate-vs-preserve split:**
- **Must be eliminated / corrected (defects):** C-1 (DELETE), C-4 (REFACTOR to one source), C-5 (REPLACE with evidence-only generation). These are redundant, fabricated, or authoring paths that violate the single-Gamma claim without adding a distinct scientific layer.
- **Scientifically legitimate — preserve (not duplicates of the LAB engine):** C-2 (benchmark-specific scenario computation) and C-3 (FULL_SPEC §7.1 separate policy layer). Neither should be force-replaced with `evaluate_decision`; each is a different scientific layer that happens to share the non-compensatory *operator*.

**Net effect on the "one Gamma" goal.** After the three defect actions, the **LAB authorization decision** has a single implementation (the frozen `evaluate_decision` / its guarded vectorized twin), reused everywhere it is the LAB decision. C-2 and C-3 remain as *explicitly documented distinct layers* (a scenario harness and a broader §7.1 policy), not competing copies of the LAB engine — which satisfies both requirements: **one implementation of Gamma, and the full scientific contribution preserved.**

---

*Classification and recommended actions only. No code, no modification, no implementation. All citations are `file:line` from the current working tree.*
