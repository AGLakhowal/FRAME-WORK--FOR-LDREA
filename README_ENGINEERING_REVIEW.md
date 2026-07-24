# README Engineering Review

Review-only. The current README is treated as canonical. **Nothing in this review was applied** —
every recommendation below is a proposal with an exact patch. No metric, result, equation, claim,
terminology, experiment description or architecture explanation is altered by any *applied* change,
because no change was applied.

## Verification summary

| Check | Result |
|---|--:|
| Internal anchors (52 links vs 127 headings) | ✅ all resolve |
| Markdown links, repo-wide (50 local links across `*.md`, `docs/`, `README/`) | ⚠️ 4 broken (all screenshot placeholders) |
| Referenced files exist (26 targets in README) | ⚠️ 4 missing (same placeholders) |
| Image references (16) | ⚠️ 4 unresolved |
| Code blocks (62 fences, balanced) | ✅ no syntax errors¹ |
| Commands still valid (`--fast`, `--only`, `--no-figures`, agentdojo venv, test suite) | ✅ all valid |
| Duplicate headings | ✅ none |
| Badges accurate | ❌ **2 of 11 contradict the artifacts** |

¹ `bash -n` flags `git clone <repository-url>` and one fenced block nested in a blockquote. The second
is a false positive (renders correctly on GitHub). The first is real but cosmetic — see M-1.

---

# CRITICAL

## C-1 · The README's auto-generated blocks silently stopped tracking the artifacts

**Severity:** Critical · **Files:** `experiments/generate_readme_results.py:137`,
`RUN_ALL_EXPERIMENTS.py:1060` · **Location:** README `<!-- BEGIN:BADGES -->` and
`<!-- BEGIN:PROVENANCE -->` blocks (lines ~18–19, ~262).

**The inconsistency.** The README states values that the artifacts contradict:

| Value | README says | Artifacts say |
|---|--:|--:|
| Experiments executed | **12 / 12** | **13** (`experiments/_meta/run_index.json`: E1–E12 + E5b) |
| Claims validated | **16 / 16** | **17** (`evidence_manifest.json`) |
| Git commit (provenance block) | `763008a…` | `264b9ec…` |

**Why it happens.** Two independent bugs compound:

1. `experiments/generate_readme_results.py:137` sorted experiment ids with
   `sorted(exps, key=lambda x: int(x[1:]))`. The run index now contains the id **`E5b`**, and
   `int("5b")` raises `ValueError: invalid literal for int() with base 10: '5b'`. The generator dies
   before it can rewrite a single marker block.

2. `RUN_ALL_EXPERIMENTS.py:1060` invokes every generator as
   `subprocess.run([sys.executable, str(gp)], cwd=ROOT)` — **with no `check=` and no return-code
   inspection**. The crash is swallowed. `RUN_ALL_EXPERIMENTS.py` therefore reports a clean run while
   the README quietly keeps stale numbers.

This is precisely the failure mode the generator's own docstring exists to prevent: *"a README that
contradicts the dashboard is a reproducibility defect regardless of how good the code is."*

**Safest fix.** Bug 1 is already repaired in the working tree (sort numerically, then by suffix, so a
non-numeric suffix cannot crash it). Bug 2 is the structural one and is **not** yet fixed — without it,
the next generator crash is silent again.

```diff
--- a/RUN_ALL_EXPERIMENTS.py
+++ b/RUN_ALL_EXPERIMENTS.py
@@ -1057,7 +1057,11 @@
             gp = EXP / gen
             if gp.exists():
                 if not DASH:
                     hr(f"generator: {gen}")
-                subprocess.run([sys.executable, str(gp)], cwd=ROOT)
+                gr = subprocess.run([sys.executable, str(gp)], cwd=ROOT)
+                if gr.returncode != 0:
+                    # A generator that dies silently leaves README/dashboard contradicting the
+                    # artifacts — the one failure mode this harness exists to prevent. Surface it.
+                    print(f"  !! generator FAILED: {gen} (exit {gr.returncode})")
+                    results.setdefault("_generator_failures", []).append(gen)
```

**Does the fix change scientific outputs?** **No.** It only surfaces a failure that is currently
hidden. It changes no metric, no artifact and no computed value.

**Does regenerating the README change reported values?** **Yes — and that is why I did not do it.**
Running the (now-repaired) generator rewrites the badges to `13/13` and `17/17`, updates the commit
hash, and refreshes the host-variable latency table. Those edits are *correct* — they make the README
match the artifacts — but they change reported values, which this task forbids. **Your decision.**

