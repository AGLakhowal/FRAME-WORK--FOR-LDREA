"""Phase G --- publication figures (dependency-free SVG) + CSV source + HTML dashboard.

matplotlib/scipy are unavailable in this environment, so figures are emitted as hand-rolled SVG
(scalable vector — the publication master) plus the CSV source behind every figure. PNG/PDF are
derivable from the SVG via any vector converter (documented; not fabricated here). Every figure is
computed from real statistics produced by stats_engine.
"""
from __future__ import annotations

from pathlib import Path

from ._util import write_text
import csv


# ------------------------------------------------------------------ SVG primitives
def _svg(w: int, h: int, body: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{title}">'
            f'<rect width="{w}" height="{h}" fill="white"/>'
            f'<text x="{w/2}" y="20" text-anchor="middle" font-family="sans-serif" '
            f'font-size="14" font-weight="bold">{title}</text>{body}</svg>')


def _bar_chart(title: str, labels, values, w=640, h=360, color="#3b6ea5") -> str:
    if not values:
        return _svg(w, h, '<text x="20" y="200" font-family="sans-serif">no data</text>', title)
    m = max(values) or 1
    pad_l, pad_b, pad_t = 60, 90, 40
    bw = (w - pad_l - 20) / max(1, len(values))
    body = []
    for i, (lab, v) in enumerate(zip(labels, values)):
        bh = (h - pad_b - pad_t) * (v / m)
        x = pad_l + i * bw + 4
        y = h - pad_b - bh
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-8:.1f}" height="{bh:.1f}" fill="{color}"/>')
        body.append(f'<text x="{x+bw/2-4:.1f}" y="{y-4:.1f}" text-anchor="middle" font-family="sans-serif" font-size="10">{v}</text>')
        body.append(f'<text x="{x+bw/2-4:.1f}" y="{h-pad_b+14:.1f}" text-anchor="end" font-family="sans-serif" '
                    f'font-size="9" transform="rotate(-35 {x+bw/2-4:.1f} {h-pad_b+14:.1f})">{_short(str(lab))}</text>')
    body.append(f'<line x1="{pad_l}" y1="{h-pad_b}" x2="{w-10}" y2="{h-pad_b}" stroke="#333"/>')
    body.append(f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{h-pad_b}" stroke="#333"/>')
    return _svg(w, h, "".join(body), title)


def _heatmap(title: str, row_labels, col_labels, matrix, w=680, h=380) -> str:
    if not matrix or not matrix[0]:
        return _svg(w, h, '<text x="20" y="200" font-family="sans-serif">no data</text>', title)
    mx = max((max(r) for r in matrix), default=1) or 1
    pad_l, pad_t = 160, 60
    cw = (w - pad_l - 20) / len(col_labels)
    ch = (h - pad_t - 40) / len(row_labels)
    body = []
    for i, rl in enumerate(row_labels):
        for j, _cl in enumerate(col_labels):
            v = matrix[i][j]
            inten = v / mx
            r = int(255 - 155 * inten); g = int(255 - 200 * inten); b = int(255 - 60 * inten)
            x = pad_l + j * cw; y = pad_t + i * ch
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
                        f'fill="rgb({r},{g},{b})" stroke="#eee"/>')
            body.append(f'<text x="{x+cw/2:.1f}" y="{y+ch/2+3:.1f}" text-anchor="middle" '
                        f'font-family="sans-serif" font-size="9">{v}</text>')
        body.append(f'<text x="{pad_l-6}" y="{pad_t+i*ch+ch/2+3:.1f}" text-anchor="end" '
                    f'font-family="sans-serif" font-size="10">{_short(str(rl),22)}</text>')
    for j, cl in enumerate(col_labels):
        body.append(f'<text x="{pad_l+j*cw+cw/2:.1f}" y="{pad_t-6}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="10">{_short(str(cl),12)}</text>')
    return _svg(w, h, "".join(body), title)


def _short(s: str, n: int = 14) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


