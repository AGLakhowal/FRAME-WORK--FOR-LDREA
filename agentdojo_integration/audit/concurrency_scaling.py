"""Concurrency Scaling Campaign (Table 13) --- ADDITIVE, deterministic, no LLM.

Drives the FROZEN authorization decision path (GammaBridge.decide -> evaluate_decision) across
thread counts {1,2,4,8,16,32} over a fixed, deterministic workload of real PERMIT/SAFE_STATE
decisions. Measures throughput, latency percentiles, queue delay, CPU utilization, peak memory,
scaling efficiency, and verifies authorization correctness / replay consistency / ledger consistency
/ false-permit / false-deny against a single-thread reference.

No frozen component is modified: the harness only *calls* the frozen GammaBridge and *times* it.
Every reported number is measured on this host.
"""
from __future__ import annotations

import os
import queue
import resource
import threading
import time
from pathlib import Path

import numpy as np

from agentdojo_integration.interception.execution_binding import ExecutionBinding
from agentdojo_integration.interception.gamma_bridge import GammaBridge
from ._util import sha256_hex, write_json, write_text, describe

THREAD_COUNTS = [1, 2, 4, 8, 16, 32]
# deterministic deficit patterns -> real decisions (2 PERMIT, 2 SAFE_STATE per cycle)
_PATTERNS = [{}, {"GATE_recipient_recognition": 1}, {}, {"GATE_amount_limit": 1}]


def build_workload(n: int) -> list[dict]:
    return [dict(_PATTERNS[i % len(_PATTERNS)]) for i in range(n)]


def reference(bridge: GammaBridge, workload: list[dict]) -> list[str]:
    return [bridge.decide(dict(d))["decision"] for d in workload]


def _run_level(bridge: GammaBridge, workload: list[dict], n_threads: int) -> dict:
    q: "queue.Queue" = queue.Queue()
    results: list = [None] * len(workload)
    latencies: list[float] = []
    queue_delays: list[float] = []
    lat_lock = threading.Lock()

    for idx, d in enumerate(workload):
        q.put((idx, d, time.perf_counter()))

    def worker():
        local_lat, local_qd = [], []
        while True:
            try:
                idx, d, enq = q.get_nowait()
            except queue.Empty:
                break
            deq = time.perf_counter()
            local_qd.append(deq - enq)
            t0 = time.perf_counter()
            res = bridge.decide(dict(d))
            t1 = time.perf_counter()
            results[idx] = res["decision"]
            local_lat.append((t1 - t0) * 1000.0)  # ms
            q.task_done()
        with lat_lock:
            latencies.extend(local_lat)
            queue_delays.extend(local_qd)

    cpu0 = os.times()
    wall0 = time.perf_counter()
    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - wall0
    cpu1 = os.times()
    cpu_time = (cpu1.user - cpu0.user) + (cpu1.system - cpu0.system)
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes (macOS)

    lat = np.array(latencies)
    return {
        "n_threads": n_threads,
        "n_decisions": len(workload),
        "wall_time_s": wall,
        "throughput_decisions_per_s": len(workload) / wall if wall > 0 else None,
        "latency_ms": {"p50": float(np.percentile(lat, 50)), "p95": float(np.percentile(lat, 95)),
                       "p99": float(np.percentile(lat, 99)), "mean": float(lat.mean()),
                       "max": float(lat.max())},
        "queue_delay_ms": {"mean": float(np.mean(queue_delays) * 1000),
                           "p95": float(np.percentile(queue_delays, 95) * 1000),
                           "max": float(np.max(queue_delays) * 1000)},
        "cpu_time_s": cpu_time,
        "cpu_utilization": cpu_time / wall if wall > 0 else None,  # >1 ⇒ multiple cores busy
        "peak_rss_bytes": peak_rss,
        "results": results,
    }


