# FINAL FORENSIC AUTHORIZATION AUDIT

**Objective:** certify whether the repository contains **exactly one** implementation of authorization semantics (L-DREA → Γ aggregation → SAFE_STATE/ACT_PERMIT), as the IEEE paper claims.
**Stance:** independent artifact-evaluation audit. Previous analyses are **not trusted**; every decision-computing site was re-verified by direct read + repository-wide grep. No file modified.
**Roles:** IEEE Access Artifact-Evaluation Committee · Software-Verification Engineer · Runtime-Systems Auditor · Static-Analysis Engineer · Security Code Auditor.

---

## 0. Verdict up front

> **CRITICAL QUESTION — "There exists exactly one implementation of authorization semantics in the repository."**
> **VERDICT: FALSE.**

The canonical frozen engine (`gamma_test_runner.evaluate_decision`) is genuinely reused by FCR, the AgentDojo interception, and **most** of ConcurBench. However, **four additional sites compute a PERMIT/SAFE_STATE (or Γ/π) authorization outcome WITHOUT calling the frozen engine**, and one further site **authors** authorization outputs directly from the label. The "single authorization engine" claim is therefore not currently true; §5 enumerates every competing path and §10 states what must be reconciled before implementation.

---

## 1. Method

- Repository-wide grep for every token that could compute or emit an authorization outcome: `gamma_g`, `gamma_class`, `pi`, `decision =`, `permit =`, `PERMIT`/`SAFE_STATE` literals, `def *decide/gamma/evaluate/enforce/level/asb`, non-compensatory aggregation, threshold comparisons.
- For every hit: determine whether it **calls the frozen `evaluate_decision`** (reuse), **re-derives the decision inline** (copy), **implements a separate rule** (independent engine), **authors the outcome** (fabrication), or merely **reads/verifies/displays** an already-computed value.
- Cross-checked which modules `import evaluate_decision` (the single ground truth of reuse).

**Reuse ground truth (who imports the frozen engine):** `fcr_test.py:36,63`; `concurbench_full.py:42` (used at :225,259,310,346,480); `agentdojo_integration/interception/gamma_bridge.py:19,51`; and the runner's own timed path `gamma_test_runner.py:1145`. **Does NOT import it:** `full_spec_conformance.py`, `stress_test.py`, `external_validation/*`, `gamma_map_raw.py`.

---

## 2. The canonical (frozen) authorization engine

| Location | Symbol | Role |
|---|---|---|
| `gamma_test_runner.py:133-178` | `evaluate_decision` | **PRIMARY AUTHORIZATION ENGINE** (single-row): deficit loop over `NODE_GATE_COLS` + `HARM_RISK>θ` + stale/telemetry, `gamma_class` from `ReasonCodes`, `pi = 1[deficit=0 ∧ gamma_class=0]`, `decision = PERMIT|SAFE_STATE` |
| `gamma_test_runner.py:868-892` | vectorized block in `main` | **PRIMARY AUTHORIZATION ENGINE** (vectorized): the same rule over the full DataFrame (`DerivedGammaG`, `DerivedGammaClass`, `DerivedPi`, `DerivedDecision`) |

**Intra-engine nuance (not a competing engine, but a duplication):** the engine exists in **two code representations** — single-row (:133) and vectorized (:868-892). The runner explicitly cross-checks their agreement (`measured_latency.timed_path_agreement = 50000` in `gamma_summary.json`; docstring :136 "Mirrors the vectorized Law-of-Concurrence logic exactly"). This is **one engine with a self-consistency guard**, but it is a maintenance hazard: the two copies could drift; only the timed sample (≤50k rows) is cross-verified. Classified: **PRIMARY ENGINE (duplicated representation, guarded).**

---

## 3. Sites that correctly REUSE the frozen engine (safe)

