# CHEATSHEET — Daily Usage & Common Mistakes

Print this page. It's the "if I want X, run Y" table plus the errors you'll actually hit and how to fix
them.

---

## 1. "If I want to…" → run this

| I want to… | Command |
|------------|---------|
| **Run everything** (experiments + figures + tables + validators) | `./.venv/bin/python RUN_ALL_EXPERIMENTS.py` |
| Run everything **quickly** (lighter stress test) | `./.venv/bin/python RUN_ALL_EXPERIMENTS.py --fast` |
| Run **only some experiments** | `./.venv/bin/python RUN_ALL_EXPERIMENTS.py --only formal replay robustness` |
| **Only regenerate tables** (after a full run) | `./.venv/bin/python experiments/generate_tables.py` |
| **Only regenerate figures** | `./.venv/bin/python experiments/generate_figures.py` |
| **Only regenerate statistics** | `./.venv/bin/python experiments/generate_statistics.py` |
| **Only regenerate the provenance graph** | `./.venv/bin/python experiments/generate_provenance.py` |
| **Only regenerate the reviewer docs / final report** | `./.venv/bin/python experiments/generate_publication_docs.py` |
| **Only rerun LAB (E1 correctness)** | `./.venv/bin/python gamma_test_runner.py --no-html --no-open` |
| **Only rerun the replay check (E2)** | `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl` |
| **Only rerun the formal check (E3)** | `./.venv/bin/python independent_verifier.py` |
| **Only rerun the stress test (E4)** | `./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])"` |
| **Only rerun ablation (E5)** | `./.venv/bin/python experiment_ablation.py` |
| **Only rerun profiling (E6)** | `./.venv/bin/python -c "from agentdojo_integration.audit import runtime_profile as r; r.run('experiments/profiling',5000)"` |
| **Only rerun AgentDojo boundary (E7, no LLM)** | `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py` |
| **Only rerun robustness (E8)** | `./.venv/bin/python experiment_robustness.py` |
| **Generate FRESH AgentDojo episodes** (needs Ollama) | `agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run` |
| **Validate every paper number** | `./.venv/bin/python validate_paper_claims.py` |
| **Check scientific consistency / integrity** | `./.venv/bin/python scientific_consistency.py` |
| **Build the interactive HTML dashboard** (older suite) | `./.venv/bin/python run_all.py --no-open` |
| **See which experiment outputs already exist** | `./.venv/bin/python experiment_registry.py` |

> **Rule of thumb:** experiments write JSON; generators read JSON and write tables/figures/docs;
> validators check consistency. If you only changed presentation, re-run the generators — you don't need
> to re-run the experiments.

---

## 2. What to read after a run

| I want to see… | Open this |
|----------------|-----------|
| the overall summary | `FINAL_EVIDENCE_REPORT.md` |
| every claim → evidence → status | `CLAIM_EVIDENCE_MATRIX.md` |
| answers to likely reviewer criticisms | `reviewer_mapping.md` |
| the pictures | `experiments/figures/*.svg` |
| the paper tables (Markdown + LaTeX) | `experiments/tables/*.md`, `*.tex` |
| the confidence intervals / effect sizes | `experiments/statistics/statistics_report.md` |
| did the numbers validate? | `PAPER_CLAIM_VALIDATION.md` |
| is everything consistent? | `SCIENTIFIC_CONSISTENCY_REPORT.md` |
| how to reproduce | `REPRODUCIBILITY_AUDIT.md` |
| one experiment's result | `experiments/<name>/summary.md` |

---

## 3. Common mistakes & how to fix them

### ❌ `ModuleNotFoundError: No module named 'agentdojo'`
**Why:** you used the main venv for an AgentDojo command.
**Fix:** use the AgentDojo venv for E7 / fresh episodes:
```bash
agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py
```

