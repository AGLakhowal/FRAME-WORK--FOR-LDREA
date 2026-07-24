#!/usr/bin/env python3
"""
experiment_ablation.py — GENUINE component-ablation experiment (fresh execution).
=================================================================================

This is a real experiment, not a table populated from a prior JSON. It builds a synthetic
decision workload with a controlled mix of deficit patterns, then runs the FROZEN software
decision path (`gamma_test_runner.evaluate_decision`) under configurations that individually
DISABLE a structural component, measuring — per configuration, from fresh timing:

  * authorization latency distribution (n, mean, median, std, min, max, p50/p90/p95/p99, bootstrap CI)
  * throughput (decisions/s)
  * peak RSS (resource.getrusage)
  * permits / denials
  * LEAKED PERMITS: decisions that flip SAFE_STATE -> PERMIT relative to the full-config reference
    (the software-measurable safety-regression signal when a control is removed)
  * ledger hash + replay consistency (second independent pass must reproduce the decision stream)

SCOPE (stated honestly): this measures the SOFTWARE (Tier-S) decision path on a synthetic
deficit workload. It is NOT the paper's Table-9 FPR ablation, which requires the LAB v1.0
360,000-item adversarial-mutation generator (absent from this repo) and Tier-H FPGA/SGX/HSM
hardware. "Leaked permits" here is the deterministic count of denials a removed control would
convert to permits on this workload — the causal, measurable analogue of an FPR delta.

Outputs (fresh): fresh_evidence/ablation/ablation.{json,csv} + ablation_log.jsonl
"""
from __future__ import annotations

import csv
import hashlib
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gamma_test_runner as G  # frozen engine
import metrics_engine as ME

OUT = ROOT / "fresh_evidence" / "ablation"
THETA = 0.5
N = 60_000                      # workload size (deterministic)
TAU = 0.15                       # compensatory permit threshold (paper negative-control)


def _clean_row() -> dict:
    row = {c: True for c in G.NODE_GATE_COLS}
    row.update({"HARM_RISK": 0.0, "StaleContext": False, "TelemetryFresh": True,
                "ReasonCodes": "NONE", "Actuated": False, "ACT_PERMIT": False,
                "TOKEN_VALID": True, "AuthoritySignatureValid": True})
    return row


def build_workload(n: int) -> list[dict]:
    """Deterministic mix: clean, single-node-deficit, class-veto-only, multi-deficit.
    Pattern is index-driven (no RNG) so the workload is byte-reproducible."""
    rows = []
    gates = G.NODE_GATE_COLS
    for i in range(n):
        r = _clean_row()
        k = i % 4
        if k == 0:
            pass  # clean -> PERMIT under full config
        elif k == 1:
            r[gates[i % len(gates)]] = False           # single node deficit
        elif k == 2:
            r["ReasonCodes"] = "CLASS_1_FRAUD"          # class-veto only (all nodes clean)
        else:
            r[gates[i % len(gates)]] = False            # multi: node deficit + class veto
            r["ReasonCodes"] = "GOODHART_DRIFT"
        rows.append(r)
    return rows


# ---- ablated decision functions (each returns "PERMIT"/"SAFE_STATE") ----
def decide_baseline(row) -> str:
    return G.evaluate_decision(dict(row), THETA)["decision"]


def decide_no_class_veto(row) -> str:
    r = dict(row); r["ReasonCodes"] = "NONE"            # neutralize class veto
    return G.evaluate_decision(r, THETA)["decision"]


def decide_no_noncompensatory(row) -> str:
    # replace max-aggregation with compensatory weighted (mean) sum; permit if mean < tau
    deficits = [0 if row[g] else 1 for g in G.NODE_GATE_COLS]
    deficits.append(1 if row["HARM_RISK"] > THETA else 0)
    deficits.append(1 if row["StaleContext"] else 0)
    deficits.append(0 if row["TelemetryFresh"] else 1)
    gamma_w = sum(deficits) / len(deficits)
    reason = str(row["ReasonCodes"]).upper()
    gamma_class = 1 if ("CLASS_1" in reason or "GOODHART" in reason) else 0
    # compensatory rule still respects class veto (only Γ aggregation ablated)
    return "PERMIT" if (gamma_w < TAU and gamma_class == 0) else "SAFE_STATE"


def decide_no_authorization(row) -> str:
    return "PERMIT"                                     # authorization layer removed


CONFIGS = [
    ("baseline_full_LDREA", decide_baseline),
    ("remove_class_veto", decide_no_class_veto),
    ("remove_noncompensatory_gamma", decide_no_noncompensatory),
    ("remove_authorization_layer", decide_no_authorization),
]


