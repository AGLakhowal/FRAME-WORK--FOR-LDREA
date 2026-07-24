# Release Notes — `v1.0-paper`

**The frozen reproducibility artifact accompanying the IEEE Access submission.**

This tag reproduces the paper. Every number, figure, table and document in it is regenerated from
executed code by a single command. Nothing is hand-written, estimated, or copied from the manuscript.

---

## What this release is

| | |
|---|---|
| **Version** | `v1.0-paper` |
| **Git commit** | `264b9ec` |
| **Paper** | IEEE Access submission — **frozen** |
| **Python** | 3.9+ (reference run: CPython 3.9.6) |
| **Platform** | macOS · Linux · Windows (WSL2 recommended). Reference host: macOS 26.5.1, arm64 |
| **Dependencies** | `pandas` · `numpy` · `pynacl` (core) — `matplotlib`, `pytest` optional |

## Reproduce it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy pynacl
./.venv/bin/python RUN_ALL_EXPERIMENTS.py
open SCIENTIFIC_DASHBOARD.html
```

**≈ 503 s** for the full campaign on the reference host. The run ends with
`✓ all generators and validators completed successfully` when the derived artifacts are in sync with
the executed evidence — if a generator fails, it now says so loudly.

## What is in it

| | |
|---|--:|
| Experiments executed | **13 / 13** (E1–E12 + E5b) |
| Claims validated | **17 / 17** (16 supported · 1 partially supported · 1 explicitly not claimed) |
| Figures | 28 (`paper_figures/`) + 10 (`experiments/figures/`) |
| Tables | 51 (`paper_tables/`) |
| Publication package | 59 files (`PUBLICATION_PACKAGE/`) |
| Experiment JSON | 41 artifacts under `experiments/` |
| Tests | 29 / 29 passing |

## Headline evidence (unchanged from the paper)

| Metric | Result |
|---|--:|
| Unauthorized executions (UER) | **0 / 284,807** |
| False Permit Rate (authorization soundness) | **0 / 492** |
| AgentDojo boundary FPR (foreign attacker targets) | **0 / 62** |
| Replay determinism | **1.0** |
| Runtime predicate coverage | **13 / 13 = 100 %** |
| Formal verification | 2^16 exhaustive + 3 TLA⁺ invariants (TLC) |
| Throughput scaling | **negative result — disclosed** (CPython GIL) |

## Changed in this release

Engineering only. **No scientific output changed.** See [`CHANGELOG.md`](CHANGELOG.md) for the full list.
The headline fix: `RUN_ALL_EXPERIMENTS.py` no longer ignores generator return codes, so the README,
dashboard and publication package can no longer silently drift out of sync with the artifacts — the one
failure mode that would undermine a reproducibility artifact.

## Known limitations, carried into the release deliberately

- **License is not declared.** `LICENSE` is a placeholder. Declare one before the public release —
  reviewers who must run the code need explicit permission to do so.
- **Author names, DOI, year and volume are placeholders** in `CITATION.cff` and README §21. They are
  not present anywhere in this repository and were **not invented**.
- **`scientific_consistency.py` reports 8/9 gates.** Gate 3 flags that **E11 and E12** register no
  artifacts in the run index (they bypass the `Experiment` collector). This is a bookkeeping gap, not
  an evidence gap — both produce artifacts on disk under `production_evidence/`.
- **Throughput does not scale across cores** (CPython GIL). Disclosed, not hidden.
- Some prose counts in the README (§1 elevator pitch) predate E5b/E11/E12 and are being reconciled
  separately — the badges and provenance block are authoritative and are regenerated from artifacts.
