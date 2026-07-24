#!/usr/bin/env python3
"""Deterministic bootstrap confidence intervals (Part 3).

Seeded, so the interval is reproducible. No numpy dependency beyond arithmetic. Used to put a CI
on rate metrics (recall, precision, FPR) where the Wilson interval assumes a single binomial and we
want a resampling check that respects the empirical distribution.
"""
from __future__ import annotations

import random
import statistics


def bootstrap_rate_ci(successes_mask, *, resamples=2000, alpha=0.05, seed=1729):
    """successes_mask: list[bool] of per-item successes. Returns percentile bootstrap CI of the rate.

    Deterministic given the seed. Returns None fields when the input is empty.
    """
    n = len(successes_mask)
    if n == 0:
        return {"point": None, "low": None, "high": None, "resamples": resamples, "n": 0}
    rng = random.Random(seed)
    data = [1 if x else 0 for x in successes_mask]
    point = sum(data) / n
    rates = []
    for _ in range(resamples):
        s = 0
        for _ in range(n):
            s += data[rng.randrange(n)]
        rates.append(s / n)
    rates.sort()
    lo = rates[max(0, int((alpha / 2) * resamples) - 1)]
    hi = rates[min(resamples - 1, int((1 - alpha / 2) * resamples) - 1)]
    return {"point": point, "low": lo, "high": hi, "resamples": resamples, "n": n,
            "alpha": alpha, "method": "percentile bootstrap (seeded, deterministic)"}


def bootstrap_metric_ci(values, fn, *, resamples=2000, alpha=0.05, seed=1729):
    """Bootstrap CI for an arbitrary scalar statistic fn(resampled_values)."""
    n = len(values)
    if n == 0:
        return {"point": None, "low": None, "high": None, "n": 0}
    rng = random.Random(seed)
    point = fn(values)
    stats = []
    for _ in range(resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        try:
            stats.append(fn(sample))
        except Exception:
            continue
    if not stats:
        return {"point": point, "low": None, "high": None, "n": n}
    stats.sort()
    lo = stats[max(0, int((alpha / 2) * len(stats)) - 1)]
    hi = stats[min(len(stats) - 1, int((1 - alpha / 2) * len(stats)) - 1)]
    return {"point": point, "low": lo, "high": hi, "n": n,
            "spread": statistics.pstdev(stats) if len(stats) > 1 else 0.0,
            "method": "percentile bootstrap (seeded, deterministic)"}