**Recommended sequence, when you want it:**

```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py            # FULL campaign — see the warning below
./.venv/bin/python experiments/generate_readme_results.py
```

> ⚠️ **Do not run the generator after a partial `--only` run.** The `PROVENANCE` block writes
> `total_duration_s` verbatim. After a partial run it will state something like
> *"Total wall-clock **5.4 s** for all 13 experiments"* — a figure that is technically read from an
> artifact but scientifically misleading. Always regenerate from a full campaign.

---

# HIGH

## H-1 · Three different experiment counts and three different claim counts coexist in the README

**Severity:** High · **File:** `README.md` · **Locations:** line 108 (elevator pitch), lines 633, 718,
1832, 2020 (prose), lines 18–19 + 262 (auto-blocks).

| Location | Experiments | Claims | Reviewer concerns |
|---|--:|--:|--:|
| Elevator pitch (line 108) | **8** | **14** | **11** |
| Badges / provenance block | **12** | **16** | — |
| Prose (633, 718, 1832, 2020) | — | **14** | **11** |
| **Artifacts (ground truth)** | **13** | **17** | **12** (`reviewer_mapping.md`: R1–R11 + R6-ext) |

The elevator pitch — the first prose a reviewer reads — advertises *"8 experiments, 14 pre-registered
claims, 11 reviewer concerns"*, while the badge directly above it says 12 and 16, and the artifacts say
13 and 17. A reviewer who checks the numbers will find three answers.

**Rationale.** These are hand-written prose counts that drifted as E5b, E11 and E12 were added. They
are stale metadata, not experimental results — but they *are* reported values, so **I am not patching
them**. Proposed patch, for your sign-off:

```diff
--- a/README.md
+++ b/README.md
@@ -108
-> framework** that measures it: 8 experiments, 14 pre‑registered claims, 11 reviewer concerns, and a
-> single command that regenerates every number, figure, table and document from executed code.
+> framework** that measures it: 13 experiments, 17 pre‑registered claims, 12 reviewer concerns, and a
+> single command that regenerates every number, figure, table and document from executed code.
```

The same three counts recur at lines 633, 718, 1832 and 2020 and should move in the same pass. Best
done **immediately after** the C-1 regeneration, so prose and badges land on the same numbers.

## H-2 · §8 documents only E1–E10; E11, E12 and E5b have no section

**Severity:** High · **File:** `README.md` · **Location:** §8 · Experiments.

§8 has `### E1` … `### E10` and stops. **E5b** (combined ablation — the experiment that answers
reviewer concern R6-ext), **E11** (runtime evidence stack) and **E12** (blind dataset detection) are
executed, appear in `run_index.json`, are cited by the dashboard, and are the two longest-running
experiments in the campaign — but a reader working through §8 never meets them.

**Rationale.** This is a navigation/completeness gap, not a scientific one. It is also the most likely
thing for a reviewer to notice, because §8 is where they will go to check "are all components
necessary?" (R6-ext).

**Fix:** add three `### E5b / ### E11 / ### E12` subsections in §8 following the existing template
(purpose · command · artifact · runtime). **No patch supplied** — writing them requires describing the
experiments, and experiment descriptions are explicitly out of bounds for me. Content already exists,
verbatim and executed, in `README/COMBINED_ABLATION.md` and `experiments/{combined_ablation,…}/summary.md`.

---

# MEDIUM

## M-1 · `git clone <repository-url>` is not copy-pasteable

**Severity:** Medium · **File:** `README.md` · **Locations:** Quick start (step 1) and §12.2 (step 1).

In `bash`, `<repository-url>` is a redirect: pasting the block yields
`syntax error near unexpected token 'newline'`. This is the very first command a new reviewer runs.

**Safe patch** (placeholder becomes inert, and the reader is told to substitute):

```diff
-git clone <repository-url>
+git clone "$REPO_URL"          # e.g. REPO_URL=https://github.com/<org>/<repo>.git
 cd "Independent Benchmark and Reviewer-Closure Framework for L-DREA"
```

Changes no scientific content. Applies in both locations.

## M-2 · Four screenshot assets are referenced but absent

**Severity:** Medium · **Files:** `README.md` (🖼️ Screenshots), plus the pre-existing banner reference.

