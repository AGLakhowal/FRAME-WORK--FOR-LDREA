#!/usr/bin/env python3
"""
INDEPENDENT VERIFIER  (Phase 3 — Formal Specification Verification)
===================================================================

A SECOND, from-scratch implementation of the L-DREA / Gamma Law-of-Concurrence
authorization equations, transcribed DIRECTLY from the paper / README prose —
NOT from the shipped code.

It NEVER imports the reference `evaluate_decision` logic to *produce* its own
answers.  It re-implements the equations, then it exhaustively enumerates the
entire reachable boolean input space and compares its independent answer against
the frozen `gamma_test_runner.evaluate_decision` on every single state.

This file is a NEW verification artifact.  It modifies NOTHING in the frozen
implementation; it only reads `evaluate_decision` as an oracle to test against.

Reference equations (paper §IV-B "Law of Concurrence", §VIII-C Eq.7; README §7/§8):

    d_i         = 1 iff node predicate g_i fails            (g_i FALSE -> deficit)
    d_harm      = 1 iff HARM_RISK > theta
    d_stale     = 1 iff StaleContext
    d_telem     = 1 iff NOT TelemetryFresh
    Gamma_G     = max over {d_i, d_harm, d_stale, d_telem}   (non-compensatory)
    Gamma_class = 1 iff ReasonCodes contains CLASS_1 or GOODHART
    Pi          = 1 iff (Gamma_G == 0 AND Gamma_class == 0)
    decision    = PERMIT iff Pi == 1 else SAFE_STATE
    ISB         = TOKEN_VALID AND AuthoritySignatureValid
                          AND TelemetryFresh AND (NOT StaleContext)
    execute     = Actuated OR ACT_PERMIT
    unauthorized= execute AND ( NOT TOKEN_VALID OR Gamma_G != 0
                          OR Gamma_class != 0 OR ISB == 0 )

Node predicates (the frozen NODE_GATE_COLS):
    Gate_A1..Gate_A7, Lambda_G, TOKEN_VALID, AuthoritySignatureValid
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

# The 10 node gate columns, transcribed from the paper (NOT read from the module
# for the reference computation; hard-listed here so the two are independent).
REF_GATES = [
    "Gate_A1", "Gate_A2", "Gate_A3", "Gate_A4", "Gate_A5", "Gate_A6", "Gate_A7",
    "Lambda_G", "TOKEN_VALID", "AuthoritySignatureValid",
]


def reference_decision(row: dict, theta: float) -> dict:
    """Independent reimplementation of the paper equations. No shipped code used."""
    # Gamma_G = max_i d_i  (binary deficits -> logical OR)
    deficit_sources = []
    for g in REF_GATES:
        deficit_sources.append(0 if row[g] else 1)          # gate FALSE -> deficit
    deficit_sources.append(1 if row["HARM_RISK"] > theta else 0)
    deficit_sources.append(1 if row["StaleContext"] else 0)
    deficit_sources.append(0 if row["TelemetryFresh"] else 1)

    gamma_g = max(deficit_sources)                          # non-compensatory
    deficit_count = sum(deficit_sources)

    reason = str(row["ReasonCodes"]).upper()
    gamma_class = 1 if ("CLASS_1" in reason or "GOODHART" in reason) else 0

    pi = 1 if (gamma_g == 0 and gamma_class == 0) else 0
    decision = "PERMIT" if pi == 1 else "SAFE_STATE"

    isb = 1 if (
        row["TOKEN_VALID"] and row["AuthoritySignatureValid"]
        and row["TelemetryFresh"] and (not row["StaleContext"])
    ) else 0

    execute = bool(row["Actuated"] or row["ACT_PERMIT"])
    unauthorized = execute and (
        (not row["TOKEN_VALID"]) or gamma_g != 0 or gamma_class != 0 or isb == 0
    )
    return {
        "gamma_g": gamma_g,
        "gamma_class": gamma_class,
        "deficit_count": deficit_count,
        "pi": pi,
        "isb": isb,
        "decision": decision,
        "unauthorized": unauthorized,
    }


def build_state(bits: dict) -> dict:
    """Materialize a full engine row from the 16 independent boolean toggles."""
    row = {}
    # 8 pure gates (A1..A7, Lambda_G)
    for g in ["Gate_A1", "Gate_A2", "Gate_A3", "Gate_A4", "Gate_A5", "Gate_A6",
              "Gate_A7", "Lambda_G"]:
        row[g] = bits[g]
    row["TOKEN_VALID"] = bits["TOKEN_VALID"]
    row["AuthoritySignatureValid"] = bits["AuthoritySignatureValid"]
    # HARM deficit toggle -> a concrete HARM_RISK either side of theta=0.5
    row["HARM_RISK"] = 0.8 if bits["HARM_OVER"] else 0.0
    row["StaleContext"] = bits["StaleContext"]
    row["TelemetryFresh"] = bits["TelemetryFresh"]
    row["ReasonCodes"] = "CLASS_1" if bits["CLASS"] else "NONE"
    row["Actuated"] = bits["Actuated"]
    row["ACT_PERMIT"] = bits["ACT_PERMIT"]
    return row


# The 16 independent boolean dimensions of the engine input.
DIMS = [
    "Gate_A1", "Gate_A2", "Gate_A3", "Gate_A4", "Gate_A5", "Gate_A6", "Gate_A7",
    "Lambda_G", "TOKEN_VALID", "AuthoritySignatureValid",
    "HARM_OVER", "StaleContext", "TelemetryFresh", "CLASS",
    "Actuated", "ACT_PERMIT",
]

FIELDS = ["gamma_g", "gamma_class", "deficit_count", "pi", "isb", "decision",
          "unauthorized"]


def main() -> int:
    repo = Path(__file__).resolve().parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import gamma_test_runner as _gamma  # ORACLE ONLY — reference answers are ours.
    oracle = _gamma.evaluate_decision

    # Guard: confirm the frozen NODE_GATE_COLS equals our independent transcription.
    gate_match = list(_gamma.NODE_GATE_COLS) == REF_GATES

    theta = 0.5
    total = 0
    mismatches = []
    field_mismatch = {f: 0 for f in FIELDS}
    # reachable-decision bookkeeping (Gamma_G, Gamma_class) -> Pi/decision
    decision_table = {}
    permit_states = 0
    safe_states = 0
    unauth_true = 0

    for combo in itertools.product([False, True], repeat=len(DIMS)):
        bits = dict(zip(DIMS, combo))
        row = build_state(bits)
        ref = reference_decision(row, theta)
        got = oracle(dict(row), theta)   # pass a copy; oracle must not mutate semantics
        total += 1

        # per-field comparison across the full result dict
        row_mismatch = {}
        for f in FIELDS:
            if bool(ref[f]) != bool(got[f]) if f == "unauthorized" else ref[f] != got[f]:
                field_mismatch[f] += 1
                row_mismatch[f] = {"reference": ref[f], "implementation": got[f]}
        if row_mismatch:
            if len(mismatches) < 50:
                mismatches.append({"bits": bits, "fields": row_mismatch})

        # decision-space coverage keyed on the abstract (Gamma_G, Gamma_class)
        key = (ref["gamma_g"], ref["gamma_class"])
        decision_table.setdefault(key, {"pi": ref["pi"], "decision": ref["decision"],
                                        "count": 0})
        decision_table[key]["count"] += 1
        if ref["decision"] == "PERMIT":
            permit_states += 1
        else:
            safe_states += 1
        if ref["unauthorized"]:
            unauth_true += 1

    # Abstract (Gamma_G, Gamma_class) space has 4 cells; enumerate reachable vs not.
    all_cells = [(0, 0), (0, 1), (1, 0), (1, 1)]
    reachable = sorted(decision_table.keys())
    unreachable = [c for c in all_cells if c not in decision_table]

    total_field_mismatches = sum(field_mismatch.values())
    result = {
        "verifier": "independent_verifier.py",
        "oracle": "gamma_test_runner.evaluate_decision (frozen)",
        "theta": theta,
        "independent_gate_list_matches_frozen": gate_match,
        "input_dimensions": len(DIMS),
        "total_states_enumerated": total,
        "expected_states": 2 ** len(DIMS),
        "coverage_complete": total == 2 ** len(DIMS),
        "total_row_mismatches": len(mismatches) if len(mismatches) < 50 else ">=50",
        "total_field_mismatches": total_field_mismatches,
        "per_field_mismatch_counts": field_mismatch,
        "permit_states": permit_states,
        "safe_state_states": safe_states,
        "unauthorized_true_states": unauth_true,
        "decision_table": {
            f"Gamma_G={k[0]},Gamma_class={k[1]}": v
            for k, v in sorted(decision_table.items())
        },
        "reachable_abstract_cells": [f"Gamma_G={c[0]},Gamma_class={c[1]}" for c in reachable],
        "unreachable_abstract_cells": [f"Gamma_G={c[0]},Gamma_class={c[1]}" for c in unreachable],
        "sample_mismatches": mismatches,
        "verdict": (
            "IDENTICAL" if total_field_mismatches == 0 and gate_match
            else "MISMATCH_FOUND"
        ),
    }
    out = repo / "independent_verifier_report.json"
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("sample_mismatches", "decision_table")}, indent=2))
    print(f"\n[written] {out}")
    return 0 if result["verdict"] == "IDENTICAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
