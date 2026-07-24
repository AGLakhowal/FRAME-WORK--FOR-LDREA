# Repository Release Report — `v1.0-paper`

Generated from the executed state of the repository after a **full** `RUN_ALL_EXPERIMENTS.py` campaign.

---

## 1 · Identity

| | |
|---|---|
| **Repository version** | `v1.0-paper` |
| **Git commit** | `264b9ec` |
| **Paper version** | IEEE Access submission — **FROZEN** |
| **Python** | 3.9+ · reference run CPython **3.9.6** |
| **Platform** | macOS · Linux · Windows (WSL2). Reference host: macOS 26.5.1, arm64 (Apple M-series) |
| **Dependencies** | `pandas` 2.3.3 · `numpy` 2.0.2 · `pynacl` 1.6.2 — optional: `matplotlib`, `pytest` |

## 2 · Executed evidence

| | |
|---|--:|
| **Experiments** | **13 / 13 executed** (E1–E12 + E5b) |
| **Claims** | **17 / 17 validated** (16 supported · 1 partially supported · 1 explicitly not claimed) |
| **Full-campaign wall-clock** | **503.3 s** |
| **Reviewer concerns mapped** | 12 (R1–R11 + R6-ext) |

| Experiment | Status | Runtime |
|---|---|--:|
| E1 · Authorization Correctness | EXECUTED | 23.8 s |
| E2 · Replay Integrity | EXECUTED | 1.9 s |
| E3 · Formal Verification | EXECUTED | 0.9 s |
| E4 · Stress / Concurrency | EXECUTED | 26.6 s |
| E5 · Component Ablation | EXECUTED | 4.4 s |
| E5b · Combined Ablation | EXECUTED | 120.6 s |
| E6 · Runtime Profiling | EXECUTED | 1.7 s |
| E7 · AgentDojo Governance | EXECUTED | 3.5 s |
| E8 · Robustness | EXECUTED | 0.9 s |
| E9 · Predicate Coverage | EXECUTED | 0.3 s |
| E10 · Audit Bundle Export | EXECUTED | 16.0 s |
| E11 · Runtime Evidence Stack | EXECUTED | 24.8 s |
| E12 · Blind Dataset Detection | EXECUTED | 281.3 s |

## 3 · Generated artifacts

| Artifact class | Count | Location |
|---|--:|---|
| Figures (paper) | 28 | `paper_figures/` |
| Figures (experiment) | 10 | `experiments/figures/` |
| Tables | 51 | `paper_tables/` |
| Experiment JSON | 41 | `experiments/**` |
| Publication package | 59 files | `PUBLICATION_PACKAGE/` |
| Dashboard | 2 | `SCIENTIFIC_DASHBOARD.html`, `RUNTIME_EVALUATION_DASHBOARD.html` |
| Screenshots | 3 | `docs/assets/` |

## 4 · Validation status

| Check | Result |
|---|---|
| Test suite | ✅ **29 / 29 passing** |
| Generators + validators | ✅ all generators completed; **1 validator reported findings** (see §6) |
| README internal anchors | ✅ all resolve |
| README markdown links | ✅ all resolve |
| Referenced files exist | ✅ all exist |
| Image references | ✅ 15 / 15 resolve |
| Repo-wide markdown links (58) | ✅ **0 broken** |
| Commands in README | ✅ all valid and executed |
| Badges | ✅ accurate (13/13, 17/17, AgentDojo 0/62, coverage 100 %, License NOT YET DECLARED) |
| Experiment sections | ✅ E1–E12 + E5b all documented |
| Benchmark values vs frozen paper | ✅ **identical** (FPR 0/492 · AgentDojo 0/62 · UER 0) |

## 5 · Broken links / missing files

**None.** All 58 markdown links across `*.md`, `docs/` and `README/` resolve; all 15 image references
resolve; all referenced files exist.

## 6 · Outstanding limitations

| # | Item | Severity | Blocks release? |
|---|---|---|---|
| 1 | **License not declared** — `LICENSE` is a placeholder; all rights reserved by default | High | **Yes, for a public release.** Reviewers who must execute the code need explicit permission. |
| 2 | **`CITATION.cff` / §21 contain TODO placeholders** — authors, DOI, year, volume | High | Yes for citation; deliberately **not invented** |
| 3 | **`scientific_consistency.py`: 8/9 gates.** Gate 3 flags E11/E12 as EXECUTED with no artifacts recorded in `run_index.json` — they are hand-rolled and bypass the `Experiment` collector | Medium | No. Bookkeeping gap, not evidence gap: both produce artifacts under `production_evidence/`. Now **surfaced loudly** rather than silently swallowed. |
| 4 | **Stale prose counts** in README §1 ("8 experiments, 14 pre-registered claims, 11 reviewer concerns") and one table row ("10 / 10") predate E5b/E11/E12 | Medium | No, but visible. Not auto-corrected: they are manually written text, and the brief forbids changing it. **Recommend fixing to 13 / 17 / 12 before release.** |
| 5 | **Architecture & scientific-workflow screenshots not generated** — they are Mermaid diagrams; no offline renderer available (mermaid-cli install was blocked) | Low | No. They render natively on GitHub and are linked instead of duplicated. |
| 6 | **Throughput does not scale across cores** (CPython GIL) | — | No. **Disclosed negative result**, not a defect. |

## 7 · Release checklist

| | Item | Status |
|---|---|---|
| ✅ | Paper frozen | No paper file, figure, table, equation, claim or value modified |
| ✅ | Repository reproducible | One command; full campaign 503.3 s; 13/13 executed |
| ✅ | README synchronized | Auto-blocks regenerated from a **full** run (13/13, 17/17, commit, wall-clock) |
| ✅ | Dashboard synchronized | Regenerated; reads 13/13 experiments, 17/17 claims |
| ✅ | Experiments synchronized | All 13 EXECUTED; run index current |
| ✅ | Publication package synchronized | 59/59 artifacts validated |
| ✅ | No stale generated artifacts | Generator health recorded in `run_index.json` (`generators_ok`) |
| ✅ | No broken links | 0 / 58 |
| ✅ | No silent generator failures | Return codes checked, failures reported and summarised |
| ⚠️ | GitHub ready | **Blocked only by the undeclared license** (item 1) |
