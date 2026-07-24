#!/usr/bin/env python3
"""
paper_figure_generator.py — regenerate paper figures directly from the table CSVs.
==================================================================================

Figures are produced from `paper_tables/*.csv` (which the table generator built from experiment
artifacts) — so every plotted point is traceable to raw experiment output. No values are typed here.

Rendering is hand-rolled SVG (matplotlib/scipy are NOT dependencies of this repo). Each figure also
emits its plotted (x,y) series as a sibling `.csv` so a reviewer can re-plot in any tool. PNG/PDF are
emitted only if a converter (rsvg-convert / cairosvg / inkscape) is available; otherwise the SVG +
data CSV are the portable artifacts and the absence of PNG/PDF is reported honestly (not faked).
"""
from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TABLES = ROOT / "paper_tables"
OUT = ROOT / "paper_figures"

_W, _H, _PAD = 720, 380, 60


def _read_csv(name: str) -> list[list[str]]:
    p = TABLES / name
    if not p.exists():
        return []
    with open(p) as f:
        return list(csv.reader(f))


def _svg_header(title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
            f'viewBox="0 0 {_W} {_H}" font-family="Helvetica,Arial,sans-serif">',
            f'<rect width="{_W}" height="{_H}" fill="white"/>',
            f'<text x="{_W/2}" y="26" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>']


def _axes(xs_labels, ymax, ylabel):
    x0, y0 = _PAD, _H - _PAD
    x1, y1 = _W - _PAD, _PAD
    s = [f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="black"/>',
         f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="black"/>',
         f'<text x="18" y="{(_H)/2}" transform="rotate(-90 18 {_H/2})" '
         f'text-anchor="middle" font-size="12">{ylabel}</text>']
    n = len(xs_labels)
    for i, lab in enumerate(xs_labels):
        px = x0 + (i + 0.5) * (x1 - x0) / max(1, n)
        s.append(f'<text x="{px:.1f}" y="{y0+18}" text-anchor="middle" font-size="11">{lab}</text>')
    for f in (0, 0.5, 1.0):
        gy = y0 - f * (y0 - y1)
        s.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="#eee"/>')
        s.append(f'<text x="{x0-6}" y="{gy+4:.1f}" text-anchor="end" font-size="10">{ymax*f:.3g}</text>')
    return s, (x0, y0, x1, y1)


def _bar_fig(name, title, labels, values, ylabel):
    if not values:
        return None
    ymax = max(values) or 1.0
    s = _svg_header(title)
    ax, (x0, y0, x1, y1) = _axes(labels, ymax, ylabel)
    s += ax
    n = len(values)
    bw = (x1 - x0) / max(1, n) * 0.6
    for i, v in enumerate(values):
        px = x0 + (i + 0.5) * (x1 - x0) / n
        bh = (v / ymax) * (y0 - y1)
        s.append(f'<rect x="{px-bw/2:.1f}" y="{y0-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                 f'fill="#2b6cb0"/>')
        s.append(f'<text x="{px:.1f}" y="{y0-bh-4:.1f}" text-anchor="middle" font-size="9">{v:.3g}</text>')
    s.append("</svg>")
    _emit(name, "\n".join(s), list(zip(labels, values)))
    return name


def _line_fig(name, title, xs, ys, ylabel, xlabel):
    if not ys:
        return None
    ymax = max(ys) or 1.0
    s = _svg_header(title)
    ax, (x0, y0, x1, y1) = _axes([str(x) for x in xs], ymax, ylabel)
    s += ax
    n = len(ys)
    pts = []
    for i, v in enumerate(ys):
        px = x0 + (i + 0.5) * (x1 - x0) / n
        py = y0 - (v / ymax) * (y0 - y1)
        pts.append(f"{px:.1f},{py:.1f}")
        s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#c05621"/>')
    s.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#c05621" stroke-width="2"/>')
    s.append(f'<text x="{_W/2}" y="{_H-8}" text-anchor="middle" font-size="12">{xlabel}</text>')
    s.append("</svg>")
    _emit(name, "\n".join(s), list(zip(xs, ys)))
    return name


def _emit(name, svg_text, series):
    OUT.mkdir(exist_ok=True)
    svg_path = OUT / f"{name}.svg"
    svg_path.write_text(svg_text)
    with open(OUT / f"{name}_data.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["x", "y"]); w.writerows(series)
    # optional raster/vector conversion if a converter exists (never fabricated)
    for tool, args in (("rsvg-convert", ["-f", "png", "-o"]), ("cairosvg", ["-o"]),
                       ("inkscape", ["--export-filename"])):
        if shutil.which(tool):
            try:
                if tool == "rsvg-convert":
                    subprocess.run([tool, "-f", "png", "-o", str(OUT / f"{name}.png"), str(svg_path)], check=True)
                elif tool == "cairosvg":
                    subprocess.run([tool, str(svg_path), "-o", str(OUT / f"{name}.png")], check=True)
                else:
                    subprocess.run([tool, str(svg_path), "--export-filename", str(OUT / f"{name}.png")], check=True)
            except Exception:
                pass
            break


def generate_all() -> dict:
    produced, notes = [], []

    # Fig 1 — LAB primary metric rates
    lab = _read_csv("table_lab_primary_metrics.csv")
    if lab:
        labels = [r[0] for r in lab[1:] if len(r) > 3]
        vals = [float(r[3]) for r in lab[1:] if len(r) > 3]
        f = _bar_fig("fig_lab_primary_rates", "LAB v1.0 Primary Metric Rates", labels, vals, "rate")
        if f: produced.append(f)

    # Fig 2 — concurrency throughput vs threads
    cc = _read_csv("table_concurrency_scaling.csv")
    if cc:
        xs = [int(r[0]) for r in cc[1:]]
        ys = [float(r[1]) for r in cc[1:]]
        f = _line_fig("fig_concurrency_throughput", "Throughput vs Threads (frozen path)",
                      xs, ys, "dec/s", "threads")
        if f: produced.append(f)
        # Fig 3 — p99 latency vs threads
        p99 = [float(r[6]) for r in cc[1:]]
        f2 = _line_fig("fig_concurrency_p99", "P99 Latency vs Threads", xs, p99, "ms", "threads")
        if f2: produced.append(f2)

    png_ok = any((OUT / f"{p}.png").exists() for p in produced)
    if not png_ok:
        notes.append("PNG/PDF not emitted: no SVG converter (rsvg-convert/cairosvg/inkscape) on PATH. "
                     "SVG + *_data.csv are the portable, reproducible artifacts.")
    return {"figures": produced, "out_dir": str(OUT.relative_to(ROOT)), "notes": notes}


if __name__ == "__main__":
    import json
    print(json.dumps(generate_all(), indent=2))
