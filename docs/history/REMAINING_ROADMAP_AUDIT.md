# REMAINING ROADMAP AUDIT (after Commit 5.1)

**Planning audit only. No code, no implementation, no file modification.** Audits every `ENGINEERING_MIGRATION_ROADMAP.md` commit remaining after the (narrowed) Commit 5.1, classifies each, surfaces hidden dependencies, and proposes the fastest safe completion order.

**Roles:** Lead Runtime-Systems Architect · Repository-Migration Engineer · IEEE Artifact Engineer · Software-Verification Engineer.

**Completed to date:** 0.1, 0.2, 1.1, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 4.1, **5.1 (narrowed transport subset)**.

---

## 0. Headline finding — the narrowing of 5.1 opened a REQUIRED gap before 5.2

Commit 5.1 was approved as the **transport subset only** (evidence-only EEB trace; no predicate binding). But roadmap **5.2** says "flip the default to the Class-blind pipeline **(5.1)** as the reported credit-card arm" and its test requires "replay determinism on the **new trace** … Class-blindness **end-to-end**." A pipeline that *reports decisions* needs the evidence trace **converted into engine inputs** — the credit-card **Predicate Generator / binding** (S6/S8). That binding is exactly what 5.1's narrowing **deferred**, and it is **gated** on the five scientific rulings. Therefore a **new commit must exist between 5.1 and 5.2** — call it **5.1-B (credit-card predicate binding)** — and it is **Category C (scientific)**. 5.2 cannot proceed without it. This is the same hidden-assumption class discovered inside 5.1, now made explicit at the roadmap level.

---

## 1. Remaining roadmap table

| # | Title | Category | Blocked? | Runs relative to gate |
|---|---|---|---|---|
| **5.1-B** *(inserted)* | credit-card predicate binding (evidence→predicates; S6/S8) | **C** Scientific | **YES** — 5 rulings | pre-5.2 (prerequisite) |
| **5.2** | activate Class-blind pipeline; retire `gamma_map_raw` label authoring ⚠️ **GATED** | **C** Scientific | **YES** — 5 rulings + 5.1-B | the gate |
| **6.1** | docs(stress): label `stress_test` as scenario layer (C-2) | **A** Pure Eng | No | pre-gate (now) |
| **6.2** | docs(fullspec): label `enforce()` as §7.1 policy layer (C-3) | **A** Pure Eng | No | pre-gate (now) |
| **6.3** | test(regression): LAB/ConcurBench/AgentDojo/replay parity gates | **A** Pure Eng | No (design caveats) | pre-gate now; **re-baseline post-5.2** |
| **6.4** | ci: promote single-engine guardrail warn→enforce | **A** Pure Eng | **Partial** — full form needs 5.2 | reduced now / full post-5.2 |
| **6.5** | chore(artifacts): regenerate dashboard/reports | **A** Pure Eng | No | pre-gate now; **re-run post-5.2** |

**Category tally:** A = 6.1, 6.2, 6.3, 6.5 (+ 6.4 reduced). C = 5.1-B, 5.2 (+ 6.4-full, 6.3-rebaseline, 6.5-rerun are post-gate engineering). **No Category B** (no commit is unblockable-by-a-single-clarification other than the gated set, which needs the full ruling package).

---

## 2. Per-commit detail

### 5.1-B (inserted) — credit-card predicate binding (evidence → predicates)
- **Purpose:** map the 5.1 evidence trace into the engine's decision schema (`NODE_GATE_COLS` booleans, `HARM_RISK`, thresholded `StaleContext`/`TelemetryFresh`, veto) so the frozen engine computes real Class-blind decisions via 4.1.
- **Dependencies:** 5.1 (trace), 4.1 (EEB→engine adapter), the 5 rulings.
- **Blockers (hidden dependencies):** amount-limit `L_amt`; velocity/ordering envelope; freshness θ; **HARM_RISK proxy admissibility**; gate→plane binding; class-veto plane; global-vs-per-subject windows. All in `IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10` / EEB spec §10.
- **Impl effort:** **High.** **Review effort:** **High (scientific sign-off).** **Time:** blocked; ~2–4 sessions of engineering *after* rulings.

### 5.2 — activate Class-blind pipeline; retire `gamma_map_raw` label authoring ⚠️ GATED
- **Purpose:** flip the reported credit-card arm to the Class-blind pipeline; archive the label-authoring branch (`gamma_map_raw.py:150-181`). Makes FPR/FDR/UER genuine measurements.
- **Dependencies:** 5.1-B, the 5 rulings, sign-off on the *expected* metric change (a deliberate, reviewed diff).
- **Blockers:** all of 5.1-B's, plus explicit owner acceptance that reported numbers change (non-neutral by design).
- **Impl effort:** **High.** **Review effort:** **High (scientific).** **Time:** blocked; ~1–2 sessions after 5.1-B.

