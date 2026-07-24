#!/usr/bin/env python3
"""External latency profiler for the financial stress scenarios (Part 5).

WRAPPER ONLY. This module does not modify stress_test.py, does not modify
stress_test_report.json, and does not recompute any scientific result. It imports the scenario
builders through their public entry points and times them with time.perf_counter().

What is measured
    Wall-clock time to construct a scenario's predicate vector and adjudicate it through
    stress_test.gamma_decision() -- i.e. the Layer-1 (predicate) + Layer-2 (Gamma) path.

What is NOT measured, and why
    Replay generation, Evidence-Quad assembly and independent verification are NOT timed here,
    because the stress layer (C-2) never invokes them. Those stages are measured in Experiment 2
    (Runtime Replay Integrity). Reporting a replay latency for this experiment would be fabrication.

Output
    stress_latency_report.json   (a NEW artifact; no existing report is read for writing or changed)

    python experiments/profile_stress_scenarios.py [--repeats N]
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "stress_latency_report.json"

# The stages the stress layer actually executes. Anything absent here is reported as
# "not_executed" rather than silently omitted or invented.
NOT_EXECUTED = {
    "replay_generation": "Not executed in this experiment — replay integrity is evaluated in Experiment 2.",
    "evidence_quad": "Not executed in this experiment — the Evidence Quad is assembled in Experiment 2.",
    "independent_verifier": "Not executed in this experiment — independent verification runs in Experiment 2.",
}


def _percentile(sorted_vals, q):
    """Nearest-rank percentile. Deterministic, no interpolation, no numpy dependency."""
    if not sorted_vals:
        return None
    k = max(1, min(len(sorted_vals), int(round(q / 100.0 * len(sorted_vals) + 0.5))))
    return sorted_vals[k - 1]


def _stats(samples_s):
    ms = sorted(s * 1000.0 for s in samples_s)
    return {
        "n": len(ms),
        "mean_ms": statistics.fmean(ms),
        "median_ms": statistics.median(ms),
        "min_ms": ms[0],
        "max_ms": ms[-1],
        "p95_ms": _percentile(ms, 95),
        "p99_ms": _percentile(ms, 99),
        "stdev_ms": statistics.pstdev(ms) if len(ms) > 1 else 0.0,
        "total_ms": sum(ms),
    }


def _count_decisions(scenario):
    """Runtime Gamma adjudications the scenario performed, read from what it actually returned."""
    n = 1 if isinstance(scenario.get("decision"), dict) else 0
    return n + len(scenario.get("subcases", {}) or {})


def profile(repeats: int) -> dict:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import stress_test  # public module; imported, never modified

    builders = [
        ("P1", "Ghost Treasury Transfer", stress_test.p1_ghost_treasury),
        ("P2", "Sanctions Drift Cascade", stress_test.p2_sanctions_drift),
        ("P3", "Multi-Agent Liquidity Panic", stress_test.p3_liquidity_panic),
        ("P4", "Sovereign Cascade Edge Case", stress_test.p4_sovereign_cascade),
    ]

    scenarios, all_samples = [], []
    for sid, name, fn in builders:
        fn()  # warm-up: exclude import/first-call effects from the sample
        samples = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            sc = fn()
            samples.append(time.perf_counter() - t0)
        all_samples.extend(samples)

        n_dec = _count_decisions(sc)
        st = _stats(samples)
        st_mean_s = st["mean_ms"] / 1000.0
        scenarios.append({
            "id": sid,
            "name": name,
            "runtime_decisions": n_dec,
            "measured_stages": ["predicate_evaluation", "gamma_computation", "authorization_decision"],
            "not_executed": NOT_EXECUTED,
            "latency": st,
            "decisions_per_s": (n_dec / st_mean_s) if st_mean_s > 0 else None,
        })

    overall = _stats(all_samples)
    total_decisions = sum(s["runtime_decisions"] for s in scenarios)
    return {
        "report": "stress_scenario_latency",
        "layer": "C-2 (illustrative scenario layer)",
        "method": ("time.perf_counter() around the public scenario builders in stress_test.py. "
                   "External wrapper: stress_test.py and stress_test_report.json are not modified."),
        "measures": "predicate evaluation + Gamma computation + authorization decision",
        "does_not_measure": NOT_EXECUTED,
        "repeats_per_scenario": repeats,
        "host": {"python": platform.python_version(), "platform": platform.platform(),
                 "machine": platform.machine()},
        "scenarios": scenarios,
        "aggregate": {
            "scenarios": len(scenarios),
            "total_runtime_decisions": total_decisions,
            "latency": overall,
            "note": ("Percentiles are nearest-rank over per-invocation samples. Timing is wall-clock "
                     "and therefore varies between runs; it is a measurement, not a frozen constant."),
        },
        "integrity": ("This report is a new artifact. It reads stress_test.py through its public "
                      "entry points and changes no existing experimental output, metric or claim."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=2000,
                    help="invocations per scenario (default 2000)")
    args = ap.parse_args()

    rep = profile(args.repeats)
    OUT.write_text(json.dumps(rep, indent=2) + "\n")

    agg = rep["aggregate"]["latency"]
    print(f"[stress-latency] {rep['repeats_per_scenario']} repeats x {len(rep['scenarios'])} scenarios")
    for s in rep["scenarios"]:
        l = s["latency"]
        print(f"  {s['id']}  mean {l['mean_ms']:.4f} ms  p95 {l['p95_ms']:.4f}  p99 {l['p99_ms']:.4f}"
              f"  max {l['max_ms']:.4f}  ({s['runtime_decisions']} Γ decisions)")
    print(f"[stress-latency] overall mean {agg['mean_ms']:.4f} ms  p95 {agg['p95_ms']:.4f}  "
          f"p99 {agg['p99_ms']:.4f}  total {agg['total_ms']:.1f} ms")
    print(f"[stress-latency] wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
