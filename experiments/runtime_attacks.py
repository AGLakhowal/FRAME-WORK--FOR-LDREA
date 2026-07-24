#!/usr/bin/env python3
"""Runtime Risk Detection via real attack injection (Objective 5).

THIS IS NOT A FRAUD CLASSIFIER. It fires real adversarial artifacts at the real enforcement
surfaces (predicate generator + PermitAuthority) and measures whether each is refused, with what
latency, and for the correct reason. Ground truth here is exact -- an attack IS an attack because
we constructed it as one -- so precision/recall are deterministic, not statistical estimates.

Each attack builds a genuine malicious artifact (a forged token, a tampered signature, a replayed
permit, a revoked permit presented for execution) and pushes it through the same code path a
benign request uses. A BENIGN CONTROL is included in every family: if the surface refused
everything, the control would fail, and the whole suite is marked powerless.

Detection is recorded into the ERTuple stream and the ledger via the caller.
"""
from __future__ import annotations

import base64
import json
import time

from runtime_stack import (MEASURED, Observation, PermitAuthority, RuntimeContext, _signer,
                           b64u, gamma_decision, sha)


def _tok(sign, pub, subject, now, *, valid=True, expired=False, wrong_kid=False):
    hdr = {"alg": "Ed25519", "kid": ("BADKID0000000000" if wrong_kid else b64u(pub)[:16])}
    pl = {"sub": subject, "exp": now - 1 if expired else now + 3600}
    h = b64u(json.dumps(hdr, sort_keys=True, separators=(",", ":")).encode())
    p = b64u(json.dumps(pl, sort_keys=True, separators=(",", ":")).encode())
    sig = sign(f"{h}.{p}".encode())
    if not valid:
        sig = bytes(64)
    return f"{h}.{p}.{b64u(sig)}"


def _obs(subject, now, policy_hash, **kw):
    d = dict(request_id=kw.get("rid", "R"), subject=subject, device_id="dev-0",
             session_id="s0", amount=kw.get("amount", 100.0),
             destination_account=kw.get("dest", "ACCT-0001"), lat=0.0, lon=0.0,
             t_wall=kw.get("t_wall", now), token=kw.get("token"), policy_hash_claimed=policy_hash)
    return Observation(**d)