| Path | Purpose | Status |
|---|---|---|
| `docs/assets/dashboard.png` | Scientific dashboard | ❌ missing |
| `docs/assets/architecture.png` | System architecture | ❌ missing |
| `docs/assets/runtime-pipeline.png` | Runtime pipeline | ❌ missing |
| `docs/assets/scientific-workflow.png` | Scientific workflow | ❌ missing |
| `docs/assets/banner.png` | Hero banner (pre-existing placeholder) | ❌ missing |

These are the **only** broken links anywhere in the repository. On GitHub they render as broken-image
icons, which reads as neglect on the page a reviewer lands on first.

**Suggested screenshots** (all reproducible from the repo today):

1. `SCIENTIFIC_DASHBOARD.html` — the experiments + claims panel (the single most persuasive artifact).
2. The §5.1 architecture mermaid diagram, rendered.
3. The §5.2 authorization pipeline (decision sequence).
4. `paper_figures/fig_combined_ablation_heatmap.svg` — the E5b interaction matrix.

**Interim safe patch** — if the images will not land soon, prevent broken-image icons by linking rather
than embedding:

```diff
-| **Scientific dashboard** | ![Dashboard](docs/assets/dashboard.png) |
+| **Scientific dashboard** | _screenshot pending_ — open [`SCIENTIFIC_DASHBOARD.html`](SCIENTIFIC_DASHBOARD.html) |
```

---

# LOW · polish, rendering and GitHub enhancements

| # | Severity | Item | Rationale |
|---|---|---|---|
| L-1 | Low | **Collapse the long reference sections** (§6 repository tour, §9 metrics, §24 appendix) in `<details>` | §6 and §24 are long reference material; collapsing them shortens the scroll to the sections reviewers actually read. §12.2 already uses `<details open>` — the pattern is established. |
| L-2 | Low | **Wide tables on mobile** | The §10.1 confusion-matrix and metric tables (6–7 columns incl. three Wilson bounds) overflow horizontally on phones. GitHub does not scroll them; it squeezes them. Consider splitting the three interval columns into a second table, or wrapping in `<div align="center">`. |
| L-3 | Low | **Add a LICENSE file** | The `License: NOT YET DECLARED` badge is *accurate* (no `LICENSE*` file exists) — but for an IEEE artifact-evaluation submission an undeclared license is a blocker for reviewers who must run the code. |
| L-4 | Low | **Repo metadata** | No `.github/` directory. Add `CITATION.cff` (GitHub renders a "Cite this repository" button — valuable for a paper artifact) and an issue template for reviewers. |
| L-5 | Low | **Mermaid diagrams** (10 blocks) | Render natively on GitHub — good. They do **not** render on PyPI/some mirrors; if the README is reused there, export PNGs alongside. |
| L-6 | Low | **Terminology is consistent** — no action | Verified: the E5b names (URR / BFR / Blind Detection Recall) appear only in E5b contexts, and the authorization False Permit Rate is never conflated with them. Capitalization of metric names is consistent throughout. |

---

# Things that are correct and should NOT be "fixed"

- **All 52 internal anchors resolve.** Two previously-broken anchors (`#3--what-is-l-drea`,
  `#107--…`) were repaired earlier; the headings contain a non-ASCII hyphen (U+2011) that GitHub
  strips, so the anchors intentionally read `…l-drea` → `…ldrea`. Do not "correct" them back.
- **The `> ```bash` block inside the §1 blockquote** is valid Markdown and renders correctly. `bash -n`
  flags it only because the `>` prefix is included; it is not a bug.
- **The `License: NOT YET DECLARED` badge is accurate**, not stale.
- **AgentDojo `0/62` and predicate-coverage `100%` badges are accurate** — both verified against
  `boundary_fpr.json` (`permitted=0, n=62`) and `predicate_coverage.json` (13/13).
- **Repetition of the URR-vs-FPR distinction is deliberate** and should stay: it is restated at each
  point where a reviewer could misread a number.

---

## Recommended order of work

1. **C-1** — apply the `RUN_ALL_EXPERIMENTS.py` return-code patch (safe, no value change).
2. **C-1** — run a **full** campaign, then the README generator; badges and provenance become truthful.
3. **H-1** — in the same pass, align the prose counts with the refreshed badges.
4. **H-2** — add §8 subsections for E5b/E11/E12.
5. **M-1, M-2** — clone command; screenshots.
6. **L-*** — polish.

Steps 2 and 3 change reported values in the README. They make it *match* the artifacts, but they are
value changes, so they are yours to authorize — which is why nothing here was applied.
