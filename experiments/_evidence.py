#!/usr/bin/env python3
"""
experiments/_evidence.py — shared helpers for the publication-evidence generators & validators.
===============================================================================================

Pure standard-library. Resolves a dotted JSON pointer against a loaded artifact, evaluates a
relation spec, and derives a claim's evidence status live from the executed artifacts. No metric
value is stored here; everything is read from disk at call time.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_CACHE: dict[str, object] = {}


def load(artifact_rel: str):
    p = ROOT / artifact_rel
    if not p.exists():
        return None
    if artifact_rel not in _CACHE:
        try:
            _CACHE[artifact_rel] = json.loads(p.read_text())
        except Exception:
            _CACHE[artifact_rel] = None
    return _CACHE[artifact_rel]


def resolve(obj, pointer: str):
    """Dotted path with list indices: 'a.b.0.c' or 'levels.-1.speedup'. Returns (found, value)."""
    cur = obj
    for part in pointer.split("."):
        if cur is None:
            return (False, None)
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return (False, None)
        elif isinstance(cur, dict):
            if part not in cur:
                return (False, None)
            cur = cur[part]
        else:
            return (False, None)
    return (True, cur)


def check_relation(value, relation: str) -> bool:
    if relation == "exists":
        return value is not None
    if value is None:
        return False
    try:
        if relation == "==0":
            return float(value) == 0
        if relation == "==1.0":
            return float(value) == 1.0
        if relation == "==True":
            return value is True
        if relation == ">0":
            return float(value) > 0
        if relation == ">=1":
            return float(value) >= 1
        if relation == "is_zero":
            return float(value) == 0
        if relation.startswith("eq:"):
            return str(value) == relation[3:]
        if relation.startswith("ge:"):
            return float(value) >= float(relation[3:])
        if relation.startswith("le:"):
            return float(value) <= float(relation[3:])
    except (TypeError, ValueError):
        return False
    return False


def evaluate_claim(claim: dict) -> dict:
    """Resolve every evidence pointer live and derive a status. Returns a rich record."""
    results = []
    all_ok, any_missing = True, False
    for ev in claim.get("evidence", []):
        art = load(ev["artifact"])
        if art is None:
            results.append({**ev, "found": False, "value": None, "holds": False,
                            "note": "artifact missing"})
            all_ok = False
            any_missing = True
            continue
        found, val = resolve(art, ev["pointer"])
        holds = found and check_relation(val, ev["relation"])
        # make value JSON-serializable / short
        sval = val if isinstance(val, (int, float, str, bool, type(None))) else str(val)
        results.append({**ev, "found": found, "value": sval, "holds": holds})
        all_ok = all_ok and holds
        if not found:
            any_missing = True

    # derive status
    forced = claim.get("expected_status")
    if not claim.get("evidence"):
        status = forced or "Not Claimed"
    elif all_ok and forced and "Partially" in forced:
        status = "Partially Supported"
    elif all_ok:
        status = forced if (forced and "negative" in forced.lower()) else "Supported"
    elif any_missing:
        status = "Pending (artifact missing — run RUN_ALL_EXPERIMENTS.py)"
    else:
        status = "NOT Supported"
    return {"id": claim["id"], "statement": claim["statement"],
            "category": claim.get("category"), "paper_section": claim.get("paper_section"),
            "experiments": claim.get("experiments", []), "figures": claim.get("figures", []),
            "tables": claim.get("tables", []), "evidence_checks": results, "status": status,
            "note": claim.get("partial_reason")}


def sha256_file(artifact_rel: str) -> str | None:
    p = ROOT / artifact_rel
    if not p.exists() or p.is_dir():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def wilson_ci(successes: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return {"p": None, "low": None, "high": None, "n": 0, "successes": 0}
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / denom
    return {"p": p, "low": max(0.0, center - half), "high": min(1.0, center + half),
            "n": n, "successes": successes}


def rule_of_three(n: int):
    """For 0 events in n trials, the ~95% upper bound on the true rate is 3/n."""
    return None if n == 0 else 3.0 / n
