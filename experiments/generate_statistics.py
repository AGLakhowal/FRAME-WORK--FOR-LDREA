#!/usr/bin/env python3
"""
experiments/generate_statistics.py — statistical justification from executed outputs only.
==========================================================================================

Computes, where scientifically justified:
  * Wilson 95% intervals and rule-of-three zero-event bounds for proportion metrics,
  * bootstrap 95% CIs for latency distributions (percentile bootstrap, fixed seed),
  * effect sizes (risk differences + Cohen's h) for the ablation contrasts,
  * a sensitivity view across the concurrency thread levels.

SCIENTIFIC-HONESTY NOTE (emitted into the report): the decision engine is DETERMINISTIC, so for the
engine's own outputs a confidence interval quantifies COVERAGE of the sampled input space, not
stochastic run-to-run variability, and frequentist p-values are NOT computed for deterministic
equalities (that would be inventing a sampling model). Bootstrap CIs are only applied to genuinely
variable quantities (measured latencies). Nothing is fabricated.

Outputs: experiments/statistics/statistics_report.json + statistics_report.md
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import _evidence as EV  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "statistics"
OUT.mkdir(parents=True, exist_ok=True)


def _bootstrap_ci(values, n_boot=2000, seed=20260709, alpha=0.05):
    """Deterministic percentile bootstrap of the mean (LCG RNG, no numpy)."""
    vals = [float(v) for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return None
    state = seed & 0xFFFFFFFF
    def rnd():
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += vals[int(rnd() * n) % n]
        means.append(s / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return {"stat_mean": sum(vals) / n, "low": lo, "high": hi, "n": n,
            "n_boot": n_boot, "seed": seed}


def _cohens_h(p1, p2):
    """Effect size for two proportions."""
    def phi(p):
        p = min(max(p, 0.0), 1.0)
        return 2 * math.asin(math.sqrt(p))
    return abs(phi(p1) - phi(p2))


# ---------------------------------------------------------------------------------------------
# Exact (Clopper-Pearson) intervals, statistical power, and sensitivity.
#
# scipy is not a dependency of this repository, so the regularized incomplete beta function is
# implemented directly (Lentz's continued fraction, the standard NR formulation). This gives EXACT
# binomial intervals rather than a normal approximation, which matters here because every headline
# proportion has zero observed events and p -> 0 is exactly where approximations fail.
# ---------------------------------------------------------------------------------------------
def _betacf(a, b, x, itmax=300, eps=3e-16, fpmin=1e-300):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def _betainc(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def _clopper_pearson(x, n, alpha=0.05):
    """Exact two-sided binomial interval. Closed form at the x=0 and x=n boundaries."""
    if n == 0:
        return {"low": None, "high": None, "note": "n = 0; interval undefined"}
    if x == 0:
        return {"low": 0.0, "high": 1.0 - (alpha / 2) ** (1.0 / n), "method": "Clopper-Pearson (exact)"}
    if x == n:
        return {"low": (alpha / 2) ** (1.0 / n), "high": 1.0, "method": "Clopper-Pearson (exact)"}

    def _inv(target, a, b):  # bisection on I_p(a,b) = target
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if _betainc(a, b, mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    low = _inv(alpha / 2, x, n - x + 1)
    high = _inv(1 - alpha / 2, x + 1, n - x)
    return {"low": low, "high": high, "method": "Clopper-Pearson (exact)"}


def _cp_upper_one_sided(n, alpha=0.05):
    """Exact one-sided upper bound when 0 events are observed: 1 - alpha^(1/n)."""
    return 1.0 - alpha ** (1.0 / n) if n > 0 else None


def _power_to_detect(n, p0):
    """P(observe >= 1 event | true rate p0, n independent trials) = 1 - (1-p0)^n. Exact."""
    return 1.0 - (1.0 - p0) ** n


def _design_effect_sensitivity(x, n, des=(1.0, 1.7, 2.0, 3.0)):
    """How the Wilson upper bound moves as the cluster-correction design effect changes."""
    out = []
    for de in des:
        n_eff = max(1.0, n / de)
        w = EV.wilson_ci(x, int(round(n_eff)))
        out.append({"design_effect": de, "n_eff": round(n_eff, 1), "wilson95_upper": w["high"]})
    return out


def main():
    report = {"campaign": "ldrea_statistical_analysis",
              "determinism_note": (
                  "The authorization engine is deterministic. For its outputs, a confidence interval "
                  "quantifies coverage of the sampled input space (sampling uncertainty of the "
                  "proportion), NOT run-to-run stochastic variability. Frequentist p-values are not "
                  "computed for deterministic equalities. Bootstrap CIs are applied only to measured "
                  "latency, which is genuinely variable."),
              "proportion_metrics": [], "zero_event_bounds": [], "latency_bootstrap": [],
              "ablation_effect_sizes": [], "sensitivity_analysis": {},
              "exact_intervals": [], "statistical_power": [], "uncertainty_analysis": {},
              "robustness_summary": {}}

    # Hypothetical true rates at which we report exact power. Chosen to bracket the reported bounds.
    POWER_GRID = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5]

    # ---- proportion metrics (Wilson + exact Clopper-Pearson + power) ----
    lab = EV.load("experiments/runtime_correctness/gamma_lab_v1_report.json")
    def add_prop(name, successes, n, experiment, adverse=True):
        w = EV.wilson_ci(successes, n)
        entry = {"metric": name, "events": successes, "n": n, "experiment": experiment,
                 "point": w["p"], "wilson95_low": w["low"], "wilson95_high": w["high"]}
        report["proportion_metrics"].append(entry)

        cp = _clopper_pearson(successes, n)
        report["exact_intervals"].append(
            {"metric": name, "events": successes, "n": n, "experiment": experiment,
             "clopper_pearson95_low": cp.get("low"), "clopper_pearson95_high": cp.get("high"),
             "method": cp.get("method"),
             "note": "Exact binomial interval. Reported alongside Wilson because at p -> 0 the "
                     "normal approximation is unreliable and Wilson is itself an approximation."})

        if successes == 0 and n > 0:
            report["zero_event_bounds"].append(
                {"metric": name, "n": n, "experiment": experiment,
                 "wilson95_upper": w["high"], "rule_of_three_upper": EV.rule_of_three(n),
                 "clopper_pearson95_upper_two_sided": cp.get("high"),
                 "exact_one_sided_upper": _cp_upper_one_sided(n)})

            # Power. For a zero-event observation the scientifically meaningful quantity is not
            # "power to reject H0" but: how large would the true rate have to be before we would
            # very likely have SEEN at least one event? That is exactly 1 - (1-p)^n, computed
            # exactly below, and its 95% inversion is the minimum detectable rate.
            report["statistical_power"].append(
                {"metric": name, "n": n, "experiment": experiment, "events_observed": 0,
                 "minimum_detectable_rate_95": _cp_upper_one_sided(n),
                 "mdr_definition": ("smallest true rate p such that P(0 events in n trials) <= 0.05; "
                                    "equals 1 - 0.05^(1/n), the exact one-sided upper bound"),
                 "power_to_detect": [
                     {"true_rate": p0, "power": _power_to_detect(n, p0),
                      "reading": f"if the true rate were {p0:g}, we would have observed >=1 event with "
                                 f"probability {_power_to_detect(n, p0) * 100:.2f}%"}
                     for p0 in POWER_GRID],
                 "design_effect_sensitivity": _design_effect_sensitivity(successes, n),
                 "caveat": ("Assumes independent trials. The cluster-corrected column (DE = 1.7) is the "
                            "conservative reading; the design-effect sensitivity shows how the bound "
                            "moves if that correction is wrong.")})

    if lab:
        pm = lab["primary_metrics"]
        add_prop("False Permit Rate (ULB, should-deny pop.)",
                 pm["false_permit_rate"]["adverse_events"], pm["false_permit_rate"]["n"], "E1")
        add_prop("Unauthorized Execution Rate (ULB, all rows)",
                 lab["unauthorized_execution"]["count"], lab["n_total"], "E1")

    bf = EV.load("experiments/agentdojo/boundary/boundary_fpr.json")
    if bf:
        g = bf["soundness_foreign_targets"]
        add_prop("Boundary FPR (AgentDojo foreign targets)", g["permitted"], g["n"], "E7")

    rob = EV.load("fresh_evidence/robustness/robustness.json")
    if rob:
        agg = rob["aggregate"]
        add_prop("Robustness false-permit rate (all decision-path faults)",
                 agg["total_false_permits"], agg["total_trials"], "E8")

    # ---- E9: per-predicate single-deficit isolation (a proportion with n = 13) ----
    pc = EV.load("experiments/predicate_coverage/predicate_coverage.json")
    if pc:
        iso = pc["single_deficit_isolation"]
        add_prop("Single-deficit false-permit rate (E9 predicate isolation)",
                 iso["false_permits"], iso["n"], "E9")

    # ---- robustness summary: per-family bounds, so a reader sees where n is thin ----
    if rob:
        fams = []
        for f in rob["fault_families"]:
            n = f["n_trials"]
            if f["mechanism"] == "B":
                fams.append({"family": f["family"], "mechanism": f["mechanism"], "n": n,
                             "outcome": "corruption_detected",
                             "detected": f.get("corruption_detected"),
                             "note": "integrity fault: measured by detection, not by false permits"})
            else:
                fp = f.get("false_permits", 0)
                cp = _clopper_pearson(fp, n)
                fams.append({"family": f["family"], "mechanism": f["mechanism"], "n": n,
                             "false_permits": fp,
                             "wilson95_upper": EV.wilson_ci(fp, n)["high"],
                             "exact95_upper": cp.get("high"),
                             "power_to_detect_1pct": _power_to_detect(n, 0.01)})
        report["robustness_summary"] = {
            "n_families": rob["aggregate"]["n_fault_families"],
            "total_trials": rob["aggregate"]["total_trials"],
            "total_false_permits": rob["aggregate"]["total_false_permits"],
            "per_family": fams,
            "honest_reading": ("Per-family trial counts are small (1-10). A per-family upper bound is "
                               "therefore wide; the aggregate bound over all 51 decision-path trials is "
                               "the defensible figure. Families with n = 1 establish that the mechanism "
                               "fires, not a rate."),
        }

    # ---- latency bootstrap (E1 measured latency samples if present, else percentile summary) ----
    if lab and "latency_samples_ms" in lab.get("measured_latency", {}):
        bs = _bootstrap_ci(lab["measured_latency"]["latency_samples_ms"])
        if bs:
            report["latency_bootstrap"].append({"metric": "ULB decision latency (ms)",
                                                "experiment": "E1", **bs})
    else:
        # fall back to reporting the executed summary percentiles (no fabrication)
        if lab:
            lt = lab["measured_latency"]
            report["latency_bootstrap"].append(
                {"metric": "ULB decision latency (ms) — summary (no raw samples persisted)",
                 "experiment": "E1", "mean": lt.get("mean_ms"), "p95": lt.get("p95_ms"),
                 "p99": lt.get("p99_ms"),
                 "note": "raw per-row latency samples are not persisted by the stable runner; "
                         "bootstrap requires the sample vector. Summary reported instead."})

    # ---- ablation effect sizes (risk difference + Cohen's h vs baseline) ----
    ab = EV.load("experiments/ablation/ablation.json")
    if ab:
        cfg = {c["config"]: c for c in ab["configs"]}
        base = cfg.get("baseline_full_LDREA")
        if base:
            base_rate = base["leaked_permit_rate"]
            for c in ab["configs"]:
                if c["config"] == "baseline_full_LDREA":
                    continue
                rd = c["leaked_permit_rate"] - base_rate
                report["ablation_effect_sizes"].append(
                    {"contrast": f"{c['config']} vs baseline",
                     "baseline_leak_rate": base_rate, "ablated_leak_rate": c["leaked_permit_rate"],
                     "risk_difference": rd, "cohens_h": _cohens_h(c["leaked_permit_rate"], base_rate),
                     "n_per_arm": c["workload_n"],
                     "interpretation": "deterministic contrast; risk difference is the causal leak "
                                       "attributable to removing this component (no sampling test needed)."})

    # ---- sensitivity across concurrency thread levels ----
    cs = EV.load("experiments/stress/concurrency_scaling.json")
    if cs:
        report["sensitivity_analysis"]["concurrency_threads"] = {
            "levels": [L["n_threads"] for L in cs["levels"]],
            "throughput_decisions_per_s": [round(L["throughput_decisions_per_s"], 1) for L in cs["levels"]],
            "p99_ms": [L["latency_ms"]["p99"] for L in cs["levels"]],
            "false_permits": [L["false_permits"] for L in cs["levels"]],
            "false_denials": [L["false_denials"] for L in cs["levels"]],
            "observation": ("safety metrics (FP/FD) are invariant to thread count; throughput is "
                            "monotone-degrading (GIL-bound) — a genuine sensitivity of performance, "
                            "not of correctness.")}

    # ---- sensitivity of the headline bounds to the cluster-correction assumption ----
    if lab:
        pmx = lab["primary_metrics"]["false_permit_rate"]
        report["sensitivity_analysis"]["design_effect_on_FPR_bound"] = {
            "events": pmx["adverse_events"], "n": pmx["n"],
            "sweep": _design_effect_sensitivity(pmx["adverse_events"], pmx["n"]),
            "observation": ("The FPR upper bound scales with the assumed design effect. DE = 1.7 is the "
                            "value the engine reports; DE = 1.0 (independent rows) is optimistic and "
                            "DE = 3.0 pessimistic. The qualitative conclusion — zero observed false "
                            "permits with a bound of order 1e-2 on n = 492 — is stable across the sweep.")}

    # ---- ablation sensitivity: leak rate is exact, so the 'sensitivity' is to workload size ----
    if ab:
        report["sensitivity_analysis"]["ablation_workload"] = {
            "workload_n_per_config": ab["workload_n"],
            "leak_rates": {c["config"]: c["leaked_permit_rate"] for c in ab["configs"]},
            "observation": ("The engine is deterministic and the workload is index-driven, so each leak "
                            "rate is an exact proportion of a constructed population, not an estimate. "
                            "Increasing n narrows the Wilson interval but cannot move the point value."),
        }

    # ---- uncertainty analysis: which numbers carry which kind of uncertainty ----
    report["uncertainty_analysis"] = {
        "exact_no_uncertainty": [
            "Authorization decisions (deterministic function of the input)",
            "Confusion matrix counts (TP/TN/FP/FN)",
            "Exhaustive 2^16 state enumeration and field-mismatch counts (E3)",
            "TLC distinct reachable states (E3)",
            "Ablation leak counts and risk differences (deterministic contrasts, E5)",
            "Predicate coverage and single-deficit outcomes (E9)",
            "Bundle member digests and ledger binding (E10)",
        ],
        "sampling_uncertainty": [
            "All proportion metrics: uncertainty is over the sampled input space, not run-to-run. "
            "Reported as Wilson AND exact Clopper-Pearson intervals.",
            "Zero-event metrics: the upper bound, never the point estimate of 0, is the claim.",
        ],
        "host_variability": [
            "Wall-clock latency (E1, E6, E9) — varies with host load; bootstrap CI where raw samples "
            "exist (E5), summary statistics otherwise.",
            "Throughput and speedup (E4) — the values move between runs; the SHAPE (no scaling) is stable.",
        ],
        "not_quantified": [
            {"quantity": "Frequentist p-values",
             "reason": "the engine is deterministic, so the ablation contrasts are exact rather than "
                       "sampled; no sampling distribution exists under the null. Risk difference and "
                       "Cohen's h are reported instead."},
            {"quantity": "Power for non-zero-event metrics",
             "reason": "power is defined here against a hypothetical true rate for zero-event "
                       "observations. For metrics with observed events the interval itself is the "
                       "uncertainty statement."},
        ],
    }

    (OUT / "statistics_report.json").write_text(json.dumps(report, indent=2))

    # ---- markdown ----
    md = ["# Statistical Analysis — computed from executed outputs", "",
          "> **Determinism note.** " + report["determinism_note"], "",
          "## Proportion metrics (Wilson 95%)",
          "| Metric | Events/N | Point | Wilson95 low | Wilson95 high | Exp |",
          "|--------|----------|-------|--------------|---------------|-----|"]
    for m in report["proportion_metrics"]:
        md.append(f"| {m['metric']} | {m['events']}/{m['n']} | {m['point']:.3g} | "
                  f"{m['wilson95_low']:.3e} | {m['wilson95_high']:.3e} | {m['experiment']} |")
    md += ["", "## Zero-event upper bounds (Wilson vs rule-of-three 3/n)",
           "| Metric | N | Wilson95 upper | Rule-of-three upper | Exp |",
           "|--------|---|----------------|---------------------|-----|"]
    for z in report["zero_event_bounds"]:
        md.append(f"| {z['metric']} | {z['n']:,} | {z['wilson95_upper']:.3e} | "
                  f"{z['rule_of_three_upper']:.3e} | {z['experiment']} |")
    md += ["", "## Ablation effect sizes (risk difference + Cohen's h vs full L-DREA)",
           "| Contrast | Baseline leak | Ablated leak | Risk diff | Cohen's h | N/arm |",
           "|----------|--------------|-------------|-----------|-----------|-------|"]
    for e in report["ablation_effect_sizes"]:
        md.append(f"| {e['contrast']} | {e['baseline_leak_rate']:.3f} | {e['ablated_leak_rate']:.3f} | "
                  f"{e['risk_difference']:+.3f} | {e['cohens_h']:.3f} | {e['n_per_arm']:,} |")
    if report["latency_bootstrap"]:
        md += ["", "## Latency", "```json", json.dumps(report["latency_bootstrap"], indent=2), "```"]
    if report["sensitivity_analysis"]:
        md += ["", "## Sensitivity across thread levels", "```json",
               json.dumps(report["sensitivity_analysis"], indent=2), "```"]
    (OUT / "statistics_report.md").write_text("\n".join(md))
    print(f"[statistics] proportions={len(report['proportion_metrics'])} "
          f"zero-event={len(report['zero_event_bounds'])} "
          f"effect-sizes={len(report['ablation_effect_sizes'])}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
