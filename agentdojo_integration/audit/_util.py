"""Shared primitives: hashing, JSON IO, and statistics (Wilson / bootstrap / descriptive).

Pure and deterministic where possible. Statistics use numpy only (no scipy). z=1.96 for 95% CIs.
No fabricated values: every function computes on inputs it is given.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

Z95 = 1.959963984540054  # standard normal 0.975 quantile


def sha256_hex(obj: Any) -> str:
    """Deterministic sha256 of a str/bytes or canonical-JSON of any object."""
    if isinstance(obj, bytes):
        data = obj
    elif isinstance(obj, str):
        data = obj.encode("utf-8")
    else:
        data = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: str | Path) -> list[dict]:
    out: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, default=str))


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


# ---------------------------------------------------------------- statistics
def wilson_ci(successes: int, n: int, z: float = Z95) -> dict:
    """Wilson score interval for a binomial proportion. Returns point + [low, high]."""
    if n == 0:
        return {"p": None, "low": None, "high": None, "n": 0, "successes": successes}
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return {"p": p, "low": max(0.0, center - half), "high": min(1.0, center + half),
            "n": n, "successes": successes}


def bootstrap_ci(values: Sequence[float], stat=np.mean, n_boot: int = 2000,
                 seed: int = 12345, alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for an arbitrary statistic. Deterministic via fixed seed."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    if v.size == 0:
        return {"stat": None, "low": None, "high": None, "n": 0, "n_boot": n_boot, "seed": seed}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, v.size, size=(n_boot, v.size))
    boots = np.array([stat(v[i]) for i in idx])
    return {"stat": float(stat(v)),
            "low": float(np.quantile(boots, alpha / 2)),
            "high": float(np.quantile(boots, 1 - alpha / 2)),
            "n": int(v.size), "n_boot": n_boot, "seed": seed}


def describe(values: Sequence[float]) -> dict:
    """min/max/mean/median/std/var/IQR/quartiles. Empty-safe."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    if v.size == 0:
        return {k: None for k in ("count", "min", "max", "mean", "median", "std",
                                  "var", "q1", "q3", "iqr")} | {"count": 0}
    q1, q3 = float(np.quantile(v, 0.25)), float(np.quantile(v, 0.75))
    return {"count": int(v.size), "min": float(v.min()), "max": float(v.max()),
            "mean": float(v.mean()), "median": float(np.median(v)),
            "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "var": float(v.var(ddof=1)) if v.size > 1 else 0.0,
            "q1": q1, "q3": q3, "iqr": q3 - q1}


def shannon_entropy(counts: Iterable[int], base: float = 2.0) -> float:
    """Shannon entropy of a categorical distribution given category counts."""
    c = np.asarray([x for x in counts if x is not None], dtype=float)
    total = c.sum()
    if total <= 0:
        return 0.0
    p = c[c > 0] / total
    return float(-(p * (np.log(p) / np.log(base))).sum())


def histogram(values: Sequence[float], bins: Sequence[float]) -> dict:
    """Fixed-edge histogram -> {edges, counts}. Deterministic."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    counts, edges = np.histogram(v, bins=np.asarray(bins, dtype=float)) if v.size else (
        np.zeros(len(bins) - 1, dtype=int), np.asarray(bins, dtype=float))
    return {"edges": [float(e) for e in edges], "counts": [int(c) for c in counts]}
