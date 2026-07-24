#!/usr/bin/env python3
"""Unified blind runtime evaluation across all discovered datasets (Parts 1-5, reuse 6-10).

One pipeline, every dataset:

    discover -> adapter -> calibrate (unlabeled warmup) -> predicate vector -> gamma_decision
             -> ERTuple -> Merkle ledger -> [labels opened only now] -> score + bootstrap CI

Gamma (stress_test.gamma_decision) is imported and used identically for all datasets. The label is
never in the decision path: adapters return it separately and the scorer opens it after every
decision is chained.

    python experiments/run_dataset_eval.py [--limit 100000] [--only ULB IEEE-CIS UNSW-NB15]

Every metric is Measured Runtime (real data, real decisions). Nothing is synthetic; nothing is
hardcoded. A dataset that is not discovered is reported status=NOT_FOUND with no metrics.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import dataset_adapters as DA
from bootstrap_ci import bootstrap_rate_ci
from runtime_stack import Ledger, _signer, build_ertuple, ExecutionTimeline, score, sha
from stress_test import gamma_decision

OUT = ROOT / "production_evidence" / "datasets"
DEFAULT_LIMIT = 100_000
DEFAULT_WARMUP = 0.25


def _stats(v, unit="ms"):
    if not v:
        return {"n": 0, "unit": unit}
    s = sorted(v)
    q = lambda p: s[max(1, min(len(s), int(round(p / 100 * len(s) + 0.5)))) - 1]
    return {"n": len(v), "unit": unit, "mean": statistics.fmean(v), "min": s[0], "max": s[-1],
            "median": q(50), "p95": q(95), "p99": q(99),
            "stdev": statistics.pstdev(v) if len(v) > 1 else 0.0}


def evaluate(rec: dict, limit: int) -> dict:
    A = rec["cls"](Path(rec["path"]))
    t_load0 = time.perf_counter()
    feats, labels = A.load(limit)
    load_s = time.perf_counter() - t_load0
    n = len(feats)
    n_warm = int(n * DEFAULT_WARMUP)

    # --- calibrate on the unlabeled warmup prefix ------------------------------------------------
    A.calibrate(feats[:n_warm])
    # warm any online state (behaviour baselines) without reading labels
    for f in feats[:n_warm]:
        A.observe(f)

    _sk, pub, sign, verify = _signer()
    policy_hash = sha({"dataset": A.name, "calib": {k: str(v)[:40] for k, v in A.calib.items()}})
    ledger = Ledger(sign)

    decisions, gammas, batch = [], [], []
    pred_lat, auth_lat, e2e = [], [], []
    permits = 0

    eval_feats = feats[n_warm:]
    eval_labels = labels[n_warm:]
    for i, f in enumerate(eval_feats):
        tl = ExecutionTimeline()
        tl.t_received = time.perf_counter_ns()
        t0 = time.perf_counter_ns()
        preds = A.predicates(f)                      # observables -> predicate vector (blind)
        t1 = time.perf_counter_ns()
        dec = gamma_decision(preds)                  # dataset-independent aggregation, untouched
        t2 = time.perf_counter_ns()
        tl.t_authorize = t2
        if dec["decision"] == "PERMIT":
            permits += 1
        replay_hash = sha({"f": {k: str(v)[:64] for k, v in f.items()}, "policy": policy_hash})
        er = build_ertuple(execution_id=f"{A.name}-E{i:08d}", decision=dec, permit=None,
                           predicates=preds, policy_hash=policy_hash, replay_hash=replay_hash,
                           ledger_hash=ledger.blocks[-1]["current_hash"] if ledger.blocks else "0"*64,
                           timeline=tl, worker_id=0, clock_offset_ns=0,
                           evidence_id=f"{A.name}-EV{i:08d}", nonce=sha((A.name, i))[:32], sign=sign)
        batch.append(er)
        if len(batch) == 128:
            ledger.append(batch); batch = []
        A.observe(f)
        decisions.append(dec["decision"]); gammas.append(dec["gamma"])
        pred_lat.append((t1 - t0) / 1e6); auth_lat.append((t2 - t1) / 1e6)
        e2e.append((time.perf_counter_ns() - tl.t_received) / 1e6)
    if batch:
        ledger.append(batch)
    chain_ok, chain_err = ledger.verify()

    # --- labels opened HERE, and only here -------------------------------------------------------
    det = score(decisions, gammas, eval_labels, evidence_level="Measured Runtime")

    # bootstrap CI on recall and false-permit rate (per-item masks)
    denied = [d == "SAFE_STATE" for d in decisions]
    fraud_mask = [(denied[j]) for j in range(len(denied)) if eval_labels[j] == 1]   # caught?
    legit_denied_mask = [(denied[j]) for j in range(len(denied)) if eval_labels[j] == 0]
    det["recall_bootstrap95"] = bootstrap_rate_ci(fraud_mask)
    det["false_deny_bootstrap95"] = bootstrap_rate_ci(legit_denied_mask)

    return {
        "dataset": A.name, "domain": A.domain, "evidence_level": "Measured Runtime",
        "source_file": rec["relpath"], "rows_loaded": n, "warmup_rows": n_warm,
        "evaluated_rows": len(eval_feats),
        "sampling": A.sampling,
        "prevalence": sum(labels) / n if n else None,
        "prevalence_note": ("UNSW-NB15 is a curated intrusion benchmark with high attack prevalence, "
                            "not a rare-event stream; ULB and IEEE-CIS are natural low-prevalence "
                            "fraud streams" if A.name == "UNSW-NB15" else None),
        "predicates_per_decision": len(A.predicates(feats[0])),
        "predicate_names": [p["name"] for p in A.predicates(feats[0])],
        "calibration": {k: (v if isinstance(v, (int, float, str)) else
                            (sorted(v)[:8] + ["..."] if isinstance(v, set) and len(v) > 8
                             else sorted(v) if isinstance(v, set) else str(v)[:60]))
                        for k, v in A.calib.items()},
        "blindness": ("adapter returns (features, label) separately; label absent from the "
                      "predicate/decision path; opened only in score() after chaining"),
        "permits_issued": permits, "safe_state": len(decisions) - permits,
        "load_seconds": load_s,
        "latency": {"predicate_ms": _stats(pred_lat), "authorization_ms": _stats(auth_lat),
                    "end_to_end_ms": _stats(e2e),
                    "throughput_decisions_per_s": len(decisions) / (sum(e2e) / 1000.0)
                                                  if sum(e2e) else None},
        "evidence": {"ledger_blocks": len(ledger.blocks), "batch_size": 128,
                     "hash_chain_valid": bool(chain_ok), "chain_error": chain_err,
                     "merkle_root_head": ledger.blocks[-1]["merkle_root"] if ledger.blocks else None,
                     "ertuples": len(decisions), "evidence_level": "Derived From Measured"},
        "detection": det,
        "threats_to_validity": [
            "Predicates are unsupervised anomaly bounds calibrated on an unlabeled prefix, not "
            "domain fraud/intrusion features. Results are a floor for governance-predicate "
            "authorization, not a tuned classifier.",
            f"Bounded sample of {len(eval_feats):,} evaluated rows (first-N slice). A time-ordered "
            "distribution shift between prefix and tail would bias the operating point.",
            "Single split, no cross-validation, single host.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    disc = DA.discover()
    if a.only:
        disc = [r for r in disc if r["adapter"] in a.only]
    status = DA.status()

    summaries = []
    for rec in disc:
        print(f"[dataset-eval] {rec['adapter']:10} {rec['relpath']}")
        t0 = time.time()
        try:
            rep = evaluate(rec, a.limit)
        except Exception as ex:  # noqa: BLE001
            import traceback
            rep = {"dataset": rec["adapter"], "status": "FAILED", "error": str(ex),
                   "traceback": traceback.format_exc()[-1500:]}
            print(f"[dataset-eval]   FAILED: {ex}")
        rep["wall_seconds"] = round(time.time() - t0, 2)
        slug = rec["adapter"].lower().replace("-", "_")
        (OUT / f"{slug}_eval.json").write_text(json.dumps(rep, indent=2) + "\n")
        d = rep.get("detection", {})
        if d:
            cm = d["confusion_matrix"]
            print(f"[dataset-eval]   n={rep['evaluated_rows']:,} prev={rep['prevalence']*100:.2f}% "
                  f"| P={_n(d['precision'])} R={_n(d['recall_detection_rate'])} "
                  f"F1={_n(d['f1'])} MCC={_n(d['matthews_corrcoef'])} AUROC={_n(d['auroc'])}")
            print(f"[dataset-eval]   TP={cm['tp_fraud_denied']} FN={cm['fn_fraud_permitted']} "
                  f"FP={cm['fp_legit_denied']} TN={cm['tn_legit_permitted']} "
                  f"| chain_ok={rep['evidence']['hash_chain_valid']}")
        summaries.append({"dataset": rep["dataset"], "domain": rep.get("domain"),
                          "evaluated_rows": rep.get("evaluated_rows"),
                          "prevalence": rep.get("prevalence"),
                          "precision": d.get("precision") if d else None,
                          "recall": d.get("recall_detection_rate") if d else None,
                          "f1": d.get("f1") if d else None,
                          "auroc": d.get("auroc") if d else None,
                          "mcc": d.get("matthews_corrcoef") if d else None,
                          "status": rep.get("status", "EXECUTED"),
                          "evidence_level": rep.get("evidence_level")})

    combined = {
        "experiment": "E12_dataset_independent_blind_evaluation",
        "discovery": status,
        "pipeline": ["discover", "adapter", "calibrate(unlabeled)", "predicate_vector",
                     "gamma_decision", "ertuple", "merkle_ledger", "REVEAL_LABELS",
                     "score+bootstrap"],
        "gamma_untouched": "stress_test.gamma_decision imported and used identically for all datasets",
        "datasets_evaluated": len(summaries),
        "not_found": status["not_found"],
        "summaries": summaries,
    }
    (OUT / "dataset_eval_summary.json").write_text(json.dumps(combined, indent=2) + "\n")
    print(f"[dataset-eval] {len(summaries)} datasets evaluated; wrote {OUT.relative_to(ROOT)}/")
    return 0


def _n(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}f}"


if __name__ == "__main__":
    sys.exit(main())
