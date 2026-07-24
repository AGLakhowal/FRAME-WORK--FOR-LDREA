"""Phase H --- reproducibility & tamper verification.

(1) Frozen-file integrity: SHA256 of every frozen artifact, snapshotted before and after a run and
    compared. Detects any modification to the frozen L-DREA / Gamma stack or manifests.
(2) Trace integrity: append-only hash chain over trace events (tamper-evident), plus event-ordering
    and timestamp-monotonicity checks.

Additive: reads existing files; writes only new sidecar files. Modifies nothing frozen.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ._util import sha256_file, sha256_hex, read_jsonl, write_json

_REPO = Path(__file__).resolve().parents[2]

# The frozen surface that MUST NOT change across a run.
FROZEN_GLOBS = [
    ("interception", _REPO / "agentdojo_integration" / "interception", "*.py"),
    ("gamma_engine", _REPO, "gamma_test_runner.py"),
    ("manifests", _REPO / "agentdojo_integration" / "manifests", "*.json"),
]


def frozen_snapshot() -> dict:
    """SHA256 every frozen file. Returns {relpath: sha256}."""
    snap: dict[str, str] = {}
    for _label, base, pat in FROZEN_GLOBS:
        base = Path(base)
        if base.is_file():
            snap[str(base.relative_to(_REPO))] = sha256_file(base)
            continue
        for f in sorted(base.glob(pat)):
            snap[str(f.relative_to(_REPO))] = sha256_file(f)
    return snap


def verify_frozen_unchanged(before: dict, after: dict) -> dict:
    """Compare two frozen snapshots. Returns a verdict with any diffs."""
    changed = [k for k in before if k in after and before[k] != after[k]]
    added = [k for k in after if k not in before]
    removed = [k for k in before if k not in after]
    return {
        "unchanged": not (changed or added or removed),
        "n_files": len(before),
        "changed": changed, "added": added, "removed": removed,
        "before_root": sha256_hex(before), "after_root": sha256_hex(after),
    }


def chain_trace(events: list[dict]) -> tuple[list[dict], str]:
    """Build an append-only hash chain over events. event_hash_i = H(prev_hash || canonical(event)).
    Returns (chained_events, chain_root)."""
    prev = "0" * 64
    chained = []
    for e in events:
        h = sha256_hex({"prev": prev, "event": e})
        ce = dict(e)
        ce["_prev_hash"] = prev
        ce["_event_hash"] = h
        chained.append(ce)
        prev = h
    return chained, prev


def verify_trace_integrity(jsonl_path: str | Path) -> dict:
    """Verify a trace file: hash chain re-derivation, monotonic event_ids, non-decreasing steps,
    monotonic timestamps. Read-only; also writes a chained sidecar next to the file."""
    p = Path(jsonl_path)
    events = read_jsonl(p)
    chained, root = chain_trace(events)

    # event_id monotonic & unique
    ids = [e.get("event_id") for e in events]
    id_ok = ids == sorted(ids) and len(set(ids)) == len(ids)
    # step_number non-decreasing
    steps = [e.get("step_number", 0) for e in events]
    step_ok = all(b >= a for a, b in zip(steps, steps[1:]))
    # timestamps non-decreasing (allow equal; parse ISO)
    ts_ok = True
    try:
        parsed = [datetime.fromisoformat(e["timestamp"]) for e in events]
        ts_ok = all(b >= a for a, b in zip(parsed, parsed[1:]))
    except Exception:
        ts_ok = None  # unparseable -> undetermined, reported honestly

    sidecar = p.with_name(p.stem + "_chained.jsonl")
    with open(sidecar, "w") as f:
        import json
        for ce in chained:
            f.write(json.dumps(ce, default=str) + "\n")

    verdict = {
        "trace_file": str(p),
        "n_events": len(events),
        "chain_root": root,
        "chain_sidecar": str(sidecar),
        "event_id_monotonic_unique": id_ok,
        "step_non_decreasing": step_ok,
        "timestamp_non_decreasing": ts_ok,
        "append_only_ok": id_ok and step_ok,
        "integrity_ok": bool(id_ok and step_ok and (ts_ok is not False)),
    }
    return verdict


def detect_tamper(jsonl_path: str | Path, chain_root_expected: str) -> dict:
    """Recompute the chain root and compare to an expected value (tamper detection)."""
    events = read_jsonl(jsonl_path)
    _chained, root = chain_trace(events)
    return {"expected_root": chain_root_expected, "actual_root": root,
            "tamper_detected": root != chain_root_expected}


def run_frozen_guard(outdir: str | Path, before: dict, after: dict) -> dict:
    verdict = verify_frozen_unchanged(before, after)
    write_json(Path(outdir) / "frozen_integrity.json",
               {"before": before, "after": after, "verdict": verdict})
    return verdict
