#!/usr/bin/env python3
"""
experiment_predicate_coverage.py — E9: Runtime Predicate Coverage & Single-Deficit Isolation.
=============================================================================================

WHY THIS EXPERIMENT EXISTS
--------------------------
E1 adjudicates the real ULB corpus and reports zero false permits. But on that corpus only four of
the runtime predicates are ever falsified (`Gate_A3`, `Gate_A7`, `Lambda_G`, `HARM_RISK_THETA`); the
remaining node gates are TRUE on all 284,807 rows. Their runtime behaviour is therefore *never
exercised* by E1 — a coverage gap in the evaluation, not in the architecture.

E3 closes the gap formally (it enumerates the complete 2^16 decision abstraction), but E3 compares an
independent reference function against the engine; it does not drive the engine's own runtime path.

E9 closes the gap *empirically*, on the frozen `evaluate_decision` entry point, with a deterministic
synthetic suite. Each case falsifies exactly ONE predicate while holding every other predicate clean.
That construction does three things at once:

  1. It exercises every runtime predicate in both polarities (TRUE and FALSE).
  2. It is a direct per-predicate test of Non-Compensatory Soundness (invariant I3): a single deficit,
     with nine concurring predicates, must still deny.
  3. It isolates the class-level veto (I4): a row where every node gate concurs but a class reason
     code is present must still deny (Goodhart resistance).

SCIENTIFIC HONESTY
------------------
* The engine is NOT modified. This experiment imports the frozen `evaluate_decision` and calls it.
* The cases are SYNTHETIC and are labelled as such everywhere they are reported. They establish that
  every predicate is wired into the decision correctly; they do NOT establish that the ULB corpus
  exercises them, and they do not replace or weaken the E1 corpus-coverage limitation.
* Nothing here changes any E1 metric. E9 writes its own artifact.
* Expected results are asserted per case. A case whose observed outcome differs from the specified
  outcome is recorded as a FAILURE, not silently dropped.

Output: fresh_evidence/predicate_coverage/predicate_coverage.json (+ .csv, + log.jsonl)
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gamma_test_runner import (  # noqa: E402  frozen engine — imported, never modified
    NODE_GATE_COLS,
    evaluate_decision,
    wilson_interval,
)

OUT = ROOT / "fresh_evidence" / "predicate_coverage"
THETA = 0.5

# The three derived deficits, and the exact mutation that triggers each.
DERIVED_DEFICITS = {
    "HARM_RISK_THETA": ("HARM_RISK", 0.99, "HARM_RISK > theta"),
    "STALE_CONTEXT": ("StaleContext", True, "StaleContext == TRUE"),
    "TELEMETRY_STALE": ("TelemetryFresh", False, "TelemetryFresh == FALSE"),
}

# Reason-code tokens that raise the class-level veto (Gamma_class = 1).
CLASS_VETO_TOKENS = ["CLASS_1", "GOODHART"]

# The four conjuncts of ISB. Each must independently drive ISB to 0.
ISB_CONJUNCTS = {
    "TOKEN_VALID": ("TOKEN_VALID", False),
    "AuthoritySignatureValid": ("AuthoritySignatureValid", False),
    "TelemetryFresh": ("TelemetryFresh", False),
    "StaleContext": ("StaleContext", True),  # ISB requires NOT StaleContext
}


def clean_row(actuated: bool = False) -> dict:
    """A proposal on which every predicate concurs. Baseline: must PERMIT."""
    row = {g: True for g in NODE_GATE_COLS}
    row.update({
        "HARM_RISK": 0.01,          # below theta
        "StaleContext": False,
        "TelemetryFresh": True,
        "ReasonCodes": "CLASS_0_LEGITIMATE;ALL_GATES_PASS",
        "Actuated": actuated,
        "ACT_PERMIT": actuated,
    })
    return row


def run_case(case_id, category, predicate, mutation, row, expect):
    """Adjudicate one synthetic proposal and compare against its specified expectation."""
    t0 = time.perf_counter_ns()
    res = evaluate_decision(row, THETA)
    dt_ms = (time.perf_counter_ns() - t0) / 1e6

    observed = {k: res[k] for k in expect}
    passed = all(res[k] == v for k, v in expect.items())
    return {
        "case_id": case_id,
        "category": category,
        "predicate": predicate,
        "mutation": mutation,
        "expected": expect,
        "observed": observed,
        "decision": res["decision"],
        "gamma_g": res["gamma_g"],
        "gamma_class": res["gamma_class"],
        "deficit_count": res["deficit_count"],
        "pi": res["pi"],
        "isb": res["isb"],
        "unauthorized": res["unauthorized"],
        "latency_ms": round(dt_ms, 6),
        "passed": passed,
    }


def build_cases():
    cases = []
    cid = 0

    # ---- 0. Baseline control: everything concurs -> PERMIT ---------------------------------
    cid += 1
    cases.append(("C%03d" % cid, "control", "(none)", "all predicates concur",
                  clean_row(), {"decision": "PERMIT", "gamma_g": 0, "gamma_class": 0,
                                "deficit_count": 0, "pi": 1, "isb": 1}))

    # ---- 1. Each node gate, falsified in isolation -> SAFE_STATE, exactly one deficit -------
    for g in NODE_GATE_COLS:
        cid += 1
        row = clean_row()
        row[g] = False
        # TOKEN_VALID / AuthoritySignatureValid are ALSO ISB conjuncts, so ISB drops to 0 too.
        expect = {"decision": "SAFE_STATE", "gamma_g": 1, "gamma_class": 0,
                  "deficit_count": 1, "pi": 0}
        expect["isb"] = 0 if g in ("TOKEN_VALID", "AuthoritySignatureValid") else 1
        cases.append(("C%03d" % cid, "node_gate", g, f"{g} = FALSE", row, expect))

    # ---- 2. Each derived deficit, triggered in isolation -----------------------------------
    for name, (field, value, rule) in DERIVED_DEFICITS.items():
        cid += 1
        row = clean_row()
        row[field] = value
        expect = {"decision": "SAFE_STATE", "gamma_g": 1, "gamma_class": 0,
                  "deficit_count": 1, "pi": 0}
        # STALE_CONTEXT and TELEMETRY_STALE are also ISB conjuncts.
        expect["isb"] = 0 if name in ("STALE_CONTEXT", "TELEMETRY_STALE") else 1
        cases.append(("C%03d" % cid, "derived_deficit", name, rule, row, expect))

    # ---- 3. Class-level veto in isolation: every node gate concurs, yet it must deny --------
    #         This is the Goodhart-resistance case: Gamma_G = 0 but Gamma_class = 1.
    for token in CLASS_VETO_TOKENS:
        cid += 1
        row = clean_row()
        row["ReasonCodes"] = f"{token};ALL_GATES_PASS"
        cases.append(("C%03d" % cid, "class_veto", f"Gamma_class::{token}",
                      f"ReasonCodes contains {token} (all node gates TRUE)", row,
                      {"decision": "SAFE_STATE", "gamma_g": 0, "gamma_class": 1,
                       "deficit_count": 0, "pi": 0, "isb": 1}))

    # ---- 4. Each ISB conjunct, falsified in isolation -> ISB = 0 ----------------------------
    for name, (field, value) in ISB_CONJUNCTS.items():
        cid += 1
        row = clean_row()
        row[field] = value
        cases.append(("C%03d" % cid, "isb_conjunct", f"ISB::{name}",
                      f"{field} = {value}", row, {"isb": 0, "pi": 0}))

    # ---- 5. Eq.7 unauthorized-execution detection -------------------------------------------
    #         An actuated proposal carrying a deficit must be flagged unauthorized.
    cid += 1
    row = clean_row(actuated=True)
    row["Gate_A1"] = False
    cases.append(("C%03d" % cid, "unauthorized_eq7", "Eq7::deficit_while_actuated",
                  "Actuated with Gate_A1 = FALSE", row,
                  {"unauthorized": True, "decision": "SAFE_STATE"}))

    cid += 1
    row = clean_row(actuated=True)
    row["ReasonCodes"] = "CLASS_1_FRAUD"
    cases.append(("C%03d" % cid, "unauthorized_eq7", "Eq7::class_veto_while_actuated",
                  "Actuated with class veto raised", row,
                  {"unauthorized": True, "decision": "SAFE_STATE"}))

    #         A clean actuated proposal must NOT be flagged (guards against trivial detection).
    cid += 1
    cases.append(("C%03d" % cid, "unauthorized_eq7", "Eq7::clean_actuated_control",
                  "Actuated, all predicates concur", clean_row(actuated=True),
                  {"unauthorized": False, "decision": "PERMIT"}))

    return cases


def main(write: bool = True):
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.time()
    cases = build_cases()
    results = [run_case(*c) for c in cases]

    # ---- coverage accounting -----------------------------------------------------------------
    # A predicate is COVERED when it has been observed in both polarities: concurring (in the
    # control / every other case) and falsified in isolation (its own case).
    node_gate_cases = {r["predicate"] for r in results if r["category"] == "node_gate" and r["passed"]}
    derived_cases = {r["predicate"] for r in results if r["category"] == "derived_deficit" and r["passed"]}
    control_ok = all(r["passed"] for r in results if r["category"] == "control")

    covered_gates = sorted(node_gate_cases) if control_ok else []
    covered_derived = sorted(derived_cases) if control_ok else []

    total_predicates = len(NODE_GATE_COLS) + len(DERIVED_DEFICITS)
    covered = len(covered_gates) + len(covered_derived)
    coverage_rate = covered / total_predicates if total_predicates else 0.0

    # ---- single-deficit denial: the per-predicate I3 result ----------------------------------
    isolation = [r for r in results if r["category"] in ("node_gate", "derived_deficit")]
    denied = sum(1 for r in isolation if r["decision"] == "SAFE_STATE" and r["deficit_count"] == 1)
    # wilson_interval returns (point, lower, upper); previously mis-unpacked as (lo, hi, p), which
    # transposed the bounds in the emitted artifact (low=1.0 > high=0.772). Values were correct,
    # fields were swapped. Fixed ordering here changes no number.
    p, lo, hi = wilson_interval(denied, len(isolation))

    veto = [r for r in results if r["category"] == "class_veto"]
    veto_denied = sum(1 for r in veto if r["decision"] == "SAFE_STATE" and r["gamma_g"] == 0)

    isb = [r for r in results if r["category"] == "isb_conjunct"]
    isb_zeroed = sum(1 for r in isb if r["isb"] == 0)

    eq7 = [r for r in results if r["category"] == "unauthorized_eq7"]
    eq7_ok = sum(1 for r in eq7 if r["passed"])

    n_pass = sum(1 for r in results if r["passed"])
    lat = sorted(r["latency_ms"] for r in results)
    duration = time.time() - t0

    report = {
        "experiment": "E9_runtime_predicate_coverage",
        "scope": ("SYNTHETIC deterministic suite over the FROZEN evaluate_decision entry point. "
                  "Establishes that every runtime predicate is wired into the decision correctly "
                  "and that each, alone, denies. Does NOT claim the ULB corpus exercises them."),
        "engine_entrypoint": "gamma_test_runner.evaluate_decision (frozen, imported not modified)",
        "theta": THETA,
        "deterministic": True,
        "seed_required": False,
        "started_utc": started,
        "duration_s": round(duration, 4),

        "control": {
            "clean_proposal_permits": control_ok,
            "note": ("Without this the coverage result would be trivially satisfiable by an engine "
                     "that denies everything."),
        },

        "predicate_coverage": {
            "definition": ("A predicate is covered when observed in BOTH polarities: concurring (in "
                           "the clean control) and falsified in isolation (its own case)."),
            "node_gates_total": len(NODE_GATE_COLS),
            "node_gates_covered": len(covered_gates),
            "derived_deficits_total": len(DERIVED_DEFICITS),
            "derived_deficits_covered": len(covered_derived),
            "total_predicates": total_predicates,
            "covered": covered,
            "coverage_rate": round(coverage_rate, 6),
            "uncovered": sorted(
                (set(NODE_GATE_COLS) | set(DERIVED_DEFICITS)) - set(covered_gates) - set(covered_derived)
            ),
            "covered_node_gates": covered_gates,
            "covered_derived_deficits": covered_derived,
        },

        "single_deficit_isolation": {
            "property": "I3 non-compensatory soundness, tested per predicate",
            "statement": ("With nine predicates concurring, ONE deficit must still deny "
                          "(deficit_count == 1 and decision == SAFE_STATE)."),
            "n": len(isolation),
            "denied": denied,
            "denial_rate": round(p, 8),
            "wilson95": {"low": lo, "high": hi, "n": len(isolation), "successes": denied},
            "false_permits": len(isolation) - denied,
        },

        "class_veto_isolation": {
            "property": "I4 class-level veto adequacy / Goodhart resistance",
            "statement": "Every node gate concurs (Gamma_G = 0) yet the class veto denies.",
            "n": len(veto),
            "denied_with_gamma_g_zero": veto_denied,
            "tokens_tested": CLASS_VETO_TOKENS,
        },

        "isb_conjunct_isolation": {
            "property": "Execution binding",
            "statement": "Each ISB conjunct, falsified alone, drives ISB to 0.",
            "n": len(isb),
            "isb_zeroed": isb_zeroed,
            "conjuncts_tested": sorted(ISB_CONJUNCTS),
        },

        "unauthorized_execution_eq7": {
            "property": "Eq.7 unauthorized-execution detection",
            "n": len(eq7),
            "cases_passed": eq7_ok,
            "includes_negative_control": True,
        },

        "latency_ms": {
            "n": len(lat),
            "min": lat[0] if lat else None,
            "max": lat[-1] if lat else None,
            "mean": round(sum(lat) / len(lat), 6) if lat else None,
            "median": lat[len(lat) // 2] if lat else None,
            "note": "Per-case adjudication cost, no ledger write. Not comparable to E1's timed path.",
        },

        "aggregate": {
            "n_cases": len(results),
            "cases_passed": n_pass,
            "cases_failed": len(results) - n_pass,
            "all_cases_pass": n_pass == len(results),
            "coverage_complete": coverage_rate == 1.0,
        },

        "cases": results,
    }

    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "predicate_coverage.json").write_text(json.dumps(report, indent=2))
        with (OUT / "predicate_coverage.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["case_id", "category", "predicate", "mutation", "decision", "gamma_g",
                        "gamma_class", "deficit_count", "pi", "isb", "unauthorized", "passed"])
            for r in results:
                w.writerow([r["case_id"], r["category"], r["predicate"], r["mutation"], r["decision"],
                            r["gamma_g"], r["gamma_class"], r["deficit_count"], r["pi"], r["isb"],
                            r["unauthorized"], r["passed"]])
        with (OUT / "predicate_coverage_log.jsonl").open("w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")

    pc = report["predicate_coverage"]
    print(f"[E9] cases {n_pass}/{len(results)} pass · predicate coverage "
          f"{pc['covered']}/{pc['total_predicates']} = {pc['coverage_rate'] * 100:.1f}%")
    print(f"[E9] single-deficit denial {denied}/{len(isolation)} · class veto {veto_denied}/{len(veto)} "
          f"· ISB {isb_zeroed}/{len(isb)} · Eq.7 {eq7_ok}/{len(eq7)}")
    if pc["uncovered"]:
        print(f"[E9] UNCOVERED: {pc['uncovered']}")
    return report


def run(write: bool = True):
    return main(write=write)


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["aggregate"]["all_cases_pass"] and rep["aggregate"]["coverage_complete"] else 1)
