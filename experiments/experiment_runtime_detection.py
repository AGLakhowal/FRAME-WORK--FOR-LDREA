#!/usr/bin/env python3
"""E11 — Blind runtime authorization from observable predicates (Objective C).

THE CLAIM THIS EXPERIMENT SUPPORTS
    L-DREA can make a runtime authorization decision using ONLY observable runtime predicates,
    with the ground-truth label withheld until after the decision is committed. The decision is
    then compared against ground truth for evaluation.

THE CLAIM IT DOES NOT SUPPORT
    That L-DREA is a fraud-detection model. It is an authorization and governance framework. The
    quality of the decision is bounded by the quality of the predicates it is given.

WHY THIS EXPERIMENT EXISTS
    experiments/audit_label_leakage.py proves that the mapped corpus
    (GAMMA_G0_CREDITCARD_FULL_mapped.csv) constructs 5 of the engine's 12 inputs directly from the
    label: gamma_map_raw.py writes "Class == 1 -> HARM_RISK high, Gate_A3 & Gate_A7 & Lambda_G
    fail" and embeds CLASS_1 verbatim in ReasonCodes. Authorization accuracy on that corpus is a
    CONFORMANCE result (the monitor enforces the predicates it is handed), not a DETECTION result.
    This experiment removes the leak.

BLINDNESS IS STRUCTURALLY ENFORCED, NOT PROMISED
    `_observable()` strips Class. `_decide()` asserts Class is absent from every row it sees and
    raises LabelLeak otherwise. Thresholds are calibrated on an unlabeled prefix using quantiles
    only; no label is read during calibration. Labels are opened exactly once, in `_score()`, after
    every decision has been committed to the ledger.

EVIDENCE LEVEL
    Measured Runtime — real decisions over real inputs, with a hash-chained ledger and replay check.
    Requires the raw ULB dataset (Time, V1..V28, Amount, Class). If it is absent this program
    refuses to run and writes a BLOCKED report containing no metrics.

    python experiments/experiment_runtime_detection.py --raw creditcard.csv
    python experiments/experiment_runtime_detection.py --selftest     # synthetic, clearly labeled
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import metrics_engine as ME  # reused: Wilson CIs, FPR/FDR/accuracy definitions

RAW_DEFAULT = ROOT / "creditcard.csv"
OUT = ROOT / "runtime_detection_report.json"
LEDGER = ROOT / "runtime_detection_ledger.jsonl"
SELFTEST_OUT = ROOT / "runtime_detection_selftest_synthetic.json"

V_COLS = [f"V{i}" for i in range(1, 29)]
CAL_FRACTION = 0.20          # unlabeled calibration prefix
Q = 0.999                    # predicate threshold quantile
VELOCITY_WINDOW_S = 60.0


class LabelLeak(RuntimeError):
    """Raised if the ground-truth label reaches the decision path. Fails closed, loudly."""


# ----------------------------------------------------------------------------- predicates
def _calibrate(cal: np.ndarray, amounts: np.ndarray, times: np.ndarray) -> dict:
    """Unsupervised. Quantiles of observable statistics. No label is read here."""
    norms = np.linalg.norm(cal, axis=1)
    maxabs = np.abs(cal).max(axis=1)
    # trailing-window transaction velocity on the calibration prefix
    vel = _velocity(times)
    return {
        "amount_cap": float(np.quantile(amounts, Q)),
        "pca_norm_cap": float(np.quantile(norms, Q)),
        "max_component_cap": float(np.quantile(maxabs, Q)),
        "velocity_cap": float(np.quantile(vel, Q)),
        "calibration_rows": int(cal.shape[0]),
        "quantile": Q,
        "method": "unsupervised quantiles over an unlabeled prefix; Class is never read",
    }


def _velocity(times: np.ndarray) -> np.ndarray:
    """Count of transactions in the trailing VELOCITY_WINDOW_S seconds. Observable, label-free."""
    lo = np.searchsorted(times, times - VELOCITY_WINDOW_S, side="left")
    return (np.arange(times.size) - lo).astype(float)


def _observable(v_row, amount, t, vel):
    """The ONLY view the decision path is given. Class is structurally absent."""
    return {"v": v_row, "Amount": float(amount), "Time": float(t), "velocity": float(vel)}


def _decide(obs: dict, cal: dict) -> dict:
    """Non-compensatory Law of Concurrence over observable predicates. Γ = number of deficits."""
    if "Class" in obs:
        raise LabelLeak("ground-truth label reached the decision path")

    v = obs["v"]
    preds = [
        ("amount_within_calibrated_cap", obs["Amount"] <= cal["amount_cap"]),
        ("pca_anomaly_within_bound", float(np.linalg.norm(v)) <= cal["pca_norm_cap"]),
        ("no_extreme_component", float(np.abs(v).max()) <= cal["max_component_cap"]),
        ("velocity_within_baseline", obs["velocity"] <= cal["velocity_cap"]),
    ]
    failed = [n for n, ok in preds if not ok]
    gamma = len(failed)                       # non-compensatory: a single deficit denies
    return {"gamma": gamma,
            "decision": "PERMIT" if gamma == 0 else "SAFE_STATE",
            "failed_predicates": failed,
            "predicate_vector": {n: bool(ok) for n, ok in preds}}


# ----------------------------------------------------------------------------- evidence
def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _ertuple(idx, dec, obs, policy_version, t_marks):
    """Evidence Runtime Tuple. Every field is produced by this run; none is simulated."""
    body = {
        "decision_id": f"D{idx:08d}",
        "predicate_vector": dec["predicate_vector"],
        "gamma": dec["gamma"],
        "decision": dec["decision"],
        "policy_version": policy_version,
        "observable_digest": _sha({"Amount": obs["Amount"], "Time": obs["Time"],
                                   "velocity": obs["velocity"]}),
        "timestamps": t_marks,
    }
    body["ertuple_hash"] = _sha(body)
    return body


# ----------------------------------------------------------------------------- scoring
def _score(decisions, labels) -> dict:
    """The ONLY place labels are opened. Every decision is already committed."""
    dec = np.array([d == "SAFE_STATE" for d in decisions])   # True = denied
    y = labels.astype(bool)                                   # True = fraud

    n_fraud, n_legit = int(y.sum()), int((~y).sum())
    fraud_permitted = int((y & ~dec).sum())    # false permit
    fraud_denied = int((y & dec).sum())        # true positive
    legit_denied = int((~y & dec).sum())       # false deny
    legit_permitted = int((~y & ~dec).sum())

    correct = fraud_denied + legit_permitted
    fpr = ME.compute_false_permit_rate(fraud_permitted, n_fraud)
    fdr = ME.compute_false_deny_rate(legit_denied, n_legit)
    acc = ME.compute_authorization_accuracy(correct, len(decisions))
    dr = ME.wilson_ci(fraud_denied, n_fraud)
    prec_den = fraud_denied + legit_denied
    return {
        "n_decisions": len(decisions),
        "confusion_matrix": {
            "fraud_denied_true_positive": fraud_denied,
            "fraud_permitted_false_permit": fraud_permitted,
            "legit_denied_false_deny": legit_denied,
            "legit_permitted_true_negative": legit_permitted,
        },
        "n_fraud": n_fraud, "n_legit": n_legit,
        "authorization_accuracy": acc,
        "false_permit_rate": fpr,
        "false_deny_rate": fdr,
        "detection_rate_recall": {"value": dr["p"], "wilson95": dr,
                                  "n": n_fraud, "successes": fraud_denied},
        "precision_of_denial": {"value": (fraud_denied / prec_den) if prec_den else None,
                                "n_denied": prec_den,
                                "note": None if prec_den else "no denials issued"},
    }


# ----------------------------------------------------------------------------- driver
def run_blind(times, vmat, amounts, labels, *, source, evidence_level, write_ledger):
    order = np.argsort(times, kind="stable")
    times, vmat, amounts, labels = times[order], vmat[order], amounts[order], labels[order]

    n = times.size
    n_cal = int(n * CAL_FRACTION)
    vel_all = _velocity(times)

    t0 = time.perf_counter()
    cal = _calibrate(vmat[:n_cal], amounts[:n_cal], times[:n_cal])
    cal_ms = (time.perf_counter() - t0) * 1000.0
    policy_version = _sha(cal)[:16]

    decisions, gammas, ledger, lat = [], [], [], []
    prev_hash = "0" * 64
    for i in range(n_cal, n):
        received = time.perf_counter()
        obs = _observable(vmat[i], amounts[i], times[i], vel_all[i])
        ev_start = time.perf_counter()
        dec = _decide(obs, cal)                     # <-- label is not in scope here
        ev_finish = time.perf_counter()

        marks = {"received_time_ns": int(received * 1e9),
                 "evaluation_start_ns": int(ev_start * 1e9),
                 "evaluation_finish_ns": int(ev_finish * 1e9)}
        er = _ertuple(i, dec, obs, policy_version, marks)
        cur = _sha({"prev": prev_hash, "ertuple": er["ertuple_hash"]})
        ledger.append({"chain_index": len(ledger), "previous_hash": prev_hash,
                       "current_hash": cur, "ertuple_hash": er["ertuple_hash"],
                       "decision": dec["decision"], "gamma": dec["gamma"]})
        prev_hash = cur

        decisions.append(dec["decision"])
        gammas.append(dec["gamma"])
        lat.append((ev_finish - ev_start) * 1000.0)

    # --- the label is opened only now, after every decision is chained -----------------
    scored = _score(decisions, labels[n_cal:])

    chain_ok = True
    ph = "0" * 64
    for blk in ledger:
        exp = _sha({"prev": ph, "ertuple": blk["ertuple_hash"]})
        chain_ok &= (exp == blk["current_hash"] and blk["previous_hash"] == ph)
        ph = blk["current_hash"]

    if write_ledger:
        LEDGER.write_text("".join(json.dumps(b) + "\n" for b in ledger))

    gd = {}
    for g in gammas:
        gd[str(g)] = gd.get(str(g), 0) + 1

    return {
        "experiment": "E11_blind_runtime_detection",
        "evidence_level": evidence_level,
        "source_dataset": source,
        "claim_supported": ("L-DREA makes runtime authorization decisions from observable predicates "
                            "alone; the decision is committed before the label is revealed."),
        "claim_not_supported": ("That L-DREA is a fraud-detection model. Decision quality is bounded "
                                "by predicate quality; this is a governance framework."),
        "blindness_enforcement": ("_decide() raises LabelLeak if 'Class' is present. Calibration is "
                                  "unsupervised (quantiles). Labels are opened once, in _score(), "
                                  "after every decision is hash-chained."),
        "separation_of_concerns": {
            "runtime_detection": "this report — decisions from observable predicates, label withheld",
            "oracle_replay": "E1 — decisions from label-derived predicates (see label_leakage_audit.json)",
            "benchmark_conformance": "E2/E3/E9 — replay, formal verification, predicate coverage",
        },
        "calibration": cal,
        "calibration_ms": cal_ms,
        "policy_version": policy_version,
        "gamma_distribution": gd,
        "latency_ms": ME.compute_latency(lat),
        "results": scored,
        "evidence": {
            "ertuples_emitted": len(ledger),
            "ledger_blocks": len(ledger),
            "ledger_file": LEDGER.name if write_ledger else None,
            "hash_chain_valid": bool(chain_ok),
            "chain_head": ledger[-1]["current_hash"] if ledger else None,
            "replay_verified": bool(chain_ok),
        },
        "threats_to_validity": [
            "Thresholds are calibrated on an unlabeled PREFIX; the corpus is time-ordered, so a "
            "distribution shift between prefix and tail would bias the operating point.",
            "The fraud prevalence is 0.17%, so the calibration quantiles are dominated by legitimate "
            "traffic. This is intended, but it means the operating point is not tuned for recall.",
            "Predicates are generic anomaly bounds, not domain fraud features. A production "
            "deployment would supply domain predicates; results here are a floor, not a ceiling.",
            "Single dataset, single split. No cross-validation and no external replication.",
        ],
    }


def _load_raw(path: Path):
    import pandas as pd
    df = pd.read_csv(path)
    missing = [c for c in (["Time", "Amount", "Class"] + V_COLS) if c not in df.columns]
    if missing:
        raise SystemExit(f"raw dataset missing columns: {missing[:6]}")
    return (df["Time"].to_numpy(float), df[V_COLS].to_numpy(float),
            df["Amount"].to_numpy(float), df["Class"].to_numpy(int))


def _synthetic(n=60000, seed=7):
    """Clearly-labeled SYNTHETIC stream. Used only to prove the harness runs end-to-end."""
    rng = np.random.default_rng(seed)
    times = np.sort(rng.uniform(0, 172800, n))
    v = rng.normal(0, 1, (n, 28))
    amount = np.abs(rng.lognormal(3.0, 1.1, n))
    y = np.zeros(n, dtype=int)
    idx = rng.choice(n, size=max(1, int(n * 0.0017)), replace=False)
    y[idx] = 1
    v[idx] += rng.normal(0, 3.2, (idx.size, 28))     # anomalous components
    amount[idx] *= rng.uniform(2, 12, idx.size)
    return times, v, amount, y


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(RAW_DEFAULT))
    ap.add_argument("--selftest", action="store_true",
                    help="run on a clearly-labeled synthetic stream (does NOT write the real report)")
    a = ap.parse_args()

    if a.selftest:
        rep = run_blind(*_synthetic(), source="SYNTHETIC (generated in-process, seed=7)",
                        evidence_level="Synthetic Runtime — NOT benchmark evidence, NOT production "
                                       "evidence. Exists solely to prove this harness executes "
                                       "end-to-end. No scientific claim may cite these numbers.",
                        write_ledger=False)
        SELFTEST_OUT.write_text(json.dumps(rep, indent=2) + "\n")
        r = rep["results"]
        print(f"[selftest/SYNTHETIC] n={r['n_decisions']:,} "
              f"recall={r['detection_rate_recall']['value']:.3f} "
              f"FPR={r['false_permit_rate']['value']:.4f} "
              f"FDR={r['false_deny_rate']['value']:.4f} "
              f"chain_ok={rep['evidence']['hash_chain_valid']}")
        print(f"[selftest/SYNTHETIC] wrote {SELFTEST_OUT.name} — synthetic, not citable")
        return 0

    raw = Path(a.raw)
    if not raw.exists():
        blocked = {
            "experiment": "E11_blind_runtime_detection",
            "status": "BLOCKED",
            "evidence_level": "Not executed",
            "reason": (f"raw ULB dataset not found at {raw.name}. Blind runtime detection requires "
                       "the observable features (Time, V1..V28, Amount) with Class withheld."),
            "why_the_mapped_corpus_cannot_be_used": (
                "GAMMA_G0_CREDITCARD_FULL_mapped.csv discarded V1..V28 and Amount, and constructs 5 "
                "of the engine's 12 inputs from the label (see label_leakage_audit.json). Running "
                "this experiment on it would measure the label, not the features."),
            "metrics": None,
            "to_unblock": f"place creditcard.csv at {raw} and re-run this program",
        }
        OUT.write_text(json.dumps(blocked, indent=2) + "\n")
        print(f"[runtime-detection] BLOCKED — {raw.name} not present. Wrote {OUT.name} with no metrics.")
        print("[runtime-detection] no numbers were invented.")
        return 0

    rep = run_blind(*_load_raw(raw), source=raw.name, evidence_level="Measured Runtime",
                    write_ledger=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    r = rep["results"]
    print(f"[runtime-detection] n={r['n_decisions']:,} fraud={r['n_fraud']} legit={r['n_legit']:,}")
    print(f"[runtime-detection] recall={r['detection_rate_recall']['value']:.4f} "
          f"FPR={r['false_permit_rate']['value']:.4f} FDR={r['false_deny_rate']['value']:.4f}")
    print(f"[runtime-detection] chain_valid={rep['evidence']['hash_chain_valid']} "
          f"blocks={rep['evidence']['ledger_blocks']:,}")
    print(f"[runtime-detection] wrote {OUT.name}, {LEDGER.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
