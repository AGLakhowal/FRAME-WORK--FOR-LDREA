# Contributing

Thank you for looking at this repository. Please read this first — it is a **frozen research
artifact**, so the contribution rules are stricter than for a normal open-source project.

## The one rule that matters

> **Never hand-edit a generated artifact, and never change a reported value except by re-executing
> the code that produces it.**

Every number, figure, table and document in this repository is produced by executing code. Nothing is
hand-written, estimated, or carried over from the paper. A pull request that edits a number in
`README.md`, a `.json` under `experiments/`, a file in `paper_tables/`, or the dashboard **will be
rejected**, even if the new number is "more correct" — because that breaks the chain from claim to
evidence, which is the entire point of the artifact.

If a value is wrong, the *generator* is wrong. Fix the generator, re-run, and let the artifacts change
themselves.

## Frozen for the paper

The `v1.0-paper` tag reproduces the IEEE Access submission exactly. The following are **frozen** and
will not be changed on that tag:

- the paper, its figures, tables, numbering and equations
- scientific claims, benchmark values and experimental methodology
- dashboard metrics and generated JSON evidence
- the reviewer mapping

Engineering improvements (documentation, packaging, CI, developer experience) are welcome and land on
`main` for a future release.

## What is welcome

- Documentation, navigation and readability fixes.
- Reproducibility fixes: a command that does not work on your platform, a missing dependency, a path
  that breaks on Linux/Windows.
- Bugs in a **generator** that cause the README / dashboard / publication package to disagree with the
  executed artifacts. These are the highest-value reports.
- Independent reproduction reports — including **failures to reproduce**. A credible negative result is
  more valuable to us than a passing run.

## Before you open a pull request

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy pynacl

./.venv/bin/python RUN_ALL_EXPERIMENTS.py      # full campaign
./.venv/bin/python -m unittest discover -s tests -p "test_*"
./.venv/bin/python scientific_consistency.py
```

Check that:

1. `RUN_ALL_EXPERIMENTS.py` ends with **`✓ all generators and validators completed successfully`**.
   If it reports a generator failure, the derived artifacts are stale — fix that before proceeding.
2. The test suite passes.
3. `git diff` contains **no unexplained change to a reported value**. Timestamps, durations and hashes
   move between runs by design; metrics must not.

## Reporting a reproduction failure

Open an issue with: your platform, Python version, the exact command, the full output, and the
contents of `experiments/_meta/run_index.json`. That file records the status of every experiment and,
since `v1.0-paper`, of every generator.

## Security

See [`SECURITY.md`](SECURITY.md). Do not open a public issue for an undisclosed bypass of the action
boundary.
