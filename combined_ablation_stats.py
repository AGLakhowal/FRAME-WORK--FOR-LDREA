#!/usr/bin/env python3
"""
combined_ablation_stats.py — statistical primitives for the combined ablation (Step 7).
=======================================================================================

Effect sizes and significance tests computed WITHOUT scipy (deterministic, dependency-free):

  * cohen_d            standardized mean difference (pooled SD), + magnitude label
  * cliffs_delta       non-parametric effect size in [-1, 1], rank-based O((n+m) log(n+m))
  * mann_whitney_u     U statistic + normal-approx two-sided p (tie-corrected), + significance
  * two_proportion_z   z-test + p for a difference in two binomial rates (FPR/recall deltas)

Wilson and bootstrap CIs are REUSED from metrics_engine (which reuses the frozen audit `_util`),
so no second, divergent CI implementation is introduced.
"""
from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import metrics_engine as ME  # noqa: E402


def _norm_cdf(x: float) -> float:
    """Standard-normal CDF via erf (stdlib math.erf)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def cohen_d(a, b) -> dict:
    """Standardized mean difference (a − b) / pooled_sd. Positive ⇒ a > b."""
    a = [float(x) for x in a]; b = [float(x) for x in b]
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return {"d": None, "magnitude": "undefined (n<2)", "n_a": na, "n_b": nb}
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)) or 1e-12
    d = (ma - mb) / pooled
    ad = abs(d)
    mag = ("negligible" if ad < 0.2 else "small" if ad < 0.5 else
           "medium" if ad < 0.8 else "large")
    return {"d": round(d, 4), "magnitude": mag, "mean_a": ma, "mean_b": mb, "n_a": na, "n_b": nb}


def _ranks(vals):
    """Average (fractional) ranks, 1-based, with ties averaged. Returns (ranks_in_order, tie_term)."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    tie_term = 0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = r
        t = j - i + 1
        if t > 1:
            tie_term += t ** 3 - t
        i = j + 1
    return ranks, tie_term


def mann_whitney_u(a, b) -> dict:
    """Two-sided Mann–Whitney U with normal approximation (tie-corrected) and Cliff's delta.
    O((n+m) log(n+m)). Returns U, z, p, cliffs_delta, and a significance flag (α=0.05)."""
    a = [float(x) for x in a]; b = [float(x) for x in b]
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return {"U": None, "z": None, "p_value": None, "significant": None,
                "cliffs_delta": None, "cliffs_magnitude": "undefined"}
    combined = a + b
    ranks, tie_term = _ranks(combined)
    R1 = sum(ranks[:n1])
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    mu = n1 * n2 / 2.0
    N = n1 + n2
    var = (n1 * n2 / 12.0) * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 0.0
    sigma = math.sqrt(var) if var > 0 else 0.0
    z = (U - mu) / sigma if sigma > 0 else 0.0
    p = 2.0 * (1.0 - _norm_cdf(abs(z))) if sigma > 0 else 1.0
    # Cliff's delta from U1: delta = 2*U1/(n1*n2) - 1  (a vs b; positive ⇒ a tends larger)
    delta = (2.0 * U1) / (n1 * n2) - 1.0
    ad = abs(delta)
    mag = ("negligible" if ad < 0.147 else "small" if ad < 0.33 else
           "medium" if ad < 0.474 else "large")
    return {"U": U, "z": round(z, 4), "p_value": round(min(1.0, max(0.0, p)), 6),
            "significant": bool(p < 0.05), "cliffs_delta": round(delta, 4),
            "cliffs_magnitude": mag}


def two_proportion_z(x1, n1, x2, n2) -> dict:
    """Two-sided z-test for H0: p1 == p2 (pooled). Returns z, p, significance, and the rate delta."""
    if n1 == 0 or n2 == 0:
        return {"z": None, "p_value": None, "significant": None, "delta": None}
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2)) or 1e-12
    z = (p1 - p2) / se
    pval = 2.0 * (1.0 - _norm_cdf(abs(z)))
    return {"z": round(z, 4), "p_value": round(min(1.0, max(0.0, pval)), 6),
            "significant": bool(pval < 0.05), "delta": round(p1 - p2, 6),
            "p1": round(p1, 6), "p2": round(p2, 6)}