### ❌ `ImportError: attempted relative import with no known parent package`
**Why:** you ran an `agentdojo_integration/audit/*.py` file directly instead of importing it as a package.
**Fix:** run it from the repo root as a module import (this is what RUN_ALL does):
```bash
./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])"
```

### ❌ `ollama not found` / AgentDojo fresh episodes won't run
**Why:** generating *new* AgentDojo episodes needs a local LLM; the boundary probe (E7) does **not**.
**Fix:** the boundary FPR (the soundness number) already runs without an LLM. For fresh episodes:
```bash
brew install ollama && ollama serve & ollama pull llama3.1:8b
agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run
```
This is the **only** dependency-blocked item — it's documented, not hidden.

### ❌ E3's TLC step says "BLOCKED — no Java runtime"
**Why:** the exhaustive 2¹⁶ check (the main formal result) is pure Python and always runs; the *optional*
TLA⁺/TLC model-check needs Java.
**Fix:** it's optional. To enable it, install a JRE + `tla2tools.jar` (the project expects them at
`~/.ldrea_tla/`). E3's primary result does not depend on Java.

### ❌ `FileNotFoundError: gamma_replay_manifest.jsonl` (E2 fails)
**Why:** E2 audits the ledger that **E1 produces**. If you never ran E1, the ledger doesn't exist.
**Fix:** run E1 first (or just run the full `RUN_ALL_EXPERIMENTS.py`, which orders them correctly).

### ❌ `FileNotFoundError: ...GAMMA_G0_CREDITCARD_FULL_mapped.csv`
**Why:** the 451 MB dataset isn't present (it's large and may be stored via Git LFS or separately).
**Fix:** restore the dataset to the repo root. Check `git lfs pull` if the repo uses LFS, or copy it back
from your data store. Nothing that reads the full corpus (E1) can run without it.

### ❌ Wrong Python / "it works on my machine but not here"
**Why:** the project targets **Python 3.9.6** in `./.venv`. Using system Python can pull wrong package
versions.
**Fix:** always call the venv Python explicitly:
```bash
./.venv/bin/python -V          # should print Python 3.9.6
./.venv/bin/python RUN_ALL_EXPERIMENTS.py
```

### ❌ A partial run "overwrote" my full results index
**Why:** older behavior; `--only` runs update the run index.
**Fix:** this is handled now — `--only` **merges** into `experiments/_meta/run_index.json` instead of
replacing it. If ever unsure, just re-run the full `RUN_ALL_EXPERIMENTS.py` to get one clean, coherent
index.

### ❌ Broken/odd figures (SVG won't open)
**Why:** almost always a stale figure from a previous partial state.
**Fix:** regenerate them — they're built from the JSON, so it's instant and safe:
```bash
./.venv/bin/python experiments/generate_figures.py
```

### ❌ "Which 'run everything' do I use?"
**Fix:** `RUN_ALL_EXPERIMENTS.py` for the **reproducible reviewer package** (E1–E8 + docs).
`run_all.py` for the **interactive HTML dashboard**. See PROJECT_GUIDE.md §6.

---

## 4. 30-second health check (am I set up correctly?)

```bash
./.venv/bin/python -V                                             # Python 3.9.6 ?
agentdojo_integration/.venv/bin/python -c "import agentdojo;print('agentdojo ok')"
ls -la GAMMA_G0_CREDITCARD_FULL_mapped.csv                         # dataset present ?
./.venv/bin/python experiment_registry.py                         # which artifacts exist ?
```
If all four succeed, you're ready to run `RUN_ALL_EXPERIMENTS.py`.

---

## 5. The absolute minimum you need to remember

```bash
# do everything, then prove it:
./.venv/bin/python RUN_ALL_EXPERIMENTS.py
./.venv/bin/python validate_paper_claims.py
./.venv/bin/python scientific_consistency.py
# then read FINAL_EVIDENCE_REPORT.md
```
That's the whole workflow. Everything else is a detail you can look up here.
