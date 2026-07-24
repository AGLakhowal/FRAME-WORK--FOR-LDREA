#!/usr/bin/env python3
"""Adapter that maps AgentDojo-style actions into Gamma/L-DREA EEA objects."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List


def _canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def build_eea(action: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an AgentDojo action into an Externally Effective Action (EEA)."""
    tool_name = str(action.get("tool", "unknown")).lower()
    target = str(action.get("target", "unknown"))
    user = str(action.get("user", "agent"))
    metadata = action.get("metadata") or {}
    risk = str(metadata.get("risk", "low")).lower()
    amount = float(action.get("amount", 0.0))

    action_type = "financial" if "purchase" in tool_name or "transfer" in tool_name else "file" if "file" in tool_name else "comm" if "email" in tool_name else "db" if "database" in tool_name else "system" if "command" in tool_name else "observation"
    sensitivity = "high" if action_type in {"financial", "system"} or risk == "high" or amount >= 100 else "medium" if action_type in {"file", "db", "comm"} else "low"

    # Conservative Gamma-style mapping for an external validation harness.
    # A single sensitive or high-risk action is denied by SAFE_STATE.
    decision = "SAFE_STATE" if sensitivity == "high" else "PERMIT"
    token_valid = bool(action.get("token_valid", True))
    telemetry_fresh = bool(action.get("telemetry_fresh", True))
    stale_context = bool(action.get("stale_context", False))
    authority_required = bool(action.get("authority_required", True))

    eea = {
        "action_type": action_type,
        "sensitivity": sensitivity,
        "tool": tool_name,
        "target": target,
        "user": user,
        "risk": risk,
        "amount": amount,
        "token_valid": token_valid,
        "telemetry_fresh": telemetry_fresh,
        "stale_context": stale_context,
        "authority_required": authority_required,
        "decision": decision,
        "policy": "gamma_g0",
        "evidence": {
            "method": "agentdojo_adapter",
            "policy_hash": hashlib.sha256(b"gamma-g0-agentdojo").hexdigest(),
        },
    }
    return eea


def evaluate_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a candidate action through the Gamma/L-DREA runtime style."""
    eea = build_eea(action)
    # Evaluate the same core predicate bundle used by the Gamma runtime.
    # The policy here is intentionally conservative to preserve fail-closed behavior.
    gamma_g = 1 if eea["sensitivity"] == "high" else 0
    gamma_class = 1 if str(action.get("metadata", {}).get("risk", "")).lower() == "high" else 0
    pi = 1 if (gamma_g == 0 and gamma_class == 0 and eea["token_valid"] and eea["telemetry_fresh"] and not eea["stale_context"] and eea["authority_required"]) else 0
    decision = "PERMIT" if pi == 1 else "SAFE_STATE"
    return {
        "decision": decision,
        "policy": eea["policy"],
        "gamma_g": gamma_g,
        "gamma_class": gamma_class,
        "eea": eea,
        "decision_hash": hashlib.sha256(_canonical_json({"action": action, "decision": decision}).encode()).hexdigest(),
    }


def run_scenario(action: Dict[str, Any]) -> Dict[str, Any]:
    """Runtime bridge wrapper around evaluation and evidence capture."""
    result = evaluate_action(action)
    return {
        **result,
        "timestamp": int(time.time() * 1000),
        "audit": {
            "kind": "agentdojo_runtime_bridge",
            "outcome": result["decision"],
            "recorded": True,
        },
    }