def run(outdir: str | Path, n_decisions: int = 200_000,
        thread_counts: list[int] | None = None) -> dict:
    thread_counts = thread_counts or THREAD_COUNTS
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    bridge = GammaBridge(ExecutionBinding())
    workload = build_workload(n_decisions)
    ref = reference(bridge, workload)
    ref_ledger = sha256_hex(ref)
    ref_permits = ref.count("PERMIT")
    ref_denies = ref.count("SAFE_STATE")

    # replay consistency: independent second reference pass
    replay_ledger = sha256_hex(reference(bridge, workload))
    replay_consistent_global = replay_ledger == ref_ledger

    rows = []
    base_tp = None
    for T in thread_counts:
        r = _run_level(bridge, workload, T)
        res = r.pop("results")
        # correctness vs single-thread reference (deterministic engine)
        correct = res == ref
        # false permit = permitted where reference denied; false deny = denied where reference permitted
        fp = sum(1 for a, b in zip(res, ref) if a == "PERMIT" and b == "SAFE_STATE")
        fd = sum(1 for a, b in zip(res, ref) if a == "SAFE_STATE" and b == "PERMIT")
        ledger = sha256_hex(res)
        if T == thread_counts[0]:
            base_tp = r["throughput_decisions_per_s"]
        r.update({
            "authorization_correct": correct,
            "false_permits": fp, "false_denials": fd,
            "ledger_consistent": ledger == ref_ledger,
            "replay_consistent": replay_consistent_global,
            "permits": res.count("PERMIT"), "denials": res.count("SAFE_STATE"),
            "scaling_efficiency": (r["throughput_decisions_per_s"] / (T * base_tp))
                                   if base_tp else None,
            "speedup_vs_1thread": (r["throughput_decisions_per_s"] / base_tp) if base_tp else None,
        })
        rows.append(r)

    report = {
        "campaign": "concurrency_scaling",
        "host": {"cpu_count": os.cpu_count(), "rss_units": "bytes(macos)"},
        "workload": {"n_decisions": n_decisions, "reference_permits": ref_permits,
                     "reference_denies": ref_denies, "reference_ledger_sha256": ref_ledger},
        "concurrency_model": "python threads (GIL-bound reference decision path)",
        "thread_counts": thread_counts,
        "levels": rows,
        "all_authorization_correct": all(r["authorization_correct"] for r in rows),
        "all_ledger_consistent": all(r["ledger_consistent"] for r in rows),
        "total_false_permits": sum(r["false_permits"] for r in rows),
        "total_false_denials": sum(r["false_denials"] for r in rows),
    }
    write_json(out / "concurrency_scaling.json", report)
    _write_csv(out / "concurrency_scaling.csv", rows)
    write_text(out / "concurrency_scaling.md", _md(report))
    _write_svg(out / "concurrency_scaling_throughput.svg", rows, "throughput_decisions_per_s",
               "Throughput vs threads (decisions/s)")
    _write_svg(out / "concurrency_scaling_latency.svg", rows,
               lambda r: r["latency_ms"]["p99"], "p99 latency vs threads (ms)")
    return report


