#!/usr/bin/env python3
"""Intercept AgentDojo-style execution requests and return PERMIT or SAFE_STATE."""

from __future__ import annotations

from typing import Any, Dict

from external_validation.agentdojo_adapter import run_scenario


def intercept(action: Dict[str, Any]) -> Dict[str, Any]:
    """The minimal interception point for an AgentDojo-style tool call."""
    return run_scenario(action)