def wilson(x, n):
    return ME.wilson_ci(x, n) if n else None


def bootstrap(values):
    v = [float(x) for x in values if x is not None]
    return ME.compute_bootstrap_ci(v)["bootstrap95"] if len(v) > 1 else None


# --------------------------------------------------------------------------- #
# Descriptive statistics + proportion effect size + generic bootstrap          #
# --------------------------------------------------------------------------- #
def describe(v) -> dict:
    """mean / median / stdev / min / max over a sample."""
    v = [float(x) for x in v if x is not None]
    if not v:
        return {"n": 0, "mean": None, "median": None, "stdev": None, "min": None, "max": None}
    s = sorted(v); n = len(v)
    return {"n": n, "mean": sum(v) / n, "median": statistics.median(s),
            "stdev": statistics.pstdev(v) if n > 1 else 0.0, "min": s[0], "max": s[-1]}


def cohen_h(p1, p2) -> dict:
    """Effect size for a DIFFERENCE OF PROPORTIONS (arcsine transform). Cohen's d is not
    appropriate for Bernoulli rates; h is the standard proportion effect size."""
    if p1 is None or p2 is None:
        return {"h": None, "magnitude": "undefined"}
    phi = lambda p: 2.0 * math.asin(math.sqrt(min(max(float(p), 0.0), 1.0)))
    h = phi(p1) - phi(p2)
    ah = abs(h)
    mag = ("negligible" if ah < 0.2 else "small" if ah < 0.5 else "medium" if ah < 0.8 else "large")
    return {"h": round(h, 4), "magnitude": mag}


def resample_index(n, n_boot=500, seed=12345):
    """Seeded bootstrap resample-index matrix (n_boot x n). numpy-accelerated, deterministic."""
    import numpy as np
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_statistic(values_fn, idx_matrix) -> dict | None:
    """Bootstrap an ARBITRARY statistic. `values_fn(idx_row)` returns the statistic for one
    resample. Returns mean/median/stdev/min/max of the replicate distribution + 95% percentile CI.
    Used for composite metrics (balanced accuracy, predicate coverage, RIS) that are functions of
    the per-decision data rather than a single Bernoulli rate."""
    reps = []
    for row in idx_matrix:
        v = values_fn(row)
        if v is not None:
            reps.append(float(v))
    if not reps:
        return None
    s = sorted(reps)
    d = describe(reps)
    d["ci95_low"] = s[int(0.025 * len(s))]
    d["ci95_high"] = s[min(len(s) - 1, int(0.975 * len(s)))]
    d["n_boot"] = len(reps)
    return d


def bootstrap_difference(fn_a, fn_b, idx_matrix) -> dict:
    """Bootstrap the DIFFERENCE (a − b) of a composite statistic. Significant at α=0.05 when the
    95% percentile CI of the difference excludes 0. Effect size = mean difference / SD of the
    difference distribution (a standardized bootstrap effect size)."""
    diffs = []
    for row in idx_matrix:
        va, vb = fn_a(row), fn_b(row)
        if va is not None and vb is not None:
            diffs.append(float(va) - float(vb))
    if not diffs:
        return {"significant": None, "note": "no bootstrap replicates"}
    s = sorted(diffs)
    lo, hi = s[int(0.025 * len(s))], s[min(len(s) - 1, int(0.975 * len(s)))]
    d = describe(diffs)
    sd = d["stdev"] or 0.0
    eff = (d["mean"] / sd) if sd > 1e-12 else (0.0 if abs(d["mean"]) < 1e-12 else float("inf"))
    ae = abs(eff) if eff != float("inf") else 99.0
    mag = ("negligible" if ae < 0.2 else "small" if ae < 0.5 else "medium" if ae < 0.8 else "large")
    return {"mean_difference": d["mean"], "ci95_low": lo, "ci95_high": hi,
            "significant": bool(lo > 0 or hi < 0), "standardized_effect": round(eff, 4)
            if eff != float("inf") else None, "magnitude": mag, "n_boot": len(diffs)}