| File | Function | Lines | Evidence of reuse | Classification |
|---|---|---|---|---|
| `fcr_test.py` | `_fc_block` | :63 | `evaluate_decision(inst, 0.5)["decision"]` | **SUPPORTING (reuse)** |
| `concurbench_full.py` | `level2` (adaptive/contam) | :225, :259, :310 | `evaluate_decision(...)` | **BENCHMARK (reuse)** |
| `concurbench_full.py` | `level3` (canonical baseline) | :346 | `evaluate_decision(row_dict(r),0.5)` | **BENCHMARK (reuse)** |
| `concurbench_full.py` | `asb` | :480 | `evaluate_decision(b,0.5)` | **BENCHMARK (reuse)** |
| `agentdojo_integration/interception/gamma_bridge.py` | `GammaBridge.decide` | :51 | `return evaluate_decision(row, harm_threshold)` | **SUPPORTING (reuse)** |
| `agentdojo_integration/interception/predicate_evaluation.py` | `PredicateEvaluator.evaluate` | :120 | computes **deficits only**; decision delegated to the bridge → frozen engine | **SUPPORTING (no decision)** |
| `agentdojo_integration/interception/governed_runtime.py` | `run_function` | :50-80 | reads `result["decision"]` from the bridge; the one non-reuse literal (`"decision":"SAFE_STATE"` at :58) is the **fail-closed default for an unknown tool**, not an aggregation | **SUPPORTING (reuse + fail-closed default)** |
| `gamma_replay_verify.py` | `main` | :103 | `expect_permit = (gg==0 and gc==0)` — **re-checks** recorded π/Γ for self-consistency; issues no authorization | **REPLAY ONLY** |

The `governed_runtime.py:58` unknown-tool `SAFE_STATE` is the frozen fail-closed policy (FULL_SPEC 2.3/0.10), not a competing decision rule — it denies without aggregating, which is the specified default. Acceptable.

---

## 4. Class-leakage, hardcoded-policy, and synthetic re-checks (independent of the engine question)

**Class / label used before evaluation:**
- `gamma_map_raw.py:123` `is_fraud = (Class==1)` → authors gates/HARM/Status/ReasonCodes (:150-181). **Leakage confirmed** (label consumed during generation).
- `fcr_test.py:83`, `concurbench_full.py` (`gt_deny` from `ReasonCodes` "CLASS_1"), `full_spec_conformance.py` (`gt_deny`), `gamma_test_runner.py:954` (`truth_permit` from `Status`) — all use the label token as **ground truth at the scoring stage** (legitimate) **but** the token itself (`CLASS_1` in `ReasonCodes`, `Status`) was authored from `Class` upstream, so ground truth and prediction share the label origin. **Consistent with the tautology finding**; not a *new* engine issue.

**Hardcoded policy constants (thresholds/limits):** `gamma_test_runner.py:1011` `tau=0.15`; `:218/harm-threshold default 0.5`; `full_spec_conformance.py:126` `ptp_skew=1.0`, `:318` `40192`; `concurbench_full.py` `>0.5`, seeds; `stress_test.py` authored strings; `external_validation/agentdojo_report.py:49-56` literal `0.0` metrics. These are policy/attestation constants (tracked in the prior hardcode register); relevant here only where they live **inside a competing engine** (§5).

**Synthetic / placeholder / competing markers:** `external_validation/*` self-describes as an "external validation harness" with a "conservative Gamma-style mapping" (`agentdojo_adapter.py:28`) — an explicit **separate** decision path. No `TODO`/`FIXME`/`mock` authorization stubs found elsewhere.

---

## 5. COMPETING AUTHORIZATION IMPLEMENTATIONS (the finding)

Each site below produces an authorization outcome (PERMIT/SAFE_STATE, or Γ/π) **without** the frozen engine. Ordered by severity.