# ------------------------------------------------------------------ figures
def generate(stats: dict, outdir: str | Path) -> dict:
    out = Path(outdir); (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "figures" / "csv").mkdir(parents=True, exist_ok=True)
    figs = {}

    # Fig 1 — Gamma histogram
    g = stats["gamma_global"]["distribution"]
    labels = [f"Γ={i}" for i in range(len(g["counts"]))]
    _fig(out, "fig1_gamma_histogram", _bar_chart("Γ_global distribution", labels, g["counts"], color="#3b6ea5"),
         [["gamma_global", "count"]] + [[i, c] for i, c in enumerate(g["counts"])], figs)

    # Fig 2 — Pi histogram
    p = stats["pi"]["distribution"]
    _fig(out, "fig2_pi_histogram", _bar_chart("Π distribution", [f"Π={i}" for i in range(len(p['counts']))],
         p["counts"], color="#6a8d3b"),
         [["pi", "count"]] + [[i, c] for i, c in enumerate(p["counts"])], figs)

    # Fig 3 — predicate activation heatmap (predicate x {activations, failures})
    pf = stats["predicate_frequency"]
    rows = sorted(pf, key=lambda k: -pf[k]["activations"])
    matrix = [[pf[r]["activations"], pf[r]["failures"]] for r in rows]
    _fig(out, "fig3_predicate_heatmap", _heatmap("Predicate activation vs failure", rows,
         ["activations", "failures"], matrix),
         [["predicate", "activations", "failures"]] + [[r, pf[r]["activations"], pf[r]["failures"]] for r in rows], figs)

    # Fig 4 — tool authorization heatmap (tool x {permit, deny})
    tf = stats["tool_frequency"]
    trows = sorted(tf, key=lambda k: -tf[k]["n"])
    tmatrix = [[tf[t]["permit"], tf[t]["deny"]] for t in trows]
    _fig(out, "fig4_tool_authorization_heatmap", _heatmap("Tool authorization (permit/deny)", trows,
         ["permit", "deny"], tmatrix),
         [["tool", "permit", "deny"]] + [[t, tf[t]["permit"], tf[t]["deny"]] for t in trows], figs)

    # Fig 5 — latency by event type
    lt = stats["latency_ms"]["by_event_type"]
    lrows = sorted(lt, key=lambda k: -(lt[k]["mean"] or 0))
    _fig(out, "fig5_latency_by_event", _bar_chart("Mean latency by event type (ms)", lrows,
         [round(lt[k]["mean"] or 0, 3) for k in lrows], w=760, color="#a5533b"),
         [["event_type", "mean_ms", "count"]] + [[k, lt[k]["mean"], lt[k]["count"]] for k in lrows], figs)

    # Fig 6 — policy utilization
    pu = stats["policy_utilization"]
    prows = sorted(pu, key=lambda k: -pu[k])
    _fig(out, "fig6_policy_utilization", _bar_chart("Policy-class utilization", prows,
         [pu[k] for k in prows], color="#7a3ba5"),
         [["policy_class", "count"]] + [[k, pu[k]] for k in prows], figs)

    # HTML dashboard embedding all SVGs
    html = ["<!doctype html><meta charset='utf-8'><title>L-DREA Audit Dashboard</title>",
            "<style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}"
            "figure{margin:1.5rem 0;border:1px solid #ddd;border-radius:8px;padding:1rem}"
            "svg{max-width:100%;height:auto}</style>",
            "<h1>L-DREA × AgentDojo × Gamma — Statistical Dashboard</h1>",
            f"<p>Episodes: {stats['n_episodes']} · Gamma decisions: {stats['n_decisions']} "
            f"(PERMIT {stats['n_authorizations_permit']}, SAFE_STATE {stats['n_denials']})</p>"]
    for key, fig in figs.items():
        html.append(f"<figure><figcaption><b>{key}</b> (source: figures/csv/{key}.csv)</figcaption>{fig['svg']}</figure>")
    write_text(out / "dashboard.html", "\n".join(html))
    return {"n_figures": len(figs), "figures": list(figs.keys()), "dashboard": str(out / "dashboard.html")}


def _fig(out: Path, name: str, svg: str, csv_rows, figs: dict):
    write_text(out / "figures" / f"{name}.svg", svg)
    with open(out / "figures" / "csv" / f"{name}.csv", "w", newline="") as f:
        csv.writer(f).writerows(csv_rows)
    figs[name] = {"svg": svg, "csv": f"figures/csv/{name}.csv"}
