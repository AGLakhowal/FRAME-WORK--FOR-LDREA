#!/usr/bin/env python3
"""
experiments/_report.py — the single reporting toolkit for the L-DREA evaluation suite.
======================================================================================

PRESENTATION ONLY. This module renders values; it never computes, estimates, infers, or
hardcodes a scientific metric. Every number it prints is either

  * read verbatim from an artifact that an experiment executed and wrote, or
  * an explicit arithmetic reduction of such values, tagged ``derived`` and shown with
    its formula, or
  * absent — in which case it renders ``Not computed`` together with the reason.

The last case is the point of this module. A benchmark that silently omits a metric it did
not compute is indistinguishable from one that computed it and got a convenient answer. The
:class:`NotComputed` sentinel makes the distinction unavoidable: a missing value has to carry
a reason before it can be printed at all.

Provenance tags
---------------
``measured``  produced by code executed during this run
``attested``  imported from an external source (e.g. Paper A's TLC log); NOT executed here
``derived``   arithmetic over executed values; the formula is displayed

Public surface used by _dashboard.py:
    colour helpers, rule/banner/section/subsection, kv, metric, table, bullets, note
    Artifacts (cached artifact loader + JSON-pointer resolver)
    NotComputed, resolve_or, fmt_* formatters
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"

# ---------------------------------------------------------------------------- colour / width
_PLAIN = ("--plain" in sys.argv) or bool(os.environ.get("NO_COLOR")) or not sys.stdout.isatty()


def _term_width() -> int:
    try:
        return shutil.get_terminal_size((100, 24)).columns
    except Exception:
        return 100


W = max(78, min(100, _term_width()))

_ANSI = re.compile(r"\033\[[0-9;]*m")


def _c(code: str, s: str) -> str:
    return s if _PLAIN else f"\033[{code}m{s}\033[0m"


def bold(s):   return _c("1", str(s))
def dim(s):    return _c("2", str(s))
def red(s):    return _c("31", str(s))
def green(s):  return _c("32", str(s))
def yellow(s): return _c("33", str(s))
def blue(s):   return _c("34", str(s))
def mag(s):    return _c("35", str(s))
def cyan(s):   return _c("36", str(s))


def vlen(s: str) -> int:
    """Visible length: character count with ANSI escapes removed."""
    return len(_ANSI.sub("", str(s)))


def pad(s, n: int, align: str = "<") -> str:
    """Pad to *n* visible columns (ljust/rjust that is ANSI-aware)."""
    gap = max(0, n - vlen(s))
    if align == ">":
        return " " * gap + str(s)
    if align == "^":
        left = gap // 2
        return " " * left + str(s) + " " * (gap - left)
    return str(s) + " " * gap


# ---------------------------------------------------------------------------- the NotComputed sentinel
class NotComputed:
    """A metric that does not exist in any executed artifact.

    Carrying the *reason* is mandatory. Rendering code prints the reason next to the metric so
    an absent value can never be mistaken for a zero, a pass, or an oversight.
    """

    __slots__ = ("reason",)

    def __init__(self, reason: str):
        if not reason or not str(reason).strip():
            raise ValueError("NotComputed requires a non-empty reason")
        self.reason = str(reason)

    def __bool__(self):
        return False

    def __repr__(self):
        return f"NotComputed({self.reason!r})"


def is_missing(v) -> bool:
    return isinstance(v, NotComputed)


# ---------------------------------------------------------------------------- artifact access
class Artifacts:
    """Cached loader for the JSON artifacts written by the experiments.

    ``get(rel, pointer, reason=...)`` resolves a dotted JSON pointer inside a repo-relative
    artifact and returns either the value or a :class:`NotComputed` explaining precisely why the
    value is unavailable — file absent, pointer absent, or value explicitly null.
    """

    def __init__(self, root: Path = ROOT):
        self.root = root
        self._cache: dict[str, object] = {}

    def load(self, rel: str):
        if rel in self._cache:
            return self._cache[rel]
        p = self.root / rel
        val = None
        if p.exists():
            try:
                val = json.loads(p.read_text())
            except Exception as ex:  # noqa: BLE001
                val = NotComputed(f"{rel} is present but unparseable ({ex})")
        else:
            val = NotComputed(f"{rel} not present (its experiment did not run in this scope)")
        self._cache[rel] = val
        return val

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def text(self, rel: str):
        p = self.root / rel
        if not p.exists():
            return NotComputed(f"{rel} not present")
        try:
            return p.read_text(errors="replace")
        except Exception as ex:  # noqa: BLE001
            return NotComputed(f"{rel} unreadable ({ex})")

    def get(self, rel: str, pointer: str = "", reason: str | None = None):
        doc = self.load(rel)
        if is_missing(doc):
            return doc
        if not pointer:
            return doc
        cur = doc
        walked: list[str] = []
        for part in pointer.split("."):
            walked.append(part)
            if isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                    continue
                except (ValueError, IndexError):
                    return NotComputed(reason or f"{rel} has no index '{'.'.join(walked)}'")
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
                continue
            return NotComputed(reason or f"{rel} has no field '{'.'.join(walked)}'")
        if cur is None:
            return NotComputed(reason or f"{rel}:{pointer} is explicitly null in the artifact")
        return cur


def resolve_or(value, reason: str):
    """Coerce a possibly-``None`` value into a value or a reasoned NotComputed."""
    return value if value is not None else NotComputed(reason)


# ---------------------------------------------------------------------------- formatters
def fmt_int(v, _="") -> str:
    return f"{v:,}" if isinstance(v, (int, float)) else str(v)


def fmt_num(v, nd=4) -> str:
    return f"{v:,.{nd}f}" if isinstance(v, (int, float)) else str(v)


def fmt_pct(v, nd=4) -> str:
    return f"{v * 100:.{nd}f}%" if isinstance(v, (int, float)) else str(v)


def fmt_sci(v, nd=3) -> str:
    return f"{v:.{nd}e}" if isinstance(v, (int, float)) else str(v)


def fmt_ms(v, nd=5) -> str:
    return f"{v:.{nd}f} ms" if isinstance(v, (int, float)) else str(v)


def fmt_bytes(v) -> str:
    if not isinstance(v, (int, float)):
        return str(v)
    for unit, div in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if v >= div:
            return f"{v / div:.1f} {unit}"
    return f"{v} B"


def fmt_ratio(events, n) -> str:
    if is_missing(events) or is_missing(n):
        return "—"
    return f"{events:,} / {n:,}"


PROV_TAG = {
    "measured": lambda: dim("[measured]"),
    "attested": lambda: yellow("[attested — not executed here]"),
    "derived": lambda: cyan("[derived]"),
}


def prov(tag: str | None) -> str:
    return PROV_TAG[tag]() if tag in PROV_TAG else ""


# ---------------------------------------------------------------------------- primitives
def rule(char="─", color=dim):
    print(color(char * W))


def banner(title, subtitle=None, color=cyan):
    print()
    print(color("╔" + "═" * (W - 2) + "╗"))
    line = f" {title}"
    print(color("║") + pad(bold(line), W - 2) + color("║"))
    if subtitle:
        print(color("║") + pad(dim(f" {subtitle}"), W - 2) + color("║"))
    print(color("╚" + "═" * (W - 2) + "╝"))


def section(title, color=blue):
    print()
    print(color("┌─ ") + bold(title) + " " + color("─" * max(0, W - 5 - vlen(title))))


def subsection(title):
    print()
    print("  " + bold(title))


def kv(k, v, pad_to=26, indent=2):
    print(" " * indent + pad(str(k), pad_to) + dim(":") + " " + str(v))


def note(text, prefix="Note", color=yellow, indent=2):
    for i, line in enumerate(wrap(text, W - indent - 8)):
        head = color(f"{prefix}: ") if i == 0 else " " * (len(prefix) + 2)
        print(" " * indent + head + dim(line))


def wrap(text, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def badge(status) -> str:
    s = str(status).upper()
    if s in ("PASS", "OK", "EXECUTED", "TRUE", "IDENTICAL", "COMPLETE", "HOLD", "YES",
             "GENERATED", "SUPPORTED", "RESOLVED", "SOUND", "INTACT", "DETECTED"):
        return green(f"[ {s} ]")
    if s in ("FAIL", "FALSE", "ERROR", "NO", "BROKEN", "VIOLATED", "UNSOUND"):
        return red(f"[ {s} ]")
    if s in ("PARTIAL", "WARNING", "BLOCKED", "SKIPPED", "PENDING", "NOT COMPUTED",
             "NOT RUN", "ATTESTED", "PARTIALLY RESOLVED", "OUT OF SCOPE"):
        return yellow(f"[ {s} ]")
    return dim(f"[ {s} ]")


def _lbl(label, pad_to: int) -> str:
    """Pad a label, but never let an over-long label butt against its value."""
    s = str(label)
    return pad(s, pad_to) if vlen(s) < pad_to else s + "  "


def metric(label, value, extra="", ok=None, pad_to=34, indent=2, provenance=None):
    """Render one metric line.

    ``value`` may be a :class:`NotComputed`, in which case the reason is printed instead of a
    number and no PASS/FAIL mark is emitted — an uncomputed metric is never scored.
    """
    if is_missing(value):
        print(" " * indent + _lbl(label, pad_to) + yellow("Not computed"))
        for ln in wrap(value.reason, W - indent - pad_to - 4):
            print(" " * (indent + pad_to + 2) + dim(ln))
        return
    dot = "" if ok is None else (green(" ✓") if ok else red(" ✗"))
    line = " " * indent + _lbl(label, pad_to) + bold(str(value))
    tail = "  ".join(x for x in (str(extra) if extra else "", prov(provenance)) if x)
    if tail:
        line += "  " + (dim(tail) if not provenance else tail)
    print(line + dot)


def bullets(header, items, mark="•", color=dim, indent=2):
    """Bulleted list. Long items wrap under a hanging indent; an empty header is skipped."""
    if not items:
        return
    if header:
        print(" " * indent + bold(header))
    body = indent + 2
    for it in items:
        lines = wrap(str(it), W - body - 2)
        print(" " * body + color(mark) + " " + lines[0])
        for cont in lines[1:]:
            print(" " * (body + 2) + cont)


def steps(items, indent=4):
    for s in items:
        print(" " * indent + dim("▸ " + str(s)))


def table(headers, rows, aligns=None, indent=4, footnote=None):
    """Fixed-width table. ``rows`` cells may be pre-coloured; widths are ANSI-aware."""
    if not rows:
        return
    ncol = len(headers)
    aligns = aligns or ["<"] * ncol
    widths = [vlen(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r[:ncol]):
            widths[i] = max(widths[i], vlen(cell))
    head = "  ".join(pad(dim(h), widths[i], aligns[i]) for i, h in enumerate(headers))
    print(" " * indent + head)
    print(" " * indent + dim("─" * (sum(widths) + 2 * (ncol - 1))))
    for r in rows:
        print(" " * indent + "  ".join(pad(c, widths[i], aligns[i]) for i, c in enumerate(r[:ncol])))
    if footnote:
        for ln in wrap(footnote, W - indent - 2):
            print(" " * indent + dim(ln))


def files_list(paths, indent=4, root: Path = ROOT):
    """Print generated artifact paths with size, skipping absent ones honestly."""
    if not paths:
        print(" " * indent + dim("(none declared)"))
        return
    for p in paths:
        fp = root / p if not str(p).startswith("/") else Path(p)
        if fp.exists():
            size = fmt_bytes(fp.stat().st_size)
            print(" " * indent + green("✓") + " " + pad(str(p), 58) + dim(size))
        else:
            print(" " * indent + yellow("○") + " " + pad(str(p), 58) + dim("not produced"))


def count_glob(rel_dir: str, pattern: str, root: Path = ROOT) -> int:
    d = root / rel_dir
    return len(list(d.glob(pattern))) if d.exists() else 0
