#!/usr/bin/env python3
"""
experiments/generate_figures.py — publication figures from executed artifacts only.
===================================================================================

Pure-Python SVG (no matplotlib dependency, fully reproducible). Every value plotted is
read from an experiment JSON produced by RUN_ALL_EXPERIMENTS.py; nothing is hardcoded.
Figures emitted to experiments/figures/:
  fig_authorization_accuracy.svg   fig_false_permit_rate.svg   fig_latency.svg
  fig_throughput.svg               fig_replay_integrity.svg    fig_component_ablation.svg
  fig_runtime_breakdown.svg
A figure whose source artifact is missing is skipped and noted in figures/INDEX.md.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
FIG = EXP / "figures"
FIG.mkdir(parents=True, exist_ok=True)

W, H = 640, 400
PAD_L, PAD_R, PAD_T, PAD_B = 80, 30, 50, 60
PLOT_W, PLOT_H = W - PAD_L - PAD_R, H - PAD_T - PAD_B
BLUE, RED, GREEN, GREY = "#2c5f8a", "#b5423a", "#3a8a5f", "#888"


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _x(s):
    """XML-escape text content (labels/titles may contain & < >)."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_open(title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            'font-family="Helvetica,Arial,sans-serif">',
            f'<rect width="{W}" height="{H}" fill="white"/>',
            f'<text x="{W/2}" y="26" font-size="16" font-weight="bold" text-anchor="middle">{_x(title)}</text>']


def _axes(body, ylab, xlab):
    body.append(f'<line x1="{PAD_L}" y1="{PAD_T}" x2="{PAD_L}" y2="{H-PAD_B}" stroke="#333"/>')
    body.append(f'<line x1="{PAD_L}" y1="{H-PAD_B}" x2="{W-PAD_R}" y2="{H-PAD_B}" stroke="#333"/>')
    body.append(f'<text x="18" y="{PAD_T+PLOT_H/2}" font-size="12" text-anchor="middle" '
                f'transform="rotate(-90 18 {PAD_T+PLOT_H/2})">{_x(ylab)}</text>')
    body.append(f'<text x="{PAD_L+PLOT_W/2}" y="{H-16}" font-size="12" text-anchor="middle">{_x(xlab)}</text>')


def _bars(title, labels, values, ylab, fmt="{:.3g}", colors=None, ymax=None, ci=None):
    body = _svg_open(title)
    _axes(body, ylab, "")
    n = len(values)
    if not n:
        body.append('</svg>'); return "\n".join(body)
    ymax = ymax if ymax is not None else (max(values) * 1.2 or 1.0)
    bw = PLOT_W / n * 0.6
    gap = PLOT_W / n
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = PAD_L + gap * i + (gap - bw) / 2
        bh = (v / ymax) * PLOT_H if ymax else 0
        y = (H - PAD_B) - bh
        c = (colors[i] if colors else BLUE)
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{c}"/>')
        body.append(f'<text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="10" text-anchor="middle">{fmt.format(v)}</text>')
        if ci and ci[i] is not None:
            lo, hi = ci[i]
            ylo = (H - PAD_B) - (lo / ymax) * PLOT_H
            yhi = (H - PAD_B) - (hi / ymax) * PLOT_H
            cx = x + bw / 2
            body.append(f'<line x1="{cx:.1f}" y1="{ylo:.1f}" x2="{cx:.1f}" y2="{yhi:.1f}" stroke="#222"/>')
            body.append(f'<line x1="{cx-4:.1f}" y1="{yhi:.1f}" x2="{cx+4:.1f}" y2="{yhi:.1f}" stroke="#222"/>')
        body.append(f'<text x="{x+bw/2:.1f}" y="{H-PAD_B+16:.1f}" font-size="9.5" text-anchor="middle">{_x(lab)}</text>')
    body.append('</svg>')
    return "\n".join(body)


