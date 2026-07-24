"""Bridge to the EXISTING Gamma engine. Creates NO authorization logic and defines NO mapping.

Imports gamma_test_runner.evaluate_decision (the canonical LLC decision) and translates a
frozen-manifest deficit vector into that engine's row schema. The predicate-family -> Gamma-slot
mapping is READ from the frozen Predicate Manifest via the injected PolicyLoader; this module holds
no scientific mapping of its own.

Spec: IEEE Paper Section IV-B (LLC); reuse mandate; refactor item 1 (slot map from manifest).
"""
from __future__ import annotations
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
import gamma_test_runner as _gamma  # noqa: E402  (existing Gamma engine; NOT reimplemented)

evaluate_decision = _gamma.evaluate_decision
NODE_GATE_COLS = _gamma.NODE_GATE_COLS
METHOD_VERSION = _gamma.METHOD_VERSION


class GammaBridge:
    """Translate {frozen_family: deficit} -> Gamma row -> REUSED evaluate_decision."""

    def __init__(self, binding):
        self.binding = binding  # ExecutionBinding (Layer 2); supplies the family -> gamma_slot map

    def decide(self, deficits: dict, harm_threshold: float = 0.5) -> dict:
        row = {c: True for c in NODE_GATE_COLS}
        row.update({
            "HARM_RISK": 0.0, "StaleContext": False, "TelemetryFresh": True,
            "ReasonCodes": "NONE", "Actuated": False, "ACT_PERMIT": False,
            "TOKEN_VALID": True, "AuthoritySignatureValid": True,
        })
        for fam, d in deficits.items():
            if d != 1:
                continue
            slot = self.binding.family_slot(fam)         # <-- mapping comes from the Execution Binding Manifest
            if slot == "__TOKEN_VALID__":
                row["TOKEN_VALID"] = False
            elif slot == "__StaleContext__":
                row["StaleContext"] = True
            elif slot == "__ReasonCodes_CLASS__":
                row["ReasonCodes"] = "CLASS_1"
            elif slot == "__aggregator__":
                pass                                     # GAMMA is the LLC aggregator, not a node predicate
            elif slot in row:
                row[slot] = False
        return evaluate_decision(row, harm_threshold)