### C-1 — `external_validation/agentdojo_adapter.py` — INDEPENDENT ENGINE (live, fabricated)
- **Function/lines:** `build_eea` :16-56 (`decision = "SAFE_STATE" if sensitivity=="high" else "PERMIT"`, :30); `evaluate_action` :58-70 (`gamma_g = 1 if eea["sensitivity"]=="high" else 0`, :63; `gamma_class` :64; `pi` :65; `decision` :66).
- **Purpose:** score AgentDojo actions for the "external validation" dashboard section.
- **Scientific role:** NONE legitimate — it invents a heuristic `sensitivity→gamma_g` rule unrelated to the predicate vector. **Engineering role:** produces `external_validation/agentdojo_report.json`, wired into the suite at `run_all.py:101`.
- **Classification: COMPETING AUTHORIZATION PATH (independent engine).**
- **Why scientifically dangerous:** it emits `decision`/`gamma_g`/`gamma_class`/`policy:"gamma_g0"` that *look* like Gamma outputs but are computed by a different rule, and surfaces them on the live dashboard as "independent validation." A reviewer cannot distinguish these from frozen-engine results. This is the single most dangerous path: **non-Gamma decisions presented as Gamma.**

### C-2 — `stress_test.py` — INDEPENDENT ENGINE (financial scenarios)
- **Function/lines:** `gamma_decision` :34-45 (`gamma = len(failed)`; `permit = (gamma==0) and not class_veto`; `decision = "PERMIT" if permit else "SAFE_STATE"`).
- **Purpose:** evaluate the four financial stress scenarios.
- **Scientific role:** re-implements non-compensatory aggregation for authored predicates. **Engineering role:** produces `stress_test_report.json`, dashboarded via `run_all.py:97`.
- **Classification: COMPETING AUTHORIZATION PATH (independent engine).**
- **Why dangerous:** a *second* non-compensatory Γ implementation. It happens to mirror the frozen rule, but it is a separate copy that can drift; the stress "fail-closed" verdicts and the (authored) "78.4%" are attributed to "non-compensatory Gamma" while never touching the certified engine.

### C-3 — `full_spec_conformance.py` — DIVERGENT ENGINE (extended aggregation)
- **Function/lines:** `enforce` :90-200 (`gamma = node_deficit | band_deficit | ais_deficit | class_veto` :145; `permit = ~gamma` :146; false-permit/denial vs `gt_permit` :196).
- **Purpose:** FULL_SPEC §7.1 conjunctive-band conformance.
- **Scientific role:** computes a **superset** aggregation — node gates **∪ §7.1 bands ∪ AIS ∪ class-veto** — which is broader than the frozen engine's node-gate rule. **Engineering role:** `full_spec_conformance_report.json`, dashboarded via `run_all.py:110`.
- **Classification: COMPETING AUTHORIZATION PATH (divergent/independent).**
- **Why dangerous:** it does not import or call `evaluate_decision`; its `permit` for a given row can differ from the frozen engine's because it adds band/AIS deficits. It may be *intentionally* broader (FULL_SPEC is a wider policy than LAB), but that is precisely a **second, different implementation of authorization semantics** — the "exactly one" claim cannot hold while a divergent aggregator ships as a headline conformance result.

### C-4 — `concurbench_full.py` `level1` — INLINE COPY (internal inconsistency)
- **Function/lines:** `level1` :114-124 (`deficit |= ~df[g]` loop :118-122; `gamma_class` :123; `yhat_permit = (~deficit) & (~gamma_class)` :124).
- **Purpose:** ConcurBench Level-1 scoring over the full corpus.
- **Scientific role:** re-derives the decision **inline** even though the *same module* imports and uses `evaluate_decision` elsewhere (levels 2/3/ASB). **Engineering role:** `concurbench_full_report.json` L1 metrics ("0 false permits").
- **Classification: COMPETING AUTHORIZATION PATH (re-derivation copy).**
- **Why dangerous:** internal inconsistency within one file — L1's headline numbers come from a hand-copied rule, not the engine the rest of the file trusts. If the copy and `evaluate_decision` diverge, L1 silently reports a different engine's result. (Vectorization for performance is a legitimate motive, but it is still a second implementation and must be acknowledged.)

