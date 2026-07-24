"""Runtime Context + Replay latency profiling (Table 10 completion) --- ADDITIVE, timers only.

The existing per-stage profiler isolates build / bind / adapt / eval / emit but NOT the Runtime
Context plane (RCL FreshnessClock + CommitActuateJournal) nor the Replay manifest generation. This
campaign isolates both by WRAPPING TIMERS around the frozen callables (no frozen logic modified):

  * Runtime Context latency = accumulated time inside FreshnessClock.{context_age,telemetry_age} and
    CommitActuateJournal.{record_commit,record_actuate,commit_reading,actuate_reading,
    ordering_observation} while running the frozen `run_pipeline` with injected plane-B timing.
  * Replay latency = time of the frozen `write_replay_manifest` (via write_pipeline_manifest).

Every number is measured on this host. The wrappers call the original method and return its unchanged
value; only elapsed time is recorded.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import numpy as np

from ._util import write_json, write_text
from runtime_context import context_objects as _ctx
from runtime_context.class_blind_pipeline import run_pipeline, write_pipeline_manifest

_RC_METHODS = {
    _ctx.FreshnessClock: ["context_age", "telemetry_age"],
    _ctx.CommitActuateJournal: ["record_commit", "record_actuate", "commit_reading",
                                "actuate_reading", "ordering_observation"],
}


class _Acc:
    def __init__(self):
        self.total = 0.0
        self.calls = 0


def _install_rc_timers(acc: _Acc):
    originals = {}
    for cls, methods in _RC_METHODS.items():
        for m in methods:
            orig = getattr(cls, m, None)
            if orig is None:
                continue
            originals[(cls, m)] = orig

            def make(orig):
                def wrapped(self, *a, **k):
                    t0 = time.perf_counter()
                    r = orig(self, *a, **k)
                    acc.total += time.perf_counter() - t0
                    acc.calls += 1
                    return r
                return wrapped
            setattr(cls, m, make(orig))
    return originals


def _restore(originals):
    for (cls, m), orig in originals.items():
        setattr(cls, m, orig)


def _workload(n: int):
    reqs, rts = [], []
    for i in range(n):
        reqs.append({"Amount": 100.0 + (i % 500), "Time": 1000 + i,
                     "V1": (i % 7) * 0.1, "V2": -(i % 5) * 0.2})
        rts.append({"decision_time": 1005.0 + i, "context_capture_time": 1000.0 + i,
                    "heartbeat_time": 1004.0 + i, "commit_time": 1006.0 + i,
                    "actuate_time": 1007.0 + i, "request_id": f"r{i}"})
    return reqs, rts


def run(outdir: str | Path, n_rows: int = 5000) -> dict:
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    reqs, rts = _workload(n_rows)

    # --- Runtime Context isolation via wrapped RCL timers ---
    acc = _Acc()
    originals = _install_rc_timers(acc)
    try:
        t0 = time.perf_counter()
        result = run_pipeline(reqs, run_id="rcprofile", runtimes=rts)
        full_pipeline_s = time.perf_counter() - t0
    finally:
        _restore(originals)
    rc_total_s = acc.total
    rc_ms_per_row = rc_total_s / n_rows * 1000.0

    # --- Replay isolation: frozen write_replay_manifest timing ---
    tmp = Path(tempfile.mkdtemp()) / "manifest.jsonl"
    t0 = time.perf_counter()
    write_pipeline_manifest(result, tmp)
    replay_s = time.perf_counter() - t0
    replay_ms_per_row = replay_s / n_rows * 1000.0

    full_ms_per_row = full_pipeline_s / n_rows * 1000.0
    denom = full_ms_per_row + replay_ms_per_row  # measured end-to-end incl. replay
    report = {
        "campaign": "runtime_context_and_replay_profiling",
        "n_rows": n_rows,
        "runtime_context": {
            "isolation": "wrapped FreshnessClock + CommitActuateJournal (timers only)",
            "rcl_calls": acc.calls,
            "latency_ms_per_row": rc_ms_per_row,
            "total_s": rc_total_s,
            "pct_of_end_to_end": (rc_ms_per_row / denom * 100.0) if denom else None,
        },
        "replay": {
            "isolation": "frozen write_replay_manifest (write_pipeline_manifest)",
            "latency_ms_per_row": replay_ms_per_row,
            "total_s": replay_s,
            "pct_of_end_to_end": (replay_ms_per_row / denom * 100.0) if denom else None,
        },
        "full_pipeline_ms_per_row_measured": full_ms_per_row,
        "end_to_end_incl_replay_ms_per_row": denom,
        "note": ("Runtime Context here = the RCL plane-B operations (freshness/velocity/commit-actuate "
                 "ordering) that ablation `without_runtime_context` disables; measured by wrapping the "
                 "frozen FreshnessClock/CommitActuateJournal with timers. Replay = the frozen ERTuple "
                 "manifest emitter. No frozen logic modified."),
    }
    write_json(out / "runtime_profile.json", report)
    write_text(out / "runtime_profile.md", _md(report))
    return report


def _md(r) -> str:
    rc, rp = r["runtime_context"], r["replay"]
    return "\n".join([
        "# Runtime Context & Replay Profiling (measured)", "",
        f"- Rows: {r['n_rows']} · end-to-end (incl. replay): {r['end_to_end_incl_replay_ms_per_row']:.5f} ms/row",
        "",
        "| stage | latency (ms/row) | % of end-to-end | isolation |",
        "|---|---|---|---|",
        f"| Runtime Context (RCL plane-B) | {rc['latency_ms_per_row']:.6f} | {rc['pct_of_end_to_end']:.2f}% | {rc['isolation']} |",
        f"| Replay (ERTuple manifest) | {rp['latency_ms_per_row']:.6f} | {rp['pct_of_end_to_end']:.2f}% | {rp['isolation']} |",
        "", f"> {r['note']}"])


if __name__ == "__main__":
    import sys
    outdir = sys.argv[1] if len(sys.argv) > 1 else "agentdojo_integration/audit_run/summary/runtime_profile"
    rep = run(outdir)
    print(f"[runtime_profile] Runtime Context: {rep['runtime_context']['latency_ms_per_row']:.6f} ms/row "
          f"({rep['runtime_context']['rcl_calls']} RCL calls); "
          f"Replay: {rep['replay']['latency_ms_per_row']:.6f} ms/row")
