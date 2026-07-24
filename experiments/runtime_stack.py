#!/usr/bin/env python3
"""Runtime Predicate Generation Layer + blind detection pipeline (Objectives 1, 2, 3, 7, 8, 9).

WHAT IS REAL HERE
    Every predicate below is COMPUTED from an observable field of the request: a rolling window, a
    registry lookup, a clock comparison, an Ed25519 verification, a sliding-window counter, a
    behaviour baseline, a policy-hash comparison, a great-circle speed. Nothing is read from a
    dataset column that already encodes the answer.

WHAT THE LABEL MAY NEVER TOUCH
    `generate_predicates()` receives an Observation, which structurally cannot carry the label
    (`Observation` has no `label` field; the label lives in a separate sealed vector). The Gamma
    decision is taken, the permit is issued and the ERTuple is chained BEFORE `score()` is called.

GAMMA IS NOT REDEFINED
    The non-compensatory rule is imported from stress_test.gamma_decision() and used unmodified.

EVIDENCE LEVELS
    Measured Runtime      predicate latency, decision latency, crypto verification, lifecycle marks
    Derived From Measured ERTuples, ledger blocks, Merkle roots
    Synthetic Runtime     any detection metric computed over the synthetic stream (--source synthetic)

    The synthetic stream exists because the mapped ULB corpus discarded the observable features
    (V1..V28, Amount) and derives 5 of 12 engine inputs from the label (label_leakage_audit.json).
    Detection metrics over a synthetic stream describe the GENERATOR, not the world. They are
    labelled Synthetic Runtime and are not citable as detection evidence.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import statistics
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stress_test import P, gamma_decision  # published non-compensatory rule, imported unmodified

MEASURED = "Measured Runtime"
DERIVED = "Derived From Measured"
SYNTHETIC = "Synthetic Runtime"
SIMULATED = "Repository Simulation"

# ---- authority keys (real Ed25519; seed is a published test vector, not a credential) -----------
AUTHORITY_SEED = b"L-DREA-runtime-authority-seed-01"


def _signer():
    import nacl.exceptions
    import nacl.signing
    sk = nacl.signing.SigningKey(AUTHORITY_SEED)
    vk = nacl.signing.VerifyKey(bytes(sk.verify_key))
    bad = nacl.exceptions.BadSignatureError

    def verify(msg: bytes, sig: bytes) -> bool:
        try:
            vk.verify(msg, sig)
            return True
        except Exception:
            return False

    return sk, bytes(sk.verify_key), (lambda m: bytes(sk.sign(m).signature)), verify


def sha(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


# ============================================================ observation (no label field, ever)
@dataclass(frozen=True)
class Observation:
    """The ONLY thing the predicate layer may see. There is deliberately no `label` attribute."""
    request_id: str
    subject: str
    device_id: str
    session_id: str
    amount: float
    destination_account: str
    lat: float
    lon: float
    t_wall: float                    # seconds, wall clock as claimed by the caller
    token: str                       # compact JWT-like: b64(header).b64(payload).b64(sig)
    policy_hash_claimed: str


# ============================================================ Objective 1: predicate generators
class RuntimeContext:
    """All state a predicate generator may consult. Learned ONLINE from observations only.

    No label ever enters this object. Baselines are updated after the decision, from the
    observation itself, exactly as a production monitor would.
    """

    def __init__(self, policy_hash: str, verify, authority_pub: bytes, *,
                 daily_cap=25_000.0, velocity_window_s=60.0, velocity_cap=8,
                 freshness_ms=300_000.0, stale_ctx_ms=600_000.0,
                 anomaly_z=6.0, max_kmh=900.0, baseline_min=30):
        self.policy_hash = policy_hash
        self.verify = verify
        self.authority_pub = authority_pub
        self.daily_cap = daily_cap
        self.velocity_window_s = velocity_window_s
        self.velocity_cap = velocity_cap
        self.freshness_ms = freshness_ms
        self.stale_ctx_ms = stale_ctx_ms
        self.anomaly_z = anomaly_z
        self.max_kmh = max_kmh
        self.baseline_min = baseline_min

        self.vendor_registry: set[str] = set()
        self.daily: dict[str, deque] = {}        # subject -> deque[(t, amount)]
        self.velocity: dict[str, deque] = {}     # subject -> deque[t]
        self.amounts: dict[str, deque] = {}      # subject -> deque[amount]  (behaviour baseline)
        self.last_geo: dict[str, tuple] = {}     # subject -> (t, lat, lon)
        self.last_device: dict[str, str] = {}
        self.recent_denials: dict[str, deque] = {}

    # -- individual generators. Each returns (name, passed, detail). All computed, none read. ----
    def _token_valid(self, o: Observation, now: float):
        try:
            h, p, s = o.token.split(".")
            pad = lambda x: x + "=" * (-len(x) % 4)
            payload = json.loads(base64.urlsafe_b64decode(pad(p)))
            sig = base64.urlsafe_b64decode(pad(s))
            msg = f"{h}.{p}".encode()
            if not self.verify(msg, sig):
                return ("TOKEN_VALID", False, "signature verification failed")
            if payload.get("exp", 0) <= now:
                return ("TOKEN_VALID", False, f"expired at {payload['exp']:.3f}")
            if payload.get("sub") != o.subject:
                return ("TOKEN_VALID", False, "subject mismatch")
            return ("TOKEN_VALID", True, "Ed25519 verified, unexpired, subject bound")
        except Exception as e:
            return ("TOKEN_VALID", False, f"malformed token: {type(e).__name__}")

    def _authority_sig(self, o: Observation, now: float):
        try:
            h, p, s = o.token.split(".")
            pad = lambda x: x + "=" * (-len(x) % 4)
            hdr = json.loads(base64.urlsafe_b64decode(pad(h)))
            ok = hdr.get("alg") == "Ed25519" and hdr.get("kid") == b64u(self.authority_pub)[:16]
            return ("AuthoritySignatureValid", bool(ok),
                    "kid bound to authority public key" if ok else "unknown signing authority")
        except Exception:
            return ("AuthoritySignatureValid", False, "unparsable header")

    def _telemetry_fresh(self, o: Observation, now: float):
        age_ms = (now - o.t_wall) * 1000.0
        ok = 0 <= age_ms <= self.freshness_ms
        return ("TelemetryFresh", ok, f"observation age {age_ms:.1f} ms")

    def _stale_context(self, o: Observation, now: float):
        last = self.last_geo.get(o.subject)
        if last is None:
            return ("StaleContext", True, "no prior context (first sighting)")
        age_ms = (now - last[0]) * 1000.0
        ok = age_ms <= self.stale_ctx_ms
        return ("StaleContext", ok, f"context age {age_ms:.1f} ms")

    def _amount_within_daily_limit(self, o: Observation, now: float):
        dq = self.daily.setdefault(o.subject, deque())
        while dq and now - dq[0][0] > 86_400.0:
            dq.popleft()
        rolling = sum(a for _, a in dq) + o.amount
        ok = rolling <= self.daily_cap
        return ("amount_within_daily_limit", ok,
                f"rolling 24h {rolling:.2f} vs cap {self.daily_cap:.2f}")

    def _destination_recognized(self, o: Observation, now: float):
        ok = o.destination_account in self.vendor_registry
        return ("destination_account_recognized", ok,
                f"vendor {'in' if ok else 'absent from'} registry ({len(self.vendor_registry)})")

    def _velocity(self, o: Observation, now: float):
        dq = self.velocity.setdefault(o.subject, deque())
        while dq and now - dq[0] > self.velocity_window_s:
            dq.popleft()
        n = len(dq) + 1
        ok = n <= self.velocity_cap
        return ("velocity_check", ok, f"{n} req / {self.velocity_window_s:.0f}s vs cap {self.velocity_cap}")

    def _behaviour_anomaly(self, o: Observation, now: float):
        hist = self.amounts.get(o.subject)
        if not hist or len(hist) < self.baseline_min:
            return ("behaviour_anomaly", True, f"baseline warming ({len(hist or [])}/{self.baseline_min})")
        med = statistics.median(hist)
        mad = statistics.median([abs(x - med) for x in hist]) or 1e-9
        z = 0.6745 * (o.amount - med) / mad          # robust modified z-score
        ok = z <= self.anomaly_z
        return ("behaviour_anomaly", ok, f"robust z={z:.2f} vs {self.anomaly_z}")

    def _policy_consistency(self, o: Observation, now: float):
        ok = o.policy_hash_claimed == self.policy_hash
        return ("policy_consistency", ok, "policy hash match" if ok else "policy hash divergence")

    def _impossible_travel(self, o: Observation, now: float):
        last = self.last_geo.get(o.subject)
        if last is None:
            return ("impossible_travel_absent", True, "no prior fix")
        t0, la, lo = last
        dt_h = max((now - t0) / 3600.0, 1e-6)
        km = _haversine_km(la, lo, o.lat, o.lon)
        kmh = km / dt_h
        ok = kmh <= self.max_kmh
        return ("impossible_travel_absent", ok, f"{km:.0f} km in {dt_h*3600:.0f}s -> {kmh:.0f} km/h")

    def generate(self, o: Observation, now: float) -> list[dict]:
        """Objective 1. Returns the predicate vector for one observation. Never sees a label."""
        gens = (self._token_valid, self._authority_sig, self._telemetry_fresh, self._stale_context,
                self._amount_within_daily_limit, self._destination_recognized, self._velocity,
                self._behaviour_anomaly, self._policy_consistency, self._impossible_travel)
        return [P(n, ok, d) for n, ok, d in (g(o, now) for g in gens)]

    def observe(self, o: Observation, now: float, denied: bool):
        """Post-decision state update. Uses the observation, never the label."""
        self.daily.setdefault(o.subject, deque()).append((now, o.amount))
        self.velocity.setdefault(o.subject, deque()).append(now)
        h = self.amounts.setdefault(o.subject, deque(maxlen=500))
        h.append(o.amount)
        self.last_geo[o.subject] = (now, o.lat, o.lon)
        self.last_device[o.subject] = o.device_id
        dq = self.recent_denials.setdefault(o.subject, deque(maxlen=50))
        if denied:
            dq.append(now)


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ============================================================ Objective 7: runtime signals
def runtime_signals(o: Observation, ctx: RuntimeContext, now: float) -> dict:
    """Observable, label-free. Signals are advisory context; they do not alter the Gamma decision."""
    lt = time.localtime(o.t_wall)
    dq = ctx.recent_denials.get(o.subject, ())
    vel = ctx.velocity.get(o.subject, ())
    hist = ctx.amounts.get(o.subject, ())
    med = statistics.median(hist) if hist else 0.0
    return {
        "weekend_execution": lt.tm_wday >= 5,
        "outside_business_hours": not (9 <= lt.tm_hour < 17),
        "large_amount": bool(med and o.amount > 10 * med),
        "unknown_destination": o.destination_account not in ctx.vendor_registry,
        "device_mismatch": bool(ctx.last_device.get(o.subject)
                                and ctx.last_device[o.subject] != o.device_id),
        "repeated_failures": len([t for t in dq if now - t <= 300.0]) >= 3,
        "burst_execution": len(vel) >= ctx.velocity_cap,
        "token_age_s": max(0.0, now - o.t_wall),
        "behaviour_drift": bool(hist and med and abs(o.amount - med) / max(med, 1e-9) > 3.0),
        "cross_session_anomaly": bool(ctx.last_device.get(o.subject)
                                      and ctx.last_device[o.subject] != o.device_id
                                      and o.amount > max(med * 5, 1.0)),
    }


# ============================================================ Objective 8: ERTuple v2
@dataclass
class ExecutionTimeline:
    """Objective 3. Every mark is time.perf_counter_ns() taken at the real point in the pipeline."""
    t_received: int = 0
    t_validate: int = 0
    t_predicate: int = 0
    t_authorize: int = 0
    t_issue: int = 0
    t_execute_start: int = 0
    t_execute_finish: int = 0
    t_commit: int = 0
    t_finalize: int = 0
    t_replay: int = 0

    def as_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def spans_ms(self):
        d = self.as_dict()
        keys = list(d)
        return {f"{keys[i]}__{keys[i+1]}": (d[keys[i + 1]] - d[keys[i]]) / 1e6
                for i in range(len(keys) - 1) if d[keys[i + 1]] and d[keys[i]]}


def build_ertuple(*, execution_id, decision, permit, predicates, policy_hash, replay_hash,
                  ledger_hash, timeline: ExecutionTimeline, worker_id, clock_offset_ns,
                  evidence_id, nonce, sign) -> dict:
    body = {
        "execution_id": execution_id,
        "evidence_id": evidence_id,
        "worker_id": worker_id,
        "runtime_predicates": {p["name"]: bool(p["passed"]) for p in predicates},
        "predicate_details": {p["name"]: p["detail"] for p in predicates},
        "gamma": decision["gamma"],
        "decision": decision["decision"],
        "failed_predicates": decision["failed_predicates"],
        "permit_id": (permit or {}).get("permit_id"),
        "policy_hash": policy_hash,
        "replay_hash": replay_hash,
        "ledger_hash": ledger_hash,
        "execution_timestamps": timeline.as_dict(),
        "clock_offset_ns": clock_offset_ns,
        "nonce": nonce,
    }
    body["ertuple_hash"] = sha(body)
    body["signature"] = sign(body["ertuple_hash"].encode()).hex()
    return body


# ============================================================ Objective 9: Merkle hash-chain ledger
def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return "0" * 64
    lvl = list(leaves)
    while len(lvl) > 1:
        if len(lvl) % 2:
            lvl.append(lvl[-1])
        lvl = [hashlib.sha256((lvl[i] + lvl[i + 1]).encode()).hexdigest()
               for i in range(0, len(lvl), 2)]
    return lvl[0]


class Ledger:
    """Append-only, hash-chained, Merkle-rooted. Tamper and fork detection are measured, not asserted."""

    def __init__(self, sign):
        self.blocks: list[dict] = []
        self.sign = sign

    def append(self, ertuples: list[dict]) -> dict:
        prev = self.blocks[-1]["current_hash"] if self.blocks else "0" * 64
        root = merkle_root([e["ertuple_hash"] for e in ertuples])
        body = {
            "chain_index": len(self.blocks),
            "previous_hash": prev,
            "merkle_root": root,
            "execution_ids": [e["execution_id"] for e in ertuples],
            "permit_ids": [e["permit_id"] for e in ertuples],
            "ertuple_hashes": [e["ertuple_hash"] for e in ertuples],
            "policy_hash": ertuples[0]["policy_hash"],
            "replay_hash": sha([e["replay_hash"] for e in ertuples]),
            "evidence_hash": sha([e["evidence_id"] for e in ertuples]),
            "worker_ids": sorted({e["worker_id"] for e in ertuples}),
            "timestamp_ns": time.time_ns(),
        }
        body["current_hash"] = sha(body)
        body["signature"] = self.sign(body["current_hash"].encode()).hex()
        self.blocks.append(body)
        return body

    def verify(self) -> tuple[bool, str | None]:
        prev = "0" * 64
        for b in self.blocks:
            if b["previous_hash"] != prev:
                return False, f"chain break at {b['chain_index']}"
            body = {k: v for k, v in b.items() if k not in ("current_hash", "signature")}
            if sha(body) != b["current_hash"]:
                return False, f"hash mismatch at {b['chain_index']}"
            if merkle_root(b["ertuple_hashes"]) != b["merkle_root"]:
                return False, f"merkle mismatch at {b['chain_index']}"
            prev = b["current_hash"]
        return True, None

    def detect_fork(self, competing: dict) -> bool:
        """A competing block at an existing index with a different hash is a fork."""
        i = competing["chain_index"]
        return i < len(self.blocks) and competing["current_hash"] != self.blocks[i]["current_hash"]


# ============================================================ Objective 2: detection metrics
def _roc_pr(scores, labels):
    """ROC and PR curves over the ordinal Gamma score. No sklearn; nearest-rank, no interpolation."""
    pts = sorted(zip(scores, labels), key=lambda x: -x[0])
    P_ = sum(labels)
    N_ = len(labels) - P_
    if P_ == 0 or N_ == 0:
        return None, None, None, None
    roc, pr = [(0.0, 0.0)], []
    tp = fp = 0
    prev = None
    for s, y in pts:
        if prev is not None and s != prev:
            roc.append((fp / N_, tp / P_))
            pr.append((tp / P_, tp / max(tp + fp, 1)))
        tp += (y == 1); fp += (y == 0)
        prev = s
    roc.append((fp / N_, tp / P_))
    pr.append((tp / P_, tp / max(tp + fp, 1)))
    auroc = sum((roc[i + 1][0] - roc[i][0]) * (roc[i + 1][1] + roc[i][1]) / 2
                for i in range(len(roc) - 1))
    pr_sorted = sorted(pr)
    auprc = sum((pr_sorted[i + 1][0] - pr_sorted[i][0]) *
                (pr_sorted[i + 1][1] + pr_sorted[i][1]) / 2 for i in range(len(pr_sorted) - 1))
    return roc, pr, auroc, auprc


def score(decisions, gammas, labels, *, fp_cost=1.0, fn_cost=20.0, evidence_level=SYNTHETIC):
    """The ONLY place labels are opened. Called after every decision is chained."""
    import metrics_engine as ME
    denied = [d == "SAFE_STATE" for d in decisions]
    tp = sum(1 for d, y in zip(denied, labels) if d and y == 1)
    fn = sum(1 for d, y in zip(denied, labels) if not d and y == 1)
    fp = sum(1 for d, y in zip(denied, labels) if d and y == 0)
    tn = sum(1 for d, y in zip(denied, labels) if not d and y == 0)

    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
    bal = ((rec + spec) / 2) if rec is not None and spec is not None else None
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / den) if den else None
    roc, pr, auroc, auprc = _roc_pr(gammas, labels)

    # calibration: empirical fraud rate per Gamma bucket
    buckets = {}
    for g, y in zip(gammas, labels):
        b = buckets.setdefault(g, [0, 0])
        b[0] += 1; b[1] += (y == 1)
    calib = {str(g): {"n": n, "positives": p, "empirical_rate": p / n}
             for g, (n, p) in sorted(buckets.items())}

    return {
        "evidence_level": evidence_level,
        "confusion_matrix": {"tp_fraud_denied": tp, "fn_fraud_permitted": fn,
                             "fp_legit_denied": fp, "tn_legit_permitted": tn},
        "n": len(labels), "positives": tp + fn, "negatives": tn + fp,
        "precision": prec, "recall_detection_rate": rec, "specificity": spec, "f1": f1,
        "balanced_accuracy": bal, "matthews_corrcoef": mcc,
        "auroc": auroc, "auprc": auprc,
        "roc_curve": roc, "pr_curve": pr,
        "false_permit_rate": ME.compute_false_permit_rate(fn, tp + fn),
        "false_deny_rate": ME.compute_false_deny_rate(fp, tn + fp),
        "recall_wilson95": ME.wilson_ci(tp, tp + fn) if tp + fn else None,
        "precision_wilson95": ME.wilson_ci(tp, tp + fp) if tp + fp else None,
        "calibration_by_gamma": calib,
        "cost_model": {"fp_cost": fp_cost, "fn_cost": fn_cost,
                       "total_cost": fp * fp_cost + fn * fn_cost,
                       "note": "costs are a stated modelling assumption, not a measurement"},
    }


# ============================================================ Permit authority (real enforcement)
class PermitAuthority:
    """Issue / verify / consume / revoke Permit-to-Act tokens. Real Ed25519, real state.

    Every rejection reason below is exercised by an attack in experiments/runtime_attacks.py, and
    a benign control must be ACCEPTED -- otherwise a verifier that refused everything would look
    like a perfect detector.
    """

    ALLOWED_SCOPES = frozenset({"execute:transaction"})

    def __init__(self, sign, verify, key_epoch=1, ttl_s=300.0):
        self.sign, self.verify = sign, verify
        self.key_epoch, self.ttl_s = key_epoch, ttl_s
        self.consumed: set[str] = set()
        self.nonces: set[str] = set()
        self.revoked: set[str] = set()
        self.executions: set[str] = set()

    def _body_msg(self, body):
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()

    def issue(self, permit_id, subject, nonce, policy_hash, now_ns):
        body = {"permit_id": permit_id, "subject": subject, "nonce": nonce,
                "scope": "execute:transaction", "key_epoch": self.key_epoch,
                "policy_hash": policy_hash, "issued_ns": now_ns,
                "expiration_ns": now_ns + int(self.ttl_s * 1e9)}
        return {**body, "signature": self.sign(self._body_msg(body)).hex()}

    def verify_permit(self, permit, now_ns, expect_policy_hash):
        """(accepted, reason). Order matters: consumed is checked before nonce so that a replayed
        permit reports ALREADY_CONSUMED while a fresh permit bearing a spent nonce reports
        NONCE_REUSED."""
        sig = permit.get("signature")
        if not sig:
            return False, "MISSING_SIGNATURE"
        try:
            raw = bytes.fromhex(sig)
        except Exception:
            return False, "MALFORMED_SIGNATURE"
        if len(raw) != 64:
            return False, "MALFORMED_SIGNATURE"
        body = {k: v for k, v in permit.items() if k != "signature"}
        if not self.verify(self._body_msg(body), raw):
            return False, "BAD_SIGNATURE"
        if permit.get("key_epoch") != self.key_epoch:
            return False, "KEY_EPOCH_INACTIVE"
        if permit.get("policy_hash") != expect_policy_hash:
            return False, "POLICY_MISMATCH"
        if permit.get("scope") not in self.ALLOWED_SCOPES:
            return False, "SCOPE_NOT_ALLOWED"
        if now_ns >= permit["expiration_ns"]:
            return False, "EXPIRED"
        if permit["permit_id"] in self.revoked:
            return False, "REVOKED"
        if permit["permit_id"] in self.consumed:
            return False, "ALREADY_CONSUMED"
        if permit["nonce"] in self.nonces:
            return False, "NONCE_REUSED"
        return True, "OK"

    def consume(self, permit, now_ns, expect_policy_hash, execution_id=None):
        ok, reason = self.verify_permit(permit, now_ns, expect_policy_hash)
        if ok and execution_id is not None and execution_id in self.executions:
            return False, "DUPLICATE_EXECUTION"
        if ok:
            self.consumed.add(permit["permit_id"])
            self.nonces.add(permit["nonce"])
            if execution_id is not None:
                self.executions.add(execution_id)
        return ok, reason

    def revoke(self, permit_id):
        self.revoked.add(permit_id)