### C-5 — `gamma_map_raw.py` — DECISION AUTHORING (fabrication, not aggregation)
- **Function/lines:** `main` :150-181 (`Gamma=1`, `SAFE_STATE=True`, `Status="SAFE_STATE"`, `ACT_PERMIT=...`, `ReasonCodes=...` set directly from `is_fraud`).
- **Purpose:** generate the golden-trace CSV.
- **Scientific role:** it does **not aggregate predicates**; it **writes the authorization outputs** the engine will later "re-derive." **Engineering role:** produces `GAMMA_G0_CREDITCARD_FULL_mapped.csv`.
- **Classification: COMPETING AUTHORIZATION PATH (degenerate — authors outcomes).**
- **Why dangerous:** it is the tautology's origin (already verified). As an *authorization-semantics* site it is the most degenerate form: the decision is decided by the label author, then the frozen engine merely reconstructs it.

---

## 6. Consolidated authorization-site map

| # | File · function · lines | Computes a decision? | Uses frozen engine? | Classification |
|---|---|---|---|---|
| — | `gamma_test_runner.py:133` `evaluate_decision` | yes | **is the engine** | **PRIMARY ENGINE** |
| — | `gamma_test_runner.py:868-892` vectorized | yes | is the engine (2nd representation) | **PRIMARY ENGINE (guarded duplicate)** |
| ok | `fcr_test.py:63` | yes | **yes** | SUPPORTING (reuse) |
| ok | `concurbench_full.py:225,259,310,346,480` | yes | **yes** | BENCHMARK (reuse) |
| ok | `agentdojo_integration/.../gamma_bridge.py:51` | yes | **yes** | SUPPORTING (reuse) |
| ok | `agentdojo_integration/.../governed_runtime.py:58` | fail-closed default only | n/a (no aggregation) | SUPPORTING (policy default) |
| ok | `gamma_replay_verify.py:103` | re-checks only | n/a | REPLAY ONLY |
| **C-1** | `external_validation/agentdojo_adapter.py:30,58-70` | yes | **NO** | **COMPETING (independent, live, fabricated)** |
| **C-2** | `stress_test.py:34-45` `gamma_decision` | yes | **NO** | **COMPETING (independent)** |
| **C-3** | `full_spec_conformance.py:145-146` `enforce` | yes | **NO** | **COMPETING (divergent/superset)** |
| **C-4** | `concurbench_full.py:114-124` `level1` | yes | **NO** (inline copy) | **COMPETING (re-derivation copy)** |
| **C-5** | `gamma_map_raw.py:150-181` | authors outcome | **NO** | **COMPETING (degenerate/fabrication)** |

**Count:** 1 primary engine (2 guarded representations) + 4 reuse sites + **5 non-reuse authorization sites** (C-1…C-5). The paper's "single authorization mechanism" is contradicted by C-1…C-5.

---

## 7. Special-attention check — Γ/gamma_g/SAFE_STATE/PERMIT computed outside the frozen engine?

**Yes — five places (C-1…C-5).** Specifically, `gamma_g` is computed outside the frozen engine at `external_validation/agentdojo_adapter.py:63`; a non-compensatory `gamma`/`permit` at `stress_test.py:38-39`, `full_spec_conformance.py:145-146`, and `concurbench_full.py:117-124`; and `Gamma`/`SAFE_STATE`/`Status` are authored at `gamma_map_raw.py:154-161`. Only FCR, AgentDojo, ConcurBench L2/L3/ASB, and the runner's timed path route through `evaluate_decision`.

---

## 8. Severity assessment

| Path | Ships to dashboard? | Presents as Gamma? | Drift risk vs frozen engine | Severity |
|---|---|---|---|---|
| C-1 external_validation | **Yes** (`run_all.py:101`) | **Yes** (`policy:"gamma_g0"`) | total (unrelated rule) | **CRITICAL** |
| C-5 gamma_map_raw authoring | Yes (feeds every LAB number) | it *is* the input | n/a (tautology) | **CRITICAL** |
| C-3 full_spec enforce | Yes (`run_all.py:110`) | Yes (conformance headline) | divergent by design (superset) | **HIGH** |
| C-2 stress_test | Yes (`run_all.py:97`) | Yes ("non-compensatory Gamma") | copy may drift | **HIGH** |
| C-4 concurbench L1 | Yes (L1 headline) | Yes | copy may drift; file self-inconsistent | **MEDIUM-HIGH** |

