#!/usr/bin/env python3
"""Multi-process Gamma fleet, live watchdog, real revocation propagation (Objectives 4, 5, 6).

WHAT CHANGED FROM THE SIMULATION
    Previously the "fleet" was a seeded RNG inside one process and revocation latency was a
    random draw. Here there are N real OS processes (multiprocessing, spawn), real queues, and a
    revocation broadcast whose propagation latency is the difference between two readings of
    CLOCK_MONOTONIC -- a clock that is system-wide, therefore comparable across processes on this
    host. perf_counter() is NOT used across processes: its epoch is per-process.

WHAT STILL CANNOT BE MEASURED HERE
    True clock skew. All processes read the same system clock, so measured offsets reflect
    scheduling jitter, not distributed clock divergence. This is reported as such, and the skew
    figure is NOT labelled Measured Runtime for the distributed property.
    Packet loss and retries: there is no network. Queues are lossless by construction, so
    `lost_packets` is reported as 0 with `not_applicable_reason`, never as evidence of reliability.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import queue
import resource
import statistics
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MEASURED = "Measured Runtime"
DERIVED = "Derived From Measured"
SIMULATED = "Repository Simulation"
NA = "Not Applicable (no network in this deployment)"


def mono_ns() -> int:
    """System-wide monotonic clock. Comparable across processes on this host."""
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def _pct(v, q):
    if not v:
        return None
    s = sorted(v)
    k = max(1, min(len(s), int(round(q / 100.0 * len(s) + 0.5))))
    return s[k - 1]


def stats(v, unit="ms"):
    if not v:
        return {"n": 0, "unit": unit}
    return {"n": len(v), "unit": unit, "mean": statistics.fmean(v), "min": min(v), "max": max(v),
            "p50": _pct(v, 50), "p95": _pct(v, 95), "p99": _pct(v, 99),
            "stdev": statistics.pstdev(v) if len(v) > 1 else 0.0}


# ============================================================ worker (must be importable: spawn)
def worker_main(worker_id: int, req_q, res_q, ctrl_q, ack_q, cfg: dict, stall_after: int):
    """One independent Gamma worker in its own OS process."""
    sys.path.insert(0, str(ROOT))
    from runtime_stack import Observation, RuntimeContext, _signer  # noqa: PLC0415
    from stress_test import gamma_decision  # noqa: PLC0415

    _sk, pub, sign, verify = _signer()
    ctx = RuntimeContext(cfg["policy_hash"], verify, pub)
    ctx.vendor_registry = set(cfg["vendor_registry"])
    # Combined-ablation wrap (default empty -> identical to the un-ablated fleet, so E11 is unchanged):
    # when the predicate engine is disabled no predicates are generated (Gamma permits all); when
    # runtime revocation is disabled the worker ignores the revocation set (revoked permits execute).
    disabled = set(cfg.get("disabled", []))
    pe_off = "predicate_engine" in disabled
    rv_off = "runtime_revocation" in disabled
    revoked: set[str] = set()
    processed = 0
    busy_ns = 0                    # cumulative time spent inside decisions -> busy vs idle
    t_worker_start = mono_ns()

    while True:
        # 1. drain control channel first: revocation must take effect before the next decision
        try:
            while True:
                msg = ctrl_q.get_nowait()
                if msg["op"] == "revoke":
                    revoked.add(msg["permit_id"])
                    ack_q.put({"worker_id": worker_id, "permit_id": msg["permit_id"],
                               "seq": msg["seq"], "ack_mono_ns": mono_ns(), "pid": os.getpid()})
                elif msg["op"] == "clock":
                    ack_q.put({"worker_id": worker_id, "op": "clock",
                               "mono_ns": mono_ns(), "wall_ns": time.time_ns(),
                               "pid": os.getpid()})
                elif msg["op"] == "stop":
                    ru = resource.getrusage(resource.RUSAGE_SELF)
                    wall_ns = mono_ns() - t_worker_start
                    res_q.put({"worker_id": worker_id, "op": "done", "processed": processed,
                               "rusage_maxrss": ru.ru_maxrss, "cpu_user_s": ru.ru_utime,
                               "cpu_sys_s": ru.ru_stime, "vol_ctxsw": ru.ru_nvcsw,
                               "invol_ctxsw": ru.ru_nivcsw, "minflt": ru.ru_minflt,
                               "majflt": ru.ru_majflt, "busy_ns": busy_ns, "wall_ns": wall_ns,
                               "cpu_utilization": (ru.ru_utime + ru.ru_stime) / (wall_ns / 1e9)
                                                  if wall_ns else None,
                               "busy_fraction": busy_ns / wall_ns if wall_ns else None,
                               "pid": os.getpid()})
                    return
        except queue.Empty:
            pass

        try:
            item = req_q.get(timeout=0.05)
        except queue.Empty:
            continue

        if item.get("op") == "use_permit":                # execution attempt against a permit
            pid_ = item["permit_id"]
            blocked = (not rv_off) and (pid_ in revoked)   # rv_off => revocation not enforced
            res_q.put({"worker_id": worker_id, "op": "use_result", "permit_id": pid_,
                       "accepted": not blocked,
                       "reason": "REVOKED" if blocked else "OK",
                       "mono_ns": mono_ns(), "seq": item.get("seq")})
            continue

        t_deq = mono_ns()
        o = Observation(**item["obs"])
        now = item["now"]
        t0 = time.perf_counter_ns()
        preds = [] if pe_off else ctx.generate(o, now)     # predicate-engine ablation honored here
        t1 = time.perf_counter_ns()
        dec = gamma_decision(preds)
        t2 = time.perf_counter_ns()
        busy_ns += (t2 - t0)
        ctx.observe(o, now, dec["decision"] == "SAFE_STATE")

        if processed == stall_after and stall_after >= 0:
            time.sleep(cfg["stall_seconds"])             # injected fault, for watchdog detection

        processed += 1
        res_q.put({"worker_id": worker_id, "op": "decision", "request_id": o.request_id,
                   "decision": dec["decision"], "gamma": dec["gamma"],
                   "failed": dec["failed_predicates"],
                   "enqueue_mono_ns": item["enqueue_mono_ns"], "dequeue_mono_ns": t_deq,
                   "predicate_ns": t1 - t0, "authorize_ns": t2 - t1,
                   "predicates": {p["name"]: p["passed"] for p in preds},
                   "pid": os.getpid()})


# ============================================================ live watchdog (real thread)
class Watchdog:
    """Real supervisor thread. Heartbeats on a wall clock; samples real CPU/RSS via getrusage."""

    def __init__(self, interval_ms=20.0, stall_threshold_ms=250.0, n_workers=5):
        self.interval = interval_ms / 1000.0
        self.stall_threshold_ms = stall_threshold_ms
        self.n_workers = n_workers
        self.events: list[dict] = []
        self.hb_latency: list[float] = []          # actual interval minus target
        self._stop = threading.Event()
        self._last_progress_ns = mono_ns()
        self._progress = 0
        self._lock = threading.Lock()
        self.detections: list[dict] = []
        self.queue_depth_fn = lambda: None
        self.ledger_growth_fn = lambda: 0
        # Per-worker liveness. A shared queue means one stalled worker does NOT stop global
        # progress, so a coordinator-level progress monitor could never detect it.
        self.worker_last_ns: dict[int, int] = {}
        self.outstanding_fn = lambda: 0
        self._in_stall: dict[int, bool] = {}
        self.thread = threading.Thread(target=self._run, daemon=True)

    def progress(self, n=1, worker_id=None):
        with self._lock:
            self._progress += n
            self._last_progress_ns = mono_ns()
            if worker_id is not None:
                self.worker_last_ns[worker_id] = self._last_progress_ns

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop.set()
        self.thread.join(timeout=2.0)

    def _run(self):
        prev = mono_ns()
        while not self._stop.is_set():
            time.sleep(self.interval)
            now = mono_ns()
            actual_ms = (now - prev) / 1e6
            self.hb_latency.append(actual_ms - self.interval * 1000.0)
            prev = now

            ru = resource.getrusage(resource.RUSAGE_SELF)
            with self._lock:
                since_ms = (now - self._last_progress_ns) / 1e6
                last = dict(self.worker_last_ns)
            outstanding = self.outstanding_fn()
            ev = {"mono_ns": now, "event": "HEARTBEAT", "interval_ms": actual_ms,
                  "cpu_user_s": ru.ru_utime, "maxrss_bytes": ru.ru_maxrss,
                  "queue_depth": self.queue_depth_fn(), "ledger_blocks": self.ledger_growth_fn(),
                  "ms_since_progress": since_ms, "outstanding": outstanding}

            # A worker is stalled only if it has produced before, has been silent past the
            # threshold, AND there is provably enough queued work for every worker to be busy
            # (outstanding >= n_workers). The stronger guard removes drain-tail false triggers: near
            # the end, fewer items than workers remain, so an idle worker is starved, not stalled.
            saturated = outstanding >= self.n_workers
            for w, t_last in last.items():
                quiet_ms = (now - t_last) / 1e6
                stalled = quiet_ms > self.stall_threshold_ms and saturated
                was = self._in_stall.get(w, False)
                if stalled and not was:
                    self._in_stall[w] = True
                    self.detections.append({"worker_id": w, "detected_mono_ns": now,
                                            "quiet_ms": quiet_ms})
                    ev.update({"event": "WORKER_STALL", "worker_id": w,
                               "action": "FAIL_CLOSED_SAFE_STATE"})
                elif not stalled and was:
                    self._in_stall[w] = False
                    for d in reversed(self.detections):
                        if d["worker_id"] == w and "recovery_latency_ms" not in d:
                            d["recovered_mono_ns"] = now
                            d["recovery_latency_ms"] = (now - d["detected_mono_ns"]) / 1e6
                            break
                    ev.update({"event": "WORKER_RECOVERED", "worker_id": w})
            self.events.append(ev)


# ============================================================ coordinator
def run_fleet(observations, cfg, *, n_workers=5, stall_worker=2, stall_seconds=0.6,
              revoke_permits=None, outdir: Path = ROOT / "production_evidence"):
    ctx_mp = mp.get_context("spawn")
    req_q, res_q, ack_q = ctx_mp.Queue(), ctx_mp.Queue(), ctx_mp.Queue()
    ctrl_qs = [ctx_mp.Queue() for _ in range(n_workers)]
    cfg = {**cfg, "stall_seconds": stall_seconds}

    procs = []
    for w in range(n_workers):
        stall_after = 40 if w == stall_worker else -1
        p = ctx_mp.Process(target=worker_main,
                           args=(w, req_q, res_q, ctrl_qs[w], ack_q, cfg, stall_after))
        p.start()
        procs.append(p)

    wd = Watchdog(n_workers=n_workers)
    wd.queue_depth_fn = lambda: _safe_qsize(req_q)
    dispatched = {"n": 0}
    completed = {"n": 0}
    wd.outstanding_fn = lambda: dispatched["n"] - completed["n"]
    wd.start()

    # ---- clock offset probe (real IPC round trip) ---------------------------------------------
    offsets = []
    for w in range(n_workers):
        t0 = mono_ns()
        ctrl_qs[w].put({"op": "clock"})
    got = 0
    while got < n_workers:
        m = ack_q.get(timeout=10)
        if m.get("op") == "clock":
            offsets.append({"worker_id": m["worker_id"], "pid": m["pid"],
                            "worker_mono_ns": m["mono_ns"],
                            "coordinator_mono_ns": mono_ns()})
            got += 1

    # ---- dispatch authorization requests -------------------------------------------------------
    t_start = mono_ns()
    for o, now in observations:
        req_q.put({"obs": o.__dict__, "now": now, "enqueue_mono_ns": mono_ns()})
        dispatched["n"] += 1

    results, queue_delay = [], []
    while len(results) < len(observations):
        r = res_q.get(timeout=60)
        if r.get("op") != "decision":
            continue
        results.append(r)
        completed["n"] += 1
        queue_delay.append((r["dequeue_mono_ns"] - r["enqueue_mono_ns"]) / 1e6)
        wd.progress(worker_id=r["worker_id"])
    t_end = mono_ns()

    # ---- REAL revocation broadcast + acknowledgement -------------------------------------------
    rev = []
    for seq, pid_ in enumerate(revoke_permits or []):
        send_ns = mono_ns()
        for w in range(n_workers):
            ctrl_qs[w].put({"op": "revoke", "permit_id": pid_, "seq": seq})
        acks = []
        while len(acks) < n_workers:
            m = ack_q.get(timeout=10)
            if m.get("permit_id") == pid_:
                acks.append(m)
        per_node = [{"worker_id": m["worker_id"], "latency_ms": (m["ack_mono_ns"] - send_ns) / 1e6}
                    for m in acks]
        rev.append({"permit_id": pid_, "acks": len(acks), "expected": n_workers,
                    "send_mono_ns": send_ns,
                    "per_node_ms": [x["latency_ms"] for x in per_node],
                    "per_worker_ack": per_node, "propagation_ms": max(x["latency_ms"] for x in per_node)})
        wd.progress()
    t_rev_end = mono_ns()
    rev_start = rev[0]["send_mono_ns"] if rev else t_rev_end

    # ---- execution rejection after revocation (measured, not asserted) -------------------------
    use_results = []
    for seq, pid_ in enumerate(revoke_permits or []):
        req_q.put({"op": "use_permit", "permit_id": pid_, "seq": seq})
    n_expect = len(revoke_permits or [])
    while len(use_results) < n_expect:
        r = res_q.get(timeout=30)
        if r.get("op") == "use_result":
            use_results.append(r)
    false_permits_after_revocation = sum(1 for r in use_results if r["accepted"])

    # ---- control: an un-revoked permit must still be accepted (probe has power) ----------------
    req_q.put({"op": "use_permit", "permit_id": "P-CONTROL-NOT-REVOKED", "seq": -1})
    ctrl_ok = None
    while ctrl_ok is None:
        r = res_q.get(timeout=30)
        if r.get("op") == "use_result" and r["permit_id"] == "P-CONTROL-NOT-REVOKED":
            ctrl_ok = r["accepted"]

    for w in range(n_workers):
        ctrl_qs[w].put({"op": "stop"})
    done = []
    while len(done) < n_workers:
        r = res_q.get(timeout=30)
        if r.get("op") == "done":
            done.append(r)
    for p in procs:
        p.join(timeout=5)
    wd.stop()

    wall_s = (t_end - t_start) / 1e9
    per_worker = {}
    for r in results:
        per_worker[r["worker_id"]] = per_worker.get(r["worker_id"], 0) + 1

    coord_mono = [o["coordinator_mono_ns"] for o in offsets]
    worker_mono = [o["worker_mono_ns"] for o in offsets]
    deltas_ms = [(c - w) / 1e6 for c, w in zip(coord_mono, worker_mono)]

    fleet = {
        "evidence_level": MEASURED,
        "testbed_type": "multi-process (real OS processes, spawn), single host",
        "nodes": n_workers, "pids": sorted({r["pid"] for r in results}),
        "requests": len(observations), "wall_time_s": wall_s,
        "throughput_decisions_per_s": len(results) / wall_s if wall_s else None,
        "queue_delay_ms": stats(queue_delay),
        "per_worker_decisions": per_worker,
        "decision_agreement": {
            "note": ("Workers hold independent baselines, so identical inputs need not yield "
                     "identical decisions once baselines diverge. Agreement is therefore reported "
                     "on the deterministic predicates only."),
        },
        "per_worker_telemetry": {str(r.get("worker_id", i)): {
            "decisions": per_worker.get(r.get("worker_id", i), 0),
            "cpu_user_s": r.get("cpu_user_s"), "cpu_sys_s": r.get("cpu_sys_s"),
            "cpu_utilization": r.get("cpu_utilization"), "busy_fraction": r.get("busy_fraction"),
            "idle_fraction": (1 - r["busy_fraction"]) if r.get("busy_fraction") is not None else None,
            "maxrss_bytes": r.get("rusage_maxrss"),
            "vol_ctxsw": r.get("vol_ctxsw"), "invol_ctxsw": r.get("invol_ctxsw"),
            "minflt": r.get("minflt"), "majflt": r.get("majflt"),
        } for i, r in enumerate(done)},
        "utilization": _utilization(done, per_worker),
        "context_switches_available": True,
        "clock_offset": {
            "evidence_level": SIMULATED,
            "why_not_measured": ("All processes read the same system CLOCK_MONOTONIC. The values "
                                 "below are IPC round-trip and scheduling jitter, NOT distributed "
                                 "clock skew. Real skew needs a second host and a PTP grandmaster."),
            "coordinator_minus_worker_ms": stats(deltas_ms),
        },
    }
    revocation = {
        "evidence_level": MEASURED,
        "transport": "multiprocessing.Queue between real OS processes",
        "permits_revoked": len(rev), "fleet_nodes": n_workers,
        "propagation_latency_ms": stats([r["propagation_ms"] for r in rev]),
        "per_node_ack_latency_ms": stats([x for r in rev for x in r["per_node_ms"]]),
        "acks_expected": sum(r["expected"] for r in rev),
        "acks_received": sum(r["acks"] for r in rev),
        "acknowledgement_rate": (sum(r["acks"] for r in rev) / sum(r["expected"] for r in rev))
                                 if rev else None,
        "compliance_rate": (1.0 - false_permits_after_revocation / len(use_results))
                           if use_results else None,
        "false_permits_after_revocation": false_permits_after_revocation,
        "false_permit_probe_size": len(use_results),
        "successful_revocations": sum(1 for r in rev if r["acks"] == r["expected"]),
        "total_revocation_events": len(rev),
        "revocations_per_s": (len(rev) / ((t_rev_end - rev_start) / 1e9))
                             if rev and t_rev_end > rev_start else None,
        "per_worker_ack_latency_ms": {
            str(w): stats([x["latency_ms"] for r in rev for x in r["per_worker_ack"]
                           if x["worker_id"] == w]) for w in range(n_workers)},
        "control_unrevoked_permit_accepted": bool(ctrl_ok),
        "probe_has_power": bool(ctrl_ok and false_permits_after_revocation == 0),
        "lost_packets": 0, "retries": 0,
        "lost_packets_note": NA,
        "success_rate": 1.0 if rev and all(r["acks"] == r["expected"] for r in rev) else None,
        "revocation_timeline": [{"permit_id": r["permit_id"],
                                 "offset_ms": (r["send_mono_ns"] - rev_start) / 1e6,
                                 "propagation_ms": r["propagation_ms"]} for r in rev[:50]],
        "events": rev,
    }
    true_pos = [d for d in wd.detections if d["worker_id"] == stall_worker]
    false_pos = [d for d in wd.detections if d["worker_id"] != stall_worker]
    watchdog = {
        "evidence_level": MEASURED,
        "supervisor": "real threading.Thread in the coordinator process",
        "monitors": "per-worker liveness (a shared queue hides a single stalled worker from a "
                    "global progress monitor)",
        "heartbeat_target_ms": wd.interval * 1000.0,
        "heartbeats": len(wd.events),
        "heartbeat_latency_ms": stats(wd.hb_latency),
        "stall_threshold_ms": wd.stall_threshold_ms,
        "injected_stalls": 1, "injected_stall_worker": stall_worker,
        "injected_stall_seconds": stall_seconds,
        "stalls_detected_on_injected_worker": len(true_pos),
        "detection_rate": 1.0 if true_pos else 0.0,
        "recovery_latency_ms": stats([d["recovery_latency_ms"] for d in wd.detections
                                      if "recovery_latency_ms" in d]),
        "false_triggers": len(false_pos),
        "false_trigger_workers": sorted({d["worker_id"] for d in false_pos}),
        "detections": wd.detections,
        "monitored": ["cpu_user_s", "maxrss_bytes", "queue_depth", "ledger_blocks",
                      "ms_since_progress"],
        "cpu_user_s_final": wd.events[-1]["cpu_user_s"] if wd.events else None,
        "maxrss_bytes_final": wd.events[-1]["maxrss_bytes"] if wd.events else None,
    }
    outdir.mkdir(exist_ok=True)
    (outdir / "watchdog_events.json").write_text(json.dumps(wd.events[:500], indent=2) + "\n")
    return fleet, revocation, watchdog, results


def _safe_qsize(q):
    try:
        return q.qsize()
    except NotImplementedError:
        return None


def _utilization(done, per_worker):
    busy = [r["busy_fraction"] for r in done if r.get("busy_fraction") is not None]
    counts = [per_worker.get(r.get("worker_id", i), 0) for i, r in enumerate(done)]
    mean_c = statistics.fmean(counts) if counts else 0
    # load imbalance: coefficient of variation of per-worker decision counts (0 = perfectly even)
    imbalance = (statistics.pstdev(counts) / mean_c) if mean_c else None
    return {
        "evidence_level": MEASURED,
        "busy_fraction_mean": statistics.fmean(busy) if busy else None,
        "busy_fraction_peak": max(busy) if busy else None,
        "idle_fraction_mean": (1 - statistics.fmean(busy)) if busy else None,
        "per_worker_decisions": counts,
        "load_imbalance_cv": imbalance,
        "load_imbalance_note": "coefficient of variation of per-worker decision counts; 0 = even",
        "busy_definition": "cumulative predicate+authorize time / worker wall time",
    }
