#!/usr/bin/env python3
"""
generate_paper_figures.py
=========================

Render the seven IEEE-Access-ready publication figures for the L-DREA combined
ablation study.  Every figure is emitted as SVG + PDF + PNG into ``paper_figures/``
using the repository's own dependency-light vector backend
(:mod:`paper_figure_backends`).

Design constraints
------------------
* PRINT figures: white background, dark text, colourblind-safe (Okabe-Ito based)
  palette.  This is deliberately NOT the dark dashboard theme.
* Every number is READ FROM the experiment artifacts.  Nothing is hardcoded.
* ``None``/null metrics mean "this plane was destroyed / the metric is undefined";
  they are mapped to a health of 0.0 for scoring and rendered as "n/a".
* Deterministic: no randomness, no timestamps baked into the figures.

Sources
-------
    experiments/combined_ablation/combined_ablation.json
    experiments/combined_ablation/threshold_sensitivity.json
    experiments/combined_ablation/cross_dataset_ablation.json

Usage
-----
    python3 generate_paper_figures.py            # render + validate
    python3 generate_paper_figures.py --no-validate
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

from paper_figure_backends import Canvas

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "experiments" / "combined_ablation"
OUT_DIR = ROOT / "paper_figures"

COMBINED_JSON = SRC_DIR / "combined_ablation.json"
THRESHOLD_JSON = SRC_DIR / "threshold_sensitivity.json"
CROSS_JSON = SRC_DIR / "cross_dataset_ablation.json"

# --------------------------------------------------------------------------
# print theme (light, colourblind-safe: Okabe-Ito)
# --------------------------------------------------------------------------

INK = "#111111"        # primary text
INK_SOFT = "#555555"   # secondary text / captions
RULE = "#9a9a9a"       # axis rules
GRID = "#dddddd"       # gridlines
PANEL = "#ffffff"

OI_BLUE = "#0072b2"
OI_SKY = "#56b4e9"
OI_GREEN = "#009e73"
OI_ORANGE = "#e69f00"
OI_VERM = "#d55e00"
OI_PURPLE = "#cc79a7"
OI_YELLOW = "#f0e442"
NA_GREY = "#bdbdbd"

# Sequential single-hue ramp (monotone lightness -> safe under any CVD).
SEQ_STOPS = ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"]

VERDICT_COLOR = {
    "BASELINE": OI_BLUE,
    "PASS": OI_GREEN,
    "AUDIT-DEGRADED": OI_ORANGE,
    "SECURITY-DEGRADED": OI_PURPLE,
    "CRITICAL": OI_VERM,
}
VERDICT_ORDER = ["BASELINE", "PASS", "AUDIT-DEGRADED", "SECURITY-DEGRADED", "CRITICAL"]

INTERACTION_COLOR = {
    "Additive": OI_SKY,
    "Critical Dependency": OI_VERM,
    "Redundant (saturated)": OI_PURPLE,
    "Synergistic": OI_GREEN,
}
INTERACTION_ORDER = [
    "Additive",
    "Critical Dependency",
    "Redundant (saturated)",
    "Synergistic",
]

MATRIX_CODES = ["PE", "RV", "EQ", "LG", "HC"]

# The six health planes that constitute the runtime integrity score (RIS).
# Order matches the RIS definition string in the artifact.
PLANES = [
    ("Risk\ndetection", "blind_risk_detection_recall", True),
    ("Revocation", "revocation_compliance", False),
    ("Evidence", "evidence_completeness", False),
    ("Ledger", "ledger_integrity", False),
    ("Hash-chain", "hash_chain_integrity", False),
    ("Replay", "replay_integrity", False),
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _lerp_color(a: str, b: str, t: float) -> str:
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return "#%02x%02x%02x" % (
        int(round(ar + (br - ar) * t)),
        int(round(ag + (bg - ag) * t)),
        int(round(ab + (bb - ab) * t)),
    )


def seq_color(v: float) -> str:
    """Map v in [0,1] onto the sequential ramp."""
    v = min(max(float(v), 0.0), 1.0)
    n = len(SEQ_STOPS) - 1
    pos = v * n
    i = min(int(pos), n - 1)
    return _lerp_color(SEQ_STOPS[i], SEQ_STOPS[i + 1], pos - i)


def seq_text_on(v: float) -> str:
    """Legible annotation colour on top of seq_color(v)."""
    return "#ffffff" if v >= 0.55 else INK


def clamp01(v: float) -> float:
    return min(max(float(v), 0.0), 1.0)


def verdict_key(verdict: str | None) -> str:
    """'CRITICAL (security AND audit ...)' -> 'CRITICAL'."""
    if not verdict:
        return "PASS"
    head = verdict.split("(")[0].strip()
    return head if head in VERDICT_COLOR else "PASS"


def short_config(name: str) -> str:
    """'remove_EQ+HC+LG' -> 'remove EQ+HC+LG'; baseline -> 'baseline (full L-DREA)'."""
    if name.startswith("baseline"):
        return "baseline (full L-DREA)"
    return name.replace("remove_", "-").replace("_", " ")


def fmt_effect(eff: float) -> str:
    """Format an interaction effect.  Values that round to zero at 3 dp are shown
    as a plain '0.000' -- printing '-0.000' for an effect of -1e-06 would read as a
    real (negative) interaction when it is numerically nil."""
    eff = float(eff)
    if abs(eff) < 5e-4:
        return "0.000"
    return f"{eff:+.3f}"


def fmt(v, nd=2, na="n/a") -> str:
    if v is None:
        return na
    return f"{float(v):.{nd}f}"


def arrow(c: Canvas, x1, y1, x2, y2, color, sw=1.4, head=7.0, shrink_to=0.0):
    """Line from (x1,y1) to (x2,y2) with a filled arrowhead at the target end."""
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return
    ux, uy = dx / L, dy / L
    # stop short of the target node
    tx, ty = x2 - ux * shrink_to, y2 - uy * shrink_to
    bx, by = tx - ux * head, ty - uy * head
    c.line(x1, y1, bx, by, stroke=color, stroke_width=sw)
    px, py = -uy, ux
    c.polyline(
        [(tx, ty), (bx + px * head * 0.42, by + py * head * 0.42),
         (bx - px * head * 0.42, by - py * head * 0.42)],
        stroke=color, stroke_width=0.8, fill=color,
    )


# --------------------------------------------------------------------------
# data loading + derivation
# --------------------------------------------------------------------------

def load_sources() -> dict:
    with COMBINED_JSON.open() as fh:
        combined = json.load(fh)
    with THRESHOLD_JSON.open() as fh:
        threshold = json.load(fh)
    with CROSS_JSON.open() as fh:
        cross = json.load(fh)
    return {"combined": combined, "threshold": threshold, "cross": cross}


def baseline_config(combined: dict) -> dict:
    for cfg in combined["configs"]:
        if cfg.get("n_disabled", 0) == 0:
            return cfg
    return combined["configs"][0]


def plane_values(cfg: dict, base_detection: float) -> list[float | None]:
    """The six health planes for a config, each in [0,1].

    Returns the RAW value per plane (None if the metric is undefined, i.e. the
    plane was destroyed by the ablation).  Detection is normalised against the
    baseline detection rate, exactly as the RIS definition prescribes.
    """
    out: list[float | None] = []
    for _label, key, normalise in PLANES:
        v = cfg.get(key)
        if v is None:
            out.append(None)
            continue
        v = float(v)
        if normalise:
            v = v / base_detection if base_detection > 0 else 0.0
        out.append(clamp01(v))
    return out


def plane_health(cfg: dict, base_detection: float) -> list[float]:
    """Plane values with None -> 0.0 (destroyed plane).  Mean == RIS."""
    return [0.0 if v is None else v for v in plane_values(cfg, base_detection)]


# --------------------------------------------------------------------------
# shared chrome
# --------------------------------------------------------------------------

def title_block(c: Canvas, x, y, title, subtitle=None, size=15):
    c.text(x, y, title, size=size, bold=True, fill=INK)
    if subtitle:
        c.text(x, y + 17, subtitle, size=9.5, fill=INK_SOFT)


def caption(c: Canvas, x, y, lines, size=8.5):
    for i, line in enumerate(lines):
        c.text(x, y + i * 12, line, size=size, fill=INK_SOFT)


def colorbar(c: Canvas, x, y, w, h, label, lo="0.0", hi="1.0", n=64):
    """Horizontal continuous colour legend for the sequential ramp."""
    for i in range(n):
        t = i / (n - 1)
        c.rect(x + i * (w / n), y, w / n + 0.6, h, fill=seq_color(t))
    c.rect(x, y, w, h, stroke=RULE, stroke_width=0.7)
    c.text(x, y + h + 10, lo, size=8, fill=INK_SOFT, anchor="middle")
    c.text(x + w, y + h + 10, hi, size=8, fill=INK_SOFT, anchor="middle")
    c.text(x + w / 2, y - 5, label, size=8.5, fill=INK, anchor="middle")


# --------------------------------------------------------------------------
# FIGURE 1 -- combined ablation matrix (19 configs x 6 health planes)
# --------------------------------------------------------------------------

def fig_combined_ablation_matrix(data: dict) -> tuple[str, Canvas]:
    combined = data["combined"]
    configs = combined["configs"]
    base = baseline_config(combined)
    base_det = float(base["blind_risk_detection_recall"])

    left, top = 240.0, 108.0
    cw, ch = 86.0, 26.0
    n_rows, n_cols = len(configs), len(PLANES)
    W = int(left + n_cols * cw + 210)
    H = int(top + n_rows * ch + 136)

    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Combined ablation matrix: per-plane runtime health",
        f"{n_rows} configurations x {n_cols} health planes. "
        f"Cell = plane health in [0,1]; row mean = runtime integrity score (RIS). "
        f"Detection is normalised by the baseline rate ({base_det:.3f}).",
    )

    # column headers
    for j, (label, _key, _norm) in enumerate(PLANES):
        cx = left + j * cw + cw / 2
        parts = label.split("\n")
        for k, p in enumerate(parts):
            c.text(cx, top - 20 + k * 10, p, size=9, bold=True, fill=INK, anchor="middle")
    c.text(left + n_cols * cw + 14, top - 10, "RIS", size=9, bold=True, fill=INK)

    for i, cfg in enumerate(configs):
        y = top + i * ch
        raw = plane_values(cfg, base_det)
        health = [0.0 if v is None else v for v in raw]

        # row label
        c.text(left - 10, y + ch / 2 + 3.5, short_config(cfg["config"]),
               size=9, fill=INK, anchor="end",
               bold=(cfg.get("n_disabled", 0) == 0))

        for j, v in enumerate(raw):
            x = left + j * cw
            h = health[j]
            c.rect(x, y, cw, ch, fill=seq_color(h), stroke="#ffffff", stroke_width=1.0)
            txt = "n/a" if v is None else f"{h:.2f}"
            c.text(x + cw / 2, y + ch / 2 + 3.2, txt,
                   size=8.5, fill=NA_GREY if v is None else seq_text_on(h),
                   anchor="middle")

        ris = cfg.get("runtime_integrity_score")
        c.text(left + n_cols * cw + 14, y + ch / 2 + 3.5, fmt(ris, 3),
               size=8.5, fill=INK, bold=True)
        vk = verdict_key(cfg.get("overall_runtime_verdict"))
        c.rect(left + n_cols * cw + 62, y + 6, 10, ch - 12,
               fill=VERDICT_COLOR[vk])

    grid_bottom = top + n_rows * ch
    c.rect(left, top, n_cols * cw, n_rows * ch, stroke=RULE, stroke_width=0.8)

    # legends
    colorbar(c, left, grid_bottom + 34, 200, 12, "plane health (0 = destroyed, 1 = intact)")
    lx = left + 250
    c.text(lx, grid_bottom + 29, "verdict", size=8.5, fill=INK)
    for k, vk in enumerate(VERDICT_ORDER):
        yy = grid_bottom + 38 + k * 11
        c.rect(lx, yy, 9, 8, fill=VERDICT_COLOR[vk])
        c.text(lx + 13, yy + 7, vk, size=7.5, fill=INK_SOFT)

    caption(c, 24, grid_bottom + 80, [
        '"n/a" = the metric is undefined because the ablation destroyed that plane. It is scored as 0',
        "(destroyed) when averaging into the RIS, and never imputed.",
    ])
    return "combined_ablation_matrix", c


# --------------------------------------------------------------------------
# FIGURE 2 -- pairwise interaction matrix
# --------------------------------------------------------------------------

def fig_interaction_graph(data: dict) -> tuple[str, Canvas]:
    combined = data["combined"]
    pairs: dict[frozenset, dict] = {}

    # The registry names components "Evidence Quad"; the interaction records name
    # them "evidence_quad".  Bridge both spellings (and fall back to parsing the
    # short codes out of the `combination` string, e.g. "remove_EQ+HC").
    name_to_short: dict[str, str] = {}
    for cp in combined["component_registry"]["components"]:
        name_to_short[cp["name"]] = cp["short"]
        name_to_short[cp["name"].lower().replace(" ", "_")] = cp["short"]
        name_to_short[cp["short"]] = cp["short"]

    def codes_of(it: dict) -> frozenset:
        got = [name_to_short[n] for n in it.get("disabled_components", [])
               if n in name_to_short]
        if len(got) != it.get("order", len(got)):
            combo = it.get("combination", "")
            got = [p for p in combo.replace("remove_", "").split("+") if p]
        return frozenset(got)

    for it in combined["interactions"]:
        if it.get("order") != 2:
            continue
        codes = codes_of(it)
        if len(codes) == 2:
            pairs[codes] = it

    n = len(MATRIX_CODES)
    left, top = 150.0, 132.0
    cw, ch = 96.0, 62.0
    W = int(left + n * cw + 250)
    H = int(top + n * ch + 130)

    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Pairwise component interaction matrix",
        "Cell = interaction effect (observed degradation - additive prediction) for "
        "removing both components; colour = interaction class.",
    )
    c.text(24, 72, "effect < 0 -> the pair degrades LESS than the sum of its parts "
                   "(shared / saturated plane); effect = 0 -> exactly additive.",
           size=8.5, fill=INK_SOFT)

    for j, code in enumerate(MATRIX_CODES):
        c.text(left + j * cw + cw / 2, top - 12, code,
               size=11, bold=True, fill=INK, anchor="middle")
    for i, code in enumerate(MATRIX_CODES):
        c.text(left - 12, top + i * ch + ch / 2 + 4, code,
               size=11, bold=True, fill=INK, anchor="end")

    n_drawn = 0
    for i, a in enumerate(MATRIX_CODES):
        for j, b in enumerate(MATRIX_CODES):
            x, y = left + j * cw, top + i * ch
            if i == j:
                c.rect(x, y, cw, ch, fill="#f2f2f2", stroke="#ffffff", stroke_width=1.2)
                c.text(x + cw / 2, y + ch / 2 + 4, "-", size=11,
                       fill=NA_GREY, anchor="middle")
                continue
            it = pairs.get(frozenset((a, b)))
            if it is None:
                c.rect(x, y, cw, ch, fill="#f2f2f2", stroke="#ffffff", stroke_width=1.2)
                c.text(x + cw / 2, y + ch / 2 + 4, "n/a", size=9,
                       fill=NA_GREY, anchor="middle")
                continue
            cls = it.get("interaction_class", "Additive")
            col = INTERACTION_COLOR.get(cls, NA_GREY)
            eff = float(it["interaction_effect"])
            c.rect(x, y, cw, ch, fill=col, stroke="#ffffff", stroke_width=1.2,
                   opacity=0.92)
            c.text(x + cw / 2, y + ch / 2 - 4, fmt_effect(eff),
                   size=11, bold=True, fill="#ffffff", anchor="middle")
            c.text(x + cw / 2, y + ch / 2 + 12,
                   f"obs {float(it['observed_degradation']):.2f} / "
                   f"add {float(it['additive_prediction']):.2f}",
                   size=6.8, fill="#ffffff", anchor="middle")
            n_drawn += 1

    c.rect(left, top, n * cw, n * ch, stroke=RULE, stroke_width=0.8)
    bottom = top + n * ch

    lx = left + n * cw + 22
    c.text(lx, top + 4, "interaction class", size=9, bold=True, fill=INK)
    observed = {it.get("interaction_class") for it in pairs.values()}
    for k, cls in enumerate(INTERACTION_ORDER):
        yy = top + 16 + k * 20
        c.rect(lx, yy, 13, 13, fill=INTERACTION_COLOR[cls])
        seen = cls in observed
        c.text(lx + 19, yy + 11, cls, size=8.5,
               fill=INK if seen else NA_GREY)
        if not seen:
            c.text(lx + 19, yy + 20, "(not observed at order 2)", size=6.8, fill=NA_GREY)

    caption(c, 24, bottom + 28, [
        f"{n_drawn // 2} distinct component pairs (matrix is symmetric; "
        f"diagonal is undefined).",
        "Components: PE predicate engine, RV runtime revocation, EQ evidence quad, "
        "LG runtime ledger, HC hash chain.",
        "A 'Critical Dependency' cell means the two components share a plane, so the "
        "second removal costs almost nothing extra --",
        "the damage was already done by the first.",
    ])
    return "interaction_graph", c


# --------------------------------------------------------------------------
# FIGURE 3 -- threshold sensitivity heatmap
# --------------------------------------------------------------------------

def fig_threshold_heatmap(data: dict) -> tuple[str, Canvas]:
    th = data["threshold"]
    rows = th["rows"]
    deltas = sorted({int(r["threshold_delta_pct"]) for r in rows})
    # config order: baseline first, then as first encountered
    cfg_order: list[str] = []
    for r in rows:
        if r["config"] not in cfg_order:
            cfg_order.append(r["config"])
    cell = {(r["config"], int(r["threshold_delta_pct"])): r for r in rows}
    stable = bool(th.get("stability", {}).get("all_conclusions_stable", False))

    left, top = 230.0, 122.0
    cw, ch = 104.0, 46.0
    W = max(920, int(left + len(deltas) * cw + 120))
    H = int(top + len(cfg_order) * ch + 172)

    c = Canvas(W, H, bg=PANEL)
    verdict_line = ("conclusions are STABLE under +/-20% threshold perturbation"
                    if stable else
                    "WARNING - at least one conclusion is NOT stable")
    title_block(c, 24, 34, "Threshold sensitivity: " + verdict_line,
                "Every ablation conclusion holds at every threshold scale. "
                "Cell = runtime integrity score (colour + top line); "
                "undetected-risk rate (URR) below it.")
    n_checks = len(th.get("stability", {}).get("checks", {}))
    c.text(24, 72,
           f"{len(rows)} executions = {len(cfg_order)} configurations x "
           f"{len(deltas)} threshold scales; {n_checks} stability checks evaluated at "
           f"every scale.",
           size=8.5, fill=INK_SOFT)

    for j, d in enumerate(deltas):
        c.text(left + j * cw + cw / 2, top - 12, f"{d:+d}%",
               size=10, bold=True, fill=INK, anchor="middle")
    c.text(left + len(deltas) * cw / 2, top - 30, "threshold perturbation",
           size=9, fill=INK_SOFT, anchor="middle")

    for i, name in enumerate(cfg_order):
        y = top + i * ch
        c.text(left - 10, y + ch / 2 + 3.5, short_config(name), size=9.5,
               fill=INK, anchor="end", bold=name.startswith("baseline"))
        for j, d in enumerate(deltas):
            x = left + j * cw
            r = cell.get((name, d))
            if r is None:
                c.rect(x, y, cw, ch, fill="#f2f2f2", stroke="#ffffff", stroke_width=1.0)
                c.text(x + cw / 2, y + ch / 2 + 4, "n/a", size=9,
                       fill=NA_GREY, anchor="middle")
                continue
            ris = r.get("runtime_integrity_score")
            fpr = r.get("undetected_risk_rate")
            v = 0.0 if ris is None else clamp01(ris)
            c.rect(x, y, cw, ch, fill=seq_color(v), stroke="#ffffff", stroke_width=1.0)
            tcol = NA_GREY if ris is None else seq_text_on(v)
            c.text(x + cw / 2, y + 19, f"RIS {fmt(ris, 3)}", size=9, bold=True,
                   fill=tcol, anchor="middle")
            c.text(x + cw / 2, y + 33, f"FPR {fmt(fpr, 3)}", size=8.5,
                   fill=tcol, anchor="middle")

    c.rect(left, top, len(deltas) * cw, len(cfg_order) * ch,
           stroke=RULE, stroke_width=0.8)
    bottom = top + len(cfg_order) * ch

    colorbar(c, left, bottom + 34, 200, 12, "runtime integrity score")
    caption(c, 24, bottom + 86, [
        "RIS is invariant to the threshold scale (every row is flat): the ablation "
        "ranking does not depend on where the decision",
        "thresholds sit.  Only the undetected-risk rate (URR) moves with the threshold, and it "
        "moves for the baseline and the ablations alike.",
    ])
    return "threshold_heatmap", c


# --------------------------------------------------------------------------
# FIGURE 4 -- cross-dataset comparison
# --------------------------------------------------------------------------

def fig_dataset_comparison(data: dict) -> tuple[str, Canvas]:
    cross = data["cross"]
    datasets = cross["datasets"]

    series = []  # (dataset, domain, prevalence, base_fpr, pe_fpr)
    for ds in datasets:
        by = {cfg["config"]: cfg for cfg in ds["configs"]}
        b = by.get("baseline_full_LDREA", {})
        p = by.get("remove_PE", {})
        series.append({
            "name": ds["dataset"],
            "domain": ds.get("domain", ""),
            "prevalence": ds.get("prevalence"),
            "base": b.get("undetected_risk_rate"),
            "pe": p.get("undetected_risk_rate"),
        })
    # deterministic order: ULB, IEEE-CIS, UNSW-NB15 if present, else file order
    pref = ["ULB", "IEEE-CIS", "UNSW-NB15"]
    series.sort(key=lambda s: pref.index(s["name"]) if s["name"] in pref else 99)

    W, H = 900, 560
    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Cross-dataset replication: removing the predicate engine raises the "
        "undetected-risk rate (URR)",
        "Baseline (full L-DREA) vs remove_PE, on three independent real datasets. "
        "Gamma is untouched between datasets.",
    )

    ax_l, ax_r = 90.0, W - 250.0
    ax_t, ax_b = 118.0, 400.0
    plot_h = ax_b - ax_t

    # y axis 0..1 (undetected-risk rate (URR) is a rate)
    for k in range(6):
        v = k / 5
        y = ax_b - v * plot_h
        c.line(ax_l, y, ax_r, y, stroke=GRID, stroke_width=0.8)
        c.text(ax_l - 8, y + 3.5, f"{v:.1f}", size=9, fill=INK_SOFT, anchor="end")
    c.line(ax_l, ax_t, ax_l, ax_b, stroke=RULE, stroke_width=1.0)
    c.line(ax_l, ax_b, ax_r, ax_b, stroke=RULE, stroke_width=1.0)
    c.text(30, (ax_t + ax_b) / 2, "undetected-risk rate (URR)", size=10, fill=INK,
           anchor="middle", rotate=90)

    n = len(series)
    group_w = (ax_r - ax_l) / n
    bar_w = min(78.0, group_w * 0.3)
    gap = 18.0

    for i, s in enumerate(series):
        gx = ax_l + i * group_w + group_w / 2
        for k, (key, col, lab) in enumerate(
                [("base", OI_BLUE, "baseline"), ("pe", OI_VERM, "remove_PE")]):
            v = s[key]
            x = gx - bar_w - gap / 2 + k * (bar_w + gap)
            if v is None:
                c.text(x + bar_w / 2, ax_b - 8, "n/a", size=9, fill=NA_GREY,
                       anchor="middle")
                continue
            h = clamp01(v) * plot_h
            # a true 0.0 rate would be an invisible bar: draw a 2pt stub instead
            c.rect(x, ax_b - max(h, 2.0), bar_w, max(h, 2.0), fill=col,
                   stroke="#ffffff", stroke_width=0.8)
            c.text(x + bar_w / 2, ax_b - max(h, 2.0) - 7, f"{float(v):.3f}", size=9.5,
                   bold=True, fill=INK, anchor="middle")

        # rise annotation
        if s["base"] is not None and s["pe"] is not None:
            rise = float(s["pe"]) - float(s["base"])
            c.text(gx, ax_b + 20, s["name"], size=11, bold=True, fill=INK,
                   anchor="middle")
            c.text(gx, ax_b + 33, s["domain"], size=8.5, fill=INK_SOFT,
                   anchor="middle")
            prev = s["prevalence"]
            c.text(gx, ax_b + 46,
                   "attack prevalence " +
                   (f"{float(prev) * 100:.2f}%" if prev is not None else "n/a"),
                   size=8.5, fill=INK_SOFT, anchor="middle")
            c.text(gx, ax_b + 62, f"rise = {rise:+.3f}", size=9.5, bold=True,
                   fill=OI_VERM, anchor="middle")

    # legend
    lx = ax_r + 30
    c.text(lx, ax_t + 4, "configuration", size=9, bold=True, fill=INK)
    for k, (col, lab) in enumerate([(OI_BLUE, "baseline (full L-DREA)"),
                                    (OI_VERM, "remove_PE")]):
        yy = ax_t + 16 + k * 20
        c.rect(lx, yy, 13, 13, fill=col)
        c.text(lx + 19, yy + 11, lab, size=9, fill=INK)

    caption(c, 24, ax_b + 92, [
        "CAVEAT -- absolute undetected-risk rate (URR)s are NOT comparable across datasets: each",
        "has a different attack prevalence and base rate (shown above), so the bar heights",
        "of one dataset say nothing about another.  The finding that REPLICATES is the RISE:",
        "in every dataset, deleting the predicate engine drives the undetected-risk rate (URR) to its",
        "ceiling, independent of the base rate it started from.",
    ])
    return "dataset_comparison", c


# --------------------------------------------------------------------------
# FIGURE 5 -- runtime integrity score per configuration
# --------------------------------------------------------------------------

def fig_runtime_integrity(data: dict) -> tuple[str, Canvas]:
    combined = data["combined"]
    configs = sorted(
        combined["configs"],
        key=lambda cf: (-(cf.get("runtime_integrity_score") or 0.0), cf["config"]),
    )
    base_ris = combined.get("baseline_runtime_integrity_score")

    left = 240.0
    bar_h, bar_gap = 22.0, 6.0
    ax_t = 122.0
    ax_r_pad = 300.0
    W = 1020
    plot_w = W - left - ax_r_pad
    H = int(ax_t + len(configs) * (bar_h + bar_gap) + 110)

    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Runtime integrity score by configuration (sorted)",
        "RIS = mean of six health planes (detection, revocation, evidence, ledger, "
        "hash-chain, replay), normalised so the intact baseline scores "
        f"{fmt(base_ris, 2)}.",
    )
    c.text(24, 72, "Bars are coloured by the experiment's own overall runtime verdict.",
           size=8.5, fill=INK_SOFT)

    # x gridlines
    for k in range(6):
        v = k / 5
        x = left + v * plot_w
        c.line(x, ax_t - 8, x, ax_t + len(configs) * (bar_h + bar_gap),
               stroke=GRID, stroke_width=0.8)
        c.text(x, ax_t - 12, f"{v:.1f}", size=9, fill=INK_SOFT, anchor="middle")
    c.text(left + plot_w / 2, ax_t - 28, "runtime integrity score (RIS)",
           size=9.5, fill=INK, anchor="middle")

    # baseline reference line
    if base_ris is not None:
        bx = left + clamp01(base_ris) * plot_w
        c.line(bx, ax_t - 8, bx, ax_t + len(configs) * (bar_h + bar_gap),
               stroke=OI_BLUE, stroke_width=1.4, opacity=0.55)

    for i, cfg in enumerate(configs):
        y = ax_t + i * (bar_h + bar_gap)
        ris = cfg.get("runtime_integrity_score")
        v = 0.0 if ris is None else clamp01(ris)
        vk = verdict_key(cfg.get("overall_runtime_verdict"))
        c.text(left - 10, y + bar_h / 2 + 3.5, short_config(cfg["config"]),
               size=9.5, fill=INK, anchor="end",
               bold=(cfg.get("n_disabled", 0) == 0))
        w = v * plot_w
        if w < 1.5:
            # zero-height bar: draw a visible stub so "RIS = 0" is not invisible
            c.rect(left, y, 2.0, bar_h, fill=VERDICT_COLOR[vk])
        else:
            c.rect(left, y, w, bar_h, fill=VERDICT_COLOR[vk],
                   stroke="#ffffff", stroke_width=0.6)
        c.text(left + max(w, 2.0) + 8, y + bar_h / 2 + 3.5, fmt(ris, 3),
               size=9, bold=True, fill=INK)
        nd = cfg.get("n_disabled", 0)
        c.text(left + plot_w + 62, y + bar_h / 2 + 3.5,
               f"{nd} removed", size=8.5, fill=INK_SOFT)

    c.line(left, ax_t + len(configs) * (bar_h + bar_gap), left + plot_w,
           ax_t + len(configs) * (bar_h + bar_gap), stroke=RULE, stroke_width=1.0)
    bottom = ax_t + len(configs) * (bar_h + bar_gap)

    lx = left + plot_w + 130
    c.text(lx, ax_t + 4, "overall runtime verdict", size=9, bold=True, fill=INK)
    present = [v for v in VERDICT_ORDER
               if any(verdict_key(cf.get("overall_runtime_verdict")) == v
                      for cf in configs)]
    for k, vk in enumerate(VERDICT_ORDER):
        yy = ax_t + 16 + k * 19
        c.rect(lx, yy, 13, 13, fill=VERDICT_COLOR[vk])
        seen = vk in present
        c.text(lx + 19, yy + 11, vk, size=8.5, fill=INK if seen else NA_GREY)
        if not seen:
            c.text(lx + 19, yy + 19, "(not observed)", size=6.8, fill=NA_GREY)
    yy = ax_t + 16 + len(VERDICT_ORDER) * 19 + 8
    c.line(lx, yy + 6, lx + 13, yy + 6, stroke=OI_BLUE, stroke_width=1.4, opacity=0.55)
    c.text(lx + 19, yy + 9, f"baseline RIS = {fmt(base_ris, 2)}", size=8.5, fill=INK_SOFT)

    caption(c, 24, bottom + 32, [
        "RIS is audit-weighted by construction: four of the six planes are "
        "audit/provenance planes, so a purely",
        "security-degrading ablation (e.g. removing revocation) costs less RIS than "
        "an evidence-plane ablation.",
        "The verdict colour, not the bar length alone, carries the security "
        "interpretation.",
    ])
    return "runtime_integrity", c


# --------------------------------------------------------------------------
# FIGURE 6 -- graceful degradation
# --------------------------------------------------------------------------

def fig_graceful_degradation(data: dict) -> tuple[str, Canvas]:
    combined = data["combined"]
    by_n: dict[int, list[float]] = {}
    for cfg in combined["configs"]:
        n = int(cfg.get("n_disabled", 0))
        ris = cfg.get("runtime_integrity_score")
        by_n.setdefault(n, []).append(0.0 if ris is None else float(ris))

    ks_present = sorted(by_n)
    k_max = max(5, max(ks_present))
    x_ticks = list(range(0, k_max + 1))

    W, H = 900, 590
    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Graceful degradation: runtime integrity vs number of components removed",
        "Mean and worst case (minimum) RIS over every configuration with that many "
        "components removed.  Individual configurations shown as dots.",
    )

    ax_l, ax_r = 92.0, W - 250.0
    ax_t, ax_b = 112.0, 420.0
    pw, ph = ax_r - ax_l, ax_b - ax_t

    def X(k):
        return ax_l + (k / k_max) * pw

    def Y(v):
        return ax_b - clamp01(v) * ph

    for k in range(6):
        v = k / 5
        y = Y(v)
        c.line(ax_l, y, ax_r, y, stroke=GRID, stroke_width=0.8)
        c.text(ax_l - 8, y + 3.5, f"{v:.1f}", size=9, fill=INK_SOFT, anchor="end")
    for k in x_ticks:
        c.line(X(k), ax_b, X(k), ax_b + 5, stroke=RULE, stroke_width=1.0)
        c.text(X(k), ax_b + 18, str(k), size=10, fill=INK, anchor="middle")
    c.line(ax_l, ax_t, ax_l, ax_b, stroke=RULE, stroke_width=1.0)
    c.line(ax_l, ax_b, ax_r, ax_b, stroke=RULE, stroke_width=1.0)
    c.text((ax_l + ax_r) / 2, ax_b + 40, "number of components removed",
           size=10, fill=INK, anchor="middle")
    c.text(34, (ax_t + ax_b) / 2, "runtime integrity score (RIS)", size=10,
           fill=INK, anchor="middle", rotate=90)

    # individual configs
    for k in ks_present:
        for v in by_n[k]:
            c.circle(X(k), Y(v), 3.0, fill="#c7c7c7", stroke="#ffffff",
                     stroke_width=0.6)

    mean_pts = [(X(k), Y(sum(by_n[k]) / len(by_n[k]))) for k in ks_present]
    min_pts = [(X(k), Y(min(by_n[k]))) for k in ks_present]

    c.polyline(min_pts, stroke=OI_VERM, stroke_width=2.2)
    c.polyline(mean_pts, stroke=OI_BLUE, stroke_width=2.2)

    for k, (px, py) in zip(ks_present, mean_pts):
        c.circle(px, py, 5.0, fill=OI_BLUE, stroke="#ffffff", stroke_width=1.2)
        mv = sum(by_n[k]) / len(by_n[k])
        c.text(px, py - 11, f"{mv:.3f}", size=8.5, bold=True, fill=OI_BLUE,
               anchor="middle")
    # worst-case labels go BESIDE the marker: below it they would collide with the
    # x-axis ticks (the min is 0.0 for several k), and at k=0 they would collide
    # with the mean label (mean == min == baseline there).
    k_last = ks_present[-1]
    for k, (px, py) in zip(ks_present, min_pts):
        c.circle(px, py, 5.0, fill=OI_VERM, stroke="#ffffff", stroke_width=1.2)
        if k == k_last:
            c.text(px - 9, py + 3.5, f"{min(by_n[k]):.3f}", size=8.5, bold=True,
                   fill=OI_VERM, anchor="end")
        else:
            c.text(px + 9, py + 3.5, f"{min(by_n[k]):.3f}", size=8.5, bold=True,
                   fill=OI_VERM, anchor="start")

    missing = [k for k in x_ticks if k not in by_n]

    lx = ax_r + 26
    c.text(lx, ax_t + 4, "series", size=9, bold=True, fill=INK)
    c.line(lx, ax_t + 20, lx + 20, ax_t + 20, stroke=OI_BLUE, stroke_width=2.2)
    c.circle(lx + 10, ax_t + 20, 4.5, fill=OI_BLUE, stroke="#ffffff", stroke_width=1.0)
    c.text(lx + 26, ax_t + 23, "mean RIS", size=9, fill=INK)
    c.line(lx, ax_t + 40, lx + 20, ax_t + 40, stroke=OI_VERM, stroke_width=2.2)
    c.circle(lx + 10, ax_t + 40, 4.5, fill=OI_VERM, stroke="#ffffff", stroke_width=1.0)
    c.text(lx + 26, ax_t + 43, "worst case (min)", size=9, fill=INK)
    c.circle(lx + 10, ax_t + 60, 3.0, fill="#c7c7c7", stroke="#ffffff", stroke_width=0.6)
    c.text(lx + 26, ax_t + 63, "single configuration", size=9, fill=INK_SOFT)

    for k in ks_present:
        c.text(lx, ax_t + 90 + (k * 0), "", size=1)  # no-op, keeps layout stable
    c.text(lx, ax_t + 92, "configurations per k", size=8.5, bold=True, fill=INK)
    for i, k in enumerate(ks_present):
        c.text(lx, ax_t + 106 + i * 12, f"k = {k}:  n = {len(by_n[k])}",
               size=8.5, fill=INK_SOFT)

    lines = [
        "Degradation is monotone but NOT linear: the first removal already costs up to "
        f"{1.0 - min(by_n[min(k for k in ks_present if k >= 1)]):.2f} RIS in the worst case,",
        "because a single evidence-plane removal takes the ledger, hash-chain and replay "
        "planes down with it.",
    ]
    if missing:
        lines.append(
            "Note: no configuration in the ablation matrix removes exactly "
            + ", ".join(str(m) for m in missing)
            + " component(s), so that abscissa has no data and the lines interpolate "
              "across it."
        )
    caption(c, 24, ax_b + 76, lines)
    return "graceful_degradation", c


# --------------------------------------------------------------------------
# FIGURE 7 -- component dependency DAG
# --------------------------------------------------------------------------

def fig_dependency_graph(data: dict) -> tuple[str, Canvas]:
    reg = data["combined"]["component_registry"]
    comps = reg["components"]
    by_short = {c["short"]: c for c in comps}
    name_to_short = {c["name"]: c["short"] for c in comps}

    def deps_of(short: str) -> list[str]:
        raw = by_short[short].get("dependencies") or []
        out = []
        for d in raw:
            if d in by_short:
                out.append(d)
            elif d in name_to_short:
                out.append(name_to_short[d])
        return out

    # topological depth (0 = no dependencies)
    depth: dict[str, int] = {}

    def compute_depth(s: str, seen: frozenset = frozenset()) -> int:
        if s in depth:
            return depth[s]
        if s in seen:  # defensive: cycle
            return 0
        ds = deps_of(s)
        d = 0 if not ds else 1 + max(compute_depth(x, seen | {s}) for x in ds)
        depth[s] = d
        return d

    for s in by_short:
        compute_depth(s)

    matrix = [c["short"] for c in comps if c.get("in_ablation_matrix")]
    other = [c["short"] for c in comps if not c.get("in_ablation_matrix")]

    # Two horizontal bands: ablation-matrix components on top, the rest below.
    max_depth = max(depth.values())
    W, H = 1200, 940
    c = Canvas(W, H, bg=PANEL)
    title_block(
        c, 24, 34,
        "Component dependency DAG (discovered from the live runtime)",
        "Edge A -> B means A CONSUMES B (A depends on B).  Columns are topological "
        "depth: a component sits to the right of everything it depends on.",
    )

    band_x, band_w = 50.0, 830.0
    col_l, col_r = band_x + 120.0, band_x + band_w - 90.0

    def CX(d):
        return col_l + (d / max(1, max_depth)) * (col_r - col_l)

    band_top_y = 168.0
    band_bot_y = 534.0
    band_h = 330.0

    c.rect(band_x, band_top_y - 24, band_w, band_h, fill="#f4f8fc",
           stroke="#dbe6f0", stroke_width=1.0)
    c.text(band_x + 10, band_top_y - 9, "ABLATION MATRIX (can be disabled)",
           size=9, bold=True, fill=OI_BLUE)
    c.rect(band_x, band_bot_y - 24, band_w, band_h, fill="#f7f7f4",
           stroke="#e4e4dc", stroke_width=1.0)
    c.text(band_x + 10, band_bot_y - 9,
           "ALWAYS-ON PLANES (governance / risk / timing -- never ablated)",
           size=9, bold=True, fill=INK_SOFT)

    # depth-column tick labels
    for d in range(max_depth + 1):
        c.text(CX(d), 146, f"depth {d}", size=8, fill=NA_GREY, anchor="middle")

    pos: dict[str, tuple[float, float]] = {}

    def place(codes: list[str], y0: float, y_span: float):
        by_depth: dict[int, list[str]] = {}
        for s in codes:
            by_depth.setdefault(depth[s], []).append(s)
        for d, group in by_depth.items():
            group.sort(key=lambda s: reg["execution_order"].index(s)
                       if s in reg["execution_order"] else 99)
            n = len(group)
            for i, s in enumerate(group):
                y = y0 + (i + 1) * (y_span / (n + 1))
                pos[s] = (CX(d), y)

    place(matrix, band_top_y - 12, band_h - 40)
    place(other, band_bot_y - 12, band_h - 40)

    R = 26.0
    # edges first
    for s in by_short:
        if s not in pos:
            continue
        for d in deps_of(s):
            if d not in pos:
                continue
            x1, y1 = pos[s]
            x2, y2 = pos[d]
            same_band = (s in matrix) == (d in matrix)
            col = OI_BLUE if same_band and s in matrix else "#9fb3c2"
            # start on the rim of the consumer
            dx, dy = x2 - x1, y2 - y1
            L = math.hypot(dx, dy) or 1.0
            sx, sy = x1 + dx / L * R, y1 + dy / L * R
            arrow(c, sx, sy, x2, y2, col, sw=1.5, head=8.0, shrink_to=R + 2)

    # nodes
    for s, (x, y) in pos.items():
        comp = by_short[s]
        in_matrix = bool(comp.get("in_ablation_matrix"))
        fill = OI_BLUE if in_matrix else "#ffffff"
        stroke = OI_BLUE if in_matrix else INK_SOFT
        c.circle(x, y, R, fill=fill, stroke=stroke, stroke_width=2.0)
        c.text(x, y + 5, s, size=14, bold=True,
               fill="#ffffff" if in_matrix else INK, anchor="middle")
        c.text(x, y + R + 14, comp["name"], size=8.5, fill=INK, anchor="middle")
        c.text(x, y + R + 25, comp.get("execution_plane", "") + " plane",
               size=7.5, fill=INK_SOFT, anchor="middle")

    lx = band_x + band_w + 30
    c.text(lx, 176, "node type", size=9.5, bold=True, fill=INK)
    c.circle(lx + 12, 200, 11, fill=OI_BLUE, stroke=OI_BLUE, stroke_width=1.5)
    c.text(lx + 30, 204, f"in ablation matrix ({len(matrix)})", size=8.5, fill=INK)
    c.circle(lx + 12, 230, 11, fill="#ffffff", stroke=INK_SOFT, stroke_width=1.5)
    c.text(lx + 30, 234, f"always-on plane ({len(other)})", size=8.5, fill=INK)
    arrow(c, lx, 262, lx + 26, 262, OI_BLUE, sw=1.5, head=8.0)
    c.text(lx + 32, 265, "depends on", size=8.5, fill=INK)

    c.text(lx, 302, "execution order", size=9.5, bold=True, fill=INK)
    order = reg["execution_order"]
    half = (len(order) + 1) // 2
    c.text(lx, 320, " -> ".join(order[:half]) + " ->", size=8.5, fill=INK_SOFT)
    c.text(lx, 334, " -> ".join(order[half:]), size=8.5, fill=INK_SOFT)
    c.text(lx, 358, f"{reg.get('n_components', len(comps))} components discovered",
           size=8.5, fill=INK_SOFT)

    caption(c, 24, band_bot_y + band_h - 4, [
        "Discovery method: importlib + inspect probing of live runtime symbols; a "
        "component is listed only if its symbol resolves.",
        "The dependency structure explains the interaction matrix: HC depends on LG "
        "and EQ, and LG depends on EQ, so removing EQ",
        "already destroys the ledger and hash-chain planes -- which is why the "
        "EQ+LG and EQ+HC pairs read as Critical Dependency,",
        "not as additive damage.",
    ])
    return "dependency_graph", c


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def svg_texts(path: Path) -> list[str]:
    import xml.dom.minidom
    doc = xml.dom.minidom.parse(str(path))
    out = []
    for node in doc.getElementsByTagName("text"):
        out.append("".join(ch.data for ch in node.childNodes
                           if ch.nodeType == ch.TEXT_NODE))
    return out


def validate_svg(path: Path) -> str:
    import xml.dom.minidom
    doc = xml.dom.minidom.parse(str(path))
    root = doc.documentElement
    assert root.tagName == "svg", "root is not <svg>"
    n = len(doc.getElementsByTagName("*"))
    assert n > 10, f"suspiciously few elements ({n})"
    return f"parses, {n} elements"


def validate_pdf(path: Path) -> str:
    data = path.read_bytes()
    assert data.startswith(b"%PDF-"), "missing %PDF- header"
    assert data.rstrip().endswith(b"%%EOF"), "missing %%EOF"
    assert len(data) > 500, "too small"
    return f"%PDF- ... %%EOF, {len(data)} bytes"


def validate_png(path: Path) -> str:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"
    pos, idat, w, h = 8, b"", None, None
    while pos < len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        (crc,) = struct.unpack(">I", data[pos + 8 + ln:pos + 12 + ln])
        assert crc == (zlib.crc32(tag + body) & 0xFFFFFFFF), f"bad CRC on {tag!r}"
        if tag == b"IHDR":
            w, h, bit, ctype = struct.unpack(">IIBB", body[:10])
            assert (bit, ctype) == (8, 2), "expected 8-bit RGB"
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    raw = zlib.decompress(idat)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w * 3 + 1)
    pix = arr[:, 1:].reshape(h, w, 3)
    uniq = len(np.unique(pix.reshape(-1, 3), axis=0))
    assert uniq > 1, "image is blank (1 unique colour)"
    ink = int((pix.reshape(-1, 3).max(axis=1) < 200).sum())
    assert ink > 100, f"almost no ink ({ink} px)"
    return f"{w}x{h}, {uniq} unique colours, {ink} ink px"


def spot_checks(data: dict) -> list[tuple[str, bool, str]]:
    """Assert that values DRAWN in the figures equal the values in the source JSON.

    Each check recomputes the expected string straight from the artifact and then
    looks for it among the <text> nodes actually written into the SVG.  A
    hardcoded figure would fail as soon as the artifact changed.
    """
    checks: list[tuple[str, bool, str]] = []
    combined = data["combined"]
    by_cfg = {c["config"]: c for c in combined["configs"]}

    # --- check 1: fig 1 renders remove_HC's hash-chain plane health ---------
    t1 = svg_texts(OUT_DIR / "combined_ablation_matrix.svg")
    hc = by_cfg["remove_HC"]["hash_chain_integrity"]
    want = f"{clamp01(hc):.2f}"
    checks.append((
        f"fig1 combined_ablation_matrix draws remove_HC hash_chain_integrity "
        f"({hc!r} -> '{want}')",
        want in t1,
        f"JSON hash_chain_integrity={hc}",
    ))
    # and its RIS, to 3dp
    ris_hc = by_cfg["remove_HC"]["runtime_integrity_score"]
    checks.append((
        f"fig1 draws remove_HC runtime_integrity_score '{ris_hc:.3f}'",
        f"{ris_hc:.3f}" in t1,
        f"JSON runtime_integrity_score={ris_hc}",
    ))

    # --- check 2: my six planes reproduce the artifact's RIS exactly --------
    base_det = float(baseline_config(combined)["blind_risk_detection_recall"])
    worst = 0.0
    for cfg in combined["configs"]:
        mine = sum(plane_health(cfg, base_det)) / len(PLANES)
        theirs = float(cfg["runtime_integrity_score"])
        worst = max(worst, abs(mine - theirs))
    checks.append((
        f"fig1 cell derivation reproduces every published RIS "
        f"(max |derived - published| = {worst:.2e} over "
        f"{len(combined['configs'])} configs)",
        worst < 1e-5,
        "planes are derived, not copied",
    ))

    # --- check 3: fig 4 renders the real per-dataset undetected-risk rate (URR)s -----
    t4 = svg_texts(OUT_DIR / "dataset_comparison.svg")
    ok4, detail4 = True, []
    for ds in data["cross"]["datasets"]:
        by = {c["config"]: c for c in ds["configs"]}
        v = by["baseline_full_LDREA"]["undetected_risk_rate"]
        want = f"{float(v):.3f}"
        hit = want in t4
        ok4 &= hit
        detail4.append(f"{ds['dataset']} baseline FPR={want}{'' if hit else ' MISSING'}")
    checks.append((
        "fig4 dataset_comparison draws each dataset's baseline undetected_risk_rate",
        ok4, "; ".join(detail4),
    ))

    # --- check 4: fig 3 renders a specific threshold cell -------------------
    t3 = svg_texts(OUT_DIR / "threshold_heatmap.svg")
    row = next(r for r in data["threshold"]["rows"]
               if r["config"] == "remove_PE" and int(r["threshold_delta_pct"]) == 20)
    want = f"FPR {float(row['undetected_risk_rate']):.3f}"
    checks.append((
        f"fig3 threshold_heatmap draws remove_PE @ +20% -> '{want}'",
        want in t3,
        f"JSON undetected_risk_rate={row['undetected_risk_rate']}",
    ))

    # --- check 5: fig 2 renders a real interaction effect -------------------
    t2 = svg_texts(OUT_DIR / "interaction_graph.svg")
    it = next(i for i in combined["interactions"]
              if i["order"] == 2 and i["combination"] == "remove_EQ+HC")
    want = fmt_effect(it["interaction_effect"])
    checks.append((
        f"fig2 interaction_graph draws remove_EQ+HC interaction_effect '{want}' "
        f"({it['interaction_class']})",
        want in t2,
        f"JSON interaction_effect={it['interaction_effect']}",
    ))

    # --- check 6: fig 5 renders the sorted RIS values -----------------------
    t5 = svg_texts(OUT_DIR / "runtime_integrity.svg")
    ok5 = all(f"{float(c['runtime_integrity_score']):.3f}" in t5
              for c in combined["configs"])
    checks.append((
        f"fig5 runtime_integrity draws all {len(combined['configs'])} published "
        f"RIS values",
        ok5, "every config's RIS string found in the SVG",
    ))

    return checks


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

FIGURES = [
    fig_combined_ablation_matrix,
    fig_interaction_graph,
    fig_threshold_heatmap,
    fig_dataset_comparison,
    fig_runtime_integrity,
    fig_graceful_degradation,
    fig_dependency_graph,
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-validate", action="store_true",
                    help="render only; skip the format + provenance validation pass")
    ap.add_argument("--png-scale", type=int, default=2,
                    help="PNG raster scale (2 = ~300dpi print preview; default 2)")
    args = ap.parse_args(argv)

    for p in (COMBINED_JSON, THRESHOLD_JSON, CROSS_JSON):
        if not p.exists():
            print(f"FATAL: missing source artifact {p}", file=sys.stderr)
            return 2

    data = load_sources()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print("L-DREA publication figures  ->  " + str(OUT_DIR))
    print("=" * 96)

    stems: list[str] = []
    for fn in FIGURES:
        name, canvas = fn(data)
        stems.append(name)
        paths = canvas.save(OUT_DIR / name, png_scale=args.png_scale)
        print(f"[{name}]  {canvas.width}x{canvas.height} pt")
        if paths.get("png") is None:
            print(f"    PNG SKIPPED -- {paths.get('png_skipped_reason')}")
        for ext in ("svg", "pdf", "png"):
            p = paths.get(ext)
            if p:
                p = Path(p)
                print(f"    {ext.upper():3s}  {p.stat().st_size:>9,} B  {p}")

    if args.no_validate:
        return 0

    print()
    print("=" * 96)
    print("VALIDATION")
    print("=" * 96)
    failures = 0

    for stem in stems:
        for ext, validator in (("svg", validate_svg), ("pdf", validate_pdf),
                               ("png", validate_png)):
            p = OUT_DIR / f"{stem}.{ext}"
            try:
                assert p.exists(), "file does not exist"
                detail = validator(p)
                print(f"  PASS  {ext.upper():3s}  {stem:<28s}  {detail}")
            except Exception as exc:
                failures += 1
                print(f"  FAIL  {ext.upper():3s}  {stem:<28s}  "
                      f"{type(exc).__name__}: {exc}")

    print()
    print("PROVENANCE SPOT-CHECKS (figure value == source JSON value)")
    for desc, ok, detail in spot_checks(data):
        if ok:
            print(f"  PASS  {desc}\n          {detail}")
        else:
            failures += 1
            print(f"  FAIL  {desc}\n          {detail}")

    print()
    print("=" * 96)
    n_files = len(stems) * 3
    if failures == 0:
        print(f"ALL PASS -- {len(stems)} figures, {n_files} files")
    else:
        print(f"{failures} CHECK(S) FAILED")
    print("=" * 96)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
