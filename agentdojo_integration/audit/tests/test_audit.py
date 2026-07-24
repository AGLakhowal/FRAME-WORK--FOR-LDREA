"""Unit tests for the deterministic audit modules (no LLM, no network).

Run: agentdojo_integration/.venv/bin/python agentdojo_integration/audit/tests/test_audit.py
"""
import json
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))

from agentdojo_integration.audit import _util, integrity, replay_engine, stats_engine

FAILS = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def test_util_stats():
    print("=== _util statistics ===")
    w = _util.wilson_ci(5, 10)
    check("wilson midpoint ~0.5", abs(w["p"] - 0.5) < 1e-9 and w["low"] < 0.5 < w["high"])
    check("wilson n=0 safe", _util.wilson_ci(0, 0)["p"] is None)
    b = _util.bootstrap_ci([1.0, 1.0, 1.0, 1.0])
    check("bootstrap constant -> tight CI", b["low"] == 1.0 and b["high"] == 1.0)
    b2a = _util.bootstrap_ci([1, 2, 3, 4, 5], seed=7)
    b2b = _util.bootstrap_ci([1, 2, 3, 4, 5], seed=7)
    check("bootstrap deterministic (fixed seed)", b2a == b2b)
    d = _util.describe([1, 2, 3, 4])
    check("describe median=2.5 iqr=1.5", d["median"] == 2.5 and abs(d["iqr"] - 1.5) < 1e-9)
    check("entropy of 50/50 == 1 bit", abs(_util.shannon_entropy([5, 5]) - 1.0) < 1e-9)
    check("entropy of pure == 0", _util.shannon_entropy([10, 0]) == 0.0)


# a synthetic but STRUCTURALLY REAL trace (same schema the tracer emits) for deterministic tests
def _synthetic_trace(tmp: Path):
    events = [
        {"event_id": "evt-000001", "episode_id": "t", "timestamp": "2026-07-09T00:00:00+00:00",
         "step_number": 1, "event_type": "LLM_REQUEST", "runtime_component": "LLM", "processing_time_ms": 5.0},
        {"event_id": "evt-000002", "episode_id": "t", "timestamp": "2026-07-09T00:00:01+00:00",
         "step_number": 1, "event_type": "LLM_RESPONSE", "runtime_component": "LLM",
         "processing_time_ms": 10.0, "finish_reason": "tool_calls", "n_tool_calls": 1,
         "tool_names": ["send_money"]},
        {"event_id": "evt-000003", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "TOOL_CALL_PROPOSED", "runtime_component": "T",
         "processing_time_ms": None, "tool_name": "send_money"},
        {"event_id": "evt-000004", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "GAMMA_INTERCEPT", "runtime_component": "G",
         "processing_time_ms": 0.2, "tool_proposed": "send_money", "policy_class": "WIRE_TRANSFER"},
        {"event_id": "evt-000005", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "PREDICATE_EVALUATION", "runtime_component": "P",
         "processing_time_ms": 0.1, "predicate_name": "GATE_recipient_recognition", "deficit": 1,
         "evaluation_status": "EVALUATED_DEFICIT"},
        {"event_id": "evt-000006", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "Γ COMPUTATION", "runtime_component": "D",
         "processing_time_ms": 0.05, "gamma_global": 1, "gamma_class": 0, "deficit_count": 1},
        {"event_id": "evt-000007", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "Π COMPUTATION", "runtime_component": "D",
         "processing_time_ms": None, "final_pi": 0},
        {"event_id": "evt-000008", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "DENY_DECISION", "runtime_component": "G",
         "processing_time_ms": None, "decision": "SAFE_STATE", "blocking_predicate": "GATE_recipient_recognition"},
        {"event_id": "evt-000009", "episode_id": "t", "timestamp": "2026-07-09T00:00:02+00:00",
         "step_number": 2, "event_type": "TOOL_EXECUTION", "runtime_component": "F",
         "processing_time_ms": 0.3, "executed": False, "env_effect_delta": 0},
        {"event_id": "evt-000010", "episode_id": "t", "timestamp": "2026-07-09T00:00:03+00:00",
         "step_number": 3, "event_type": "EPISODE_FINISHED", "runtime_component": "bench",
         "processing_time_ms": None, "utility": False, "security": False},
    ]
    epi = tmp / "banking" / "user_task_0__injection_task_0"
    epi.mkdir(parents=True)
    with open(epi / "execution_trace.jsonl", "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return epi, events


def test_integrity_and_replay():
    print("=== integrity + replay ===")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        epi, events = _synthetic_trace(tmp)
        # chain determinism + tamper detection
        _c1, root1 = integrity.chain_trace(events)
        _c2, root2 = integrity.chain_trace(events)
        check("hash chain deterministic", root1 == root2)
        tampered = [dict(e) for e in events]
        tampered[5]["gamma_global"] = 0  # flip Γ
        _c3, root3 = integrity.chain_trace(tampered)
        check("hash chain detects tamper", root3 != root1)
        integ = integrity.verify_trace_integrity(epi / "execution_trace.jsonl")
        check("trace integrity ok", integ["integrity_ok"])
        check("chained sidecar written", Path(integ["chain_sidecar"]).exists())

        # replay re-derivation matches recorded (Γ=1, Π=0, SAFE_STATE)
        rep = replay_engine.replay_and_verify(epi / "execution_trace.jsonl")
        check("replay all steps consistent", rep["all_steps_consistent"])
        s = rep["steps"][1]
        check("replay derived Γ_global==1", s["derived"]["gamma_global"] == 1)
        check("replay derived Π==0 -> SAFE_STATE", s["derived"]["pi"] == 0 and s["derived"]["decision"] == "SAFE_STATE")

        # replay must FLAG an internally inconsistent trace
        bad = epi.parent / "bad__x"
        bad.mkdir()
        ev2 = [dict(e) for e in events]
        for e in ev2:
            if e["event_type"] == "Π COMPUTATION":
                e["final_pi"] = 1  # inconsistent: Γ_global=1 but Π=1
        with open(bad / "execution_trace.jsonl", "w") as f:
            for e in ev2:
                f.write(json.dumps(e) + "\n")
        rep2 = replay_engine.replay_and_verify(bad / "execution_trace.jsonl")
        check("replay flags inconsistent trace", not rep2["all_steps_consistent"])


def test_stats_engine():
    print("=== stats engine ===")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _synthetic_trace(tmp)
        stats = stats_engine.analyze(tmp)
        check("1 decision, 1 denial, 0 permit", stats["n_decisions"] == 1 and stats["n_denials"] == 1
              and stats["n_authorizations_permit"] == 0)
        check("predicate failure recorded", stats["predicate_frequency"]["GATE_recipient_recognition"]["failures"] == 1)
        check("tool denial recorded", stats["tool_frequency"]["send_money"]["deny"] == 1)
        check("policy utilization WIRE_TRANSFER", stats["policy_utilization"].get("WIRE_TRANSFER") == 1)
        check("false rates null (not fabricated)", stats["false_permit_rate"] is None and stats["false_deny_rate"] is None)
        out = tmp / "summary"
        stats_engine.write_reports(tmp, out)
        check("statistics.json + tables written", (out / "statistics.json").exists()
              and (out / "statistics_tables.md").exists() and (out / "decisions.csv").exists())


if __name__ == "__main__":
    test_util_stats()
    test_integrity_and_replay()
    test_stats_engine()
    print()
    if FAILS:
        print(f"RESULT: FAIL ({len(FAILS)}): {FAILS}"); sys.exit(1)
    print("RESULT: ALL AUDIT UNIT TESTS PASS")
