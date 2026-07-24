"""Self-test for the RCL plane-B owned objects (Commit 2.3).

Verifies the four owned objects per RUNTIME_CONTEXT_LAYER_SPECIFICATION.md §3:
ExecutionHistoryWindow, FreshnessClock, CommitActuateJournal, ExecutionContextRecord.
Covers: determinism, window bounding/eviction, timestamp-recomputability, deltas-not-verdicts,
reading immutability, append-only journal, Class-blindness, EEB-provenance validity, and the
no-wall-clock discipline. Standard library only; no pytest. Run:
    python3 tests/test_context_objects.py     # standalone; exits 0 on success
    pytest tests/test_context_objects.py      # if pytest is later added

Commit 2.3 is unconsumed scaffolding; EvidenceBundle assembly (§3.5) is Commit 2.5, not here.
"""
from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import context_objects as co  # noqa: E402
from runtime_context.context_objects import (  # noqa: E402
    ExecutionHistoryWindow, FreshnessClock, CommitActuateJournal, ExecutionContextRecord,
)
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, OriginPlane, EvidenceQuality, _check_field,
)


def _assert_plane_b(ef) -> None:
    assert isinstance(ef, EvidenceField), "readings must be Commit 2.1 EvidenceField"
    assert ef.provenance.origin_plane == OriginPlane.B, "RCL owns plane B"
    assert ef.provenance.evidence_quality == EvidenceQuality.PRESENT
    _check_field(ef, "reading")  # reuse EEB structural/provenance validation


# 1. FreshnessClock emits DELTAS (magnitudes), never thresholds or booleans
def test_freshness_clock_deltas() -> None:
    clk = FreshnessClock()
    ctx = clk.context_age(decision_time=100, context_capture_time=70)
    tel = clk.telemetry_age(decision_time=100, heartbeat_time=90)
    _assert_plane_b(ctx)
    _assert_plane_b(tel)
    assert ctx.value == 30, "context age must be a pure timestamp delta"
    assert tel.value == 10, "telemetry age must be a pure timestamp delta"
    # deltas are numeric magnitudes, never a fresh/stale verdict
    assert not isinstance(ctx.value, bool)
    assert not isinstance(tel.value, bool)


# 2. Determinism: identical injected timestamps -> identical readings
def test_freshness_determinism() -> None:
    a = FreshnessClock().context_age(decision_time=500, context_capture_time=123,
                                     observed_at="t")
    b = FreshnessClock().context_age(decision_time=500, context_capture_time=123,
                                     observed_at="t")
    assert a == b, "identical evidence must yield identical readings"


# 3. History window: velocity aggregate + bounded FIFO eviction
def test_window_velocity_and_eviction() -> None:
    w = ExecutionHistoryWindow(max_size=3)
    for i, t in enumerate([10, 20, 30, 40]):
        w.append("r%d" % i, t)
    assert w.size() == 3, "window must be bounded to max_size"
    assert w.velocity_reading().value == 3, "velocity aggregate = in-window count"
    # oldest (r0) evicted; the surviving readings are plane-B EvidenceField
    _assert_plane_b(w.velocity_reading())
    _assert_plane_b(w.ordering_reading())


# 4. History window ordering aggregate: inversions counted, no verdict
def test_window_ordering_inversions() -> None:
    ordered = ExecutionHistoryWindow(max_size=10)
    for i, t in enumerate([1, 2, 3, 4]):
        ordered.append("r%d" % i, t)
    assert ordered.ordering_reading().value == 0, "monotone stream has no inversions"

    scrambled = ExecutionHistoryWindow(max_size=10)
    for i, t in enumerate([1, 5, 2, 6, 3]):
        scrambled.append("r%d" % i, t)
    assert scrambled.ordering_reading().value == 2, "two out-of-order adjacent pairs"


# 5. Emitted readings are immutable snapshots — stable as the window evolves
def test_reading_immutable_snapshot() -> None:
    w = ExecutionHistoryWindow(max_size=10)
    w.append("a", 1)
    w.append("b", 2)
    captured = w.velocity_reading()
    assert captured.value == 2
    w.append("c", 3)  # window grows...
    assert captured.value == 2, "a captured reading must not change after later appends"
    try:
        setattr(captured, "value", 99)
        raise AssertionError("expected FrozenInstanceError on reading mutation")
    except dataclasses.FrozenInstanceError:
        pass


