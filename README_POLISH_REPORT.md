# README Polish Report

Scope: presentation, navigation and reviewer experience only. **No scientific content was changed** —
no metric renamed, no equation touched, no experiment description altered, no reported value modified,
no section removed, and no new claim invented.

---

## 1 · What was improved

### Added (all additive, placed outside the auto-generated marker blocks)

| Section | Placement | Notes |
|---|---|---|
| **⚡ Quick start** | immediately after the badges | clone → venv → deps → one command → expected runtime → expected outputs → how to open the dashboard |
| **🌟 Repository highlights** | after Quick start | one-command reproducibility, 12 experiments, 16 claims, dashboard, figures, tables, formal verification, AgentDojo, cross-dataset, provenance, reviewer mapping |
| **🧪 Experiment overview** | after the table of contents | Experiment · Purpose · Runtime · Main output · Paper § |
| **📊 Results at a glance** | after Experiment overview | primary metrics, each restated verbatim from §10 |
| **📚 Documentation** | after Results at a glance | Architecture · Experiments · Metrics · Datasets · Reproducibility · Reviewer mapping · Getting started/FAQ · Limitations |
| **🖼️ Screenshots** | after Documentation | four markdown image placeholders (see §3) |
| **🏷️ Release information** | after Screenshots | version, frozen paper version, git commit, platform, Python |

### Fixed

1. **Broken dependency command (§12.2).** The documented install was
   `pip install pandas numpy`, which **omits PyNaCl**. `experiments/runtime_stack.py::_signer()`
   imports `nacl`, so a fresh clone following the README could not run **E5b, E11 or E12** — they
   fail with `ModuleNotFoundError: No module named 'nacl'`. The line now reads
   `pip install pandas numpy pynacl`. Verified: the three experiments execute once it is installed.

2. **Two broken internal anchors (pre-existing).** Both used ASCII hyphens where the heading contains
   a non-ASCII hyphen (U+2011), which GitHub strips:
   - `#3--what-is-l-drea` → `#3--what-is-ldrea`
   - `#107--component-ablation-e5--ablationjson-…` → `#107--component-ablation-e5--60000-decisions-per-configuration`

3. **Table-of-contents navigation.** Added a "Jump to" bar linking the seven new sections.

### Verified

- **Every command in the README executes.** `RUN_ALL_EXPERIMENTS.py --help` (`--fast`, `--only`,
  `--no-figures` all present); the documented no-dataset path
  `--only formal replay ablation` was executed end-to-end (exit 0; E2/E3/E5 `EXECUTED`);
  `agentdojo_integration/.venv/bin/python` exists; the test suite runs (29/29 pass via `unittest`).
- **Every referenced local file exists** — 26 link targets checked; the only misses are the four
  intentional screenshot placeholders below.
- **All 52 internal anchors resolve** against GitHub's slug algorithm.
- **The additions survive regeneration.** `experiments/generate_readme_results.py` only rewrites the
  five marker blocks (`BADGES`, `PROVENANCE`, `RESULTS`, `RUNTIMES`, `REVIEWER`); all new sections sit
  outside them and are preserved.

---

## 2 · What was intentionally left unchanged

- Every experimental result, metric name, equation, experiment description and reported value.
- All existing sections and major explanations (§1–§24) — nothing removed or rewritten.
- Terminology, including the E5b blind-detection names (URR / BFR / Blind Detection Recall) and their
  distinction from the authorization False Permit Rate.
- **No duplicated explanation was deleted.** The brief allowed removing duplication, but on inspection
  the repetition in this README is deliberate and load-bearing: the URR-vs-FPR distinction and the
  "every value is executed" statement are restated at each point a reviewer could misread a number.
  Removing them would reduce scientific clarity, so they stay. This is the one instruction I did not
  act on, by design.

---

## 3 · Missing assets and follow-ups

### Screenshot placeholders (expected — add the images, no code change needed)

| Referenced path | Purpose |
|---|---|
| `docs/assets/dashboard.png` | Scientific dashboard |
| `docs/assets/architecture.png` | System architecture |
| `docs/assets/runtime-pipeline.png` | Runtime pipeline |
| `docs/assets/scientific-workflow.png` | Scientific workflow |

`docs/assets/banner.png` is also referenced by the pre-existing banner placeholder in the hero block.

### Open item — the README's auto-generated numbers are stale (needs your decision)

`experiments/generate_readme_results.py` was **crashing** with
`ValueError: invalid literal for int() with base 10: '5b'` — it sorted experiment ids with
`int(x[1:])`, which breaks on the `E5b` key. `RUN_ALL_EXPERIMENTS.py` invokes its generators with
`subprocess.run(...)` and does not check the return code, so the failure was **silent** and the five
marker blocks have not been refreshed for some time.

Consequence: the README's auto-blocks disagree with the artifacts —
badges say **12/12 experiments, 16/16 claims**, while `evidence_manifest.json` now holds **17 claims**
and the run index holds **13 experiments** (E1–E12 + E5b).

I fixed the crash (a sort-key change) **but deliberately did not apply its output**, because doing so
would change reported values — which this task forbids — and because running it right now would bake a
misleading `Total wall-clock 5.4 s for all 13 experiments` into the README (5.4 s is the duration of the
partial `--only` run used to verify the Quick-start command, not a full campaign).

**Recommended sequence when you want the numbers refreshed:**

```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py          # full campaign, so the wall-clock is real
./.venv/bin/python experiments/generate_readme_results.py
```

Then update the two hand-written counts in **Repository highlights** (currently `12 executed
experiments` / `16 validated claims`) to match whatever the refreshed badges report. Those two figures
are the only numbers in the sections I added that are not mechanically derived — I set them to the
README's existing reported values rather than silently introducing new ones.
