#!/usr/bin/env python3
"""Per-process clock-offset probe — real measurement, honestly scoped (Table 10).

Spawns N real OS processes. The coordinator asks each for a paired (CLOCK_MONOTONIC, wall) reading
and computes the offset between the coordinator's clock and the child's, correcting for half the
IPC round-trip. This is a GENUINE measurement.

WHAT IT IS: single-host, per-process clock read offset dominated by IPC latency and scheduler jitter.
WHAT IT IS NOT: distributed clock skew or IEEE-1588 PTP synchronization. On one machine there is one
system clock, so there is no clock skew to measure. Distributed skew requires >= 2 physical hosts and
a PTP grandmaster. Every field is labelled accordingly.

    python experiments/clock_offset_probe.py
"""
from __future__ import annotations

import json
import multiprocessing as mp
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "production_evidence" / "clock_offset_report.json"
N_NODES = 3
ROUNDS = 200


def mono_ns():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def _worker(node_id, req_q, rep_q):
    while True:
        m = req_q.get()
        if m == "stop":
            return
        rep_q.put({"node": node_id, "worker_mono_ns": mono_ns(), "worker_wall_ns": time.time_ns()})


def run() -> dict:
    ctx = mp.get_context("spawn")
    reqs = [ctx.Queue() for _ in range(N_NODES)]
    rep_q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(i, reqs[i], rep_q)) for i in range(N_NODES)]
    for p in procs:
        p.start()

    per_node = {i: [] for i in range(N_NODES)}
    rtts = {i: [] for i in range(N_NODES)}
    for _ in range(ROUNDS):
        for i in range(N_NODES):
            t0 = mono_ns()
            reqs[i].put("go")
            r = rep_q.get()
            t1 = mono_ns()
            rtt = t1 - t0
            # coordinator midpoint of the round trip, minus the worker's reading
            coord_mid = t0 + rtt / 2
            offset_ms = (coord_mid - r["worker_mono_ns"]) / 1e6
            per_node[r["node"]].append(offset_ms)
            rtts[r["node"]].append(rtt / 1e6)

    for i in range(N_NODES):
        reqs[i].put("stop")
    for p in procs:
        p.join(timeout=5)

    def st(v):
        return {"mean": statistics.fmean(v), "min": min(v), "max": max(v),
                "p50": sorted(v)[len(v) // 2], "stdev": statistics.pstdev(v)}

    nodes = {f"node_{i}": {"offset_ms": st(per_node[i]), "rtt_ms": st(rtts[i]),
                           "samples": len(per_node[i])} for i in range(N_NODES)}
    all_off = [x for i in range(N_NODES) for x in per_node[i]]
    return {
        "experiment": "clock_offset_probe",
        "evidence_level": "Measured Runtime (single-host per-process offset)",
        "what_it_is": ("per-process CLOCK_MONOTONIC read offset between coordinator and each child "
                       "process, half-RTT corrected; dominated by IPC latency and scheduler jitter"),
        "what_it_is_not": ("distributed clock skew or IEEE-1588 PTP synchronization. One host = one "
                           "system clock = no skew to measure. Distributed skew needs >=2 physical "
                           "hosts and a PTP grandmaster."),
        "nodes_processes": N_NODES, "rounds": ROUNDS,
        "per_node": nodes,
        "aggregate_offset_ms": st(all_off),
        "max_abs_offset_ms": max(abs(x) for x in all_off),
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rep = run()
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    ag = rep["aggregate_offset_ms"]
    print(f"[clock-offset] {rep['nodes_processes']} processes x {rep['rounds']} rounds")
    for k, v in rep["per_node"].items():
        print(f"  {k}: offset mean {v['offset_ms']['mean']:.4f} ms, rtt mean {v['rtt_ms']['mean']:.4f} ms")
    print(f"[clock-offset] aggregate offset mean {ag['mean']:.4f} ms, max|off| {rep['max_abs_offset_ms']:.4f} ms")
    print("[clock-offset] single-host IPC/scheduler offset — NOT distributed PTP skew")
    return 0


if __name__ == "__main__":
    sys.exit(main())