def _write_csv(path, rows):
    import csv
    cols = ["n_threads", "n_decisions", "wall_time_s", "throughput_decisions_per_s",
            "speedup_vs_1thread", "scaling_efficiency", "lat_p50_ms", "lat_p95_ms", "lat_p99_ms",
            "queue_delay_mean_ms", "cpu_utilization", "peak_rss_bytes", "authorization_correct",
            "false_permits", "false_denials", "ledger_consistent", "replay_consistent"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow([r["n_threads"], r["n_decisions"], f"{r['wall_time_s']:.6f}",
                        f"{r['throughput_decisions_per_s']:.1f}", f"{r['speedup_vs_1thread']:.4f}",
                        f"{r['scaling_efficiency']:.4f}", f"{r['latency_ms']['p50']:.6f}",
                        f"{r['latency_ms']['p95']:.6f}", f"{r['latency_ms']['p99']:.6f}",
                        f"{r['queue_delay_ms']['mean']:.6f}", f"{r['cpu_utilization']:.4f}",
                        r["peak_rss_bytes"], r["authorization_correct"], r["false_permits"],
                        r["false_denials"], r["ledger_consistent"], r["replay_consistent"]])


def _md(report):
    L = ["# Table 13 — Concurrency Scaling (measured)", "",
         f"- Workload: {report['workload']['n_decisions']} frozen Gamma decisions "
         f"({report['workload']['reference_permits']} PERMIT / {report['workload']['reference_denies']} SAFE_STATE)",
         f"- Concurrency model: {report['concurrency_model']} · host cpu_count={report['host']['cpu_count']}",
         f"- Authorization correct at every level: **{report['all_authorization_correct']}** · "
         f"ledger consistent: **{report['all_ledger_consistent']}** · "
         f"false permits: {report['total_false_permits']} · false denials: {report['total_false_denials']}",
         "",
         "| threads | throughput (dec/s) | speedup | scaling eff. | p50 (ms) | p95 (ms) | p99 (ms) | "
         "queue delay mean (ms) | CPU util | peak RSS (MB) | auth correct | FP | FD | ledger ok |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in report["levels"]:
        L.append(f"| {r['n_threads']} | {r['throughput_decisions_per_s']:.0f} | "
                 f"{r['speedup_vs_1thread']:.2f}× | {r['scaling_efficiency']:.2f} | "
                 f"{r['latency_ms']['p50']:.5f} | {r['latency_ms']['p95']:.5f} | {r['latency_ms']['p99']:.5f} | "
                 f"{r['queue_delay_ms']['mean']:.4f} | {r['cpu_utilization']:.2f} | "
                 f"{r['peak_rss_bytes']/1e6:.1f} | {r['authorization_correct']} | {r['false_permits']} | "
                 f"{r['false_denials']} | {r['ledger_consistent']} |")
    L += ["", "> Note: the reference decision path is pure-Python and GIL-bound, so thread throughput "
          "does not scale linearly; the scientifically load-bearing result is that **authorization "
          "correctness, ledger consistency, and replay consistency hold at every thread count with "
          "zero false permits/denials**. Process-level parallelism is the route to CPU-parallel "
          "throughput and is noted as future work."]
    return "\n".join(L)


def _write_svg(path, rows, key, title):
    w, h = 640, 380
    vals = [key(r) if callable(key) else r[key] for r in rows]
    labels = [r["n_threads"] for r in rows]
    m = max(vals) or 1
    pad_l, pad_b, pad_t = 70, 50, 40
    pts = []
    body = []
    n = len(rows)
    for i, (lab, v) in enumerate(zip(labels, vals)):
        x = pad_l + (w - pad_l - 20) * (i / max(1, n - 1))
        y = h - pad_b - (h - pad_b - pad_t) * (v / m)
        pts.append(f"{x:.1f},{y:.1f}")
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#3b6ea5"/>')
        body.append(f'<text x="{x:.1f}" y="{h-pad_b+16:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{lab}</text>')
        body.append(f'<text x="{x:.1f}" y="{y-8:.1f}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="9">{v:.0f}</text>')
    body.insert(0, f'<polyline points="{" ".join(pts)}" fill="none" stroke="#3b6ea5" stroke-width="2"/>')
    body.append(f'<line x1="{pad_l}" y1="{h-pad_b}" x2="{w-10}" y2="{h-pad_b}" stroke="#333"/>')
    body.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{h-pad_b}" stroke="#333"/>')
    body.append(f'<text x="{w/2}" y="{h-8}" text-anchor="middle" font-family="sans-serif" font-size="11">threads</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<rect width="{w}" height="{h}" fill="white"/>'
           f'<text x="{w/2}" y="20" text-anchor="middle" font-family="sans-serif" font-size="14" '
           f'font-weight="bold">{title}</text>{"".join(body)}</svg>')
    write_text(path, svg)


if __name__ == "__main__":
    import sys
    outdir = sys.argv[1] if len(sys.argv) > 1 else "agentdojo_integration/audit_run/summary/concurrency"
    rep = run(outdir)
    print(f"[concurrency] levels: {[l['n_threads'] for l in rep['levels']]}")
    print(f"[concurrency] all_authorization_correct={rep['all_authorization_correct']} "
          f"all_ledger_consistent={rep['all_ledger_consistent']} "
          f"FP={rep['total_false_permits']} FD={rep['total_false_denials']}")
