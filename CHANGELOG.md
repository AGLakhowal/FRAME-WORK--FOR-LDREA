# Changelog

All notable changes to this repository are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning is tied to the accompanying paper rather than to semantic versioning of an API.

> **Scientific-integrity rule.** No release ever hand-edits a reported value. Numbers change only by
> re-executing the code that produces them. Entries below are therefore split into
> **Engineering** (no effect on any scientific output) and **Scientific** (changes an executed value).

---

## [v1.0-paper] — frozen artifact for the IEEE Access submission

The repository state that reproduces the paper. The paper, its figures, tables, numbering, equations,
claims, benchmark values, methodology, dashboard metrics and generated JSON evidence are **frozen**.

### Engineering — no scientific output changed

- **Generator failures can no longer be silent.** `RUN_ALL_EXPERIMENTS.py` invoked every generator with
  `subprocess.run(...)` without inspecting the return code, so a crashed generator left the README,
  dashboard and publication package silently disagreeing with the executed artifacts. Return codes are
  now checked, failures are reported loudly, the remaining generators still run, and every failure is
  summarised at the end of the run and recorded in `experiments/_meta/run_index.json`
  (`generator_failures`, `generators_ok`).
- **Fixed a crash in `experiments/generate_readme_results.py`.** It sorted experiment ids with
  `int(x[1:])`, which raised `ValueError` on the `E5b` id. Combined with the silent-failure bug above,
  this is why the README's auto-generated blocks had stopped tracking the artifacts. Ids are now sorted
  numerically, then by suffix.
- **Fixed a `KeyError` that made the E5b experiment fail.** The Combined Ablation summary writer still
  read the pre-rename key `false_permit_rate`; E5b now reports its blind-detection metrics under their
  own names (URR / BFR / Blind Decision Accuracy / Blind Detection Recall). See
  `METRIC_COLLISION_RESOLUTION_REPORT.md`. **Values are unchanged — only names.**
- **Added the missing `pynacl` dependency to the documented install.** `experiments/runtime_stack.py`
  imports `nacl` for the Ed25519 authority signer, so E5b, E11 and E12 could not run from a clean clone
  that followed the README.
- **Purged a stale `combined_ablation` entry** from the run index that kept resurrecting a historical
  failure through the index merge.
- **README**: added Quick start, Repository highlights, Experiment overview, Results at a glance,
  Documentation, Screenshots and Release information; fixed two broken internal anchors; added
  documentation for E5b, E11 and E12.
- **Repository metadata**: added `LICENSE` (placeholder), `CITATION.cff`, `CHANGELOG.md`,
  `RELEASE_NOTES_v1.0.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`.
- **Screenshots** added under `docs/assets/`.

### Scientific — values re-executed, none hand-edited

- None. Every metric, claim, equation and experimental result is unchanged from the frozen paper. The
  full campaign was re-executed to refresh the README's auto-generated metadata blocks (experiment
  count, claim count, git commit, wall-clock, provenance); all benchmark values reproduced identically.

### Known limitations carried into the release

- `scientific_consistency.py` gate 3 reports that **E11 and E12** register no artifacts in the run
  index (they are hand-rolled and bypass the `Experiment` collector). This is a bookkeeping gap, not an
  evidence gap — both experiments produce artifacts on disk under `production_evidence/`.
- The **license is not yet declared** (`LICENSE` is a placeholder).
- **Author names, DOI, year and volume are placeholders** in `CITATION.cff` and §21 — they are not
  present anywhere in this repository and were deliberately not invented.
- Throughput does not scale across cores (CPython GIL). This is a **disclosed negative result**, not a
  defect — see `LIMITATIONS_AND_NEGATIVE_RESULTS.md`.
