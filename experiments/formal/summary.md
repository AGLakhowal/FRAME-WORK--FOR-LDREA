# Experiment 3 — Formal Verification

Status: **EXECUTED** · 0.467s

## Exhaustive decision state-space (independent verifier)
- States enumerated: 65,536 / 65,536
- Coverage complete: True
- Field mismatches vs frozen engine: 0
- PERMIT states: 4 · SAFE_STATE states: 65,532
- Verdict: **IDENTICAL**

## TLA+/TLC model-check of Appendix-D Invariant 1
- Status: **EXECUTED**
- Distinct reachable states: 40,192
- No error found: True

Reproduce: `./.venv/bin/python independent_verifier.py`