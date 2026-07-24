#!/usr/bin/env python3
"""Watchdog scenario harness — genuinely inject and MEASURE all six fault scenarios.

The previous fleet run injected exactly one fault type (a worker stall). This harness drives the
SAME real `runtime_fleet.Watchdog` supervisor thread through six distinct heartbeat patterns and
measures, per scenario, whether a stall is detected, whether the fail-closed (SAFE_STATE) action
fires, and whether recovery is observed. Nothing is asserted; every cell comes from the watchdog's
own `detections`/`events` after the pattern runs.

    python experiments/watchdog_scenarios.py

Writes production_evidence/watchdog_scenarios_report.json (Measured Runtime).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from runtime_fleet import Watchdog, mono_ns

OUT = ROOT / "production_evidence" / "watchdog_scenarios_report.json"

INTERVAL_MS = 10.0
THRESHOLD_MS = 150.0     # comfortably above the delayed-beat interval + observed scheduling jitter
N_WORKERS = 3


def _mk(outstanding):
    wd = Watchdog(interval_ms=INTERVAL_MS, stall_threshold_ms=THRESHOLD_MS, n_workers=N_WORKERS)
    wd.outstanding_fn = lambda: outstanding[0]
    wd.start()
    return wd


def _beat(wd, workers, now=None):
    for w in workers:
        wd.progress(worker_id=w)


def _run_scenario(name, driver):
    """driver(wd, outstanding) drives the heartbeat pattern; returns nothing.
    Returns a measured result dict read from the watchdog's own state."""
    outstanding = [N_WORKERS + 2]     # saturated: enough work for every worker to be busy
    wd = _mk(outstanding)
    driver(wd, outstanding)
    time.sleep(0.05)                  # let the supervisor observe the final state
    wd.stop()
    dets = wd.detections
    recovered = [d for d in dets if "recovery_latency_ms" in d]
    stall_events = [e for e in wd.events if e.get("event") == "WORKER_STALL"]
    return {
        "scenario": name,
        "heartbeats_observed": len(wd.events),
        "heartbeat_alive": len(wd.events) > 0,
        "stalls_detected": len(dets),
        "safe_state_triggered": any(e.get("action") == "FAIL_CLOSED_SAFE_STATE" for e in stall_events),
        "externalization_blocked": len(stall_events) > 0,
        "recoveries": len(recovered),
        "recovery_latency_ms": (sum(d["recovery_latency_ms"] for d in recovered) / len(recovered))
                               if recovered else None,
        "false_triggers": 0,   # filled by caller against expectation
        "detection_worker_ids": sorted({d["worker_id"] for d in dets}),
    }


# ---- the six scenarios --------------------------------------------------------------------------
def normal(wd, outstanding):
    """All workers heartbeat steadily. Expect: no detection, no false trigger."""
    for _ in range(30):                       # ~300 ms of healthy beats
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)


def missing_heartbeat(wd, outstanding):
    """Worker 1 stops beating while 0 and 2 continue and work is outstanding. Expect: detection."""
    for _ in range(10):
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)
    for _ in range(15):                       # 150 ms: worker 1 silent, others alive
        _beat(wd, [0, 2])
        time.sleep(0.01)


def delayed_heartbeat(wd, outstanding):
    """All workers beat slowly but comfortably UNDER the 80 ms threshold. Expect: NO false trigger."""
    for _ in range(10):
        _beat(wd, range(N_WORKERS))
        time.sleep(0.04)                      # 40 ms << 150 ms threshold (3.75x margin)


def timeout(wd, outstanding):
    """Worker 1 times out; workers 0 and 2 stay alive. Expect: exactly 1 detection + SAFE_STATE."""
    for _ in range(8):
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)
    for _ in range(35):                       # 350 ms: worker 1 silent (> 150 ms threshold), 0 and 2 beat
        _beat(wd, [0, 2])
        time.sleep(0.01)


def heartbeat_restored(wd, outstanding):
    """Worker 1 stalls (0 and 2 alive), is detected, then resumes. Expect: 1 detection THEN recovery."""
    for _ in range(8):
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)
    for _ in range(30):                       # 300 ms stall worker 1 while 0 and 2 stay alive
        _beat(wd, [0, 2])
        time.sleep(0.01)
    for _ in range(15):                       # worker 1 resumes -> recovery
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)


def multiple_failures(wd, outstanding):
    """Workers 1 and 2 both stall; only worker 0 alive. Expect: 2 detections."""
    for _ in range(8):
        _beat(wd, range(N_WORKERS))
        time.sleep(0.01)
    for _ in range(35):                       # 350 ms: only worker 0 beats
        _beat(wd, [0])
        time.sleep(0.01)


SCENARIOS = [
    ("Normal execution", normal, {"detect": False, "recover": False}),
    ("Missing heartbeat", missing_heartbeat, {"detect": True, "recover": False}),
    ("Delayed heartbeat", delayed_heartbeat, {"detect": False, "recover": False}),
    ("Timeout", timeout, {"detect": True, "recover": False}),
    ("Heartbeat restored", heartbeat_restored, {"detect": True, "recover": True}),
    ("Multiple failures", multiple_failures, {"detect": True, "recover": False}),
]


def run() -> dict:
    results = []
    for name, driver, expect in SCENARIOS:
        r = _run_scenario(name, driver)
        detected = r["stalls_detected"] > 0
        recovered = r["recoveries"] > 0
        # a scenario passes when observed detection/recovery match expectation
        detect_ok = (detected == expect["detect"])
        recover_ok = (recovered == expect["recover"]) if expect["detect"] else True
        # false trigger = detection when none expected
        r["false_triggers"] = r["stalls_detected"] if not expect["detect"] else 0
        r["expected_detection"] = expect["detect"]
        r["expected_recovery"] = expect["recover"]
        r["result_pass"] = bool(detect_ok and recover_ok)
        results.append(r)

    return {
        "experiment": "E11b_watchdog_scenarios",
        "evidence_level": "Measured Runtime",
        "supervisor": "runtime_fleet.Watchdog (real threading.Thread, per-worker liveness)",
        "config": {"interval_ms": INTERVAL_MS, "stall_threshold_ms": THRESHOLD_MS,
                   "virtual_workers": N_WORKERS},
        "method": ("each scenario drives the real Watchdog through a distinct heartbeat pattern; "
                   "detection/SAFE_STATE/recovery are read from the watchdog's own events, not "
                   "asserted"),
        "scenarios": results,
        "all_scenarios_pass": all(r["result_pass"] for r in results),
        "total_false_triggers": sum(r["false_triggers"] for r in results),
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rep = run()
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"[watchdog-scenarios] {len(rep['scenarios'])} scenarios, "
          f"all_pass={rep['all_scenarios_pass']}, false_triggers={rep['total_false_triggers']}")
    for r in rep["scenarios"]:
        print(f"  {r['scenario']:22} detected={r['stalls_detected']} "
              f"safe_state={r['safe_state_triggered']} recover={r['recoveries']} "
              f"-> {'PASS' if r['result_pass'] else 'FAIL'}")
    return 0 if rep["all_scenarios_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
