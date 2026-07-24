#!/usr/bin/env python3
"""
Fail-Closed Rate (FCR) test.
============================

FCR is the core "fails closed under uncertainty" guarantee of the spec:

    FCR = P( system -> SAFE_STATE | should-deny OR uncertain state )

This harness measures it over the REAL ULB corpus plus five injected
uncertainty families, and reports the adverse event (a fail-OPEN: a PERMIT
issued when the state is should-deny or uncertain) with Wilson 95% bounds.

Uncertainty families injected (each MUST fail closed):
  * should_deny_real     - the 492 real fraud rows (ground truth deny)
  * invalid_token        - TOKEN_VALID = false
  * stale_telemetry      - TelemetryFresh = false
  * stale_context        - StaleContext = true (TOCTOU)
  * missing_predicate    - one required node gate absent
  * ambiguous_signature  - AuthoritySignatureValid = false (e.g. API outage)

PASS condition: FCR = 1.0 observed (0 fail-open), Wilson 95% upper bound on
fail-open reported.

Output: fcr_test_report.json    (also returned by run()).
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List

import pandas as pd

from gamma_test_runner import evaluate_decision, wilson_interval, to_bool, NODE_GATE_COLS, BOOL_COLS

ROOT = Path(__file__).resolve().parent
MAPPED = ROOT / "GAMMA_G0_CREDITCARD_FULL_mapped.csv"
SEED = 20260701

NEEDED = list(dict.fromkeys(NODE_GATE_COLS + [
    "HARM_RISK", "StaleContext", "TelemetryFresh", "TOKEN_VALID",
    "AuthoritySignatureValid", "Actuated", "ACT_PERMIT", "ReasonCodes",
]))


def _row(r: pd.Series) -> Dict:
    d = {g: bool(r[g]) for g in NODE_GATE_COLS}
    d.update(
        HARM_RISK=float(r["HARM_RISK"]), StaleContext=bool(r["StaleContext"]),
        TelemetryFresh=bool(r["TelemetryFresh"]), TOKEN_VALID=bool(r["TOKEN_VALID"]),
        AuthoritySignatureValid=bool(r["AuthoritySignatureValid"]),
        Actuated=True, ACT_PERMIT=True, ReasonCodes=str(r["ReasonCodes"]),
    )
    return d


def _fc_block(name: str, instances: List[Dict]) -> Dict:
    """Evaluate a family; adverse = fail-open (PERMIT when it must fail closed)."""
    fail_open = 0
    for inst in instances:
        if evaluate_decision(inst, 0.5)["decision"] == "PERMIT":
            fail_open += 1
    n = len(instances)
    _, _, up = wilson_interval(fail_open, n)
    return {
        "family": name, "n": n, "fail_open_events": fail_open,
        "fail_closed": n - fail_open,
        "fail_closed_rate": round((n - fail_open) / n, 10) if n else 1.0,
        "wilson95_fail_open_upper": round(up, 10),
    }


def run(write: bool = True) -> Dict:
    print("[FCR] loading corpus ...")
    df = pd.read_csv(MAPPED, usecols=lambda c: c in NEEDED, low_memory=False)
    for c in BOOL_COLS:
        if c in df.columns:
            df[c] = to_bool(df[c])
    df["HARM_RISK"] = pd.to_numeric(df["HARM_RISK"], errors="coerce").fillna(0.0)
    df["ReasonCodes"] = df["ReasonCodes"].astype(str)
    df["gt_deny"] = df["ReasonCodes"].str.upper().str.contains("CLASS_1")

    rng = random.Random(SEED)
    adv = df[df["gt_deny"]]
    nominal = df[~df["gt_deny"]].sample(n=min(4000, (~df["gt_deny"]).sum()),
                                        random_state=SEED)
    base = [_row(r) for _, r in nominal.iterrows()]

    families = []
    # real should-deny rows
    families.append(_fc_block("should_deny_real",
                              [_row(r) for _, r in adv.iterrows()]))

    def mutate(field_setter):
        out = []
        for b in base:
            m = dict(b)
            field_setter(m, rng)
            out.append(m)
        return out

    families.append(_fc_block("invalid_token",
                    mutate(lambda m, _r: m.__setitem__("TOKEN_VALID", False))))
    families.append(_fc_block("stale_telemetry",
                    mutate(lambda m, _r: m.__setitem__("TelemetryFresh", False))))
    families.append(_fc_block("stale_context_toctou",
                    mutate(lambda m, _r: m.__setitem__("StaleContext", True))))
    families.append(_fc_block("missing_predicate",
                    mutate(lambda m, r: m.__setitem__(r.choice(NODE_GATE_COLS), False))))
    families.append(_fc_block("ambiguous_signature",
                    mutate(lambda m, _r: m.__setitem__("AuthoritySignatureValid", False))))

    total_n = sum(f["n"] for f in families)
    total_fo = sum(f["fail_open_events"] for f in families)
    _, _, up = wilson_interval(total_fo, total_n)
    overall = {
        "population": "should-deny + injected uncertainty",
        "n": total_n,
        "fail_open_events": total_fo,
        "fail_closed": total_n - total_fo,
        "FCR": round((total_n - total_fo) / total_n, 12) if total_n else 1.0,
        "wilson95_fail_open_upper": round(up, 10),
        "pass": total_fo == 0,
        "pass_threshold": "FCR = 1.0 observed; Wilson 95% upper bound reported",
    }
    report = {
        "test": "Fail-Closed Rate (FCR)",
        "definition": "FCR = P(SAFE_STATE | should-deny OR uncertain state); "
                      "adverse event = fail-open (PERMIT under uncertainty).",
        "overall": overall,
        "by_family": families,
        "engine": "non-compensatory Gamma + ISB (TOKEN_VALID & AuthoritySignatureValid "
                  "& TelemetryFresh & !StaleContext)",
    }
    if write:
        (ROOT / "fcr_test_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    r = run()
    o = r["overall"]
    print("=" * 66)
    print("  FAIL-CLOSED RATE (FCR) TEST")
    print("=" * 66)
    for f in r["by_family"]:
        print(f"  {f['family']:<22s} n={f['n']:>6}  fail-open={f['fail_open_events']}  "
              f"FCR={f['fail_closed_rate']}")
    print("-" * 66)
    print(f"  OVERALL FCR          : {o['FCR']}   (n={o['n']}, fail-open={o['fail_open_events']})")
    print(f"  Wilson95 fail-open   : < {o['wilson95_fail_open_upper']}")
    print(f"  PASS                 : {o['pass']}")
    print(f"  wrote fcr_test_report.json")
    print("=" * 66)


if __name__ == "__main__":
    main()
