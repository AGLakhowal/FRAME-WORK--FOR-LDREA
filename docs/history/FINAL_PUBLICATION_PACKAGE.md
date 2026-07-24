# Final Publication Package — Experimental Evidence

**Date:** 2026-07-09. All campaigns executed on genuine data; no fabricated/estimated/simulated
values; no frozen component modified (19 frozen files SHA256-verified unchanged).

## 1. Campaigns executed this session

| Campaign | What ran | Primary output |
|---|---|---|
| A — Larger AgentDojo corpus | 33 episodes, 4 suites, `llama3.1:8b` via Ollama; 14 Gamma decisions (11 PERMIT, 3 SAFE_STATE) | `agentdojo_integration/audit_run/summary/statistics.json` |
| B — FPR/FDR independent labeling | attacker targets from injection GOALs vs benign recognized-set | `.../summary/fpr_fdr/fpr_fdr.{json,md}` |
| C — Concurrency scaling | 1/2/4/8/16/32 threads × 200k frozen decisions | `.../summary/concurrency/concurrency_scaling.{json,csv,md,svg}` |
| D — Runtime Context + Replay profiling | timer-wrapped frozen RCL + replay emitter | `.../summary/runtime_profile/runtime_profile.{json,md}` |

## 2. New code (additive; Phase-2 framework untouched except my own driver gaining `--episodes`)

- `agentdojo_integration/audit/concurrency_scaling.py`
- `agentdojo_integration/audit/runtime_profile.py`
- `agentdojo_integration/audit/fpr_fdr_labeling.py`
- (extended, additive) `agentdojo_integration/audit/batch_runner.py`, `run_audit.py` — `--episodes` selector

## 3. Populated tables

- **Table 10 — Combined Ablation:** COMPLETE. 5/5 ablation (VALIDATION_RESULTS.json 9_ablation) +
  7/7 per-component latency; Runtime Context 0.0106 ms/row and Replay 0.0150 ms/row now measured (D).
- **Table 11 — AgentDojo Evaluation:** READY. 33 episodes; 14 decisions; permit 0.786 [0.524,0.924];
  overhead 0.0216 ms; replay 33/33; entropy 0.750; stability 0.967; frozen unchanged; FPR undefined
  (n=0, honest); FDR 0.000 [0,0.434].
- **Table 13 — Concurrency Scaling:** COMPLETE. 6 thread levels × 14 measured columns; correctness /
  ledger / replay consistent, 0 FP / 0 FD at every level (throughput GIL-bound, reported honestly).

Full provenance in `IEEE_TABLES_FINAL.md`. Reviewer matrix in `REVIEWER_CLOSURE_REPORT.md`.

## 4. Regenerated figures / reports (over the 33-episode corpus)

- Figures (SVG + CSV): `.../summary/figures/fig1..6` (Γ, Π, predicate, tool authorization, latency,
  policy utilization) + concurrency SVGs.
- `.../summary/statistics_tables.md`, `decisions.csv`, `predicates.csv`.
- `.../summary/reviewer/MASTER_REPORT.md` + `episodes/`; `.../summary/proofs/`; `all_proofs.json`.
- `.../summary/dashboard.html`, `explorer.html`; `.../summary/graphs/*.dot|*.mmd`.
- `.../summary/BENCHMARK_SUMMARY.md|json`; `.../summary/supplementary/SUPPLEMENTARY_MATERIAL.md`.

## 5. Validation status (this campaign)

- Frozen integrity: **19 files unchanged**. Trace integrity: **33/33 OK**. Replay: **33/33 consistent**.
  Proofs: **all consistent**. Unit tests: **21/21 PASS**. Concurrency: **auth-correct + 0 FP/0 FD at all levels**.

## 6. Remaining limitations before IEEE Access submission

1. **Local-agent capability / non-determinism.** `llama3.1:8b` is weak at tool use and non-deterministic
   at temperature 0. Consequences: only 14 EEAs adjudicated across 33 episodes; **0 attacker-targeted
   EEAs** were ever proposed, so **FPR has no test cases** (n=0). *Fix:* a stronger tool-calling model
   (hosted or larger local) — no code change; re-run `run_audit.py`.
2. **Finite-sample CIs.** n=14 decisions → wide Wilson intervals (permit 0.786 [0.524,0.924]).
   *Fix:* full 79×629 corpus (runtime-budget only; resume supported).
3. **FPR still not exercised (R8 partial).** The independent labeling pipeline exists and runs, but
   needs episodes where the agent actually proposes an attacker-targeted action. *Fix:* stronger agent
   + adversarial task selection.
4. **FDR near-tautological.** Legitimate class is the recognized set the monitor also uses; FDR=0 is
   expected. *Fix:* an external oracle labeling of "should-permit" independent of the gate.
5. **Concurrency throughput is GIL-bound.** The pure-Python reference decision path does not scale up
   with threads; correctness/consistency do hold at all levels. *Fix:* process-level parallelism or a
   compiled decision kernel for a true throughput-scaling curve (32-thread+ CPU-parallel).
6. **Content-layer harms out of scope.** 1/33 attack "successes" were content-layer (no EEA), Property-v
   / Group III. This is a **claim boundary**, not a defect; stated explicitly.
7. **Two latency measurement contexts in Table 10.** build/bind/adapt/eval/emit (n=2000, Campaign 7)
   vs Runtime Context/Replay (n=5000, Campaign D). *Fix (optional):* a single unified per-stage run
   that also carries the RCL + replay timers.
8. **AgentDojo utility is low** (3/33) due to (1); this measures agent capability, not the monitor,
   which is validated independently (replay/proofs/integrity).

## 7. One-command reproduction

```bash
export LOCAL_LLM_PORT=11434
agentdojo_integration/.venv/bin/python agentdojo_integration/audit/tests/test_audit.py
agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py \
    --suites workspace banking slack travel --max-user-tasks 8 --outdir agentdojo_integration/audit_run
agentdojo_integration/.venv/bin/python -m agentdojo_integration.audit.concurrency_scaling \
    agentdojo_integration/audit_run/summary/concurrency
agentdojo_integration/.venv/bin/python -m agentdojo_integration.audit.runtime_profile \
    agentdojo_integration/audit_run/summary/runtime_profile
agentdojo_integration/.venv/bin/python -m agentdojo_integration.audit.fpr_fdr_labeling \
    agentdojo_integration/audit_run/trace agentdojo_integration/audit_run/summary/fpr_fdr
```

**Status: remaining experimental campaigns executed; Tables 10 & 13 COMPLETE, Table 11 READY;
figures/reports/supplementary regenerated; reviewer closure matrix produced; limitations enumerated.**