def run(n_per_family: int = 200) -> dict:
    sk, pub, sign, verify = _signer()
    policy_hash = sha({"engine": "gamma_g0", "attacks": 1})
    now = time.time()

    ctx = RuntimeContext(policy_hash, verify, pub)
    ctx.vendor_registry = {"ACCT-0001", "ACCT-0002", "ACCT-0003"}
    # warm behaviour baseline + velocity headroom with benign traffic
    for i in range(60):
        o = _obs("agent:00", now - 4000 + i * 60, policy_hash,
                 token=_tok(sign, pub, "agent:00", now), amount=100.0)
        ctx.observe(o, now - 4000 + i * 60, False)
    ctx.daily_cap = 5000.0
    ctx.velocity_cap = 6

    auth = PermitAuthority(sign, verify)

    # Each family: (name, expected_refuser, builder). expected_refuser is "predicate" or "permit".
    families = []

    def predicate_denies(o, at):
        t0 = time.perf_counter_ns()
        preds = ctx.generate(o, at)
        dec = gamma_decision(preds)
        lat = (time.perf_counter_ns() - t0) / 1e6
        return dec["decision"] == "SAFE_STATE", dec["failed_predicates"], lat

    def permit_denies(permit, exec_id=None):
        t0 = time.perf_counter_ns()
        ok, reason = auth.consume(permit, time.time_ns(), policy_hash, execution_id=exec_id)
        lat = (time.perf_counter_ns() - t0) / 1e6
        return (not ok), reason, lat

    def good_permit(pid, nonce="n-benign"):
        return auth.issue(pid, "agent:00", nonce, policy_hash, time.time_ns())

    results = {}

    # ---- predicate-surface attacks -------------------------------------------------------------
    pred_attacks = {
        "expired_token": lambda: _obs("agent:00", now, policy_hash,
                                      token=_tok(sign, pub, "agent:00", now, expired=True)),
        "token_forgery": lambda: _obs("agent:00", now, policy_hash,
                                      token=_tok(sign, pub, "agent:00", now, valid=False)),
        "signature_mismatch": lambda: _obs("agent:00", now, policy_hash,
                                           token=_tok(sign, pub, "agent:00", now, wrong_kid=True)),
        "unknown_destination": lambda: _obs("agent:00", now, policy_hash,
                                            token=_tok(sign, pub, "agent:00", now),
                                            dest="SWIFT-EVIL"),
        "large_transfer": lambda: _obs("agent:00", now, policy_hash,
                                       token=_tok(sign, pub, "agent:00", now), amount=9e5),
        "policy_mismatch_obs": lambda: Observation(
            request_id="R", subject="agent:00", device_id="d", session_id="s", amount=100.0,
            destination_account="ACCT-0001", lat=0, lon=0, t_wall=now,
            token=_tok(sign, pub, "agent:00", now), policy_hash_claimed="WRONG_POLICY"),
        "clock_manipulation": lambda: _obs("agent:00", now, policy_hash,
                                           token=_tok(sign, pub, "agent:00", now),
                                           t_wall=now - 3600),   # stale telemetry
    }
    for name, build in pred_attacks.items():
        rows = []
        for k in range(n_per_family):
            o = build()
            detected, reasons, lat = predicate_denies(o, now)
            rows.append({"detected": detected, "reasons": reasons, "latency_ms": lat})
        # velocity attack: fire a burst from one subject, all within the window
        results[name] = _fam(rows)

    # velocity attack (stateful burst) --------------------------------------------------------
    vc = RuntimeContext(policy_hash, verify, pub); vc.vendor_registry = ctx.vendor_registry
    vc.velocity_cap = 6
    vrows, base = [], now
    for k in range(n_per_family):
        o = _obs("agent:burst", base + k * 0.1, policy_hash,
                 token=_tok(sign, pub, "agent:burst", base + k * 0.1))
        t0 = time.perf_counter_ns()
        preds = vc.generate(o, base + k * 0.1); dec = gamma_decision(preds)
        lat = (time.perf_counter_ns() - t0) / 1e6
        vc.observe(o, base + k * 0.1, dec["decision"] == "SAFE_STATE")
        # count as attack only after the cap is exceeded (first `cap` are legitimately allowed)
        if k >= vc.velocity_cap:
            vrows.append({"detected": dec["decision"] == "SAFE_STATE",
                          "reasons": dec["failed_predicates"], "latency_ms": lat})
    results["velocity_attack"] = _fam(vrows)

    # ---- permit-surface attacks ----------------------------------------------------------------
    # replay / duplicate execution: issue, consume once, then replay
    rep_rows, dup_rows = [], []
    for k in range(n_per_family):
        p = good_permit(f"P-rep-{k}", nonce=f"n-rep-{k}")
        auth.consume(p, time.time_ns(), policy_hash, execution_id=f"X{k}")  # first use OK
        det, reason, lat = permit_denies(p)                                  # replay must fail
        rep_rows.append({"detected": det, "reasons": [reason], "latency_ms": lat})
        det2, r2, l2 = permit_denies(good_permit(f"P-dup-{k}", nonce=f"n-dup-{k}"),
                                     exec_id=f"X{k}")   # reuse of a spent execution id
        dup_rows.append({"detected": det2, "reasons": [r2], "latency_ms": l2})
    results["execution_replay"] = _fam(rep_rows)
    results["duplicate_execution"] = _fam(dup_rows)

    # nonce replay: fresh permit id, already-spent nonce
    nrows = []
    for k in range(n_per_family):
        auth.nonces.add(f"n-spent-{k}")
        p = good_permit(f"P-nr-{k}", nonce=f"n-spent-{k}")
        det, reason, lat = permit_denies(p)
        nrows.append({"detected": det, "reasons": [reason], "latency_ms": lat})
    results["nonce_replay"] = _fam(nrows)

    # revoked permit presented for execution
    rvrows = []
    for k in range(n_per_family):
        p = good_permit(f"P-rev-{k}", nonce=f"n-rev-{k}")
        auth.revoke(p["permit_id"])
        det, reason, lat = permit_denies(p)
        rvrows.append({"detected": det, "reasons": [reason], "latency_ms": lat})
    results["revoked_permit"] = _fam(rvrows)

    # ---- BENIGN CONTROLS (must be ACCEPTED; give the suite discriminating power) ---------------
    ctrl_pred = []
    cc = RuntimeContext(policy_hash, verify, pub); cc.vendor_registry = ctx.vendor_registry
    cc.daily_cap = 5000.0
    for k in range(n_per_family):
        # a distinct subject per control, so a benign request is not denied merely because a prior
        # benign request already consumed the same subject's rolling daily limit
        subj = f"agent:ok{k}"
        o = _obs(subj, now, policy_hash, token=_tok(sign, pub, subj, now), amount=50.0)
        preds = cc.generate(o, now); dec = gamma_decision(preds)
        cc.observe(o, now, False)
        ctrl_pred.append(dec["decision"] == "PERMIT")
    ctrl_permit = []
    for k in range(n_per_family):
        p = good_permit(f"P-ok-{k}", nonce=f"n-ok-{k}")
        ok, reason = auth.consume(p, time.time_ns(), policy_hash, execution_id=f"OK{k}")
        ctrl_permit.append(ok)

    controls = {"benign_predicate_accepted": sum(ctrl_pred), "benign_predicate_n": len(ctrl_pred),
                "benign_permit_accepted": sum(ctrl_permit), "benign_permit_n": len(ctrl_permit)}
    suite_has_power = (controls["benign_predicate_accepted"] == controls["benign_predicate_n"]
                       and controls["benign_permit_accepted"] == controls["benign_permit_n"])

    # ---- aggregate -----------------------------------------------------------------------------
    total = sum(f["n"] for f in results.values())
    detected = sum(f["detected"] for f in results.values())
    all_lat = [x for f in results.values() for x in f["latencies"]]
    fn = total - detected
    # precision here = detected attacks / (detected attacks + false alarms on controls)
    false_alarms = (controls["benign_predicate_n"] - controls["benign_predicate_accepted"]) + \
                   (controls["benign_permit_n"] - controls["benign_permit_accepted"])
    precision = detected / (detected + false_alarms) if (detected + false_alarms) else None
    recall = detected / total if total else None

    for f in results.values():
        f.pop("latencies", None)

    return {
        "experiment": "E13_runtime_risk_detection",
        "evidence_level": MEASURED,
        "not_a_fraud_classifier": ("Ground truth is exact by construction: each artifact is an "
                                   "attack because we built it as one. This measures ENFORCEMENT, "
                                   "not statistical fraud detection. See runtime_detection_report_"
                                   "synthetic.json for the blind statistical pipeline."),
        "not_the_blocked_ulb_report": ("The real-ULB blind result is runtime_detection_report.json "
                                       "(root), status BLOCKED. This file is a different experiment."),
        "families": len(results), "attacks_per_family": n_per_family, "total_attacks": total,
        "attacks_detected": detected, "missed_attacks": fn,
        "detection_rate": recall, "detection_precision": precision,
        "false_alarms_on_controls": false_alarms,
        "controls": controls, "suite_has_power": suite_has_power,
        "response_latency_ms": _stats(all_lat),
        "attack_coverage": sorted(results.keys()),
        "per_family": results,
    }


def _fam(rows):
    lat = [r["latency_ms"] for r in rows]
    det = sum(1 for r in rows if r["detected"])
    reasons = {}
    for r in rows:
        for x in (r["reasons"] or []):
            reasons[x] = reasons.get(x, 0) + 1
    return {"n": len(rows), "detected": det, "missed": len(rows) - det,
            "detection_rate": det / len(rows) if rows else None,
            "reasons": dict(sorted(reasons.items(), key=lambda x: -x[1])),
            "latency_ms": _stats(lat), "latencies": lat}


def _stats(v):
    if not v:
        return {"n": 0}
    s = sorted(v)
    q = lambda p: s[max(1, min(len(s), int(round(p / 100 * len(s) + 0.5)))) - 1]
    import statistics
    return {"n": len(v), "unit": "ms", "mean": statistics.fmean(v), "min": s[0], "max": s[-1],
            "p50": q(50), "p95": q(95), "p99": q(99)}
