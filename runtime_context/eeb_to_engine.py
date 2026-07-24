#!/usr/bin/env python3
"""EEB -> engine input adapter (Commit 4.1) — PURE CONSUMER.

Reads decision-consumed values OUT of an already-constructed Execution Evidence Bundle and
writes them into the exact column names the FROZEN decision logic in gamma_test_runner.py reads.
This module performs one thing only:

    Execution Evidence Bundle  ->  field extraction  ->  engine schema

It NEVER constructs an EEB, and it never interprets, normalizes, infers, repairs, thresholds,
authorizes, or computes Gamma / SAFE_STATE / predicates. Construction of EEBs (the controlled
equivalence arm) is not a production concern of the adapter — it lives with the caller (the
runner's opt-in branch and the equivalence tests).

Scope (binding, Commit 4.1): targets ONLY the decision-consumed schema for Gamma_G / Pi /
Decision — the inputs evaluate_decision() reads for gamma_g/pi: NODE_GATE_COLS, HARM_RISK,
StaleContext, TelemetryFresh, ReasonCodes. It does NOT recreate all engine columns or BOOL_COLS.

Decoupling: imports only the EEB type (2.1), for typing. It does NOT import gamma_test_runner
(no cycle); the engine passes its own NODE_GATE_COLS ordering in.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence

from .execution_evidence_bundle import ExecutionEvidenceBundle  # typing only

# Non-gate decision-consumed columns (Gamma_G / Pi / Decision inputs).
HARM_COL = "HARM_RISK"
STALE_COL = "StaleContext"
FRESH_COL = "TelemetryFresh"
VETO_COL = "ReasonCodes"


def decision_inputs_from_eeb(eeb: ExecutionEvidenceBundle,
                             node_gate_cols: Sequence[str]) -> Dict[str, Any]:
    """PURE REMAP: read the decision-consumed values out of a sealed EEB.

    Returns a dict keyed by the engine's column names, each value extracted VERBATIM via `.value`
    (no interpretation, threshold, or type change). `node_gate_cols` is supplied by the engine so
    this module needs no import from gamma_test_runner (no cycle).
    """
    p = eeb.payload
    out: Dict[str, Any] = {}
    for i, g in enumerate(node_gate_cols):
        out[g] = p.node_predicate_vector[i].value            # gate booleans, verbatim
    out[HARM_COL] = p.harm_risk_score.value                  # number, verbatim
    out[STALE_COL] = p.stale_context.value                   # boolean, verbatim (NOT a delta)
    out[FRESH_COL] = p.telemetry_fresh.value                 # boolean, verbatim
    # -- LEGACY COMPATIBILITY CARRIER (temporary, Commit 4.1 only) --------------------------- #
    # The frozen engine derives Gamma_class from the ReasonCodes string. For the controlled
    # zero-logic-diff arm we read that existing veto input back through class_veto_evidence,
    # carried VERBATIM. This is a LEGACY-COMPATIBILITY carrier ONLY: it is temporary, exists
    # solely for Commit 4.1 equivalence validation, is NOT part of the Runtime Evidence
    # Architecture, and is NOT a runtime evidence source. Phase 5 replaces the ReasonCodes-based
    # veto with a genuine non-Class governance signal; do not build on this carrier.
    out[VETO_COL] = p.class_veto_evidence.value              # ReasonCodes string, verbatim
    return out


def overlay_decision_inputs(df, eebs: Iterable[ExecutionEvidenceBundle],
                            node_gate_cols: Sequence[str]):
    """Overlay ONLY the decision-consumed columns of `df` with values CONSUMED from `eebs`.

    `eebs` is an iterable of already-constructed EEBs aligned to `df`'s rows (the adapter does
    not build them). For each EEB the decision inputs are extracted via the pure remap and
    overlaid onto a copy of `df`; every other column (replay, ordering, latency, ...) is left
    exactly as-is. Because values are carried verbatim, the frozen decision yields identical
    Gamma_G / Pi / Decision.
    """
    cols: List[str] = list(node_gate_cols) + [HARM_COL, STALE_COL, FRESH_COL, VETO_COL]
    extracted: Dict[str, list] = {c: [] for c in cols}
    n = 0
    for eeb in eebs:
        vals = decision_inputs_from_eeb(eeb, node_gate_cols)
        for c in cols:
            extracted[c].append(vals[c])
        n += 1
    if n != len(df):
        raise ValueError("overlay_decision_inputs: %d EEBs for %d rows (must be row-aligned)"
                         % (n, len(df)))
    out = df.copy()
    for c in cols:
        out[c] = extracted[c]
    return out
