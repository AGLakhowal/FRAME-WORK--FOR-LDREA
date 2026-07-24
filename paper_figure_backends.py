"""
paper_figure_backends.py
========================

A self-contained, dependency-light multi-backend vector drawing module for
publication-quality figures (IEEE Access style).

Dependencies: numpy + Python standard library (zlib, struct, math, xml, pathlib).
NOTHING else. No matplotlib, no cairo, no PIL, no external SVG rasterisers.

One drawing API -> three real output formats:

  * SVG  -- hand-emitted standalone XML (parses with xml.dom.minidom).
  * PDF  -- a real PDF 1.4 file written from scratch: header, indirect objects,
            a content stream, a correct cross-reference table, trailer, %%EOF.
            Text uses the base-14 Helvetica / Helvetica-Bold Type1 fonts, so
            glyphs are rendered natively by the reader (and the text is
            selectable / searchable).
  * PNG  -- rasterised into a numpy RGB array and encoded by hand with
            zlib + struct (IHDR / IDAT / IEND, filter type 0, correct CRC-32).

Coordinate system (all backends, all user-facing calls)
-------------------------------------------------------
Top-left origin, x to the right, y DOWN -- i.e. the SVG convention.
The PDF backend flips y internally (PDF's origin is bottom-left).
Colours are "#rgb" or "#rrggbb" strings. ``None`` means "no paint".

Text
----
``rotate`` is in degrees, COUNTER-CLOCKWISE as seen on screen, about the
anchor point (x, y). ``anchor`` is one of {"start", "middle", "end"} and
positions the string relative to (x, y) along the (rotated) text baseline.

Backend notes / honest limitations
----------------------------------
* PDF opacity IS supported, via /ExtGState resources carrying /CA and /ca.
  One ExtGState object is emitted per distinct alpha value actually used.
* PDF text anchoring uses the real Helvetica / Helvetica-Bold AFM advance
  widths (embedded below as a compact table), so "middle" / "end" anchoring is
  metrically exact for the base-14 fonts.
* PNG text uses a built-in 5x7 bitmap font (uppercase, lowercase, digits and
  ASCII punctuation) drawn with a MONOSPACE advance of 0.6 * size per
  character. It is therefore *not* metrically identical to Helvetica: a long
  string will be a little wider in the PNG than in the SVG/PDF. Anchoring is
  computed per-backend using that backend's own metric, so "middle"/"end" text
  is still correctly centred / right-aligned in every format; only the exact
  glyph advances differ. The PNG is intended as a raster preview -- the SVG and
  PDF are the publication masters.
* PNG text rotation is ARBITRARY (not restricted to multiples of 90 degrees).
  It is implemented by inverse-mapping every device pixel of the rotated
  bounding box back into text-local space and sampling the glyph grid, so the
  common -60 / -45 / -90 degree tick-label cases all work.
* PNG rendering is done at 2x supersampling and box-downsampled, which gives
  anti-aliased edges and legible small text on a white background.
* PNG glyph coverage is ASCII 0x20..0x7E. A few common non-ASCII characters
  are transliterated (e.g. Greek mu -> 'u', en/em dash and U+2212 -> '-',
  multiplication sign -> 'x', degree sign has its own glyph). Anything else
  falls back to '?'.

Public API
----------
    c = Canvas(width, height, bg="#ffffff")
    c.rect(x, y, w, h, fill=None, stroke=None, stroke_width=1.0, opacity=1.0)
    c.line(x1, y1, x2, y2, stroke="#000000", stroke_width=1.0, opacity=1.0)
    c.circle(cx, cy, r, fill=None, stroke=None, stroke_width=1.0)
    c.polyline(points, stroke="#000000", stroke_width=1.0, fill=None)
    c.text(x, y, s, size=10.0, fill="#000000", anchor="start", bold=False, rotate=0.0)
    paths = c.save("/path/to/stem")   # -> {"svg": ..., "pdf": ..., "png": ...}
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

__all__ = ["Canvas"]


# ---------------------------------------------------------------------------
# colour handling
# ---------------------------------------------------------------------------

def _parse_color(c) -> tuple[float, float, float]:
    """'#rgb' / '#rrggbb' (or an (r,g,b) 0..1 tuple) -> (r, g, b) floats in 0..1."""
    if isinstance(c, (tuple, list)) and len(c) == 3:
        return (float(c[0]), float(c[1]), float(c[2]))
    if not isinstance(c, str):
        raise TypeError(f"colour must be '#rrggbb' string or (r,g,b) tuple, got {c!r}")
    s = c.strip()
    if not s.startswith("#"):
        raise ValueError(f"colour must start with '#': {c!r}")
    s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"colour must be '#rgb' or '#rrggbb': {c!r}")
    return (int(s[0:2], 16) / 255.0, int(s[2:4], 16) / 255.0, int(s[4:6], 16) / 255.0)


def _norm_color(c) -> str | None:
    """Normalise to '#rrggbb' (or None)."""
    if c is None:
        return None
    r, g, b = _parse_color(c)
    return "#%02x%02x%02x" % (
        int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    )


# ---------------------------------------------------------------------------
# Helvetica / Helvetica-Bold AFM advance widths (units per 1000 em), ASCII 32..126
# Used by the SVG (informational) and PDF (anchoring) backends.
# ---------------------------------------------------------------------------

_HELV = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]

_HELV_BOLD = [
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
    975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
    333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
    611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584,
]

assert len(_HELV) == 95 and len(_HELV_BOLD) == 95


def _afm_width(s: str, size: float, bold: bool) -> float:
    """Width of `s` in points at `size` points, in Helvetica / Helvetica-Bold."""
    table = _HELV_BOLD if bold else _HELV
    total = 0
    for ch in s:
        o = ord(ch)
        total += table[o - 32] if 32 <= o <= 126 else 556
    return total * size / 1000.0


def _anchor_frac(anchor: str) -> float:
    """Fraction of the string width to shift LEFT by, for a given anchor."""
    if anchor == "start":
        return 0.0
    if anchor == "middle":
        return 0.5
    if anchor == "end":
        return 1.0
    raise ValueError(f"anchor must be one of start/middle/end, got {anchor!r}")


# ---------------------------------------------------------------------------
# 5x7 bitmap font for the PNG backend
# ---------------------------------------------------------------------------

# The glyph cell is 5 wide x 9 tall. Rows 0..6 are ABOVE the baseline (cap
# height = 7 rows); rows 7..8 are BELOW it (the descender zone), so g/j/p/q/y
# and the comma actually descend instead of floating.
_GLYPH_W, _GLYPH_H = 5, 9
_GLYPH_ASC, _GLYPH_DESC = 7, 2

# Glyphs given as 7 rows are padded with 2 blank descender rows.
_FONT_SRC: dict[str, tuple[str, ...]] = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "%": ("##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    ",": (".....", ".....", ".....", ".....", "..##.", "..#..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "/": ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("....#", "....#", "....#", "....#", "#...#", "#...#", ".###."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "[": (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "\\": ("#....", "#....", ".#...", "..#..", "...#.", "....#", "....#"),
    "]": (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "^": ("..#..", ".#.#.", "#...#", ".....", ".....", ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "`": (".#...", "..#..", ".....", ".....", ".....", ".....", "....."),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"),
    "n": (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    "q": (".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "{": ("..##.", "..#..", "..#..", ".#...", "..#..", "..#..", "..##."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "}": (".##..", "..#..", "..#..", "...#.", "..#..", "..#..", ".##.."),
    "~": (".....", ".....", ".#..#", "#.#.#", "#..#.", ".....", "....."),
    "°": (".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
}

# Full-height (9-row) glyphs: everything that uses the descender zone.
# Rows 7 and 8 hang below the baseline.
_FONT_SRC_9: dict[str, tuple[str, ...]] = {
    "g": (".....", ".....", ".####", "#...#", "#...#", "#...#", ".####",
          "....#", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.",
          "#..#.", ".##.."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "#...#", "####.",
          "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", "#...#", ".####",
          "....#", "....#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####",
          "....#", ".###."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##..",
          "....#", "....."),
    ",": (".....", ".....", ".....", ".....", ".....", ".....", ".##..",
          "..#..", ".#..."),
    ";": (".....", ".....", ".##..", ".##..", ".....", ".....", ".##..",
          "..#..", ".#..."),
    ":": (".....", ".....", ".##..", ".##..", ".....", ".##..", ".##..",
          ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", ".....",
          ".....", "#####"),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", ".#...", "..#..",
          "...#.", "....."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "...#.", "..#..",
          ".#...", "....."),
}

# Transliterations for common non-ASCII characters that show up in figures.
_TRANSLIT = {
    "−": "-", "–": "-", "—": "-", "‐": "-",  # minus / dashes
    "×": "x", "·": ".", "•": ".",                  # times / middots
    "μ": "u", "µ": "u",                                  # mu
    "≤": "<", "≥": ">", "≈": "~",
    "’": "'", "‘": "'", "“": '"', "”": '"',
    " ": " ",
}


def _build_font_array() -> tuple[np.ndarray, dict[str, int]]:
    """Pack the font into a (n_glyphs, 9, 5) bool array + char -> index map."""
    src = dict(_FONT_SRC)
    src.update(_FONT_SRC_9)  # descender glyphs win
    chars = sorted(src)
    arr = np.zeros((len(chars) + 1, _GLYPH_H, _GLYPH_W), dtype=bool)
    index: dict[str, int] = {}
    for i, ch in enumerate(chars):
        rows = src[ch]
        if len(rows) == _GLYPH_ASC:  # 7-row glyph: pad the descender zone
            rows = rows + ("." * _GLYPH_W,) * _GLYPH_DESC
        assert len(rows) == _GLYPH_H, f"glyph {ch!r} has {len(rows)} rows"
        for r, row in enumerate(rows):
            assert len(row) == _GLYPH_W, f"glyph {ch!r} row {r}"
            for c, px in enumerate(row):
                arr[i, r, c] = px == "#"
        index[ch] = i
    # last slot = fallback glyph ('?')
    arr[len(chars)] = arr[index["?"]]
    return arr, index


_FONT_ARR, _FONT_INDEX = _build_font_array()
_FONT_FALLBACK = _FONT_ARR.shape[0] - 1


def _png_glyph_ids(s: str) -> np.ndarray:
    out = np.empty(len(s), dtype=np.int32)
    for i, ch in enumerate(s):
        ch = _TRANSLIT.get(ch, ch)
        out[i] = _FONT_INDEX.get(ch, _FONT_FALLBACK)
    return out


# PNG text metric: cell is 5 wide x 7 tall in "units"; advance is 6 units.
# One unit == _PNG_UNIT * size device px, so cap-to-baseline height == 0.7*size
# and the per-character advance == 0.6*size.
_PNG_UNIT = 0.1
_PNG_ADVANCE = 6.0 * _PNG_UNIT  # * size  -> device px per character


def _png_text_width(s: str, size: float) -> float:
    if not s:
        return 0.0
    return (6.0 * len(s) - 1.0) * _PNG_UNIT * size


# ---------------------------------------------------------------------------
# XML / PDF escaping
# ---------------------------------------------------------------------------

def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))


def _pdf_escape(s: str) -> bytes:
    """Escape a string for a PDF literal string, encoded as WinAnsi/Latin-1."""
    out = bytearray()
    for ch in s:
        try:
            b = ch.encode("latin-1")
        except UnicodeEncodeError:
            b = _TRANSLIT.get(ch, "?").encode("latin-1", "replace")
        for byte in b:
            if byte in (0x28, 0x29, 0x5C):  # ( ) \
                out.append(0x5C)
            out.append(byte)
    return bytes(out)


def _f(v: float) -> str:
    """Format a float compactly for SVG/PDF output."""
    if v == int(v):
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class Canvas:
    """A retained-mode 2-D canvas that can emit SVG, PDF and PNG.

    Primitives are recorded in draw order and replayed by each backend, so all
    three outputs show the same figure.
    """

    def __init__(self, width: int, height: int, bg: str = "#ffffff"):
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")
        self.width = int(width)
        self.height = int(height)
        self.bg = _norm_color(bg) if bg is not None else None
        self._ops: list[tuple] = []

    # -- primitives ---------------------------------------------------------

    def rect(self, x, y, w, h, fill=None, stroke=None, stroke_width=1.0, opacity=1.0):
        self._ops.append((
            "rect", float(x), float(y), float(w), float(h),
            _norm_color(fill), _norm_color(stroke), float(stroke_width),
            float(opacity),
        ))
        return self

    def line(self, x1, y1, x2, y2, stroke="#000000", stroke_width=1.0, opacity=1.0):
        self._ops.append((
            "line", float(x1), float(y1), float(x2), float(y2),
            _norm_color(stroke), float(stroke_width), float(opacity),
        ))
        return self

    def circle(self, cx, cy, r, fill=None, stroke=None, stroke_width=1.0):
        self._ops.append((
            "circle", float(cx), float(cy), float(r),
            _norm_color(fill), _norm_color(stroke), float(stroke_width),
        ))
        return self

    def polyline(self, points: Iterable[Sequence[float]], stroke="#000000",
                 stroke_width=1.0, fill=None):
        pts = [(float(px), float(py)) for px, py in points]
        self._ops.append((
            "polyline", pts, _norm_color(stroke), float(stroke_width),
            _norm_color(fill),
        ))
        return self

    def text(self, x, y, s, size=10.0, fill="#000000", anchor="start",
             bold=False, rotate=0.0):
        _anchor_frac(anchor)  # validate early
        self._ops.append((
            "text", float(x), float(y), str(s), float(size),
            _norm_color(fill) or "#000000", anchor, bool(bold), float(rotate),
        ))
        return self

    # -- output -------------------------------------------------------------

    def save(self, stem, png_scale: int = 1) -> dict:
        """Write <stem>.svg, <stem>.pdf and <stem>.png.

        Returns {"svg": Path, "pdf": Path, "png": Path}. If (and only if) the
        raster backend fails, "png" is None and "png_skipped_reason" explains why.

        `png_scale` is an OPTIONAL extra beyond the required API (default 1 =
        exactly the specified behaviour). Pass 2 or 3 to emit a
        higher-resolution PNG (width*scale x height*scale px) for print; the
        SVG and PDF are vector and unaffected.
        """
        stem = Path(stem)
        if stem.parent != Path(""):
            stem.parent.mkdir(parents=True, exist_ok=True)

        svg_path = stem.with_suffix(".svg")
        pdf_path = stem.with_suffix(".pdf")
        png_path = stem.with_suffix(".png")

        svg_path.write_text(self.to_svg(), encoding="utf-8")
        pdf_path.write_bytes(self.to_pdf())

        out = {"svg": svg_path, "pdf": pdf_path}
        try:
            png_path.write_bytes(self.to_png(scale=png_scale))
            out["png"] = png_path
        except Exception as exc:  # pragma: no cover - defensive
            out["png"] = None
            out["png_skipped_reason"] = f"{type(exc).__name__}: {exc}"
        return out

    # ======================================================================
    # SVG backend
    # ======================================================================

    def to_svg(self) -> str:
        L: list[str] = []
        L.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
        L.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">'
        )
        if self.bg is not None:
            L.append(f'<rect x="0" y="0" width="{self.width}" '
                     f'height="{self.height}" fill="{self.bg}"/>')

        for op in self._ops:
            kind = op[0]

            if kind == "rect":
                _, x, y, w, h, fill, stroke, sw, opacity = op
                a = [f'x="{_f(x)}"', f'y="{_f(y)}"',
                     f'width="{_f(w)}"', f'height="{_f(h)}"']
                a.append(f'fill="{fill}"' if fill else 'fill="none"')
                if stroke:
                    a.append(f'stroke="{stroke}"')
                    a.append(f'stroke-width="{_f(sw)}"')
                if opacity != 1.0:
                    a.append(f'opacity="{_f(opacity)}"')
                L.append("<rect " + " ".join(a) + "/>")

            elif kind == "line":
                _, x1, y1, x2, y2, stroke, sw, opacity = op
                a = [f'x1="{_f(x1)}"', f'y1="{_f(y1)}"',
                     f'x2="{_f(x2)}"', f'y2="{_f(y2)}"',
                     f'stroke="{stroke or "#000000"}"',
                     f'stroke-width="{_f(sw)}"',
                     'stroke-linecap="round"']
                if opacity != 1.0:
                    a.append(f'opacity="{_f(opacity)}"')
                L.append("<line " + " ".join(a) + "/>")

            elif kind == "circle":
                _, cx, cy, r, fill, stroke, sw = op
                a = [f'cx="{_f(cx)}"', f'cy="{_f(cy)}"', f'r="{_f(r)}"']
                a.append(f'fill="{fill}"' if fill else 'fill="none"')
                if stroke:
                    a.append(f'stroke="{stroke}"')
                    a.append(f'stroke-width="{_f(sw)}"')
                L.append("<circle " + " ".join(a) + "/>")

            elif kind == "polyline":
                _, pts, stroke, sw, fill = op
                if not pts:
                    continue
                ptstr = " ".join(f"{_f(px)},{_f(py)}" for px, py in pts)
                a = [f'points="{ptstr}"']
                a.append(f'fill="{fill}"' if fill else 'fill="none"')
                if stroke:
                    a.append(f'stroke="{stroke}"')
                    a.append(f'stroke-width="{_f(sw)}"')
                    a.append('stroke-linejoin="round"')
                    a.append('stroke-linecap="round"')
                L.append("<polyline " + " ".join(a) + "/>")

            elif kind == "text":
                _, x, y, s, size, fill, anchor, bold, rot = op
                a = [f'x="{_f(x)}"', f'y="{_f(y)}"',
                     'font-family="Helvetica, Arial, sans-serif"',
                     f'font-size="{_f(size)}"', f'fill="{fill}"']
                if bold:
                    a.append('font-weight="bold"')
                a.append(f'text-anchor="{anchor}"')
                if rot:
                    # SVG's positive rotate() is clockwise on screen; our API is
                    # counter-clockwise, so negate the angle.
                    a.append(f'transform="rotate({_f(-rot)} {_f(x)} {_f(y)})"')
                L.append("<text " + " ".join(a) + ">" + _xml_escape(s) + "</text>")

        L.append("</svg>")
        return "\n".join(L) + "\n"

    # ======================================================================
    # PDF backend
    # ======================================================================

    @staticmethod
    def _bezier_circle(cx: float, cy: float, r: float) -> list[str]:
        """Approximate a circle with 4 cubic Beziers (PDF coords, y already flipped)."""
        k = 0.5522847498307936 * r
        return [
            f"{_f(cx + r)} {_f(cy)} m",
            f"{_f(cx + r)} {_f(cy + k)} {_f(cx + k)} {_f(cy + r)} {_f(cx)} {_f(cy + r)} c",
            f"{_f(cx - k)} {_f(cy + r)} {_f(cx - r)} {_f(cy + k)} {_f(cx - r)} {_f(cy)} c",
            f"{_f(cx - r)} {_f(cy - k)} {_f(cx - k)} {_f(cy - r)} {_f(cx)} {_f(cy - r)} c",
            f"{_f(cx + k)} {_f(cy - r)} {_f(cx + r)} {_f(cy - k)} {_f(cx + r)} {_f(cy)} c",
            "h",
        ]

    def _pdf_content(self) -> tuple[bytes, dict[float, str]]:
        """Build the page content stream. Returns (stream_bytes, alpha->gs-name)."""
        H = float(self.height)
        c: list[str] = []
        alphas: dict[float, str] = {}

        def gs_for(alpha: float) -> str | None:
            a = round(min(max(alpha, 0.0), 1.0), 4)
            if a >= 1.0:
                return None
            if a not in alphas:
                alphas[a] = f"GS{len(alphas)}"
            return alphas[a]

        def set_alpha(alpha: float) -> bool:
            """Push graphics state + set alpha if needed. True => must emit Q."""
            name = gs_for(alpha)
            if name is None:
                return False
            c.append("q")
            c.append(f"/{name} gs")
            return True

        def rgb(col: str, stroking: bool) -> None:
            r, g, b = _parse_color(col)
            op = "RG" if stroking else "rg"
            c.append(f"{_f(r)} {_f(g)} {_f(b)} {op}")

        # background
        if self.bg is not None:
            rgb(self.bg, False)
            c.append(f"0 0 {_f(self.width)} {_f(H)} re f")

        for op in self._ops:
            kind = op[0]

            if kind == "rect":
                _, x, y, w, h, fill, stroke, sw, opacity = op
                if fill is None and stroke is None:
                    continue
                pushed = set_alpha(opacity)
                if fill:
                    rgb(fill, False)
                if stroke:
                    rgb(stroke, True)
                    c.append(f"{_f(sw)} w")
                c.append(f"{_f(x)} {_f(H - y - h)} {_f(w)} {_f(h)} re")
                if fill and stroke:
                    c.append("B")
                elif fill:
                    c.append("f")
                else:
                    c.append("S")
                if pushed:
                    c.append("Q")

            elif kind == "line":
                _, x1, y1, x2, y2, stroke, sw, opacity = op
                if stroke is None:
                    continue
                pushed = set_alpha(opacity)
                rgb(stroke, True)
                c.append(f"{_f(sw)} w 1 J 1 j")
                c.append(f"{_f(x1)} {_f(H - y1)} m {_f(x2)} {_f(H - y2)} l S")
                if pushed:
                    c.append("Q")

            elif kind == "circle":
                _, cx, cy, r, fill, stroke, sw = op
                if fill is None and stroke is None:
                    continue
                if fill:
                    rgb(fill, False)
                if stroke:
                    rgb(stroke, True)
                    c.append(f"{_f(sw)} w")
                c.extend(self._bezier_circle(cx, H - cy, r))
                if fill and stroke:
                    c.append("B")
                elif fill:
                    c.append("f")
                else:
                    c.append("S")

            elif kind == "polyline":
                _, pts, stroke, sw, fill = op
                if len(pts) < 2 or (stroke is None and fill is None):
                    continue
                if fill:
                    rgb(fill, False)
                if stroke:
                    rgb(stroke, True)
                    c.append(f"{_f(sw)} w 1 J 1 j")
                c.append(f"{_f(pts[0][0])} {_f(H - pts[0][1])} m")
                for px, py in pts[1:]:
                    c.append(f"{_f(px)} {_f(H - py)} l")
                if fill and stroke:
                    c.append("h B")
                elif fill:
                    c.append("h f")
                else:
                    c.append("S")

            elif kind == "text":
                _, x, y, s, size, fill, anchor, bold, rot = op
                if not s:
                    continue
                font = "/F2" if bold else "/F1"
                w = _afm_width(s, size, bold)
                off = -_anchor_frac(anchor) * w
                th = math.radians(rot)
                cc, ss = math.cos(th), math.sin(th)
                # PDF space is y-up, so a positive (screen-CCW) angle is also
                # CCW here -- no negation needed.
                tx = x + off * cc
                ty = (H - y) + off * ss
                rgb(fill, False)
                c.append("BT")
                c.append(f"{font} {_f(size)} Tf")
                c.append(f"{_f(cc)} {_f(ss)} {_f(-ss)} {_f(cc)} {_f(tx)} {_f(ty)} Tm")
                c.append("(" + _pdf_escape(s).decode("latin-1") + ") Tj")
                c.append("ET")

        stream = "\n".join(c).encode("latin-1")
        return stream, alphas

    def to_pdf(self) -> bytes:
        content, alphas = self._pdf_content()
        compressed = zlib.compress(content, 9)

        # object numbering:
        #   1 Catalog, 2 Pages, 3 Page, 4 Contents, 5 F1, 6 F2, 7.. ExtGStates
        gs_first = 7
        gs_names = list(alphas.items())  # [(alpha, name), ...] in creation order
        n_objs = 6 + len(gs_names)

        if gs_names:
            gs_res = " ".join(
                f"/{name} {gs_first + i} 0 R" for i, (_, name) in enumerate(gs_names)
            )
            extg = f"/ExtGState << {gs_res} >> "
        else:
            extg = ""

        resources = (
            "<< /Font << /F1 5 0 R /F2 6 0 R >> " + extg +
            "/ProcSet [/PDF /Text] >>"
        )

        objs: list[bytes] = []
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objs.append(
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {_f(self.width)} {_f(self.height)}] "
            f"/Resources {resources} /Contents 4 0 R >>".encode("latin-1")
        )
        objs.append(
            b"<< /Length " + str(len(compressed)).encode() +
            b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream"
        )
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                    b"/Encoding /WinAnsiEncoding >>")
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                    b"/Encoding /WinAnsiEncoding >>")
        for alpha, _name in gs_names:
            objs.append(
                f"<< /Type /ExtGState /CA {_f(alpha)} /ca {_f(alpha)} >>"
                .encode("latin-1")
            )
        assert len(objs) == n_objs

        buf = bytearray()
        buf += b"%PDF-1.4\n"
        buf += b"%\xe2\xe3\xcf\xd3\n"  # binary marker: mark the file as non-ASCII

        offsets: list[int] = []
        for i, body in enumerate(objs, start=1):
            offsets.append(len(buf))
            buf += f"{i} 0 obj\n".encode()
            buf += body
            buf += b"\nendobj\n"

        xref_off = len(buf)
        buf += f"xref\n0 {n_objs + 1}\n".encode()
        buf += b"0000000000 65535 f \n"
        for off in offsets:
            buf += f"{off:010d} 00000 n \n".encode()
        buf += b"trailer\n"
        buf += f"<< /Size {n_objs + 1} /Root 1 0 R >>\n".encode()
        buf += b"startxref\n"
        buf += f"{xref_off}\n".encode()
        buf += b"%%EOF\n"
        return bytes(buf)

    # ======================================================================
    # PNG backend
    # ======================================================================

    SS = 2  # supersampling factor (box-downsampled away before encoding)

    def _raster(self, ss: int) -> np.ndarray:
        """Rasterise into a float32 (height*ss, width*ss, 3) RGB buffer in 0..1."""
        W, H = self.width * ss, self.height * ss
        bgc = _parse_color(self.bg) if self.bg is not None else (1.0, 1.0, 1.0)
        img = np.empty((H, W, 3), dtype=np.float32)
        img[:] = np.asarray(bgc, dtype=np.float32)

        # cached pixel-centre coordinate grids (in supersampled device px)
        ys = np.arange(H, dtype=np.float32) + 0.5
        xs = np.arange(W, dtype=np.float32) + 0.5

        def blend(mask_box, x0, y0, color, alpha=1.0):
            """Blend `color` into img[y0:y0+h, x0:x0+w] where mask_box is True."""
            if mask_box is None or not mask_box.any():
                return
            h, w = mask_box.shape
            sub = img[y0:y0 + h, x0:x0 + w]
            col = np.asarray(_parse_color(color), dtype=np.float32)
            if alpha >= 1.0:
                sub[mask_box] = col
            else:
                a = np.float32(alpha)
                sub[mask_box] = sub[mask_box] * (1.0 - a) + col * a

        def box(xmin, ymin, xmax, ymax):
            """Clip a device-space bbox to the canvas; return integer bounds or None."""
            x0 = max(0, int(math.floor(xmin)))
            y0 = max(0, int(math.floor(ymin)))
            x1 = min(W, int(math.ceil(xmax)) + 1)
            y1 = min(H, int(math.ceil(ymax)) + 1)
            if x1 <= x0 or y1 <= y0:
                return None
            return x0, y0, x1, y1

        def grid(b):
            x0, y0, x1, y1 = b
            return (xs[x0:x1][None, :], ys[y0:y1][:, None])

        def seg_dist_mask(b, ax, ay, bx, by, halfw):
            """Mask of pixels within `halfw` of segment (ax,ay)-(bx,by)."""
            gx, gy = grid(b)
            vx, vy = bx - ax, by - ay
            L2 = vx * vx + vy * vy
            px, py = gx - ax, gy - ay
            if L2 <= 1e-12:
                d2 = px * px + py * py
            else:
                t = np.clip((px * vx + py * vy) / L2, 0.0, 1.0)
                dx = px - t * vx
                dy = py - t * vy
                d2 = dx * dx + dy * dy
            return d2 <= halfw * halfw

        def stroke_seg(ax, ay, bx, by, color, sw, alpha=1.0):
            hw = max(sw * ss, 1.0) / 2.0
            b = box(min(ax, bx) - hw - 1, min(ay, by) - hw - 1,
                    max(ax, bx) + hw + 1, max(ay, by) + hw + 1)
            if b is None:
                return
            m = seg_dist_mask(b, ax, ay, bx, by, hw)
            blend(m, b[0], b[1], color, alpha)

        def fill_polygon(pts, color, alpha=1.0):
            """Even-odd scanline fill of a closed polygon (device coords)."""
            if len(pts) < 3:
                return
            arr = np.asarray(pts, dtype=np.float64)
            b = box(arr[:, 0].min(), arr[:, 1].min(),
                    arr[:, 0].max(), arr[:, 1].max())
            if b is None:
                return
            gx, gy = grid(b)
            inside = np.zeros((b[3] - b[1], b[2] - b[0]), dtype=bool)
            n = len(arr)
            for i in range(n):
                x1p, y1p = arr[i]
                x2p, y2p = arr[(i + 1) % n]
                if y1p == y2p:
                    continue
                cond = ((y1p > gy) != (y2p > gy))
                with np.errstate(divide="ignore", invalid="ignore"):
                    xint = (x2p - x1p) * (gy - y1p) / (y2p - y1p) + x1p
                inside ^= cond & (gx < xint)
            blend(inside, b[0], b[1], color, alpha)

        def draw_text(x, y, s, size, color, anchor, rot):
            if not s:
                return
            u = _PNG_UNIT * size * ss           # one glyph unit, in device px
            n = len(s)
            Wt = (6.0 * n - 1.0) * u            # text width
            asc = _GLYPH_ASC * u                # above the baseline (cap height)
            desc = _GLYPH_DESC * u              # below the baseline (descenders)
            x0l = -_anchor_frac(anchor) * Wt    # local x of the string's left edge
            # local rect: baseline at local y = 0, glyphs from -asc to +desc
            corners_local = [
                (x0l, -asc), (x0l + Wt, -asc), (x0l + Wt, desc), (x0l, desc),
            ]
            th = math.radians(rot)
            cth, sth = math.cos(th), math.sin(th)
            # local -> device (screen y is down, so CCW-on-screen is [[c,s],[-s,c]])
            dev = [(x + cth * lx + sth * ly, y - sth * lx + cth * ly)
                   for lx, ly in corners_local]
            b = box(min(p[0] for p in dev) - 1, min(p[1] for p in dev) - 1,
                    max(p[0] for p in dev) + 1, max(p[1] for p in dev) + 1)
            if b is None:
                return
            gx, gy = grid(b)
            dx = gx - x
            dy = gy - y
            # inverse rotation (transpose)
            lx = cth * dx - sth * dy
            ly = sth * dx + cth * dy
            inside = (ly >= -asc) & (ly < desc) & (lx >= x0l) & (lx < x0l + Wt)
            if not inside.any():
                return
            t = (lx - x0l) / u                     # 0 .. 6n-1
            ci = np.floor(t / 6.0).astype(np.int32)
            np.clip(ci, 0, n - 1, out=ci)
            within = t - 6.0 * ci
            col = np.floor(within).astype(np.int32)
            row = np.floor(ly / u + _GLYPH_ASC).astype(np.int32)
            ok = inside & (col >= 0) & (col < _GLYPH_W) & (row >= 0) & (row < _GLYPH_H)
            gids = _png_glyph_ids(s)
            g = np.asarray(gids)[np.clip(ci, 0, n - 1)]
            sel = np.zeros(ok.shape, dtype=bool)
            idx = np.nonzero(ok)
            sel[idx] = _FONT_ARR[g[idx], np.clip(row[idx], 0, _GLYPH_H - 1),
                                 np.clip(col[idx], 0, _GLYPH_W - 1)]
            blend(sel, b[0], b[1], color, 1.0)

        # ---- replay the display list --------------------------------------
        for op in self._ops:
            kind = op[0]

            if kind == "rect":
                _, x, y, w, h, fill, stroke, sw, opacity = op
                X, Y, Wd, Hd = x * ss, y * ss, w * ss, h * ss
                if fill:
                    b = box(X, Y, X + Wd, Y + Hd)
                    if b is not None:
                        gx, gy = grid(b)
                        m = (gx >= X) & (gx < X + Wd) & (gy >= Y) & (gy < Y + Hd)
                        blend(m, b[0], b[1], fill, opacity)
                if stroke:
                    pts = [(X, Y), (X + Wd, Y), (X + Wd, Y + Hd), (X, Y + Hd), (X, Y)]
                    for i in range(4):
                        stroke_seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                   stroke, sw, opacity)

            elif kind == "line":
                _, x1, y1, x2, y2, stroke, sw, opacity = op
                if stroke:
                    stroke_seg(x1 * ss, y1 * ss, x2 * ss, y2 * ss, stroke, sw, opacity)

            elif kind == "circle":
                _, cx, cy, r, fill, stroke, sw = op
                CX, CY, R = cx * ss, cy * ss, r * ss
                hw = max(sw * ss, 1.0) / 2.0
                pad = hw + 2
                b = box(CX - R - pad, CY - R - pad, CX + R + pad, CY + R + pad)
                if b is None:
                    continue
                gx, gy = grid(b)
                d = np.sqrt((gx - CX) ** 2 + (gy - CY) ** 2)
                if fill:
                    blend(d <= R, b[0], b[1], fill, 1.0)
                if stroke:
                    blend(np.abs(d - R) <= hw, b[0], b[1], stroke, 1.0)

            elif kind == "polyline":
                _, pts, stroke, sw, fill = op
                if len(pts) < 2:
                    continue
                dev = [(px * ss, py * ss) for px, py in pts]
                if fill:
                    fill_polygon(dev, fill, 1.0)
                if stroke:
                    for i in range(len(dev) - 1):
                        stroke_seg(dev[i][0], dev[i][1], dev[i + 1][0], dev[i + 1][1],
                                   stroke, sw, 1.0)

            elif kind == "text":
                _, x, y, s, size, fill, anchor, bold, rot = op
                draw_text(x * ss, y * ss, s, size, fill, anchor, rot)
                if bold:
                    # fake bold: re-stamp offset by one supersampled pixel
                    draw_text(x * ss + 1, y * ss, s, size, fill, anchor, rot)

        return img

    def to_png(self, scale: int = 1) -> bytes:
        """Encode the canvas as an 8-bit RGB PNG of (width*scale, height*scale) px.

        Internally rasterised at SS x supersampling on top of `scale`, then
        box-downsampled by SS for anti-aliasing.
        """
        scale = int(scale)
        if scale < 1:
            raise ValueError("png_scale must be >= 1")
        ss = self.SS
        img = self._raster(ss * scale)
        # box-downsample the SS supersampling away (keeping `scale`)
        H, W = self.height * scale, self.width * scale
        img = img.reshape(H, ss, W, ss, 3).mean(axis=(1, 3))
        rgb8 = np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8)
        return _encode_png(rgb8)


# ---------------------------------------------------------------------------
# PNG encoder (zlib + struct, filter type 0)
# ---------------------------------------------------------------------------

def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _encode_png(rgb8: np.ndarray) -> bytes:
    """Encode an (H, W, 3) uint8 array as an 8-bit RGB PNG."""
    if rgb8.ndim != 3 or rgb8.shape[2] != 3 or rgb8.dtype != np.uint8:
        raise ValueError("expected an (H, W, 3) uint8 array")
    h, w, _ = rgb8.shape

    # filter type 0 (None) byte in front of every scanline
    raw = np.zeros((h, w * 3 + 1), dtype=np.uint8)
    raw[:, 1:] = rgb8.reshape(h, w * 3)

    out = bytearray(b"\x89PNG\r\n\x1a\n")
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit, colour type 2 (RGB)
    out += _png_chunk(b"IHDR", ihdr)
    out += _png_chunk(b"IDAT", zlib.compress(raw.tobytes(), 9))
    out += _png_chunk(b"IEND", b"")
    return bytes(out)


# ---------------------------------------------------------------------------
# demo + self-validation
# ---------------------------------------------------------------------------

def _demo_canvas() -> Canvas:
    c = Canvas(700, 460, bg="#ffffff")

    # frame + title
    c.rect(0, 0, 700, 460, stroke="#cccccc", stroke_width=1.0)
    c.text(350, 30, "paper_figure_backends - primitive demo",
           size=15, anchor="middle", bold=True, fill="#111111")

    # --- rects (incl. opacity) ---
    c.rect(40, 55, 90, 50, fill="#4c78a8")
    c.rect(140, 55, 90, 50, fill="#f58518", stroke="#000000", stroke_width=1.5)
    c.rect(240, 55, 90, 50, fill="#54a24b", opacity=0.35)
    c.rect(340, 55, 90, 50, stroke="#e45756", stroke_width=2.0)
    c.text(40, 122, "rects: fill / fill+stroke / opacity 0.35 / stroke-only", size=10)

    # --- lines ---
    for i in range(6):
        c.line(40 + i * 30, 145, 40 + i * 30 + 20, 205,
               stroke="#333333", stroke_width=0.5 + i * 0.8)
    c.line(240, 145, 430, 205, stroke="#4c78a8", stroke_width=2.0, opacity=0.5)
    c.text(40, 222, "lines: increasing stroke_width; last one opacity 0.5", size=10)

    # --- circles ---
    c.circle(70, 275, 25, fill="#b279a2")
    c.circle(140, 275, 25, fill="#ffd94a", stroke="#000000", stroke_width=1.5)
    c.circle(210, 275, 25, stroke="#e45756", stroke_width=2.5)
    c.text(40, 320, "circles: fill / fill+stroke / stroke-only", size=10)

    # --- polyline (open) + filled polygon ---
    pts = [(300 + i * 14, 300 - 32 * math.sin(i / 9.0 * math.pi)) for i in range(10)]
    c.polyline(pts, stroke="#4c78a8", stroke_width=2.0)
    c.polyline([(460, 300), (520, 245), (580, 300)], stroke="#54a24b",
               stroke_width=2.0, fill="#cfe8c8")
    c.text(300, 320, "polyline (open) and filled polygon", size=10)

    # --- text: anchors ---
    c.line(350, 355, 350, 400, stroke="#bbbbbb", stroke_width=1.0)
    c.text(350, 370, "anchor=start", size=11, anchor="start", fill="#4c78a8")
    c.text(350, 385, "anchor=middle", size=11, anchor="middle", fill="#e45756")
    c.text(350, 400, "anchor=end", size=11, anchor="end", fill="#54a24b")

    # --- text: rotation ---
    c.text(30, 400, "rot 90 (y-axis label)", size=11, rotate=90, anchor="start")
    c.text(120, 400, "rot -60 tick", size=10, rotate=-60, anchor="end")
    c.text(230, 400, "rot 45 bold", size=11, rotate=45, anchor="start", bold=True)

    # --- a tiny axis-like block, to eyeball legibility ---
    c.line(480, 420, 680, 420, stroke="#000000", stroke_width=1.0)
    for i, lab in enumerate(["0.0", "0.5", "1.0"]):
        x = 480 + i * 100
        c.line(x, 420, x, 425, stroke="#000000", stroke_width=1.0)
        c.text(x, 437, lab, size=9, anchor="middle")
    c.text(580, 405, "AUROC 0.912", size=10, anchor="middle", bold=True)
    return c


def _validate(stem: Path) -> int:
    import xml.dom.minidom

    failures = 0

    # ---- SVG ----
    svg = stem.with_suffix(".svg")
    try:
        doc = xml.dom.minidom.parse(str(svg))
        root = doc.documentElement
        assert root.tagName == "svg", "root element is not <svg>"
        assert root.getAttribute("xmlns") == "http://www.w3.org/2000/svg"
        n = len(doc.getElementsByTagName("*"))
        size = svg.stat().st_size
        print(f"SVG  PASS  parses with xml.dom.minidom, {n} elements, {size} bytes  "
              f"-> {svg}")
    except Exception as exc:
        failures += 1
        print(f"SVG  FAIL  {type(exc).__name__}: {exc}")

    # ---- PDF ----
    pdf = stem.with_suffix(".pdf")
    try:
        data = pdf.read_bytes()
        assert data.startswith(b"%PDF-"), "missing %PDF- header"
        assert data.rstrip().endswith(b"%%EOF"), "missing %%EOF trailer"
        assert len(data) > 500, f"too small ({len(data)} bytes)"

        # verify the startxref offset and every xref entry offset.
        tail = data.rsplit(b"startxref", 1)[1]
        xref_off = int(tail.strip().split()[0])
        assert data[xref_off:xref_off + 4] == b"xref", "startxref does not point at 'xref'"
        lines = data[xref_off:].split(b"\n")
        count = int(lines[1].split()[1])
        for i in range(1, count):  # entry 0 is the free head
            entry = lines[1 + i + 1]
            off = int(entry[:10])
            expect = f"{i} 0 obj".encode()
            assert data[off:off + len(expect)] == expect, \
                f"xref entry {i} offset {off} does not point at '{expect.decode()}'"
        assert b"/BaseFont /Helvetica" in data, "no base-14 Helvetica font resource"
        print(f"PDF  PASS  valid header/trailer, {count - 1} objects, all xref offsets "
              f"correct, {len(data)} bytes  -> {pdf}")
    except Exception as exc:
        failures += 1
        print(f"PDF  FAIL  {type(exc).__name__}: {exc}")

    # ---- PNG ----
    png = stem.with_suffix(".png")
    try:
        data = png.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"

        # walk the chunks, verifying CRCs
        pos, chunks, idat = 8, [], b""
        w = h = None
        while pos < len(data):
            (ln,) = struct.unpack(">I", data[pos:pos + 4])
            tag = data[pos + 4:pos + 8]
            body = data[pos + 8:pos + 8 + ln]
            (crc,) = struct.unpack(">I", data[pos + 8 + ln:pos + 12 + ln])
            assert crc == (zlib.crc32(tag + body) & 0xFFFFFFFF), \
                f"bad CRC on chunk {tag!r}"
            chunks.append(tag)
            if tag == b"IHDR":
                w, h, bit, ctype = struct.unpack(">IIBB", body[:10])
                assert (bit, ctype) == (8, 2), "expected 8-bit truecolour RGB"
            elif tag == b"IDAT":
                idat += body
            pos += 12 + ln
        assert chunks[0] == b"IHDR" and chunks[-1] == b"IEND"
        assert (w, h) == (700, 460), f"IHDR size {w}x{h} != canvas 700x460"

        raw = zlib.decompress(idat)
        stride = w * 3 + 1
        assert len(raw) == stride * h, "decompressed IDAT has the wrong length"
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, stride)
        assert (arr[:, 0] == 0).all(), "expected filter type 0 on every scanline"
        pix = arr[:, 1:].reshape(h, w, 3)
        uniq = len(np.unique(pix.reshape(-1, 3), axis=0))
        assert uniq > 1, "image is blank (only one unique colour)"
        ink = int((pix.reshape(-1, 3).max(axis=1) < 200).sum())
        print(f"PNG  PASS  sig ok, IHDR {w}x{h} matches, CRCs ok, {uniq} unique colours, "
              f"{ink} ink px, {len(data)} bytes  -> {png}")
    except Exception as exc:
        failures += 1
        print(f"PNG  FAIL  {type(exc).__name__}: {exc}")

    return failures


if __name__ == "__main__":
    stem = Path("/tmp/canvas_demo")
    canvas = _demo_canvas()
    paths = canvas.save(stem)
    print("saved:", {k: str(v) for k, v in paths.items()})
    print("-" * 78)
    fails = _validate(stem)
    print("-" * 78)
    print("ALL PASS" if fails == 0 else f"{fails} FORMAT(S) FAILED")
    raise SystemExit(1 if fails else 0)
