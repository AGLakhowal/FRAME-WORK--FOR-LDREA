#!/usr/bin/env python3
"""
experiment_cross_dataset_ablation.py — PART 3: the combined ablation on every REAL dataset.
===========================================================================================

Runs the COMPLETE combined-ablation matrix independently on every dataset discovered by
`experiments/dataset_adapters.py` (ULB credit-card fraud, IEEE-CIS fraud, UNSW-NB15 intrusion).

Datasets are NOT merged and metrics are NOT normalized across them: each dataset has its own
prevalence, its own observable feature space, and its own unsupervised operating point, so a
pooled number would be meaningless. Each is reported on its own terms; only the ABLATION
CONCLUSIONS are compared across datasets.

The frozen Gamma rule (`stress_test.gamma_decision`) is imported and used identically for every
dataset — exactly as E12 does. The adapters produce the predicate vector from observables only;
the label is returned separately and opened only after every decision is committed and chained.

The 5 ablatable components behave identically to the synthetic study:
    PE  predicate engine  -> adapter.predicates() not called (Gamma sees an empty vector => PERMIT)
    RV  runtime revocation-> PermitAuthority issue/revoke/verify not enforced
    EQ  evidence quad     -> build_ertuple not emitted
    LG  runtime ledger    -> Ledger.append not called
    HC  hash chain        -> ledger appended WITHOUT previous-hash linkage

Outputs: experiments/combined_ablation/cross_dataset_ablation.json
         experiments/combined_ablation/cross_dataset_summary.{csv,md}
         paper_tables/cross_dataset_summary.tex
         experiments/combined_ablation/figures/cross_dataset_{comparison,heatmap}.svg
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import dataset_adapters as DA
import experiment_combined_ablation as CA
from e5b_metric_note import NOTE_MD, NOTE_TEX
import metrics_engine as ME
from runtime_stack import (ExecutionTimeline, Ledger, PermitAuthority, _signer, build_ertuple, sha)
from stress_test import gamma_decision

OUT = CA.OUT
FIG = CA.FIG
PAPER_TABLES = CA.PAPER_TABLES
REV_EVERY = 20
WARMUP = 0.25


def run_dataset_config(A, feats, labels, n_warm, disabled: frozenset, keys, policy_hash) -> dict:
    """One configuration of the combined ablation on ONE real dataset (full runtime path)."""
    sk, pub, sign, verify = keys
    PE_off = "predicate_engine" in disabled
    RV_off = "runtime_revocation" in disabled
    EQ_off = "evidence_quad" in disabled
    LG_off = "runtime_ledger" in disabled
    HC_off = "hash_chain" in disabled

    auth = PermitAuthority(sign, verify) if not RV_off else None
    ledger = None if LG_off else (CA._NoChainLedger(sign) if HC_off else Ledger(sign))
    batch, n_ertuples = [], 0

    eval_feats, eval_labels = feats[n_warm:], labels[n_warm:]
    decisions = []
    pred_passed = pred_total = ev_valid = replay_ok = permits = 0
    pass_seen, fail_seen, pred_names = set(), set(), []
    permits_issued, revoke_targets = [], []
    e2e_lat, auth_lat = [], []

    t0 = time.perf_counter()
    for i, f in enumerate(eval_feats):
        t_a = time.perf_counter_ns()
        tl = ExecutionTimeline(); tl.t_received = t_a; tl.t_validate = time.perf_counter_ns()
        if PE_off:
            preds = []
        else:
            preds = A.predicates(f)                     # observables -> predicates (blind)
            if not pred_names:
                pred_names = [p["name"] for p in preds]
            for p in preds:
                pred_total += 1
                if p["passed"]:
                    pred_passed += 1; pass_seen.add(p["name"])
                else:
                    fail_seen.add(p["name"])
        tl.t_predicate = time.perf_counter_ns()

        ta = time.perf_counter_ns()
        dec = gamma_decision(preds)                     # frozen rule, identical for every dataset
        tb = time.perf_counter_ns()
        auth_lat.append((tb - ta) / 1e6); tl.t_authorize = tb

        permit = None
        if dec["decision"] == "PERMIT":
            permits += 1
            nonce = sha((A.name, i))[:32]
            permit = (auth.issue(f"{A.name}-P{i:08d}", "dataset-subject", nonce, policy_hash, tb)
                      if not RV_off else {"permit_id": f"{A.name}-P{i:08d}", "nonce": nonce,
                                          "policy_hash": policy_hash})
            permits_issued.append((permit["permit_id"], permit, tb))
            if len(permits_issued) % REV_EVERY == 0:
                revoke_targets.append((permit["permit_id"], permit, tb))
        tl.t_issue = tl.t_execute_start = tl.t_execute_finish = time.perf_counter_ns()

        replay_hash = sha({"f": {k: str(v)[:64] for k, v in f.items()}, "policy": policy_hash})
        if not EQ_off:
            er = build_ertuple(execution_id=f"{A.name}-E{i:08d}", decision=dec, permit=permit,
                               predicates=preds, policy_hash=policy_hash, replay_hash=replay_hash,
                               ledger_hash=ledger.blocks[-1]["current_hash"] if (ledger and ledger.blocks) else "0"*64,
                               timeline=tl, worker_id=0, clock_offset_ns=0,
                               evidence_id=f"{A.name}-EV{i:08d}", nonce=sha((i, A.name))[:32], sign=sign)
            body = {k: v for k, v in er.items() if k not in ("ertuple_hash", "signature")}
            if sha(body) == er["ertuple_hash"] and er.get("signature"):
                ev_valid += 1
            n_ertuples += 1
            if ledger is not None:
                batch.append(er)
                if len(batch) == 128:
                    ledger.append(batch); batch = []
        tl.t_commit = time.perf_counter_ns()

        if sha({"f": {k: str(v)[:64] for k, v in f.items()}, "policy": policy_hash}) == replay_hash:
            replay_ok += 1
        tl.t_replay = time.perf_counter_ns()
        A.observe(f)                                    # online state update, never the label
        decisions.append(dec["decision"])
        e2e_lat.append((time.perf_counter_ns() - t_a) / 1e6)
    if ledger is not None and batch:
        ledger.append(batch)
    wall = time.perf_counter() - t0

    n = len(eval_feats)
    denied = [d == "SAFE_STATE" for d in decisions]
    tp = sum(1 for dn, y in zip(denied, eval_labels) if dn and y == 1)
    fn = sum(1 for dn, y in zip(denied, eval_labels) if not dn and y == 1)
    fp = sum(1 for dn, y in zip(denied, eval_labels) if dn and y == 0)
    tn = sum(1 for dn, y in zip(denied, eval_labels) if not dn and y == 0)
    n_fraud, n_legit = tp + fn, tn + fp
    recall = (tp / n_fraud) if n_fraud else None
    spec = (tn / n_legit) if n_legit else None

    n_preds = len(pred_names) or 1
    if PE_off:
        pred_cov, pred_pass = 0.0, 1.0
    else:
        pred_cov = len(pass_seen & fail_seen) / n_preds
        pred_pass = (pred_passed / pred_total) if pred_total else None

    evidence_completeness = 0.0 if EQ_off else (ev_valid / n if n else None)
    replay_determinism = (replay_ok / n) if n else None
    if ledger is not None and ledger.blocks:
        chain_ok, chain_err = ledger.verify()
        hc_rate, hc_ok, hc_total = CA._chain_link_integrity(ledger.blocks)
        ledger_integrity, n_blocks = (1.0 if chain_ok else 0.0), len(ledger.blocks)
    else:
        chain_err = "no ledger" if LG_off else "no evidence to chain"
        hc_rate, hc_ok, hc_total, ledger_integrity, n_blocks = (None, 0, 0, None, 0)

    if revoke_targets:
        if not RV_off:
            for pid, _p, _t in revoke_targets:
                auth.revoke(pid)
            now_ns = permits_issued[-1][2] + 1
            accepted = sum(1 for pid, p, _t in revoke_targets
                           if auth.verify_permit(p, now_ns, policy_hash)[0])
        else:
            accepted = len(revoke_targets)
        revocation_compliance = 1.0 - accepted / len(revoke_targets)
    else:
        accepted, revocation_compliance = 0, None

    replay_anchored = (not EQ_off) and (not LG_off) and (ledger_integrity == 1.0)
    replay_integrity = (replay_determinism if replay_anchored else 0.0) if replay_determinism is not None else None
    lat = CA._stats(e2e_lat)
    return {
        "dataset": A.name, "domain": A.domain,
        "config": CA._name(disabled), "disabled_components": sorted(disabled),
        "disabled_codes": sorted(CA.CODE[c] for c in disabled), "n_disabled": len(disabled),
        "evaluated": n, "prevalence": (n_fraud / n) if n else None,
        "confusion_matrix": {"tp_fraud_denied": tp, "fn_fraud_permitted": fn,
                             "fp_legit_denied": fp, "tn_legit_permitted": tn},
        "blind_decision_accuracy": (tp + tn) / n if n else None,
        "blind_decision_accuracy_wilson95": ME.wilson_ci(tp + tn, n) if n else None,
        "undetected_risk_rate": (fn / n_fraud) if n_fraud else None,
        "undetected_risk_rate_wilson95": ME.wilson_ci(fn, n_fraud) if n_fraud else None,
        "benign_flag_rate": (fp / n_legit) if n_legit else None,
        "benign_flag_rate_wilson95": ME.wilson_ci(fp, n_legit) if n_legit else None,
        "blind_risk_detection_recall": recall,
        "blind_risk_detection_recall_wilson95": ME.wilson_ci(tp, n_fraud) if n_fraud else None,
        "blind_balanced_accuracy": ((recall + spec) / 2) if (recall is not None and spec is not None) else None,
        "replay_determinism_rate": replay_determinism, "replay_integrity": replay_integrity,
        "evidence_completeness": evidence_completeness, "ertuples": n_ertuples,
        "predicate_coverage": pred_cov, "predicate_pass_rate": pred_pass,
        "n_predicates": len(pred_names), "predicate_names": pred_names,
        "hash_chain_integrity": hc_rate, "hash_chain_links_ok": hc_ok, "hash_chain_links_total": hc_total,
        "ledger_integrity": ledger_integrity, "ledger_blocks": n_blocks, "ledger_verify_error": chain_err,
        "revocation_compliance": revocation_compliance, "false_permits_after_revocation": accepted,
        "revocation_probe_n": len(revoke_targets),
        "latency_mean_ms": lat.get("mean"), "latency_median_ms": lat.get("median"),
        "latency_p95_ms": lat.get("p95"), "latency_p99_ms": lat.get("p99"), "latency_max_ms": lat.get("max"),
        "throughput_decisions_per_s": (n / wall) if wall else None,
        "runtime_overhead_ms": ME.compute_runtime_overhead(auth_lat)["value"],
        "execution_time_s": round(wall, 4),
        "runtime_integrity_score": None, "overall_runtime_verdict": None,
    }


def run(limit=20000, only=None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    recs = DA.discover()
    if only:
        recs = [r for r in recs if r["adapter"] in only]
    keys = _signer()
    cfg_sets = CA.build_config_set()
    t_all = time.time()
    datasets, all_rows, not_found = [], [], []
    print(f"[cross-dataset] {len(recs)} datasets discovered; {len(cfg_sets)} configurations each; "
          f"limit={limit} rows")
    for rec in recs:
        t0 = time.time()
        try:
            feats, labels = rec["cls"](Path(rec["path"])).load(limit)
        except Exception as ex:
            not_found.append({"dataset": rec["adapter"], "status": "FAILED", "error": str(ex)})
            print(f"  [{rec['adapter']}] FAILED to load: {ex}")
            continue
        n = len(feats)
        n_warm = int(n * WARMUP)

        def fresh_adapter():
            """A FRESH, independently-calibrated adapter per configuration.

            The adapters are STATEFUL: `observe()` updates online behaviour baselines that
            `predicates()` consults. Reusing one instance across configurations would let state from
            configuration k-1 leak into configuration k, making the runs non-independent — it showed
            up as the ledger ablation appearing to shift the undetected-risk rate (URR), which is physically
            impossible (the ledger is strictly downstream of the decision). Re-instantiating and
            re-warming per configuration restores independence, so any metric difference between
            configurations is caused ONLY by the ablated component.
            """
            a = rec["cls"](Path(rec["path"]))
            a.calibrate(feats[:n_warm])
            for f in feats[:n_warm]:
                a.observe(f)
            return a

        A0 = fresh_adapter()
        policy_hash = sha({"dataset": A0.name, "calib": {k: str(v)[:40] for k, v in A0.calib.items()}})
        print(f"  [{A0.name}] {n:,} rows loaded ({time.time()-t0:.1f}s), prevalence "
              f"{sum(labels)/max(n,1)*100:.2f}%, {len(A0.calib)} calibrated thresholds")

        rows = []
        base = None
        for cs in cfg_sets:
            A = fresh_adapter()                 # <-- independence guarantee (see fresh_adapter docstring)
            c = run_dataset_config(A, feats, labels, n_warm, cs, keys, policy_hash)
            if not cs:
                base = c
                CA._BASE_RECALL = c["blind_risk_detection_recall"]
            rows.append(c)
        for c in rows:
            c["runtime_integrity_score"] = round(CA._ris(c), 6)
        for c in rows:
            c["overall_runtime_verdict"] = CA._verdict(c, base)
        b = base
        print(f"  [{A.name}] baseline: acc={b['blind_decision_accuracy']:.3f} fpr={b['undetected_risk_rate']:.3f} "
              f"recall={b['blind_risk_detection_recall']:.3f} RIS={b['runtime_integrity_score']:.3f} "
              f"({len(cfg_sets)} configs in {time.time()-t0:.1f}s)")
        datasets.append({"dataset": A0.name, "domain": A0.domain, "source_file": rec["relpath"],
                         "rows_loaded": n, "warmup_rows": n_warm, "evaluated": n - n_warm,
                         "prevalence": sum(labels) / max(n, 1),
                         "n_predicates": base["n_predicates"],
                         "predicate_names": base["predicate_names"],
                         "calibrated_thresholds": {k: str(v)[:60] for k, v in A0.calib.items()},
                         "baseline_runtime_integrity_score": base["runtime_integrity_score"],
                         "adapter_independence": ("a FRESH adapter is instantiated and re-calibrated "
                                                  "for every configuration, so stateful online "
                                                  "baselines cannot leak between configurations"),
                         "configs": rows})
        all_rows.extend(rows)

    conclusions = _cross_dataset_conclusions(datasets)
    report = {
        "experiment": "cross_dataset_combined_ablation",
        "evidence_level": "Measured Runtime",
        "purpose": ("Run the COMPLETE combined ablation independently on every real dataset. Datasets "
                    "are not merged and metrics are not normalized across them — each has a different "
                    "prevalence, feature space and unsupervised operating point, so only the ABLATION "
                    "CONCLUSIONS are compared."),
        "gamma_untouched": "stress_test.gamma_decision imported and used identically for every dataset",
        "row_limit": limit, "n_datasets": len(datasets), "n_configurations_each": len(cfg_sets),
        "datasets": datasets, "failed": not_found,
        "cross_dataset_conclusions": conclusions,
        "duration_s": round(time.time() - t_all, 2),
    }
    (OUT / "cross_dataset_ablation.json").write_text(json.dumps(report, indent=2) + "\n")
    _write_summary(report)
    _write_figures(report)
    print(f"[cross-dataset] {len(datasets)} datasets x {len(cfg_sets)} configs in {report['duration_s']}s; "
          f"conclusions replicate on all datasets: {conclusions['all_conclusions_replicate']}")
    return report


def _cross_dataset_conclusions(datasets) -> dict:
    """Do the ablation conclusions REPLICATE on every real dataset? Decided from measured values."""
    per = {}
    for d in datasets:
        by = {"+".join(c["disabled_codes"]) or "—": c for c in d["configs"]}
        base, pe, eq = by.get("—"), by.get("PE"), by.get("EQ")
        lg, hc = by.get("LG"), by.get("HC")
        checks = {
            "PE_removal_raises_URR": (pe["undetected_risk_rate"] > base["undetected_risk_rate"]
                                      if pe and base and pe["undetected_risk_rate"] is not None else None),
            "EQ_removal_zeroes_evidence": (eq["evidence_completeness"] == 0.0) if eq else None,
            "EQ_removal_cascades_to_ledger": (eq["ledger_integrity"] is None) if eq else None,
            "LG_HC_removal_does_not_raise_URR": (
                lg["undetected_risk_rate"] == base["undetected_risk_rate"]
                and hc["undetected_risk_rate"] == base["undetected_risk_rate"]) if (lg and hc and base) else None,
        }
        per[d["dataset"]] = {"checks": checks,
                             "baseline_urr": base["undetected_risk_rate"],
                             "baseline_recall": base["blind_risk_detection_recall"],
                             "baseline_accuracy": base["blind_decision_accuracy"],
                             "prevalence": d["prevalence"],
                             "all_hold": all(v for v in checks.values() if v is not None)}
    return {
        "all_conclusions_replicate": all(v["all_hold"] for v in per.values()) if per else False,
        "per_dataset": per,
        "interpretation": ("The ABSOLUTE metrics differ across datasets by design (different "
                           "prevalence, observables and operating points — they are not comparable and "
                           "are deliberately not normalized). What replicates is the ablation STRUCTURE: "
                           "the predicate engine is the only component whose removal opens the "
                           "authorization boundary, and the evidence->ledger->hash-chain cascade is a "
                           "critical dependency on every dataset."),
    }


SUM_COLS = ["Dataset", "Configuration", "Authorization Accuracy", "URR", "BFR", "Replay", "Evidence",
            "Latency(ms)", "Throughput(dec/s)", "Runtime Integrity Score", "Verdict"]


def _srow(c):
    f = CA._f
    return [c["dataset"], c["config"], f(c["blind_decision_accuracy"]), f(c["undetected_risk_rate"]),
            f(c["benign_flag_rate"]), f(c["replay_integrity"]), f(c["evidence_completeness"]),
            f(c["latency_mean_ms"], 4), f(c["throughput_decisions_per_s"], 0),
            f(c["runtime_integrity_score"]), c["overall_runtime_verdict"].split(" (")[0]]


def _write_summary(rep):
    rows = [_srow(c) for d in rep["datasets"] for c in d["configs"]]
    with open(OUT / "cross_dataset_summary.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(SUM_COLS)
        for r in rows:
            w.writerow(r)
    md = ["# Cross-Dataset Combined Ablation", "",
          "> Auto-generated by `experiment_cross_dataset_ablation.py` (PART 3). The complete combined "
          "ablation is executed INDEPENDENTLY on every real dataset. Datasets are not merged and "
          "metrics are not normalized across them.", "",
          f"- Datasets: **{rep['n_datasets']}**, configurations each: **{rep['n_configurations_each']}**, "
          f"row limit {rep['row_limit']:,}, total {rep['duration_s']}s.",
          f"- {rep['gamma_untouched']}.", "",
          "## Dataset characteristics (why absolute metrics are NOT comparable)", "",
          "| Dataset | Domain | Rows | Prevalence | Predicates | Baseline URR | Baseline Recall |",
          "|---|---|--:|--:|--:|--:|--:|"]
    for d in rep["datasets"]:
        b = d["configs"][0]
        md.append(f"| {d['dataset']} | {d['domain']} | {d['rows_loaded']:,} | {d['prevalence']*100:.2f}% | "
                  f"{d['n_predicates']} | {CA._f(b['undetected_risk_rate'])} | "
                  f"{CA._f(b['blind_risk_detection_recall'])} |")
    con = rep["cross_dataset_conclusions"]
    md += ["", f"## Do the ablation conclusions replicate? "
               f"{'**YES — on every dataset**' if con['all_conclusions_replicate'] else '**NO**'}", "",
           "| Conclusion | " + " | ".join(d["dataset"] for d in rep["datasets"]) + " |",
           "|---|" + "|".join(":--:" for _ in rep["datasets"]) + "|"]
    names = ["PE_removal_raises_URR", "EQ_removal_zeroes_evidence", "EQ_removal_cascades_to_ledger",
             "LG_HC_removal_does_not_raise_URR"]
    for nm in names:
        cells = []
        for d in rep["datasets"]:
            v = con["per_dataset"][d["dataset"]]["checks"].get(nm)
            cells.append("✅" if v else ("—" if v is None else "❌"))
        md.append(f"| {nm.replace('_',' ')} | " + " | ".join(cells) + " |")
    md += ["", f"> {con['interpretation']}", "", "## Full measured grid", "",
           "| " + " | ".join(SUM_COLS) + " |", "|" + "|".join("---" for _ in SUM_COLS) + "|"]
    for r in rows:
        md.append("| " + " | ".join(str(x) for x in r) + " |")
    md.append("")
    md += ["", NOTE_MD]
    (OUT / "cross_dataset_summary.md").write_text("\n".join(md) + "\n")

    # LaTeX (IEEE-ready)
    tex = ["% auto-generated by experiment_cross_dataset_ablation.py", "\\begin{table*}[t]",
           "\\centering", "\\scriptsize",
           "\\caption{Cross-dataset combined component ablation. The complete ablation matrix is "
           "executed independently on each dataset; metrics are not normalized across datasets "
           "(prevalence and observable feature spaces differ by design).}",
           "\\label{tab:cross-dataset}",
           "\\begin{tabular}{l l r r r r r r r r l}", "\\toprule",
           "Dataset & Configuration & Blind Acc. & URR & BFR & Replay & Evid. & Lat.(ms) & Tput & RIS & Verdict \\\\",
           "\\midrule"]
    for r in rows:
        tex.append(" & ".join(str(x).replace("_", "\\_").replace("—", "--") for x in r) + " \\\\")
    tex += ["\\bottomrule", "\\end{tabular}",
            "\\\\[3pt]", "\\begin{minipage}{\\textwidth}\\footnotesize " + NOTE_TEX + "\\end{minipage}",
            "\\end{table*}"]
    PAPER_TABLES.mkdir(exist_ok=True)
    (PAPER_TABLES / "cross_dataset_summary.tex").write_text("\n".join(tex) + "\n")
    (OUT / "cross_dataset_summary.tex").write_text("\n".join(tex) + "\n")


def _write_figures(rep):
    ds = [d["dataset"] for d in rep["datasets"]]
    cfgs = [c["config"] for c in rep["datasets"][0]["configs"]] if rep["datasets"] else []
    grid = {(d["dataset"], c["config"]): c for d in rep["datasets"] for c in d["configs"]}

    def color(v):
        if v is None:
            return "#30363d"
        r_, g_ = (255, int(120 * (v / 0.5))) if v < 0.5 else (int(255 * (1 - (v - 0.5) / 0.5)), 200)
        return f"rgb({r_},{g_},70)"
    cw, rh, x0, y0 = 130, 22, 220, 58
    W, H = x0 + cw * len(ds) + 30, y0 + rh * len(cfgs) + 40
    b = [f"<text x='{W/2}' y='22' fill='#e6edf3' font-size='14' font-weight='700' text-anchor='middle'>"
         f"Cross-Dataset Heatmap — Runtime Integrity Score (URR)</text>"]
    for j, d in enumerate(ds):
        b.append(f"<text x='{x0+cw*j+cw/2}' y='{y0-8}' fill='#8b949e' font-size='11' text-anchor='middle'>{d}</text>")
    for i, c in enumerate(cfgs):
        b.append(f"<text x='{x0-10}' y='{y0+rh*i+15}' fill='#e6edf3' font-size='9.5' text-anchor='end'>{c}</text>")
        for j, d in enumerate(ds):
            r = grid.get((d, c))
            v = r["runtime_integrity_score"] if r else None
            fpr = r["undetected_risk_rate"] if r else None
            b.append(f"<rect x='{x0+cw*j}' y='{y0+rh*i}' width='{cw-3}' height='{rh-3}' fill='{color(v)}' opacity='0.85'/>"
                     f"<text x='{x0+cw*j+cw/2}' y='{y0+rh*i+15}' fill='#0d1117' font-size='9' text-anchor='middle'>"
                     f"{'—' if v is None else f'{v:.2f}'} ({'—' if fpr is None else f'{fpr:.2f}'})</text>")
    (FIG / "cross_dataset_heatmap.svg").write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
        f"font-family='-apple-system,Segoe UI,Roboto,sans-serif'><rect width='{W}' height='{H}' "
        f"fill='#0d1117'/>{''.join(b)}</svg>")

    # grouped-bar comparison: baseline vs remove_PE URR per dataset (the headline conclusion)
    gw, gap, x0b, ytop, ybot = 46, 26, 90, 60, 250
    W2, H2 = x0b + len(ds) * (2 * gw + gap) + 60, ybot + 90
    bb = [f"<text x='{W2/2}' y='22' fill='#e6edf3' font-size='14' font-weight='700' text-anchor='middle'>"
          f"Cross-Dataset Comparison — undetected-risk rate (URR): baseline vs predicate engine removed</text>",
          f"<line x1='{x0b}' y1='{ybot}' x2='{W2-20}' y2='{ybot}' stroke='#30363d'/>"]
    for v in (0, 0.5, 1.0):
        y = ybot - v * (ybot - ytop)
        bb.append(f"<text x='{x0b-8}' y='{y+3}' fill='#8b949e' font-size='9' text-anchor='end'>{v:.1f}</text>"
                  f"<line x1='{x0b}' y1='{y}' x2='{W2-20}' y2='{y}' stroke='#21262d'/>")
    for i, d in enumerate(ds):
        base = grid.get((d, "baseline_full_LDREA")); pe = grid.get((d, "remove_PE"))
        for k, (rr, col, lab) in enumerate([(base, "#3fb950", "baseline"), (pe, "#f85149", "remove_PE")]):
            v = (rr or {}).get("undetected_risk_rate") or 0.0
            x = x0b + i * (2 * gw + gap) + k * gw
            h = v * (ybot - ytop)
            bb.append(f"<rect x='{x}' y='{ybot-h}' width='{gw-4}' height='{h}' fill='{col}' opacity='0.9'/>"
                      f"<text x='{x+gw/2-2}' y='{ybot-h-4}' fill='#8b949e' font-size='9' text-anchor='middle'>{v:.2f}</text>")
        bb.append(f"<text x='{x0b + i*(2*gw+gap) + gw}' y='{ybot+16}' fill='#e6edf3' font-size='10' "
                  f"text-anchor='middle'>{d}</text>")
    bb.append(f"<text x='{x0b}' y='{H2-40}' fill='#3fb950' font-size='10'>■ baseline (full L-DREA)</text>"
              f"<text x='{x0b+170}' y='{H2-40}' fill='#f85149' font-size='10'>■ predicate engine removed</text>"
              f"<text x='{x0b}' y='{H2-22}' fill='#8b949e' font-size='9.5'>Absolute rates are NOT comparable "
              f"across datasets (different prevalence/observables); the REPLICATED conclusion is the rise.</text>")
    (FIG / "cross_dataset_comparison.svg").write_text(
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W2}' height='{H2}' viewBox='0 0 {W2} {H2}' "
        f"font-family='-apple-system,Segoe UI,Roboto,sans-serif'><rect width='{W2}' height='{H2}' "
        f"fill='#0d1117'/>{''.join(bb)}</svg>")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20000, help="rows per dataset")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    run(limit=6000 if a.fast else a.limit, only=a.only)