def _line(title, xs, series, ylab, xlab, logx=False, fmt="{:.0f}"):
    """series = list of (label, [y...], color)."""
    body = _svg_open(title)
    _axes(body, ylab, xlab)
    allys = [y for _, ys, _ in series for y in ys]
    if not allys:
        body.append('</svg>'); return "\n".join(body)
    ymax = max(allys) * 1.15 or 1.0
    import math
    def sx(x):
        if logx:
            lo, hi = math.log2(min(xs)), math.log2(max(xs) or 1)
            return PAD_L + (0 if hi == lo else (math.log2(x) - lo) / (hi - lo)) * PLOT_W
        lo, hi = min(xs), max(xs)
        return PAD_L + (0 if hi == lo else (x - lo) / (hi - lo)) * PLOT_W
    def sy(y):
        return (H - PAD_B) - (y / ymax) * PLOT_H
    # x ticks
    for x in xs:
        body.append(f'<text x="{sx(x):.1f}" y="{H-PAD_B+16:.1f}" font-size="9.5" text-anchor="middle">{x}</text>')
    for i in range(5):
        yv = ymax * i / 4
        yy = sy(yv)
        body.append(f'<text x="{PAD_L-6}" y="{yy+3:.1f}" font-size="9" text-anchor="end">{fmt.format(yv)}</text>')
        body.append(f'<line x1="{PAD_L}" y1="{yy:.1f}" x2="{W-PAD_R}" y2="{yy:.1f}" stroke="#eee"/>')
    for li, (lab, ys, color) in enumerate(series):
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys))
        body.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in zip(xs, ys):
            body.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.5" fill="{color}"/>')
        body.append(f'<text x="{W-PAD_R-4}" y="{PAD_T+14+li*14}" font-size="10" text-anchor="end" fill="{color}">{_x(lab)}</text>')
    body.append('</svg>')
    return "\n".join(body)


def _stacked(title, labels, segments, ylab):
    """segments = list of (seg_label, [value per bar], color)."""
    body = _svg_open(title)
    _axes(body, ylab, "")
    n = len(labels)
    totals = [sum(seg[1][i] for seg in segments) for i in range(n)]
    ymax = (max(totals) * 1.2) if totals else 1.0
    bw = PLOT_W / max(n, 1) * 0.5
    gap = PLOT_W / max(n, 1)
    for i, lab in enumerate(labels):
        x = PAD_L + gap * i + (gap - bw) / 2
        y0 = H - PAD_B
        for seg_label, vals, color in segments:
            v = vals[i]
            bh = (v / ymax) * PLOT_H if ymax else 0
            body.append(f'<rect x="{x:.1f}" y="{y0-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{color}"/>')
            y0 -= bh
        body.append(f'<text x="{x+bw/2:.1f}" y="{H-PAD_B+16:.1f}" font-size="9.5" text-anchor="middle">{_x(lab)}</text>')
    for li, (seg_label, _, color) in enumerate(segments):
        body.append(f'<rect x="{W-PAD_R-110}" y="{PAD_T+li*16}" width="10" height="10" fill="{color}"/>')
        body.append(f'<text x="{W-PAD_R-96}" y="{PAD_T+9+li*16}" font-size="10">{_x(seg_label)}</text>')
    body.append('</svg>')
    return "\n".join(body)


