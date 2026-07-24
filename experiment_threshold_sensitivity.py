#!/usr/bin/env python3
"""
experiment_threshold_sensitivity.py — PART 2: do the ablation conclusions depend on the thresholds?
===================================================================================================

Reviewers ask whether a result is an artefact of a chosen operating point. L-DREA's predicate
thresholds are NOT hand-chosen: they are unsupervised quantiles learned from the unlabeled warmup
prefix. This experiment perturbs those LEARNED thresholds by -20%, -10%, 0, +10%, +20% and RE-RUNS
the full runtime for the baseline plus every single-component removal, measuring the same metrics.

The Gamma decision RULE is untouched (frozen, imported unmodified). Only the calibrated operating
point is scaled — the thresholds actually consulted by the predicate generators:
    daily_cap, velocity_cap, stale_context_ms, freshness_ms, anomaly_z

CONCLUSION-STABILITY is then decided from MEASURED values, not asserted:
    C1  removing the predicate engine always raises the undetected-risk rate (URR) above baseline
    C2  removing the evidence quad always destroys evidence completeness (-> 0)
    C3  removing the ledger/hash-chain always destroys ledger integrity, never the URR
    C4  the RIS ranking of the single removals is preserved across every threshold scale

Outputs: experiments/combined_ablation/threshold_sensitivity.{json,csv,md}
         experiments/combined_ablation/figures/threshold_sensitivity_heatmap.svg
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import experiment_combined_ablation as CA
from e5b_metric_note import NOTE_MD
from runtime_stack import _signer, sha
from run_runtime_stack import synth_stream

SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]
OUT = CA.OUT
FIG = CA.FIG


def run(n=6000, seed=CA.SEED) -> dict:
    import random
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    sk, pub, sign, verify = _signer()
    policy_hash = sha({"engine": "gamma_g0", "rule": "non_compensatory", "v": 1})
    t0 = time.time()
    obs, labels, _kinds = synth_stream(n, sign, pub, policy_hash, rng, t0)
    keys = (sk, pub, sign, verify)

    # baseline + every single-component removal, at every threshold scale
    cfg_sets = [frozenset()] + [frozenset([c]) for c in CA.COMPONENTS]
    rows = []
    print(f"[threshold-sensitivity] n={n} scales={SCALES} configs={len(cfg_sets)} "
          f"({len(SCALES)*len(cfg_sets)} executions)")
    for scale in SCALES:
        # RIS is normalized to the baseline OF THAT SCALE (the operating point moves, so the
        # reference recall moves with it — comparing to a different scale's baseline would be wrong)
        base = CA.run_config(frozenset(), obs, labels, policy_hash, keys, threshold_scale=scale)
        CA._BASE_RECALL = base["blind_risk_detection_recall"]
        for cs in cfg_sets:
            c = base if not cs else CA.run_config(cs, obs, labels, policy_hash, keys, threshold_scale=scale)
            c["runtime_integrity_score"] = round(CA._ris(c), 6)
            c["overall_runtime_verdict"] = CA._verdict(c, base)
            rows.append({
                "threshold_scale": scale,
                "threshold_delta_pct": int(round((scale - 1.0) * 100)),
                "config": c["config"], "disabled": "+".join(c["disabled_codes"]) or "—",
                "undetected_risk_rate": c["undetected_risk_rate"],
                "benign_flag_rate": c["benign_flag_rate"],
                "replay_integrity": c["replay_integrity"],
                "replay_determinism_rate": c["replay_determinism_rate"],
                "evidence_completeness": c["evidence_completeness"],
                "runtime_integrity_score": c["runtime_integrity_score"],
                "blind_risk_detection_recall": c["blind_risk_detection_recall"],
                "latency_mean_ms": c["latency_mean_ms"],
                "throughput_decisions_per_s": c["throughput_decisions_per_s"],
                "ledger_integrity": c["ledger_integrity"],
                "verdict": c["overall_runtime_verdict"],
            })
        b = rows[-len(cfg_sets)]
        print(f"  scale {scale:.1f} (baseline) fpr={b['undetected_risk_rate']:.3f} "
              f"recall={b['blind_risk_detection_recall']:.3f} RIS={b['runtime_integrity_score']:.3f}")

    stability = _assess_stability(rows)
    report = {
        "experiment": "threshold_sensitivity",
        "purpose": ("Determine whether the combined-ablation conclusions depend on the calibrated "
                    "operating point. Thresholds are perturbed +/-10% and +/-20%; the frozen Gamma "
                    "rule is untouched. Every value is measured from a re-executed run."),
        "perturbed_thresholds": ["daily_cap", "velocity_cap", "stale_context_ms", "freshness_ms",
                                 "anomaly_z"],
        "threshold_note": ("These are UNSUPERVISED quantiles learned from the unlabeled warmup prefix, "
                           "not hand-chosen constants; the perturbation scales that learned operating "
                           "point. max_kmh is a physical constant (commercial aviation) and is not "
                           "perturbed."),
        "scales": SCALES, "workload_n": n, "seed": seed,
        "n_executions": len(rows), "rows": rows,
        "stability": stability,
        "duration_s": round(time.time() - t0, 2),
    }
    (OUT / "threshold_sensitivity.json").write_text(json.dumps(report, indent=2) + "\n")
    _write_csv(rows)
    _write_md(report)
    _write_heatmap(rows)
    print(f"[threshold-sensitivity] conclusions stable: {stability['all_conclusions_stable']} "
          f"({report['duration_s']}s)")
    return report


def _assess_stability(rows) -> dict:
    """Decide conclusion-stability from MEASURED values only."""
    by_scale = {}
    for r in rows:
        by_scale.setdefault(r["threshold_scale"], {})[r["disabled"]] = r
    checks = {}

    # C1 — removing PE always raises URR above the same-scale baseline
    c1 = []
    for s, d in by_scale.items():
        base_fpr, pe_fpr = d["—"]["undetected_risk_rate"], d["PE"]["undetected_risk_rate"]
        c1.append({"scale": s, "baseline_urr": base_fpr, "remove_PE_urr": pe_fpr,
                   "holds": pe_fpr > base_fpr})
    checks["C1_predicate_engine_removal_always_raises_URR"] = {
        "holds_at_every_scale": all(x["holds"] for x in c1), "per_scale": c1}

    # C2 — removing EQ always destroys evidence completeness
    c2 = [{"scale": s, "evidence": d["EQ"]["evidence_completeness"],
           "holds": d["EQ"]["evidence_completeness"] == 0.0} for s, d in by_scale.items()]
    checks["C2_evidence_quad_removal_always_zeroes_evidence"] = {
        "holds_at_every_scale": all(x["holds"] for x in c2), "per_scale": c2}

    # C3 — removing LG/HC destroys ledger integrity but NEVER raises URR
    c3 = []
    for s, d in by_scale.items():
        base_fpr = d["—"]["undetected_risk_rate"]
        ok = all(d[k]["undetected_risk_rate"] == base_fpr and d[k]["ledger_integrity"] != 1.0
                 for k in ("LG", "HC"))
        c3.append({"scale": s, "holds": ok,
                   "LG_urr": d["LG"]["undetected_risk_rate"], "HC_urr": d["HC"]["undetected_risk_rate"],
                   "baseline_urr": base_fpr})
    checks["C3_ledger_removal_costs_audit_not_safety"] = {
        "holds_at_every_scale": all(x["holds"] for x in c3), "per_scale": c3}

    # C4 — the RIS ranking of the single removals is preserved across scales
    rank = {}
    for s, d in by_scale.items():
        singles = [(k, v["runtime_integrity_score"]) for k, v in d.items() if k != "—"]
        rank[s] = [k for k, _ in sorted(singles, key=lambda x: (x[1], x[0]))]
    ranks = list(rank.values())
    checks["C4_RIS_ranking_of_single_removals_preserved"] = {
        "holds_at_every_scale": all(r == ranks[0] for r in ranks),
        "ranking_per_scale": rank,
        "note": "ranking from worst (lowest RIS) to best; identical ordering at every scale ⇒ stable"}

    # measured spread of the baseline operating point across scales
    base_fprs = [by_scale[s]["—"]["undetected_risk_rate"] for s in sorted(by_scale)]
    base_recall = [by_scale[s]["—"]["blind_risk_detection_recall"] for s in sorted(by_scale)]
    return {
        "all_conclusions_stable": all(v["holds_at_every_scale"] for v in checks.values()),
        "checks": checks,
        "baseline_sensitivity": {
            "undetected_risk_rate_by_scale": dict(zip([str(s) for s in sorted(by_scale)], base_fprs)),
            "risk_detection_by_scale": dict(zip([str(s) for s in sorted(by_scale)], base_recall)),
            "urr_range": [min(base_fprs), max(base_fprs)],
            "urr_spread": round(max(base_fprs) - min(base_fprs), 6),
            "interpretation": ("The baseline operating point DOES move with the thresholds (looser "
                               "thresholds permit more, so URR rises) — that is expected and is the "
                               "point of the sweep. What matters is that every ABLATION conclusion "
                               "above holds at every scale."),
        },
    }


COLS = ["threshold_scale", "threshold_delta_pct", "config", "disabled", "undetected_risk_rate",
        "benign_flag_rate", "replay_integrity", "evidence_completeness", "runtime_integrity_score",
        "blind_risk_detection_recall", "latency_mean_ms", "throughput_decisions_per_s", "verdict"]


def _write_csv(rows):
    with open(OUT / "threshold_sensitivity.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS)
        for r in rows:
            w.writerow([r.get(c) for c in COLS])


def _f(x, nd=3):
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _write_md(rep):
    st = rep["stability"]
    md = ["# Threshold Sensitivity Analysis", "",
          "> Auto-generated by `experiment_threshold_sensitivity.py` (PART 2). Every value is measured "
          "by RE-EXECUTING the full runtime at the perturbed operating point. The frozen Gamma rule is "
          "untouched — only the unsupervised-calibrated thresholds are scaled.", "",
          f"- Perturbations: {', '.join(f'{int((s-1)*100):+d}%' for s in rep['scales'])} "
          f"applied to `{'`, `'.join(rep['perturbed_thresholds'])}`.",
          f"- Executions: **{rep['n_executions']}** (baseline + 5 single removals × 5 scales), "
          f"n={rep['workload_n']}/run, {rep['duration_s']}s.",
          f"- {rep['threshold_note']}", "",
          f"## Verdict: conclusions {'**REMAIN STABLE**' if st['all_conclusions_stable'] else '**DO NOT remain stable**'} "
          f"under ±20% threshold perturbation", ""]
    md += ["| Conclusion | Holds at every scale? |", "|---|:--:|"]
    for k, v in st["checks"].items():
        md.append(f"| {k.replace('_',' ')} | {'✅ yes' if v['holds_at_every_scale'] else '❌ no'} |")
    bs = st["baseline_sensitivity"]
    md += ["", "## Baseline operating-point sensitivity (expected, and not a threat)", "",
           "| Scale | Baseline URR | Baseline risk detection |", "|--:|--:|--:|"]
    for s in rep["scales"]:
        md.append(f"| {int((s-1)*100):+d}% | {_f(bs['undetected_risk_rate_by_scale'][str(s)])} | "
                  f"{_f(bs['risk_detection_by_scale'][str(s)])} |")
    md += ["", f"URR spread across ±20%: **{bs['urr_spread']:.3f}**. {bs['interpretation']}", "",
           "## Full measured grid", "",
           "| Scale | Config | URR | BFR | Blind Detection Recall | Evidence | Replay | Ledger | RIS | Latency (ms) | Verdict |",
           "|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for r in rep["rows"]:
        md.append(f"| {r['threshold_delta_pct']:+d}% | {r['config']} | {_f(r['undetected_risk_rate'])} | "
                  f"{_f(r['benign_flag_rate'])} | {_f(r['blind_risk_detection_recall'])} | "
                  f"{_f(r['evidence_completeness'])} | {_f(r['replay_integrity'])} | "
                  f"{_f(r['ledger_integrity'])} | {_f(r['runtime_integrity_score'])} | "
                  f"{_f(r['latency_mean_ms'],4)} | {r['verdict'].split(' (')[0]} |")
    md.append("")
    md += ["", NOTE_MD]
    (OUT / "threshold_sensitivity.md").write_text("\n".join(md) + "\n")


def _write_heatmap(rows):
    scales = sorted({r["threshold_scale"] for r in rows})
    cfgs = []
    for r in rows:
        if r["config"] not in cfgs:
            cfgs.append(r["config"])
    grid = {(r["config"], r["threshold_scale"]): r for r in rows}
    cw, rh, x0, y0 = 110, 30, 200, 58
    W, H = x0 + cw * len(scales) + 30, y0 + rh * len(cfgs) + 56

    def color(v):
        if v is None:
            return "#30363d"
        r_, g_ = (255, int(120 * (v / 0.5))) if v < 0.5 else (int(255 * (1 - (v - 0.5) / 0.5)), 200)
        return f"rgb({r_},{g_},70)"
    b = [f"<text x='{W/2}' y='22' fill='#e6edf3' font-size='14' font-weight='700' text-anchor='middle'>"
         f"Threshold Sensitivity — Runtime Integrity Score (URR in parentheses)</text>"]
    for j, s in enumerate(scales):
        b.append(f"<text x='{x0+cw*j+cw/2}' y='{y0-8}' fill='#8b949e' font-size='11' text-anchor='middle'>"
                 f"{int((s-1)*100):+d}%</text>")
    for i, c in enumerate(cfgs):
        b.append(f"<text x='{x0-10}' y='{y0+rh*i+19}' fill='#e6edf3' font-size='10' text-anchor='end'>{c}</text>")
        for j, s in enumerate(scales):
            r = grid.get((c, s))
            v = r["runtime_integrity_score"] if r else None
            fpr = r["undetected_risk_rate"] if r else None
            b.append(f"<rect x='{x0+cw*j}' y='{y0+rh*i}' width='{cw-3}' height='{rh-3}' "
                     f"fill='{color(v)}' opacity='0.85'/>"
                     f"<text x='{x0+cw*j+cw/2}' y='{y0+rh*i+19}' fill='#0d1117' font-size='10' "
                     f"text-anchor='middle'>{'—' if v is None else f'{v:.2f}'} "
                     f"({'—' if fpr is None else f'{fpr:.2f}'})</text>")
    b.append(f"<text x='{x0}' y='{H-16}' fill='#8b949e' font-size='10'>green = integrity intact · "
             f"red = destroyed · rows = configuration · columns = threshold perturbation</text>")
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
           f"font-family='-apple-system,Segoe UI,Roboto,sans-serif'>"
           f"<rect width='{W}' height='{H}' fill='#0d1117'/>{''.join(b)}</svg>")
    (FIG / "threshold_sensitivity_heatmap.svg").write_text(svg)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    run(n=2400 if a.fast else a.n)
