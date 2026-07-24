# COMMAND REFERENCE — Every Command, What It Does, What It Produces

Two Python environments exist. Use the right one:
- **`./.venv/bin/python`** — the main environment (everything except live AgentDojo episodes).
- **`agentdojo_integration/.venv/bin/python`** — only for AgentDojo (it has the `agentdojo` package).

Runtimes below are approximate on a laptop (Apple M5, 10 cores). Your numbers will differ; that's normal
for timing (correctness numbers do not change).

---

## A. The two "run everything" commands

| Command | Purpose | Runtime | Needs | Key outputs |
|---------|---------|---------|-------|-------------|
| `./.venv/bin/python RUN_ALL_EXPERIMENTS.py` | **★ Main entry point.** Runs experiments E1–E8, packages them, and auto-generates statistics, figures, tables, provenance, the claim matrix, all reviewer docs, and both validators. | ~45 s | main venv (+ optional Java for E3's TLC step; +Ollama only for *fresh* AgentDojo) | whole `experiments/` tree; `CLAIM_EVIDENCE_MATRIX.md`, `FINAL_EVIDENCE_REPORT.md`, `evidence_manifest.json`, etc. |
| `./.venv/bin/python run_all.py` | **Older suite.** Runs the LAB benchmark + ConcurBench + stress + fail-closed + full-spec and builds an interactive HTML dashboard. | ~1–2 min | main venv | `gamma_report.html`; `gamma_lab_v1_report.json`, `concurbench_full_report.json`, `stress_test_report.json`, `fcr_test_report.json`, `full_spec_conformance_report.json` |

`RUN_ALL_EXPERIMENTS.py` flags:
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py                 # full: all 8 experiments + generators + validators
./.venv/bin/python RUN_ALL_EXPERIMENTS.py --fast          # lighter: 1-8 threads for stress, quicker
./.venv/bin/python RUN_ALL_EXPERIMENTS.py --only formal replay   # run only chosen experiments
./.venv/bin/python RUN_ALL_EXPERIMENTS.py --no-figures    # skip the generators/validators stage
```

---

## B. Individual experiments (the 8 that make the paper)

| # | Command | Purpose | Runtime | Output |
|---|---------|---------|---------|--------|
| E1 | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` | Runtime authorization correctness on the full ULB corpus (FPR, FDR, class-veto, replay determinism, latency). | ~12 s | `gamma_lab_v1_report.json`, `gamma_summary.json`, `gamma_validation_results.csv`, `gamma_replay_manifest.jsonl` |
| E2 | `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl` | Independently re-verify the tamper-evident ledger (hash chain, ledger binding, consistency). | ~1 s | prints PASS/FAIL + counts; RUN_ALL captures it into `experiments/replay/replay_report.json` |
| E3 | `./.venv/bin/python independent_verifier.py` | Prove the decision logic is correct over **all** 2¹⁶ input states (independent re-implementation vs engine). | ~1 s | `independent_verifier_report.json` (verdict IDENTICAL) |
| E4 | `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])"` | Stress test: throughput/latency/RSS + safety at 1–64 threads. | ~12 s | `experiments/stress/concurrency_scaling.json` + `.csv` |
| E5 | `./.venv/bin/python experiment_ablation.py` | Remove class-veto / Γ / authorization layer; measure leaked permits. | ~2 s | `fresh_evidence/ablation/ablation.json` + `.csv` + log |
| E6 | `./.venv/bin/python -c "from agentdojo_integration.audit import runtime_profile as r; r.run('experiments/profiling',5000)"` | Per-stage timing (Runtime-Context plane, Replay plane, pipeline). | ~1 s | `experiments/profiling/runtime_profile.json` |
| E7 | `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py` | Adjudicate every real AgentDojo attacker target at the frozen boundary (**no LLM**). | ~2 s | `experiments/agentdojo/boundary/boundary_fpr.json` |
| E8 | `./.venv/bin/python experiment_robustness.py` | Inject 16 fault types (missing/corrupted predicates, replay/ledger corruption, clock skew...); check safety holds. | ~1 s | `fresh_evidence/robustness/robustness.json` + `.csv` + log |

---

## C. Generators (turn artifacts into paper-ready outputs)

These are normally run automatically by `RUN_ALL_EXPERIMENTS.py`, but you can run them alone after a full
run to regenerate just the derived outputs (they only *read* artifacts, never re-run experiments).

| Command | Purpose | Output |
|---------|---------|--------|
| `./.venv/bin/python experiments/generate_statistics.py` | Wilson CIs, rule-of-three bounds, effect sizes, sensitivity. | `experiments/statistics/statistics_report.{json,md}` |
| `./.venv/bin/python experiments/generate_figures.py` | 8 publication figures (pure SVG, no matplotlib). | `experiments/figures/*.svg` |
| `./.venv/bin/python experiments/generate_tables.py` | IEEE tables + LaTeX. | `experiments/tables/*.md`, `*.tex`, `tables.json` |
| `./.venv/bin/python experiments/generate_provenance.py` | Traceability DAG (log→metric→JSON→CSV→table→figure). | `experiments/provenance/*` |
| `./.venv/bin/python experiments/generate_publication_docs.py` | Claim matrix, reviewer map, threats, limitations, reproducibility audit, evidence manifest, final report. | 7 files at repo root |

---

## D. Validators (reviewer-grade auto-checks)

| Command | Purpose | Output | Exit code |
|---------|---------|--------|-----------|
| `./.venv/bin/python validate_paper_claims.py` | For every claim: is the value the same in JSON, table, figure, and manifest? | `PAPER_CLAIM_VALIDATION.md` (PASS/WARNING/FAIL per claim) | 0 if no FAIL |
| `./.venv/bin/python scientific_consistency.py` | 9 integrity checks: figures have data, tables cite real experiments, CIs consistent, sample sizes agree, provenance intact, no stale files, etc. | `SCIENTIFIC_CONSISTENCY_REPORT.md` | 0 if all pass |

---

## E. Supplementary / legacy commands (used inside the suites, or for the dashboard)

| Command | Purpose | Notes |
|---------|---------|-------|
| `./.venv/bin/python concurbench_full.py` | ConcurBench L1–L4 conformance. | Also runs inside `run_all.py` and E1. |
| `./.venv/bin/python stress_test.py` | Financial adversarial scenarios. | Runs inside E1/`run_all.py`. |
| `./.venv/bin/python fcr_test.py` | Fail-Closed Rate over predicate families. | Runs inside E1/`run_all.py`. |
| `./.venv/bin/python full_spec_conformance.py` | FULL_SPEC acceptance bands + confusion matrix. | Produces the confusion matrix used by E1. |
| `./.venv/bin/python reproduce_paper.py` | Legacy paper-reproduction driver. | Superseded by `RUN_ALL_EXPERIMENTS.py`. |
| `./.venv/bin/python paper_table_generator.py` / `paper_figure_generator.py` | Legacy table/figure builders. | Superseded by `experiments/generate_*`. |
| `./.venv/bin/python experiment_registry.py` | Prints which experiment outputs are present on disk. | Handy status check. |
| `agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run` | **Generate FRESH AgentDojo episodes.** | **Needs Ollama + llama3.1:8b.** This is the one BLOCKED item without that dependency. |

---

## F. Environment / tooling commands

| Command | Purpose |
|---------|---------|
| `./.venv/bin/python -V` | Confirm you're on the project Python (3.9.6). |
| `agentdojo_integration/.venv/bin/python -c "import agentdojo; print('ok')"` | Confirm the AgentDojo env works. |
| `git status --short` | See what changed. |
| `python experiment_registry.py` | See which experiment artifacts already exist. |

> **Tip:** if a command uses `from agentdojo_integration.audit import ...`, always run it from the repo
> root (not from inside `agentdojo_integration/`), or the package import will fail. `RUN_ALL_EXPERIMENTS.py`
> already does this correctly.