---

## 9. Answer to the critical question

**"There exists exactly one implementation of authorization semantics in the repository." → FALSE.**

There is one *canonical* engine (`evaluate_decision`, in two guarded representations), correctly reused by FCR, AgentDojo, and ConcurBench L2/L3/ASB. But **five sites (C-1…C-5) compute or author an authorization outcome without it**, of which two are CRITICAL (a live fabricated harness presenting non-Gamma decisions as Gamma; and the label-authoring mapper), one is a divergent superset aggregator shipped as conformance, one is an independent finance engine, and one is an inline copy that makes ConcurBench internally inconsistent. Each is scientifically dangerous for the reason stated in §5: a reader/reviewer cannot tell which "Gamma" decision was produced by the certified engine and which by a parallel rule, and any divergence between a copy and the frozen engine silently invalidates the affected headline.

---

## 10. Implementation readiness

**Can S1 (create the immutable EEB data-contract file) begin immediately?**
- **Narrowly, yes:** S1 adds a new, unconsumed data-contract module with **no decision logic and no consumer**; it cannot create or worsen a competing engine and is isolated from C-1…C-5.
- **But the audit's certification goal is NOT met:** the repository does **not** currently contain exactly one authorization engine, so the precondition the paper asserts is false. Therefore **implementation that wires the RCL/EEB into any decision path (S6/S8 of the traceability plan) must NOT begin** until the competing paths are reconciled.

**Required cleanup before full implementation (identified only — not performed):**
1. **C-1 (CRITICAL):** quarantine `external_validation/` and unwire `run_all.py:101` — it is a live, independent, fabricated engine on the dashboard.
2. **C-5 (CRITICAL):** the `gamma_map_raw.py` label-authoring branch must be superseded by the Class-blind Transaction Interpreter (per the traceability plan) — it authors the decisions the engine "re-derives."
3. **C-3 (HIGH):** rule on whether `full_spec_conformance.enforce` should (a) route its node-gate portion through `evaluate_decision` and clearly label the band/AIS extension as a *separate* policy layer, or (b) be explicitly documented as a distinct, broader aggregator — so it is not read as "the" Gamma engine.
4. **C-2 (HIGH):** rule on whether `stress_test.gamma_decision` should call the frozen engine or be explicitly labeled a scenario-illustration using a mirrored rule.
5. **C-4 (MEDIUM-HIGH):** reconcile `concurbench_full.level1`'s inline copy with the `evaluate_decision` the same module already imports (route L1 through the engine, or document the vectorized copy as engine-equivalent with a cross-check test).
6. **Guardrail for new work:** the RCL/EEB must call the frozen `evaluate_decision`; a review/lint rule should forbid any new module from computing `gamma_g`/`permit`/`SAFE_STATE` locally (the exact defect C-1 and C-2 embody).

Items 3–5 include **scientific/policy decisions** (whether a divergent aggregator is intended), so they must be ruled by their owners; items 1, 2, 6 are engineering/hygiene. **None performed here.**

---

## Certification statement

The repository **cannot** be certified as containing exactly one authorization engine at this time. One canonical engine exists and is correctly reused by three subsystems, but five non-reuse authorization sites (C-1…C-5) violate the single-mechanism claim, two of them CRITICAL and live on the dashboard. S1 may proceed as isolated engineering, but no RCL/EEB decision-path wiring should begin until at least the two CRITICAL paths (C-1, C-5) are quarantined/superseded and the three HIGH/MEDIUM divergences (C-2, C-3, C-4) are explicitly ruled as either "route through the frozen engine" or "documented separate computation." No file was modified, fixed, refactored, or redesigned in producing this audit.

---

*Forensic audit only. No code written, no file modified, no fix, no refactor, no redesign. All citations are `file:line` from the current working tree.*
