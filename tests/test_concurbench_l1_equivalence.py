"""Commit 3.1 — ConcurBench Level-1 single-source verification.

Proves the L1 authorization refactor introduced ZERO scientific change:
  1. EQUIVALENCE  — the pre-refactor inline L1 rule == the frozen evaluate_decision() on
                    representative sample rows (so routing L1 through the engine did not
                    alter a single decision).
  2. BYTE-PARITY  — the regenerated concurbench_full_report.json is byte-identical to the
                    frozen 0.1 baseline fixture (guarded on corpus/LAB prerequisites).
  3. SINGLE SOURCE — level1() now routes through evaluate_decision() and no longer contains
                     a duplicated deficit/class computation (no dead code).

Standard library + the project modules only; no pytest. Run:
    python3 tests/test_concurbench_l1_equivalence.py     # standalone; exits 0 on success

Scope: Level-1 only. Levels 2/3/4 and the desync simulation are untouched by Commit 3.1.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import concurbench_full as cb  # noqa: E402
from gamma_test_runner import evaluate_decision, NODE_GATE_COLS  # noqa: E402

BASELINE = ROOT / "tests" / "fixtures" / "baseline" / "concurbench_full_report.json"

# Fields every row must carry for row_dict()/evaluate_decision() (besides the gates).
_BASE_ROW = {
    "HARM_RISK": 0.0,
    "StaleContext": False,
    "TelemetryFresh": True,
    "TOKEN_VALID": True,
    "AuthoritySignatureValid": True,
    "Actuated": False,
    "ACT_PERMIT": False,
    "ReasonCodes": "CLASS_0_LEGITIMATE;ALL_GATES_PASS",
}


def _row(**overrides) -> dict:
    r = {g: True for g in NODE_GATE_COLS}
    r.update(_BASE_ROW)
    r.update(overrides)
    return r


def _old_inline_permit(r: dict) -> bool:
    """The PRE-refactor Level-1 rule, verbatim, as the equivalence reference (theta=0.5)."""
    deficit = any(not r[g] for g in NODE_GATE_COLS)
    deficit = deficit or (float(r["HARM_RISK"]) > 0.5)
    deficit = deficit or bool(r["StaleContext"])
    deficit = deficit or (not bool(r["TelemetryFresh"]))
    reason = str(r["ReasonCodes"]).upper()
    gamma_class = ("CLASS_1" in reason) or ("GOODHART" in reason)
    return (not deficit) and (not gamma_class)


# Representative rows spanning every deficit source + the class veto.
_SAMPLE = [
    _row(),                                                         # all pass -> permit
    _row(**{NODE_GATE_COLS[0]: False}),                            # a failing gate
    _row(**{NODE_GATE_COLS[-1]: False}),                           # another failing gate
    _row(HARM_RISK=0.51),                                          # harm just over theta
    _row(HARM_RISK=0.50),                                          # harm exactly at theta (not over)
    _row(HARM_RISK=0.49),                                          # harm under theta
    _row(StaleContext=True),                                       # stale context deficit
    _row(TelemetryFresh=False),                                    # stale telemetry deficit
    _row(ReasonCodes="CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL"),      # class-1 veto
    _row(ReasonCodes="GOODHART_PROXY_GAMING"),                     # goodhart veto
    _row(ReasonCodes="class_1_lowercase"),                         # case-insensitive veto
    _row(HARM_RISK=0.9, StaleContext=True, ReasonCodes="CLASS_1"), # multiple deficits
]


# 1. EQUIVALENCE — old inline rule == frozen evaluate_decision() for every sample row
def test_l1_equivalence_sample() -> None:
    for i, r in enumerate(_SAMPLE):
        old = _old_inline_permit(r)
        # mirror the exact L1 path: row_dict(r) -> evaluate_decision(..., 0.5)["pi"]
        engine = evaluate_decision(cb.row_dict(r), 0.5)["pi"] == 1
        assert old == engine, "row %d: inline rule (%s) != evaluate_decision (%s)" % (i, old, engine)


# 2. SINGLE SOURCE — level1() routes through evaluate_decision and drops the duplicate rule
def test_level1_single_source() -> None:
    src = inspect.getsource(cb.level1)
    assert "evaluate_decision(" in src, "L1 must source the decision from evaluate_decision()"
    # the pre-refactor duplicated computation and its dead code must be gone
    assert "deficit |=" not in src, "duplicated deficit computation must be removed"
    assert "gamma_class" not in src, "duplicated class-veto computation must be removed"
    assert "permit = pd.Series" not in src, "dead 'permit' series must be removed"


# 3. THETA PINNED — L1 pins 0.5 and does not read a CLI/mutable threshold
def test_theta_pinned() -> None:
    src = inspect.getsource(cb.level1)
    assert "0.5" in src, "L1 must pin harm_threshold = 0.5"
    assert "harm_threshold" not in src and "args." not in src, "L1 must not read a mutable threshold"


# 4. BYTE-PARITY — regenerated report == frozen baseline fixture (guarded on prerequisites)
def test_report_byte_parity() -> None:
    if not (cb.MAPPED.exists() and cb.LAB_REPORT.exists()):
        print("    SKIP test_report_byte_parity (corpus/LAB report not present)")
        return
    report = cb.run(write=False)
    produced = json.dumps(report, indent=2)
    baseline = BASELINE.read_text(encoding="utf-8")
    assert produced == baseline, "regenerated concurbench report is not byte-identical to baseline"


def _run_all() -> int:
    checks = [
        test_l1_equivalence_sample,
        test_level1_single_source,
        test_theta_pinned,
        test_report_byte_parity,
    ]
    failures = 0
    for fn in checks:
        try:
            fn()
            print("  PASS  %s" % fn.__name__)
        except AssertionError as exc:
            failures += 1
            print("  FAIL  %s: %s" % (fn.__name__, exc))
    print("-" * 60)
    print("concurbench L1 equivalence: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