def _stats(latencies_ms: list[float]) -> dict:
    v = sorted(latencies_ms)
    n = len(v)
    mean = sum(v) / n
    import math
    var = sum((x - mean) ** 2 for x in v) / n
    def pct(q):
        k = max(0, min(n - 1, int(math.ceil(q / 100.0 * n)) - 1))
        return v[k]
    return {
        "n": n, "mean_ms": mean, "median_ms": pct(50), "std_ms": math.sqrt(var),
        "min_ms": v[0], "max_ms": v[-1],
        "p50_ms": pct(50), "p90_ms": pct(90), "p95_ms": pct(95), "p99_ms": pct(99),
        "bootstrap95_ci": ME.compute_bootstrap_ci(v)["bootstrap95"],
    }


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    log = open(OUT / "ablation_log.jsonl", "w")
    workload = build_workload(N)

    # reference stream = baseline full config
    ref_stream = [decide_baseline(r) for r in workload]
    ref_ledger = hashlib.sha256("".join(ref_stream).encode()).hexdigest()
    ref_permits = ref_stream.count("PERMIT")

    results = []
    for name, fn in CONFIGS:
        latencies = []
        stream = []
        rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        t0 = time.perf_counter()
        for r in workload:
            s = time.perf_counter()
            d = fn(r)
            latencies.append((time.perf_counter() - s) * 1000.0)
            stream.append(d)
        wall = time.perf_counter() - t0
        rss1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # replay consistency: independent second pass must reproduce the stream
        replay_stream = [fn(r) for r in workload]
        ledger = hashlib.sha256("".join(stream).encode()).hexdigest()
        replay_ledger = hashlib.sha256("".join(replay_stream).encode()).hexdigest()
        permits = stream.count("PERMIT")
        # leaked permits: denials in baseline that this config turns into permits
        leaked = sum(1 for a, b in zip(stream, ref_stream)
                     if a == "PERMIT" and b == "SAFE_STATE")
        leak_rate = ME.compute_wilson_upper_bound(leaked, N)  # Wilson on the leak proportion
        rec = {
            "config": name,
            "workload_n": N,
            "permits": permits, "denials": N - permits,
            "leaked_permits_vs_baseline": leaked,
            "leaked_permit_rate": leaked / N,
            "leaked_permit_wilson95": leak_rate["wilson95"],
            "throughput_decisions_per_s": N / wall if wall else None,
            "wall_s": wall,
            "peak_rss_bytes_end": rss1, "rss_delta_bytes": rss1 - rss0,
            "ledger_sha256": ledger,
            "replay_consistent": replay_ledger == ledger,
            "matches_baseline_stream": ledger == ref_ledger,
            "latency": _stats(latencies),
        }
        results.append(rec)
        log.write(json.dumps({k: v for k, v in rec.items() if k != "latency"}) + "\n")
    log.close()

    report = {
        "experiment": "component_ablation",
        "scope": "SOFTWARE (Tier-S) decision path; synthetic deficit workload; "
                 "NOT the paper Table-9 Tier-H FPR ablation (requires LAB 360k generator + FPGA/SGX/HSM).",
        "theta": THETA, "compensatory_tau": TAU, "workload_n": N,
        "baseline_permits": ref_permits, "baseline_ledger_sha256": ref_ledger,
        "configs": results,
    }
    (OUT / "ablation.json").write_text(json.dumps(report, indent=2))
    with open(OUT / "ablation.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config", "permits", "denials", "leaked_permits", "leaked_rate",
                    "throughput_dec_s", "lat_mean_ms", "lat_p95_ms", "lat_p99_ms",
                    "replay_consistent"])
        for r in results:
            w.writerow([r["config"], r["permits"], r["denials"],
                        r["leaked_permits_vs_baseline"], f'{r["leaked_permit_rate"]:.6f}',
                        f'{r["throughput_decisions_per_s"]:.0f}',
                        f'{r["latency"]["mean_ms"]:.6f}', f'{r["latency"]["p95_ms"]:.6f}',
                        f'{r["latency"]["p99_ms"]:.6f}', r["replay_consistent"]])
    return report


if __name__ == "__main__":
    rep = run()
    for r in rep["configs"]:
        lt = r["latency"]
        print(f"{r['config']:32s} permits={r['permits']:6d} leaked={r['leaked_permits_vs_baseline']:6d} "
              f"tput={r['throughput_decisions_per_s']:8.0f}/s  mean={lt['mean_ms']:.5f}ms "
              f"p99={lt['p99_ms']:.5f}ms replay_ok={r['replay_consistent']}")
    print(f"\n[written] {OUT/'ablation.json'} + ablation.csv + ablation_log.jsonl")