# 6. CommitActuateJournal exposes the ordering FACT (observation, not I5 verdict)
def test_journal_ordering_observation() -> None:
    j = CommitActuateJournal()
    j.record_commit("req", commit_time=10, event_ref="c1")
    j.record_actuate("req", actuate_time=20, event_ref="a1")
    obs = j.ordering_observation("req")
    _assert_plane_b(obs)
    assert obs.value is True, "commit(10) precedes actuate(20)"
    assert j.commit_reading("req").value == 10
    assert j.actuate_reading("req").value == 20

    k = CommitActuateJournal()
    k.record_commit("req", commit_time=30)
    k.record_actuate("req", actuate_time=15)
    assert k.ordering_observation("req").value is False, "commit(30) after actuate(15)"


# 7. Journal is append-only: a recorded event is never overwritten
def test_journal_append_only() -> None:
    j = CommitActuateJournal()
    j.record_commit("req", commit_time=1)
    try:
        j.record_commit("req", commit_time=2)
        raise AssertionError("expected append-only violation on re-record")
    except ValueError:
        pass
    # ordering unobservable until both events exist
    try:
        j.ordering_observation("req")
        raise AssertionError("expected error when actuate missing")
    except ValueError:
        pass


# 8. ExecutionContextRecord is an immutable snapshot referencing readings
def test_context_record_immutable() -> None:
    r = FreshnessClock().context_age(decision_time=100, context_capture_time=90)
    rec = ExecutionContextRecord.snapshot(request_id="req", decision_time=100, readings=(r,))
    assert rec.request_id == "req" and rec.decision_time == 100
    assert rec.readings == (r,)
    assert isinstance(rec.to_dict()["readings"], list)
    try:
        setattr(rec, "request_id", "other")
        raise AssertionError("expected FrozenInstanceError on record mutation")
    except dataclasses.FrozenInstanceError:
        pass


# 9. Class-blindness (structural): no producer accepts a Class/label input channel
def test_class_blindness_structural() -> None:
    forbidden = {"class", "class_", "label", "y", "target", "ground_truth"}
    targets = [
        FreshnessClock.context_age, FreshnessClock.telemetry_age,
        ExecutionHistoryWindow.__init__, ExecutionHistoryWindow.append,
        ExecutionHistoryWindow.velocity_reading, ExecutionHistoryWindow.ordering_reading,
        CommitActuateJournal.record_commit, CommitActuateJournal.record_actuate,
        CommitActuateJournal.ordering_observation, ExecutionContextRecord.snapshot,
    ]
    for fn in targets:
        params = set(inspect.signature(fn).parameters)
        assert not (params & forbidden), "%s exposes a Class channel: %s" % (
            fn.__qualname__, params & forbidden)


# 10. No wall clock: the module reads no ambient time (determinism / replay discipline).
# AST-based (like the guardrail) so docstrings/comments cannot trip it — only real calls do.
def test_no_wall_clock() -> None:
    import ast
    tree = ast.parse(Path(co.__file__).read_text(encoding="utf-8"))
    banned_mods = {"time", "datetime"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] not in banned_mods, "RCL imports a clock: %s" % a.name
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_mods, \
                "RCL imports from a clock: %s" % node.module
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"now", "utcnow", "today", "time",
                                          "monotonic", "perf_counter"}, \
                "RCL calls an ambient-time source: .%s()" % node.func.attr


def _run_all() -> int:
    checks = [
        test_freshness_clock_deltas,
        test_freshness_determinism,
        test_window_velocity_and_eviction,
        test_window_ordering_inversions,
        test_reading_immutable_snapshot,
        test_journal_ordering_observation,
        test_journal_append_only,
        test_context_record_immutable,
        test_class_blindness_structural,
        test_no_wall_clock,
    ]
    failures = 0
    for fn in checks:
        try:
            fn()
            print("  PASS  %s" % fn.__name__)
        except AssertionError as exc:
            failures += 1
            print("  FAIL  %s: %s" % (fn.__name__, exc))
    print("-" * 60)
    print("context_objects self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
