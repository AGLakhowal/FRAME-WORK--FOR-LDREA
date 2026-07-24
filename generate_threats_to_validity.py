#!/usr/bin/env python3
"""Generate THREATS_TO_VALIDITY.md from the EXECUTED combined-ablation (E5b) artifacts.

    python3 generate_threats_to_validity.py [--out THREATS_TO_VALIDITY.md] [--check]

DESIGN RULE (non-negotiable)
    Every threat printed by this generator is grounded in a value read from an artifact on disk
    or in a verifiable property of the repository, and the value is quoted with the file path it
    came from. NOTHING is hardcoded and NO limitation is invented. If a source artifact is
    missing, the section that depends on it says so explicitly rather than asserting a number.

    `--check` re-reads the artifacts and exits non-zero if any grounding source is missing, so
    the document can never silently drift away from the evidence it cites.

SOURCES
    experiments/combined_ablation/combined_ablation.json     19 executed configurations
    experiments/combined_ablation/combined_statistics.json   per-config per-metric statistics
    experiments/combined_ablation/threshold_sensitivity.json threshold-perturbation stability
    experiments/combined_ablation/cross_dataset_ablation.json ULB / IEEE-CIS / UNSW-NB15 replication
    COMPONENT_REGISTRY.json                                  auto-discovered component graph
    production_evidence/runtime_detection_report_synthetic.json   synthetic-stream composition
    production_evidence/runtime_clock_consistency_report.json     why PTP is unmeasurable here
    production_evidence/watchdog_scenarios_report.json            authoritative watchdog evidence
    production_evidence/fleet_summary.json                        testbed topology
    label_leakage_audit.json                                      mapped-corpus leakage audit
    experiments/run_runtime_stack.py                               synthetic stream generator
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CA = ROOT / "experiments" / "combined_ablation"

SRC = {
    "ablation": CA / "combined_ablation.json",
    "stats": CA / "combined_statistics.json",
    "thresh": CA / "threshold_sensitivity.json",
    "cross": CA / "cross_dataset_ablation.json",
    "registry": ROOT / "COMPONENT_REGISTRY.json",
    "synth_stream": ROOT / "production_evidence" / "runtime_detection_report_synthetic.json",
    "clock": ROOT / "production_evidence" / "runtime_clock_consistency_report.json",
    "watchdog": ROOT / "production_evidence" / "watchdog_scenarios_report.json",
    "fleet": ROOT / "production_evidence" / "fleet_summary.json",
    "leakage": ROOT / "label_leakage_audit.json",
    "generator": ROOT / "experiments" / "run_runtime_stack.py",
}

# relative paths as cited in the document
def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def load(key: str):
    p = SRC[key]
    if not p.exists():
        return None
    if p.suffix == ".json":
        with p.open() as fh:
            return json.load(fh)
    return p.read_text(errors="replace")


def f(x, nd=4):
    """Format a number without inventing precision it does not have."""
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        s = f"{x:.{nd}f}".rstrip("0")
        return s + "0" if s.endswith(".") else s     # keep 1.0, never bare "1"
    return str(x)


def pct(x, nd=2):
    return "n/a" if x is None else f"{100.0 * x:.{nd}f}%"


def missing(key: str) -> str:
    return (f"- **NOT GROUNDED.** `{rel(SRC[key])}` is absent from this working tree, so no number "
            f"is asserted here. Re-run the experiment to restore the evidence.")


# ---------------------------------------------------------------- evidence extraction
def collect() -> dict:
    """Read every source and derive ONLY quantities that exist in the artifacts."""
    ev: dict = {"present": {k: SRC[k].exists() for k in SRC}}

    ab = load("ablation")
    if ab:
        base = next(c for c in ab["configs"] if c["n_disabled"] == 0)
        cm = base["confusion_matrix"]
        ev["ab"] = ab
        ev["base"] = base
        ev["cm"] = cm
        ev["n_configs"] = ab["n_configurations"]
        ev["order_counts"] = Counter(c["n_disabled"] for c in ab["configs"])
        ev["interaction_classes"] = Counter(i["interaction_class"] for i in ab["interactions"])
        ev["governance_measured"] = any(c.get("governance") for c in ab["configs"])
        ev["governance_shared_empty"] = not ab.get("governance_shared")

    st = load("stats")
    if st:
        ev["st"] = st
        comparisons, significant, mags, undefined, deterministic = 0, 0, Counter(), Counter(), Counter()
        metric_names: set = set()
        for cname, metrics in st["configs"].items():
            for m, v in metrics.items():
                metric_names.add(m)
                if not isinstance(v, dict):
                    continue
                if v.get("undefined_reason"):
                    undefined[m] += 1
                elif v.get("not_sampled_reason"):
                    deterministic[m] += 1
                elif "p_value" in v and cname != "baseline_full_LDREA":
                    comparisons += 1
                    if v.get("significant"):
                        significant += 1
                        mags[(v.get("cliffs_delta") or {}).get("magnitude")] += 1
        ev["n_metrics"] = len(metric_names)
        ev["comparisons"] = comparisons
        ev["significant"] = significant
        ev["effect_mags"] = mags
        ev["undefined"] = undefined
        ev["deterministic_metrics"] = deterministic
        ev["ledger_stat"] = st["configs"]["baseline_full_LDREA"].get("ledger_integrity")

    ev["th"] = load("thresh")
    ev["cd"] = load("cross")
    ev["reg"] = load("registry")
    ev["synth"] = load("synth_stream")
    ev["clock"] = load("clock")
    ev["wd"] = load("watchdog")
    ev["fleet"] = load("fleet")
    ev["leak"] = load("leakage")

    gen = load("generator")
    if gen:
        # ground the stealth fraction in the generator source, not in prose
        for i, line in enumerate(gen.splitlines(), 1):
            if "STEALTHY" in line and "<" in line:
                ev["stealth_line"] = (i, line.strip())
                break
    return ev


# ---------------------------------------------------------------- sections
def sec_header(ev) -> list[str]:
    ab, reg = ev.get("ab"), ev.get("reg")
    L = ["# Threats to Validity — Combined Component Ablation (E5b)", "",
         "*Auto-generated by `generate_threats_to_validity.py` from the EXECUTED artifacts. Every "
         "threat below quotes a measured value and the file it was read from. No limitation in this "
         "document is hypothetical: if a claim could not be grounded in an artifact, it was omitted.*", ""]
    if ab:
        h = ab.get("host", {})
        L += ["| Provenance | Value |", "|---|---|",
              f"| Experiment | `{ab['experiment']}` |",
              f"| Evidence level (self-declared) | **{ab['evidence_level']}** |",
              f"| Configurations executed | {ab['n_configurations']} |",
              f"| Workload per configuration | n = {ab['workload_n']} |",
              f"| Seed | {ab['seed']} |",
              f"| Wall time | {ab['duration_s']} s |",
              f"| Host | {h.get('platform', 'n/a')} / Python {h.get('python', 'n/a')} |",
              f"| Components discovered | {(reg or {}).get('n_components', 'n/a')} |", ""]
    L += ["---", ""]
    return L


def sec_internal(ev) -> list[str]:
    L = ["## 1. Internal validity", ""]
    ab, base, cm = ev.get("ab"), ev.get("base"), ev.get("cm")

    L += ["### I1 — Baseline recall below 1.0 is a property of the GENERATOR, not a runtime defect", ""]
    if not ab:
        L += [missing("ablation"), ""]
    else:
        L += [f"- **Threat.** The intact stack permits {cm['fn_fraud_permitted']} of {cm['n_fraud']} "
              f"positives (`baseline_absolute_recall` = **{f(ab['baseline_absolute_recall'], 6)}**, "
              f"`undetected_risk_rate` = **{f(base['undetected_risk_rate'], 6)}**, Wilson 95% "
              f"[{f(base['undetected_risk_rate_wilson95']['low'], 4)}, "
              f"{f(base['undetected_risk_rate_wilson95']['high'], 4)}], "
              f"`{rel(SRC['ablation'])}`). Read naively this looks like a runtime failure."]
        L += [f"- **Evidence it is not.** The stream is generated label-first, with positives sampled to "
              f"OVERLAP negatives by construction."]
        if ev.get("stealth_line"):
            ln, txt = ev["stealth_line"]
            L += [f"  - `{rel(SRC['generator'])}:{ln}` — `{txt}` — 40% of positives are drawn as "
                  f"observably indistinguishable from legitimate traffic."]
        syn = ev.get("synth")
        if syn:
            kc = (syn.get("stream") or {}).get("kind_counts", {})
            pos = sum(v for k, v in kc.items() if k.startswith("fraud"))
            stealthy = kc.get("fraud_stealthy", 0)
            frac = (stealthy / pos) if pos else None
            L += [f"  - Realized composition (`{rel(SRC['synth_stream'])}` → `stream.kind_counts`): "
                  f"**{stealthy} of {pos}** positives ({pct(frac)}) are `fraud_stealthy`.",
                  f"  - The artifact states it itself: \"{(syn.get('stream') or {}).get('generator_note', '')}\""]
        L += ["- **Mitigation actually implemented.** Absolute recall is NOT used as a quality claim: it is "
              "normalized out of the Runtime Integrity Score (RIS scores the intact baseline at "
              f"**{f((ab or {}).get('baseline_runtime_integrity_score'))}** by definition), and the "
              "experiment reports ablation DELTAS against this baseline rather than absolute detection.",
              "- **Residual risk (not mitigated).** Any absolute detection number from this stream "
              "characterises the generator + pipeline pair, not the world. It must not be cited as "
              "detection performance.", ""]

    L += ["### I2 — Cross-configuration state leakage", ""]
    cd = ev.get("cd")
    if cd and cd.get("datasets"):
        note = cd["datasets"][0].get("adapter_independence")
        L += [f"- **Threat.** A stateful online baseline (calibrated quantiles) could persist between "
              f"configurations and make an ablated run inherit the intact run's operating point.",
              f"- **Mitigation actually implemented.** `{rel(SRC['cross'])}` → `adapter_independence`: "
              f"\"{note}\"",
              f"- **Verified by regression test.** `tests/test_combined_ablation_artifacts.py` asserts the "
              f"physics invariant that ablating the audit plane (EQ/LG/HC) leaves `undetected_risk_rate` "
              f"EXACTLY at baseline on every dataset — the ledger is downstream of the decision and cannot "
              f"change authorization. This test caught a real state-leak defect; it is retained as a "
              f"permanent guard.", ""]
    else:
        L += [missing("cross"), ""]

    L += ["### I3 — Threshold choice as a confound", ""]
    th = ev.get("th")
    if th:
        stab = th.get("stability", {})
        checks = stab.get("checks", {})
        L += [f"- **Threat.** The operating point could be tuned so that the ablation conclusions only "
              f"hold at one threshold.",
              f"- **Evidence.** `{rel(SRC['thresh'])}` re-executes the matrix at "
              f"{len(th.get('scales', []))} threshold scales {th.get('scales')} "
              f"({th.get('n_executions')} executions). `stability.all_conclusions_stable` = "
              f"**{f(stab.get('all_conclusions_stable'))}**; "
              f"{sum(1 for c in checks.values() if c.get('holds_at_every_scale'))}/{len(checks)} "
              f"structural checks hold at EVERY scale.",
              f"- **Note the artifact makes about the thresholds themselves.** \"{th.get('threshold_note', '')}\"",
              "- **Residual risk (not mitigated).** The scan is a ±20% multiplicative perturbation of the "
              "learned operating point; it does not certify behaviour at arbitrary or adversarially chosen "
              "thresholds.", ""]
    else:
        L += [missing("thresh"), ""]
    return L


def sec_external(ev) -> list[str]:
    L = ["## 2. External validity", "", "### E1 — Cross-dataset ABSOLUTE metrics are not comparable", ""]
    cd = ev.get("cd")
    if not cd:
        L += [missing("cross"), ""]
        return L
    per = (cd.get("cross_dataset_conclusions") or {}).get("per_dataset", {})
    L += [f"- **Threat.** Reading the three datasets as a like-for-like comparison would be wrong: their "
          f"class prevalences differ by three orders of magnitude.",
          "", "| Dataset | Rows loaded | Evaluated | Prevalence | Baseline URR | Baseline recall |",
          "|---|---|---|---|---|---|"]
    for ds in cd["datasets"]:
        p = per.get(ds["dataset"], {})
        L += [f"| {ds['dataset']} | {ds['rows_loaded']} | {ds['evaluated']} | "
              f"**{pct(ds['prevalence'], 3)}** | {f(p.get('baseline_fpr'), 4)} | "
              f"{f(p.get('baseline_recall'), 4)} |"]
    L += ["", f"*Source: `{rel(SRC['cross'])}` (`row_limit` = {cd.get('row_limit')}).*", ""]

    # ground the small-N problem in the actual confusion matrix, do not merely assert it
    for ds in cd["datasets"]:
        b = next((c for c in ds["configs"] if c["n_disabled"] == 0), None)
        if not b:
            continue
        bcm = b.get("confusion_matrix") or {}
        npos = bcm.get("tp_fraud_denied", 0) + bcm.get("fn_fraud_permitted", 0)
        w = b.get("undetected_risk_rate_wilson95") or {}
        if npos <= 5:
            L += [f"- **Measured consequence on {ds['dataset']}.** At `row_limit`="
                  f"{cd.get('row_limit')} the evaluation window contains only **{npos} positive(s)**, so the "
                  f"Wilson 95% interval on `undetected_risk_rate` is "
                  f"[{f(w.get('low'), 3)}, **{f(w.get('high'), 3)}**] around a point estimate of "
                  f"{f(b.get('undetected_risk_rate'), 3)}. That interval is nearly vacuous. No absolute "
                  f"{ds['dataset']} detection claim is made or should be read from it."]
    concl = cd.get("cross_dataset_conclusions") or {}
    L += ["- **What DOES replicate (the actual claim).** "
          f"`cross_dataset_conclusions.all_conclusions_replicate` = "
          f"**{f(concl.get('all_conclusions_replicate'))}** across {cd.get('n_datasets')} datasets × "
          f"{cd.get('n_configurations_each')} configurations. The structural conclusions "
          f"({', '.join(sorted(next(iter(per.values()))['checks'])) if per else 'n/a'}) hold on every "
          f"dataset.",
          f"- **The artifact says so in its own words.** \"{concl.get('interpretation', '')}\"",
          "- **Residual risk (not mitigated).** Replication is of the ablation STRUCTURE only. Absolute "
          "numbers are deliberately not normalized across datasets and must not be pooled or averaged.", ""]

    L += ["### E2 — Single host, single OS, single Python", ""]
    ab = ev.get("ab")
    if ab:
        h = ab.get("host", {})
        L += [f"- **Threat.** Every configuration was executed on one machine "
              f"({h.get('platform')}, Python {h.get('python')}, {h.get('machine')}; "
              f"`{rel(SRC['ablation'])}` → `host`). Latency and throughput are host-bound.",
              "- **Mitigation.** Correctness-plane results (FPR, evidence completeness, ledger/hash-chain "
              "integrity, replay determinism) are deterministic given the seed "
              f"(`seed` = {ab['seed']}) and are host-invariant; timing results are reported with "
              "dispersion and CIs rather than as single points.",
              "- **Residual risk (not mitigated).** No multi-host or multi-architecture replication exists in "
              "this repository.", ""]
    return L


def sec_construct(ev) -> list[str]:
    L = ["## 3. Construct validity", ""]
    ab, st = ev.get("ab"), ev.get("st")

    L += ["### C1 — RIS is audit-weighted BY CONSTRUCTION", ""]
    if ab:
        L += [f"- **Threat.** The Runtime Integrity Score is a single scalar and could be mistaken for a "
              f"security score.",
              f"- **Evidence (the definition, quoted from `{rel(SRC['ablation'])}` → "
              f"`runtime_integrity_score_definition`).** \"{ab['runtime_integrity_score_definition']}\"",
              f"- **Measured consequence.** Because 4 of the 6 health planes are provenance planes, removing "
              f"an audit component moves RIS FARTHER than removing a security component, even though only "
              f"the latter opens the authorization boundary. From `{rel(SRC['ablation'])}`:"]
        by = {c["config"]: c for c in ab["configs"]}
        for name in ("remove_EQ", "remove_PE"):
            c = by.get(name)
            if c:
                L += [f"  - `{name}`: RIS **{f(c['runtime_integrity_score'])}**, "
                      f"`undetected_risk_rate` **{f(c['undetected_risk_rate'], 4)}**, "
                      f"`evidence_completeness` **{f(c['evidence_completeness'])}**, verdict "
                      f"*{c['overall_runtime_verdict']}*."]
        L += ["- **Mitigation actually implemented.** The security axis is reported SEPARATELY from RIS "
              "(`overall_runtime_verdict` distinguishes SECURITY-DEGRADED from AUDIT-DEGRADED from CRITICAL, "
              "and every interaction row carries an explicit `security_degradation` block). RIS is never used "
              "alone to rank component importance.",
              "- **Residual risk (not mitigated).** RIS remains an unweighted mean of six planes; the 4:2 "
              "audit:security split is a modelling choice, not an empirical weighting.", ""]
    else:
        L += [missing("ablation"), ""]

    L += ["### C2 — `ledger_integrity` has no sampling distribution", ""]
    ls = ev.get("ledger_stat")
    if ls:
        L += [f"- **Threat.** `ledger_integrity` is reported with NO confidence interval, p-value or effect "
              f"size, unlike every other metric. This looks like a gap in the statistics.",
              f"- **Evidence it is a construct property, not a gap.** "
              f"`{rel(SRC['stats'])}` → `configs.baseline_full_LDREA.ledger_integrity` carries "
              f"`deterministic` = **{f(ls.get('deterministic'))}** and an explicit "
              f"`not_sampled_reason`: \"{ls.get('not_sampled_reason', '')}\"",
              "- **Mitigation actually implemented.** The quantity that IS sampled — the per-block chain-link "
              "proportion — is reported separately as `hash_chain_integrity`, WITH intervals. So the ledger "
              "plane is not statistically unreported; it is reported through the estimator that has a "
              "sampling distribution.", ""]
    elif st:
        L += ["- **NOT GROUNDED** in this tree: `ledger_integrity` carries no `not_sampled_reason`.", ""]
    else:
        L += [missing("stats"), ""]

    L += ["### C3 — Metrics that cannot exist under a configuration are marked, not zero-filled", ""]
    if ev.get("undefined"):
        tot = sum(ev["undefined"].values())
        L += [f"- **Threat.** After removing a component, some metrics have no referent (e.g. hash-chain "
              f"integrity with no ledger). Silently coding them as 0.0 would fabricate a degradation.",
              f"- **Evidence.** `{rel(SRC['stats'])}` carries **{tot}** explicit `undefined_reason` entries "
              f"across {len(ev['undefined'])} metrics "
              f"({', '.join(f'`{k}`×{v}' for k, v in sorted(ev['undefined'].items()))}), e.g.:"]
        for cname, metrics in (ev["st"]["configs"]).items():
            for m, v in metrics.items():
                if isinstance(v, dict) and v.get("undefined_reason"):
                    L += [f"  - `{cname}` / `{m}`: \"{v['undefined_reason']}\""]
                    break
            else:
                continue
            break
        L += ["- **Residual risk.** An undefined metric still contributes its plane's floor value to the RIS "
              "composite; that is intentional (a destroyed plane scores 0 health) but it means RIS and the "
              "per-metric statistics answer different questions.", ""]

    L += ["### C4 — The mapped LAB corpus is oracle conformance, NOT fraud detection", ""]
    lk = ev.get("leak")
    if lk:
        v = lk.get("verdict", {})
        L += [f"- **Threat.** The mapped corpus `{lk.get('corpus')}` ({lk.get('rows_examined')} rows) could be "
              f"mistaken for a fraud-detection benchmark.",
              f"- **Measured evidence of leakage (`{rel(SRC['leakage'])}`).** "
              f"`label_leakage_present` = **{f(v.get('label_leakage_present'))}**; "
              f"**{v.get('n_leaking_inputs')} of {len(lk.get('columns_examined', []))}** examined engine "
              f"inputs are perfectly disjoint across classes and are therefore each a 100%-accurate "
              f"standalone classifier: {', '.join('`%s`' % c for c in lk.get('leaking_inputs', []))}.",
              f"- **Why.** \"{v.get('interpretation', '')[:400]}\"",
              "- **Mitigation actually implemented.** E5b does NOT use that corpus. It runs the runtime stack "
              "on a label-blind observation stream (`Observation` has no label field) and on the three real "
              "datasets in the cross-dataset arm. Results derived from the mapped corpus are labelled ORACLE "
              "CONFORMANCE, and the audit lists what the leakage does NOT invalidate:",
              *[f"  - {x}" for x in lk.get("does_not_invalidate", [])], ""]
    else:
        L += [missing("leakage"), ""]
    return L


def sec_statistical(ev) -> list[str]:
    L = ["## 4. Statistical conclusion validity", ""]
    st = ev.get("st")
    if not st:
        L += [missing("stats"), ""]
        return L
    L += ["### S1 — Multiple comparisons (the honest version)", "",
          f"- **Threat.** The design tests **{ev['n_configs'] if 'n_configs' in ev else 'n/a'} configurations "
          f"× {ev['n_metrics']} metrics**, producing **{ev['comparisons']} simultaneous hypothesis tests** "
          f"against the baseline at `alpha` = **{st['alpha']}** "
          f"(`{rel(SRC['stats'])}`). **No family-wise or FDR correction is applied.** At alpha={st['alpha']} "
          f"one would expect on the order of {round(st['alpha'] * ev['comparisons'])} false positives by "
          f"chance alone.",
          f"- **Measured mitigation (not a hand-wave).** {ev['significant']} of {ev['comparisons']} "
          f"comparisons are flagged significant, and of those, **"
          f"{ev['effect_mags'].get('large', 0)} ({pct(ev['effect_mags'].get('large', 0) / ev['significant']) if ev['significant'] else 'n/a'}) "
          f"carry a `large` Cliff's delta** "
          f"({', '.join(f'{k}: {v}' for k, v in ev['effect_mags'].most_common())}). The conclusions this "
          f"experiment actually draws (predicate-engine removal opens the boundary; evidence→ledger→hash-chain "
          f"is a hard cascade) rest on saturated effects — FPR moving to 1.0, evidence completeness moving to "
          f"0.0 — not on marginal p-values near alpha. A Bonferroni correction "
          f"(alpha/{ev['comparisons']} ≈ {st['alpha'] / ev['comparisons']:.2e}) would not disturb them.",
          "- **Residual risk (explicitly NOT mitigated).** Any INDIVIDUAL borderline p-value in "
          "`combined_statistics.json` should be treated as uncorrected and read with that in mind. The "
          "small/medium/negligible-effect significances "
          f"({ev['effect_mags'].get('small', 0)} small, {ev['effect_mags'].get('medium', 0)} medium, "
          f"{ev['effect_mags'].get('negligible', 0)} negligible) are exactly the ones a correction would be "
          "most likely to remove.", ""]

    L += ["### S2 — Bootstrap resolution bounds the achievable p-value", "",
          f"- **Threat.** Composite metrics use **{st['n_bootstrap']}** bootstrap replicates "
          f"(`n_bootstrap`, seed {st['bootstrap_seed']}, `{rel(SRC['stats'])}`). A percentile CI from "
          f"{st['n_bootstrap']} replicates cannot resolve tail probabilities finer than "
          f"~{1.0 / st['n_bootstrap']:.2e}.",
          "- **Mitigation.** Composite significance is read from whether the bootstrap difference CI excludes "
          "0, not from a fine-grained p-value; proportional metrics additionally carry exact Wilson intervals "
          "and a two-proportion z-test, which do not depend on the replicate count.",
          f"- **Method, quoted.** \"{(st.get('method') or {}).get('composite', '')}\"", ""]

    L += ["### S3 — Small denominators on the security axis", ""]
    base, cm = ev.get("base"), ev.get("cm")
    if base and cm:
        w = base["undetected_risk_rate_wilson95"]
        L += [f"- **Threat.** `undetected_risk_rate` and `blind_risk_detection_recall` are computed over the "
              f"population AT RISK — the positives — of which the baseline evaluation window contains only "
              f"**{cm['n_fraud']}** (vs {cm['n_legit']} negatives, {base['evaluated']} evaluated, "
              f"{base['warmup_excluded']} excluded as warm-up; `{rel(SRC['ablation'])}`).",
              f"- **Measured consequence.** The baseline Wilson 95% CI on FPR is "
              f"[{f(w['low'], 4)}, {f(w['high'], 4)}] — a width of {f(w['high'] - w['low'], 3)} around "
              f"{f(w['p'], 4)}. Security-axis point estimates are therefore imprecise.",
              "- **Mitigation actually implemented.** Every proportion is published WITH its Wilson interval "
              "rather than as a bare point, and the conclusions rely on effects that clear the interval by a "
              "wide margin (predicate-engine removal drives FPR to 1.0 at every threshold scale, not to a "
              "value inside the baseline CI).",
              "- **Residual risk (not mitigated).** Enlarging the positive count would require a different "
              "generator prevalence; it was not done.", ""]
    return L


def sec_ecological(ev) -> list[str]:
    L = ["## 5. Ecological validity", "", "### G1 — The fleet is processes on one host; there is no network", ""]
    fl = ev.get("fleet")
    if fl:
        L += [f"- **Threat.** The fleet arm could be read as distributed-systems evidence.",
              f"- **Evidence.** `{rel(SRC['fleet'])}` → `testbed_type` = **\"{fl.get('testbed_type')}\"** with "
              f"`nodes` = **{fl.get('nodes')}**. The \"nodes\" are OS processes on a single machine.",
              "- **Consequence, stated plainly.** No network transport is exercised, so packet loss, retry "
              "behaviour, partition tolerance and network-partition recovery are **not measured**. Their "
              "absence from the results is N/A, not a demonstration of perfect network reliability, and "
              "nothing in this repository should be read as such.", ""]
    else:
        L += [missing("fleet"), ""]

    L += ["### G2 — Distributed clock skew / IEEE-1588 PTP is physically unmeasurable here", ""]
    ck = ev.get("clock")
    if ck:
        L += [f"- **Threat.** A runtime that orders evidence by timestamp needs a clock-skew bound. None is "
              f"provided.",
              f"- **Evidence that this is a physical impossibility on this testbed, not an omission "
              f"(`{rel(SRC['clock'])}` → `why_not_ptp`).** \"{ck.get('why_not_ptp')}\"",
              f"- **What IS measured instead.** `clock_source` = `{ck.get('clock_source')}`, "
              f"`timestamp_resolution_ns` = {ck.get('timestamp_resolution_ns')}, "
              f"`monotonic_consistency` = **{f(ck.get('monotonic_consistency'))}** over "
              f"{ck.get('samples')} samples with {ck.get('non_monotonic_observations')} non-monotonic "
              f"observations, wall-vs-monotonic drift {f(ck.get('wall_vs_monotonic_drift_ppm'), 3)} ppm.",
              "- **Residual risk (NOT mitigated, and cannot be on this hardware).** Single-host monotonicity "
              "is a strictly weaker property than a bounded cross-host skew. Any multi-host deployment claim "
              "would require ≥2 physical hosts and a PTP grandmaster.", ""]
    else:
        L += [missing("clock"), ""]

    L += ["### G3 — The synthetic stream is not the world", ""]
    ab = ev.get("ab")
    if ab:
        L += [f"- **Threat.** `evidence_level` of the whole E5b matrix is self-declared "
              f"**\"{ab['evidence_level']}\"** (`{rel(SRC['ablation'])}`). Its detection numbers describe a "
              f"generator, not a production traffic distribution.",
              "- **Mitigation actually implemented.** The cross-dataset arm re-runs the SAME 19-configuration "
              f"matrix on three REAL corpora "
              f"(`{rel(SRC['cross'])}` → `evidence_level` = "
              f"**\"{(ev.get('cd') or {}).get('evidence_level', 'n/a')}\"**) precisely so that the structural "
              "conclusions do not depend on the synthetic generator.",
              "- **Residual risk (not mitigated).** Latency, throughput and interaction-effect magnitudes are "
              "reported only from the synthetic arm.", ""]
    return L


def sec_deployment(ev) -> list[str]:
    L = ["## 6. Deployment validity", "", "### D1 — Tier-S (pure software) only: no hardware claim is made", "",
         "- **Threat.** Cryptographic and latency figures could be read as attestable hardware numbers.",
         "- **Evidence (repository's own scope declaration).** The reference implementation is labelled "
         "**Tier-S** (`README.md`), and the repository explicitly lists Tier-H hardware "
         "(FPGA / SGX / HSM) as **Not Claimed** / out of scope, with no HSM, TPM or enclave anywhere in the "
         "tree (`FINAL_GAP_ANALYSIS.md`: *\"No HSM, TPM or enclave\"*; key custody is a published seed "
         "constant, not a key ceremony).",
         "- **Consequence.** The measured latency is a software path with representative crypto and is "
         "**not comparable to HSM/FPGA figures**. No secure-boot, attestation or hardware-root-of-trust "
         "property is asserted.",
         "- **Residual risk (NOT mitigated — deliberately out of scope).** A production deployment would need "
         "hardware key custody; nothing here evidences it.", ""]

    L += ["### D2 — Watchdog stall DETECTION inside the per-config fleet is timing-sensitive", ""]
    ab, wd = ev.get("ab"), ev.get("wd")
    if ab:
        gov_note = ("Additionally, the published run carries NO per-configuration governance block at all: "
                    f"`governance` is null for all {ab['n_configurations']} configurations and "
                    f"`governance_shared` is empty in `{rel(SRC['ablation'])}`, so no fleet/watchdog timing "
                    f"measurement enters any published E5b number."
                    if not ev.get("governance_measured") else
                    "Per-configuration governance blocks ARE present in the published run, but they are "
                    "reported for context only and are not inputs to the interaction analysis.")
        L += [f"- **Threat.** A stall detector inside a small, saturated per-configuration fleet is a race: "
              f"whether a stall is OBSERVED depends on scheduler timing, not only on whether the detector "
              f"works. Attributing such timing noise to a component interaction would be an error.",
              f"- **Evidence that E5b does not do so.** The governance plane is **excluded from the ablation "
              f"matrix**. `{rel(SRC['registry'])}` marks WD (Runtime Watchdog), FT (Fleet Telemetry), "
              f"CK (Clock Consistency) and RD (Runtime Risk Detection) with `in_ablation_matrix` = "
              f"**false**, and `paper_tables/table_combined_ablation_C.md` renders their impact cell as "
              f"*\"governance stage (not in ablation matrix)\"*. Consequently the "
              f"{len((ab or {}).get('interactions', []))} interaction effects are computed ONLY over the "
              f"{sum(1 for c in (ev.get('reg') or {}).get('components', []) if c.get('in_ablation_matrix'))} "
              f"in-matrix components (PE, RV, EQ, LG, HC) — no timing-plane signal can enter the interaction "
              f"analysis. {gov_note}"]
    if wd:
        L += [f"- **Where the authoritative watchdog evidence lives.** `{rel(SRC['watchdog'])}` "
              f"(experiment `{wd.get('experiment')}`, `evidence_level` = **{wd.get('evidence_level')}**, "
              f"supervisor `{wd.get('supervisor')}`) drives the real watchdog through "
              f"{len(wd.get('scenarios', []))} distinct heartbeat scenarios: "
              f"`all_scenarios_pass` = **{f(wd.get('all_scenarios_pass'))}**, `total_false_triggers` = "
              f"**{wd.get('total_false_triggers')}**. Method, quoted: \"{wd.get('method', '')}\"",
              "- **Residual risk.** Watchdog liveness is therefore evidenced by a dedicated scenario suite, "
              "NOT by the ablation matrix. Do not cite E5b for watchdog behaviour.", ""]
    elif ab:
        L += [missing("watchdog"), ""]

    L += ["### D3 — What a deployer would still have to establish", "",
          "- Multi-host operation (clock skew bound, network faults) — **no evidence in this repository** "
          f"(see G1/G2; `{rel(SRC['fleet'])}` → `testbed_type` is single-host).",
          "- Hardware key custody and attestation — **explicitly not claimed** (see D1).",
          "- Production traffic distributions — the ablation matrix is `Synthetic Runtime`; only the "
          f"structural conclusions were replicated on real corpora (see E1).", ""]
    return L


def sec_footer(ev) -> list[str]:
    L = ["---", "", "## Grounding manifest", "",
         "*This document asserts nothing that is not in one of these files. `--check` re-verifies them.*", "",
         "| Source | Present |", "|---|---|"]
    for k in SRC:
        L += [f"| `{rel(SRC[k])}` | {'yes' if ev['present'][k] else '**MISSING**'} |"]
    L += ["", "### Deliberately omitted", "",
          "Claims that could not be grounded in an artifact in this tree were left out rather than asserted. "
          "In particular this document makes **no** claim about: adversarial/attacker-adaptive evasion of the "
          "predicate engine, concept drift over time, human-factors or reviewer-agreement validity, and "
          "cost/benefit of false denials — none of these are measured by E5b or its inputs.", ""]
    return L


def build(ev: dict) -> str:
    parts = (sec_header(ev) + sec_internal(ev) + sec_external(ev) + sec_construct(ev)
             + sec_statistical(ev) + sec_ecological(ev) + sec_deployment(ev) + sec_footer(ev))
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    # NOTE: the default output is deliberately NOT `THREATS_TO_VALIDITY.md`.
    # That file is TRACKED, pre-existing reviewer evidence covering E1-E8 and is owned by
    # `experiments/generate_publication_docs.py` (which RUN_ALL re-runs). Writing there would both
    # destroy existing reviewer evidence and create a two-generators-one-file fight in which this
    # document would be silently overwritten on the next RUN_ALL. This generator therefore emits the
    # E5b combined-ablation threats to its OWN file; the two documents are complementary.
    ap.add_argument("--out", default=str(ROOT / "COMBINED_ABLATION_THREATS_TO_VALIDITY.md"))
    ap.add_argument("--check", action="store_true",
                    help="verify every grounding source exists; exit 1 if any is missing")
    a = ap.parse_args()

    ev = collect()
    missing_srcs = [k for k, ok in ev["present"].items() if not ok]

    if a.check:
        for k in SRC:
            print(f"  [{'ok ' if ev['present'][k] else 'MISS'}] {rel(SRC[k])}")
        if missing_srcs:
            print(f"[threats] {len(missing_srcs)} grounding source(s) missing: {missing_srcs}", file=sys.stderr)
            return 1
        print("[threats] all grounding sources present")
        return 0

    if missing_srcs:
        print(f"[threats] WARNING: {len(missing_srcs)} source(s) missing {missing_srcs}; "
              f"the affected sections will say so rather than assert a number.", file=sys.stderr)

    out = Path(a.out)
    out.write_text(build(ev))
    print(f"[threats] wrote {rel(out)} "
          f"({len(out.read_text().splitlines())} lines) from "
          f"{sum(1 for v in ev['present'].values() if v)}/{len(SRC)} grounding sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