### 6.1 — docs(stress): label `stress_test` as scenario-illustration layer (C-2)
- **Purpose:** report metadata/notes marking `stress_test` as an illustrative non-compensatory scenario layer; flag authored `confidence/tackled/verdict` as author-assessed.
- **Dependencies:** none scientific — the C-2 classification is **already decided** (registry: `BENCHMARK_SCENARIO_LAYER / LEGITIMATE_LAYER`).
- **Blockers:** none. No logic touched.
- **Impl effort:** **Low.** **Review effort:** **Low.** **Time:** ~minutes / 1 short turn.

### 6.2 — docs(fullspec): label `enforce()` as §7.1 separate policy layer (C-3)
- **Purpose:** annotate `full_spec_conformance` output as the broader §7.1 policy layer (node ∪ bands ∪ AIS ∪ class-veto), distinct from the LAB engine.
- **Dependencies:** none — C-3 already decided (registry: `SEPARATE_POLICY_LAYER / LEGITIMATE_LAYER`).
- **Blockers:** none. No aggregation change.
- **Impl effort:** **Low.** **Review effort:** **Low.** **Time:** ~minutes / 1 short turn.

### 6.3 — test(regression): LAB/ConcurBench/AgentDojo/replay parity gates
- **Purpose:** promote the 0.1 fixtures into enforced parity gates (LAB summary, ConcurBench, FCR, FULL_SPEC, replay SHA + verifier exit code; run AgentDojo interception test in CI).
- **Dependencies:** the 0.1 baseline fixtures (present).
- **Blockers (engineering, flagged — not scientific):** **(a) LAB timing noise** — `gamma_lab_v1_report.json` has run-varying `measured_latency/*` fields (proven in 4.1: two OFF runs differ only there); the LAB gate must key on `gamma_summary.json` (byte-stable) + replay SHA, and **exclude/normalize** the latency block, not naively byte-diff the LAB report. **(b) AgentDojo env dependency** — the interception test needs the external `agentdojo` package, absent in this environment (it errored in 4.1 verification); the gate must skip-with-notice when the package is unavailable, or CI must install it.
- **Impl effort:** **Med.** **Review effort:** **Med.** **Time:** ~1 session.
- **Post-5.2 note:** the LAB baseline is intentionally **re-baselined with sign-off** after 5.2 (a second, gated pass).

### 6.4 — ci: promote single-engine guardrail warn→enforce
- **Purpose:** flip the 0.2 guardrail to blocking, allowlisting only the documented C-2/C-3 layers.
- **Dependencies / hidden sequencing:** the roadmap says "now that **C-1/C-4/C-5** are handled." C-1 ✓ (1.1), C-4 ✓ (3.1), **C-5 ✗ — resolved only by 5.2** (archives `gamma_map_raw`). Current live findings: `gamma_map_raw.py:161` (C-5, pending 5.2) and `concurbench_full.py:358` (benign **L3-sim** SAFE_STATE label — **not** C-2/C-3; needs an allowlist entry) whose **registry status is stale** (`PENDING_REFACTOR_COMMIT_3_1`, though 3.1 is done — the outstanding 3.1-review R2 item).
- **Blockers:** full "block-all-except-C2/C3" enforce requires **5.2** (removes C-5) **and** a registry update allowlisting `concurbench:358` + refreshing the concurbench status.
- **Two forms:** **reduced** ("block **UNREGISTERED** only" — already 0 unregistered) is **Batch-1-safe now**; **full** (roadmap intent) is **post-5.2**.
- **Impl effort:** **Low.** **Review effort:** **Med** (must not falsely block). **Time:** ~1 short turn (reduced) / ~1 turn post-5.2 (full).

### 6.5 — chore(artifacts): regenerate dashboard/reports from the active pipeline
- **Purpose:** regenerate `gamma_report.html` + reports so displayed artifacts match the active pipeline; ensure every displayed value traces to a report field.
- **Dependencies:** the active pipeline (pre-5.2 = current; post-5.2 = Class-blind).
- **Blockers (engineering, flagged):** the **display-literal audit** — some dashboard values may be hardcoded in HTML rather than traced to report fields (the display-literal findings); 6.5 must make each displayed value trace to a source field. Regeneration itself is neutral.
- **Impl effort:** **Med.** **Review effort:** **Med.** **Time:** ~1 session.
- **Post-5.2 note:** re-run to reflect Class-blind results.

---

## 3. Hidden dependency analysis (the 5.1-class assumptions)

| Hidden dependency | Where it bites | Kind | Status |
|---|---|---|---|
| **Predicate binding** (evidence→gate booleans) | 5.1-B, 5.2 | Scientific | **Gated** (5 rulings) |
| **Threshold/limit selection** (`L_amt`, freshness θ, HARM θ) | 5.1-B, 5.2 | Scientific | **Gated** |
| **HARM_RISK proxy** admissibility (V1..V28 as plane-D?) | 5.1-B, 5.2 | Scientific | **Gated** (traceability §10.4 flags inadmissible w/o disclosed rationale) |
| **Gate→plane binding** + class-veto plane | 5.1-B, 5.2 | Scientific | **Gated** |
| **Global-vs-per-subject windows** | 5.1-B, 5.2 | Scientific | **Gated** |
| **Actuation timing** (Eq.7 `Actuated`/`ACT_PERMIT` semantics) | 5.2 | Scientific | **Gated** |
| **LAB replay/report timing noise** (latency fields non-deterministic) | 6.3 | Engineering | Design it out (gate `gamma_summary` + replay SHA; exclude latency) |
| **AgentDojo env dependency** (external package) | 6.3 | Engineering/Env | Skip-with-notice or CI-install |
| **C-5 still live** until archived | 6.4 (full) | Engineering-sequencing | Resolved by 5.2 |
| **`concurbench:358` benign literal** + stale registry status | 6.4 | Engineering | Allowlist + registry refresh (R2 from 3.1 review) |
| **Display-literal artifacts** (untraced dashboard values) | 6.5 | Engineering | Audit + trace to report fields |