def analyze_proportion(vec_a, vec_b, label="") -> dict:
    """FULL statistical treatment of a proportion metric measured as a per-trial Bernoulli vector.
    vec_a = this configuration's 0/1 trials, vec_b = baseline's. Reports descriptives, Wilson CI,
    bootstrap CI, two-proportion z (p-value + significance), Cohen's h (proportion effect size),
    and Cliff's delta / Mann-Whitney U computed on the Bernoulli samples."""
    a = [float(x) for x in vec_a]; b = [float(x) for x in vec_b]
    na, nb = len(a), len(b)
    xa, xb = int(sum(a)), int(sum(b))
    out = {"metric": label, "descriptive": describe(a),
           "wilson95": wilson(xa, na), "bootstrap95": bootstrap(a) if na > 1 else None,
           "successes": xa, "trials": na}
    if na == 0:
        out["undefined_reason"] = "no trials in the population at risk for this metric"
        return out
    if nb == 0:
        out["undefined_reason"] = "baseline has no trials for this metric; no comparison possible"
        return out
    pa, pb = xa / na, xb / nb
    out["two_proportion_z"] = two_proportion_z(xa, na, xb, nb)
    out["cohens_h"] = cohen_h(pa, pb)
    mw = mann_whitney_u(a, b)
    out["mann_whitney_u"] = {k: mw[k] for k in ("U", "z", "p_value", "significant")}
    out["cliffs_delta"] = {"delta": mw["cliffs_delta"], "magnitude": mw["cliffs_magnitude"]}
    out["p_value"] = out["two_proportion_z"]["p_value"]
    out["significant"] = out["two_proportion_z"]["significant"]
    out["effect_size_interpretation"] = (
        f"Cohen's h={out['cohens_h']['h']} ({out['cohens_h']['magnitude']}); "
        f"Cliff's delta={mw['cliffs_delta']} ({mw['cliffs_magnitude']})")
    if abs(pa - pb) < 1e-12:
        out["note"] = "identical to baseline (no variance between configurations)"
    return out


def analyze_distribution(vec_a, vec_b, label="") -> dict:
    """FULL statistical treatment of a continuous metric measured as per-decision samples."""
    a = [float(x) for x in vec_a]; b = [float(x) for x in vec_b]
    out = {"metric": label, "descriptive": describe(a), "bootstrap95": bootstrap(a) if len(a) > 1 else None,
           "wilson95": None, "wilson_not_applicable": "continuous metric, not a binomial proportion"}
    if not a or not b:
        out["undefined_reason"] = "no samples"
        return out
    d = cohen_d(a, b); mw = mann_whitney_u(a, b)
    out["cohens_d"] = d
    out["mann_whitney_u"] = {k: mw[k] for k in ("U", "z", "p_value", "significant")}
    out["cliffs_delta"] = {"delta": mw["cliffs_delta"], "magnitude": mw["cliffs_magnitude"]}
    out["p_value"] = mw["p_value"]
    out["significant"] = mw["significant"]
    out["effect_size_interpretation"] = (
        f"Cohen's d={d['d']} ({d['magnitude']}); Cliff's delta={mw['cliffs_delta']} ({mw['cliffs_magnitude']})")
    return out


def _selfcheck() -> int:
    # cohen_d of identical -> 0; disjoint high vs low -> large positive
    assert cohen_d([1, 1, 1, 1], [1, 1, 1, 1])["d"] == 0.0
    hi = list(range(100, 200)); lo = list(range(0, 100))
    d = cohen_d(hi, lo); assert d["d"] > 0.8 and d["magnitude"] == "large", d
    mw = mann_whitney_u(hi, lo)
    assert mw["cliffs_delta"] == 1.0 and mw["significant"], mw   # fully separated
    mw2 = mann_whitney_u([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert abs(mw2["cliffs_delta"]) < 1e-9 and not mw2["significant"], mw2
    tp = two_proportion_z(0, 100, 100, 100)
    assert tp["significant"] and tp["delta"] == -1.0, tp
    print("combined_ablation_stats self-check: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selfcheck())