def main():
    made, skipped = [], []

    def emit(name, svg):
        (FIG / name).write_text(svg); made.append(name)

    # -- Fig 1: Authorization accuracy (from confusion matrix, Exp1) --
    fs = _load(EXP / "runtime_correctness" / "full_spec_conformance_report.json")
    if fs:
        cm = fs["confusion_matrix"]
        tot = cm["true_permits"] + cm["true_denials"] + cm["false_permits"] + cm["false_denials"]
        acc = (cm["true_permits"] + cm["true_denials"]) / tot if tot else 0
        emit("fig_authorization_accuracy.svg",
             _bars("Authorization Accuracy & Confusion (Exp 1, ULB corpus)",
                   ["accuracy", "TP", "TN", "FP", "FN"],
                   [acc, cm["true_permits"], cm["true_denials"], cm["false_permits"], cm["false_denials"]],
                   "value (accuracy 0-1; counts)", fmt="{:g}",
                   colors=[GREEN, BLUE, BLUE, RED, RED], ymax=max(tot, 1)))
    else:
        skipped.append("fig_authorization_accuracy.svg (no full_spec report)")

    # -- Fig 2: False Permit Rate across experiments (Exp1 LAB + Exp7 boundary) --
    lab = _load(EXP / "runtime_correctness" / "gamma_lab_v1_report.json")
    bf = _load(EXP / "agentdojo" / "boundary" / "boundary_fpr.json")
    labels, vals, cis = [], [], []
    if lab:
        pm = lab["primary_metrics"]["false_permit_rate"]
        labels.append(f"ULB\n(n={pm['n']})"); vals.append(pm["adverse_events"] / pm["n"] if pm["n"] else 0)
        cis.append((0, pm["wilson95_clustercorrected_upper"]))
    if bf:
        g = bf["soundness_foreign_targets"]
        labels.append(f"AgentDojo\n(n={g['n']})"); vals.append(g["false_permit_rate"] or 0)
        cis.append((0, g["wilson95"]["high"]))
    if labels:
        emit("fig_false_permit_rate.svg",
             _bars("False Permit Rate with Wilson 95% upper bound", labels, vals,
                   "false permit rate", fmt="{:.2e}", colors=[BLUE]*len(labels),
                   ymax=max([c[1] for c in cis]) * 1.3, ci=cis))
    else:
        skipped.append("fig_false_permit_rate.svg")

    # -- Fig 3 & 4: latency + throughput vs threads (Exp4) --
    cs = _load(EXP / "stress" / "concurrency_scaling.json")
    if cs:
        xs = [L["n_threads"] for L in cs["levels"]]
        p50 = [L["latency_ms"]["p50"] for L in cs["levels"]]
        p95 = [L["latency_ms"]["p95"] for L in cs["levels"]]
        p99 = [L["latency_ms"]["p99"] for L in cs["levels"]]
        emit("fig_latency.svg", _line("Decision Latency vs Threads (Exp 4)", xs,
             [("p50", p50, GREEN), ("p95", p95, BLUE), ("p99", p99, RED)],
             "latency (ms)", "threads", logx=True, fmt="{:.4f}"))
        tput = [L["throughput_decisions_per_s"] for L in cs["levels"]]
        emit("fig_throughput.svg", _line("Throughput vs Threads (Exp 4)", xs,
             [("throughput", tput, BLUE)], "decisions / s", "threads", logx=True, fmt="{:.0f}"))
    else:
        skipped += ["fig_latency.svg", "fig_throughput.svg"]

    # -- Fig 5: replay integrity (Exp2) --
    rp = _load(EXP / "replay" / "replay_report.json")
    if rp:
        emit("fig_replay_integrity.svg",
             _bars("Replay Integrity Failures (Exp 2)",
                   ["records\nverified", "adjacency\nfail", "ledger-bind\nfail", "consistency\nfail"],
                   [rp["decision_records_verified"], rp["hash_chain_adjacency_failures"],
                    rp["ledger_bind_failures"], rp["self_consistency_failures"]],
                   "count", fmt="{:g}", colors=[GREEN, RED, RED, RED],
                   ymax=rp["decision_records_verified"] * 1.2))
    else:
        skipped.append("fig_replay_integrity.svg")

    # -- Fig 6: component ablation leaked permits (Exp5) --
    ab = _load(EXP / "ablation" / "ablation.json")
    if ab:
        labels = [c["config"].replace("remove_", "−").replace("_", " ").replace("baseline full LDREA", "baseline")
                  for c in ab["configs"]]
        leaks = [c["leaked_permits_vs_baseline"] for c in ab["configs"]]
        cols = [GREEN if v == 0 else RED for v in leaks]
        emit("fig_component_ablation.svg",
             _bars("Leaked Permits by Component Removed (Exp 5)", labels, leaks,
                   "leaked permits (of 60,000)", fmt="{:,.0f}", colors=cols, ymax=max(leaks) * 1.2 or 1))
    else:
        skipped.append("fig_component_ablation.svg")

    # -- Fig 7: runtime breakdown per stage (Exp6) --
    sd = _load(EXP / "profiling" / "stage_distributions.json")
    if sd and sd.get("stages"):
        labels = list(sd["stages"].keys())
        means = [sd["stages"][k]["mean_ms"] for k in labels]
        p95s = [max(sd["stages"][k]["p95_ms"] - sd["stages"][k]["mean_ms"], 0) for k in labels]
        short = [l.replace("_", "\n") for l in labels]
        emit("fig_runtime_breakdown.svg",
             _stacked("Per-Stage Runtime (mean + tail to p95), Exp 6", short,
                      [("mean ms", means, BLUE), ("→p95", p95s, "#9ec5e0")], "ms"))
    else:
        skipped.append("fig_runtime_breakdown.svg")

    # -- Fig 8: runtime robustness — safety holds per fault family (Exp8) --
    rob = _load(ROOT / "fresh_evidence" / "robustness" / "robustness.json")
    if rob and rob.get("fault_families"):
        fams = rob["fault_families"]
        labels = [f["family"].replace("_", " ")[:14] for f in fams]
        # bar height = trials; green if safety holds, red otherwise
        vals = [max(f["n_trials"], 1) for f in fams]
        cols = [GREEN if f["safety_holds"] else RED for f in fams]
        emit("fig_robustness.svg",
             _bars(f"Runtime Robustness — safety holds {rob['aggregate']['families_where_safety_holds']}"
                   f"/{rob['aggregate']['n_families_evaluable']} families, "
                   f"{rob['aggregate']['total_false_permits']} false permits (Exp 8)",
                   labels, vals, "trials (green=safety holds)", fmt="{:g}", colors=cols,
                   ymax=max(vals) * 1.25))
    else:
        skipped.append("fig_robustness.svg")

    # -- Fig 9: Predicate coverage & single-deficit isolation (Exp 9) --
    pc = _load(EXP / "predicate_coverage" / "predicate_coverage.json")
    if pc:
        cov, iso = pc["predicate_coverage"], pc["single_deficit_isolation"]
        veto, isb = pc["class_veto_isolation"], pc["isb_conjunct_isolation"]
        labels = ["node gates", "derived defs", "1-deficit denials", "class-veto", "ISB conjuncts"]
        vals = [cov["node_gates_covered"], cov["derived_deficits_covered"],
                iso["denied"], veto["denied_with_gamma_g_zero"], isb["isb_zeroed"]]
        totals = [cov["node_gates_total"], cov["derived_deficits_total"],
                  iso["n"], veto["n"], isb["n"]]
        cols = [GREEN if v == t else RED for v, t in zip(vals, totals)]
        emit("fig_predicate_coverage.svg",
             _bars(f"Runtime Predicate Coverage — {cov['covered']}/{cov['total_predicates']} "
                   f"({cov['coverage_rate'] * 100:.0f}%), {iso['false_permits']} false permits (Exp 9)",
                   labels, vals, "count covered / passing", fmt="{:g}", colors=cols,
                   ymax=max(totals) * 1.25))
    else:
        skipped.append("fig_predicate_coverage.svg")

    idx = ["# Figures — generated from executed artifacts only", "",
           f"Generated: {len(made)} figures.", ""]
    idx += [f"- ✅ {m}" for m in made] + [f"- ⏭️ skipped: {s}" for s in skipped]
    (FIG / "INDEX.md").write_text("\n".join(idx))
    print(f"[figures] wrote {len(made)}: {', '.join(made)}")
    if skipped:
        print(f"[figures] skipped {len(skipped)}: {skipped}")


if __name__ == "__main__":
    main()