**None of the 6.x engineering caveats is scientific** — all are resolvable now with engineering judgment. The only **scientific** blockers are the five rulings, which gate 5.1-B and 5.2.

---

## 4. Recommended batching strategy (minimize repeated review)

### Batch 1 — Pure engineering, pre-gate (do now, one review pass)
- **6.1** docs C-2 → **6.2** docs C-3 → **6.3** parity gates (timing-safe, AgentDojo-optional) → **6.5** regenerate current artifacts + display-literal audit.
- Order matters: 6.1/6.2 (label the legitimate layers) **before** 6.4, and 6.3 (freeze parity) **before** 6.5 (regen) so regen is gated.
- Optional add: **6.4-reduced** ("block UNREGISTERED only") — safe now (0 unregistered), non-blocking to the pending C-5/L3 items.
- **All Category A; no scientific dependency; ~1–1.5 sessions total; single consolidated review.**

### ═══ GATED BOUNDARY — requires the five owner rulings ═══

### Batch 2 — Scientific (blocked until sign-off)
- **5.1-B** credit-card predicate binding (build to the ruled spec) → **5.2** flip default + retire `gamma_map_raw` (reviewed, signed metric diff).
- **Category C; High effort + High (scientific) review; cannot start until rulings land.**

### Batch 3 — Post-gate engineering (after 5.2, one review pass)
- **6.4-full** guardrail enforce (C-5 now archived; allowlist C-2/C-3 + `concurbench:358`) → **6.3-rebaseline** LAB fixtures (signed) → **6.5-rerun** Class-blind artifacts.
- **Category A engineering, but only meaningful post-5.2; ~1 session; single review.**

---

## 5. Estimated remaining ENGINEERING effort

| Bucket | Commits | Effort | Time (notional) |
|---|---|---|---|
| Batch 1 (pre-gate) | 6.1, 6.2, 6.3, 6.5 (+6.4-reduced) | Low–Med | ~1–1.5 sessions |
| Batch 3 (post-gate) | 6.4-full, 6.3-rebaseline, 6.5-rerun | Low–Med | ~1 session |
| Binding engineering (post-rulings) | 5.1-B build, 5.2 wiring | Med–High | ~3–5 sessions |

**Total pure-engineering that is unblockable now: ~1–1.5 sessions** (Batch 1). Everything else is either post-gate or post-ruling.

## 6. Estimated remaining SCIENTIFIC effort

The **critical path is not engineering — it is the five owner rulings** (`IMPLEMENTATION_TRACEABILITY_SPECIFICATION.md §10`): actuation timing; class-veto plane; gate→plane binding; **HARM_RISK proxy + Class-blind θ/limit rationale**; global-vs-per-subject windows. These require **governance/science owner decisions**, not engineering time. Until they land, 5.1-B and 5.2 (and the post-5.2 re-baselines) cannot proceed. **Scientific effort = owner deliberation + a written, disclosed rationale for each ruling; no code can substitute.**

## 7. Recommendation — fastest safe completion

1. **Now:** execute **Batch 1** (6.1, 6.2, 6.3, 6.5, optionally 6.4-reduced) under fast-track — it drains *all* pre-gate pure-engineering work, hardens the current pipeline (parity gates, clean traced artifacts, labeled layers, unregistered-blocking guardrail), and needs one review.
2. **In parallel (non-engineering):** escalate the **five §10 rulings** to their owners — this is the true bottleneck and gates everything scientific. Provide them this audit + the traceability §10 list.
3. **After sign-off:** implement **Batch 2** (5.1-B predicate binding → 5.2 flip) with scientific review of the deliberate metric change.
4. **After 5.2:** implement **Batch 3** (6.4-full enforce, 6.3 LAB re-baseline, 6.5 Class-blind regen).

**Bottom line:** ~1–1.5 sessions of engineering can complete *everything that is safe to complete now* (Batch 1). The migration then **halts at the gated boundary** — not for engineering reasons, but pending the five scientific rulings, which are the sole critical path to finishing the roadmap. Do **not** implement 5.1-B or 5.2 until those rulings are signed; doing so would repeat the exact hidden-assumption failure that Commit 5.1 correctly stopped on.

---

*Planning audit only. No code written, no file modified, no commit implemented. Classifications and effort are engineering estimates; the five scientific rulings remain owner decisions. Awaiting your direction on Batch 1 and on escalating the rulings.*
