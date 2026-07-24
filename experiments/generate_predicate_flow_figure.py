#!/usr/bin/env python3
"""Predicate Evaluation Flow figure (SVG + PNG).

Presentation artifact only. It reads no experiment output, computes no metric and writes nothing
outside experiments/figures/. It documents how a predicate result is turned into a correctness
judgement, so that a reader of the paper or the README does not mistake an expected predicate FAIL
for an implementation failure.

    python experiments/generate_predicate_flow_figure.py

Emits:
    experiments/figures/fig_predicate_evaluation_flow.svg   (authoritative, vector)
    experiments/figures/fig_predicate_evaluation_flow.png   (raster, if a converter is available)

PNG conversion is attempted with cairosvg, then rsvg-convert, then inkscape, then macOS qlmanage.
If none is present the SVG is still written and the script exits 0 with a note; a missing raster is
never allowed to fail a build.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "figures"
SVG = OUT / "fig_predicate_evaluation_flow.svg"
PNG = OUT / "fig_predicate_evaluation_flow.png"

W, H = 880, 1000
INK, MUT, LINE = "#1a2333", "#5b6a80", "#98a6bb"
GREEN, BLUE, RED = "#1f7a4d", "#1d4f9c", "#a3202f"


def _box(x, y, w, h, label, sub="", fill="#ffffff", stroke=LINE, bold=True, rx=8):
    mid = x + w / 2
    t = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
         f'stroke="{stroke}" stroke-width="1.5"/>']
    ty = y + (h / 2 + 5) if not sub else y + h / 2 - 3
    t.append(f'<text x="{mid}" y="{ty}" font-size="15" text-anchor="middle" fill="{INK}" '
             f'font-weight="{"bold" if bold else "normal"}">{label}</text>')
    if sub:
        t.append(f'<text x="{mid}" y="{y + h / 2 + 15}" font-size="11.5" text-anchor="middle" '
                 f'fill="{MUT}">{sub}</text>')
    return "".join(t)


def _diamond(cx, cy, w, h, label):
    pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
    return (f'<polygon points="{pts}" fill="#ffffff" stroke="{LINE}" stroke-width="1.5"/>'
            f'<text x="{cx}" y="{cy + 5}" font-size="14" text-anchor="middle" fill="{INK}" '
            f'font-weight="bold">{label}</text>')


def _arrow(x, y1, y2, label=""):
    t = [f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}" stroke="{LINE}" stroke-width="1.5" '
         f'marker-end="url(#a)"/>']
    if label:
        t.append(f'<text x="{x + 8}" y="{(y1 + y2) / 2 + 4}" font-size="11.5" fill="{MUT}">{label}</text>')
    return "".join(t)


def build_svg() -> str:
    cx = W // 2
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="Helvetica,Arial,sans-serif">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto">'
         f'<path d="M0,0 L0,6 L8,3 z" fill="{LINE}"/></marker></defs>',
         f'<text x="{W / 2}" y="30" font-size="17" font-weight="bold" text-anchor="middle" '
         f'fill="{INK}">Predicate Evaluation Flow</text>',
         f'<text x="{W / 2}" y="50" font-size="12" text-anchor="middle" fill="{MUT}">'
         'Correctness is agreement between expected and observed &#8212; not PASS alone</text>']

    s.append(_box(cx - 150, 68, 300, 44, "Scenario"))
    s.append(_arrow(cx, 112, 140))
    s.append(_box(cx - 150, 140, 300, 44, "Predicate evaluation"))
    s.append(_arrow(cx, 184, 212))

    s.append(_box(cx - 300, 212, 280, 52, "Expected predicate outcome",
                  "scenario definition (stress_test.py)"))
    s.append(_box(cx + 20, 212, 280, 52, "Observed predicate outcome",
                  "artifact (stress_test_report.json)"))
    # join the two into the decision diamond
    s.append(f'<line x1="{cx - 160}" y1="264" x2="{cx - 160}" y2="288" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(f'<line x1="{cx + 160}" y1="264" x2="{cx + 160}" y2="288" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(f'<line x1="{cx - 160}" y1="288" x2="{cx + 160}" y2="288" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(_arrow(cx, 288, 312))

    s.append(_diamond(cx, 350, 190, 76, "Match?"))

    # NO branch
    s.append(f'<line x1="{cx + 95}" y1="350" x2="{cx + 190}" y2="350" stroke="{LINE}" '
             f'stroke-width="1.5" marker-end="url(#a)"/>')
    s.append(f'<text x="{cx + 118}" y="342" font-size="11.5" fill="{MUT}">NO</text>')
    s.append(_box(cx + 190, 326, 180, 48, "Implementation error", "the only red state",
                  fill="#fdecee", stroke=RED))

    # YES branch
    s.append(_arrow(cx, 388, 416, "YES"))
    s.append(_box(cx - 150, 416, 300, 44, "Predicate correct", fill="#eaf6ef", stroke=GREEN))
    s.append(_arrow(cx, 460, 488))
    s.append(_box(cx - 150, 488, 300, 52, "Aggregate decision",
                  "&#915; = count of in-scope deficits; non-compensatory"))

    # Fork: one spine down, split sideways, then an arrow into each terminal state.
    s.append(f'<line x1="{cx}" y1="540" x2="{cx}" y2="558" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(f'<line x1="{cx - 165}" y1="558" x2="{cx + 165}" y2="558" stroke="{LINE}" stroke-width="1.5"/>')
    s.append(_arrow(cx - 165, 558, 582))
    s.append(_arrow(cx + 165, 558, 582))
    s.append(_box(cx - 300, 582, 270, 56, "SAFE_STATE", "&#915; &gt; 0 or class veto &#8212; denied",
                  fill="#e8f0fb", stroke=BLUE))
    s.append(_box(cx + 30, 582, 270, 56, "EXECUTE", "&#915; = 0 and no veto &#8212; permitted",
                  fill="#eaf6ef", stroke=GREEN))

    # legend
    ly = 672
    s.append(f'<rect x="40" y="{ly}" width="{W - 80}" height="196" rx="8" fill="#f7f9fc" '
             f'stroke="{LINE}" stroke-width="1"/>')
    s.append(f'<text x="60" y="{ly + 26}" font-size="14" font-weight="bold" fill="{INK}">'
             'How to read a predicate result</text>')
    rows = [
        (GREEN, "PASS, expected PASS", "Condition satisfied. Correct."),
        (BLUE, "FAIL, expected FAIL", "Condition intentionally rejected. Correct — a detection."),
        (RED, "FAIL, expected PASS", "Observed ≠ expected. Implementation error."),
        (RED, "PASS, expected FAIL", "Observed ≠ expected. Implementation error — a false permit."),
    ]
    for i, (colour, head, body) in enumerate(rows):
        y = ly + 54 + i * 30
        s.append(f'<rect x="60" y="{y - 11}" width="14" height="14" rx="3" fill="{colour}"/>')
        s.append(f'<text x="84" y="{y}" font-size="12.5" font-weight="bold" fill="{INK}">{head}</text>')
        s.append(f'<text x="250" y="{y}" font-size="12.5" fill="{MUT}">{body}</text>')
    s.append(f'<text x="60" y="{ly + 180}" font-size="11.5" fill="{MUT}">'
             'A predicate FAIL is not a software failure. In an adversarial scenario it is the '
             'specified behaviour.</text>')

    s.append(f'<text x="{W / 2}" y="{H - 26}" font-size="11" text-anchor="middle" fill="{MUT}">'
             'L-DREA Gamma G-0 &#183; presentation artifact &#183; no experimental result is derived '
             'from this figure</text>')
    s.append('</svg>')
    return "\n".join(s)


def to_png(svg_path: Path, png_path: Path) -> str | None:
    """Rasterise with whatever is on the machine. Returns the converter used, or None."""
    try:
        import cairosvg  # type: ignore
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), scale=2.0)
        return "cairosvg"
    except Exception:
        pass

    for exe, argv in (
        ("rsvg-convert", ["rsvg-convert", "-z", "2", "-o", str(png_path), str(svg_path)]),
        ("inkscape", ["inkscape", str(svg_path), "--export-type=png", "-o", str(png_path), "-d", "192"]),
    ):
        if shutil.which(exe):
            try:
                subprocess.run(argv, check=True, capture_output=True, timeout=120)
                if png_path.exists():
                    return exe
            except Exception:
                continue

    if shutil.which("qlmanage"):  # macOS fallback
        try:
            subprocess.run(["qlmanage", "-t", "-s", str(W * 2), "-o", str(png_path.parent),
                            str(svg_path)], check=True, capture_output=True, timeout=120)
            produced = png_path.parent / (svg_path.name + ".png")
            if produced.exists():
                produced.replace(png_path)
                return "qlmanage"
        except Exception:
            pass
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SVG.write_text(build_svg())
    print(f"[predicate-flow] wrote {SVG.relative_to(ROOT)} ({SVG.stat().st_size:,} bytes)")

    used = to_png(SVG, PNG)
    if used:
        print(f"[predicate-flow] wrote {PNG.relative_to(ROOT)} "
              f"({PNG.stat().st_size:,} bytes, via {used})")
    else:
        print("[predicate-flow] no SVG->PNG converter found (cairosvg / rsvg-convert / inkscape / "
              "qlmanage); SVG written, PNG skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
