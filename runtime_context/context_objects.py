#!/usr/bin/env python3
"""Runtime Context Layer — plane-B owned observation objects (Commit 2.3).

The four plane-B objects the RCL genuinely OWNS, per
RUNTIME_CONTEXT_LAYER_SPECIFICATION.md §3 (§3.1–§3.4). These are the only evidence the
RCL *produces* rather than *exposes*:

  * ExecutionHistoryWindow (§3.2) — bounded, GLOBAL rolling view of prior mediated
    requests; exposes velocity + execution-ordering AGGREGATES. Append + bounded eviction.
  * FreshnessClock (§3.3)         — pure function of timestamps; exposes context/telemetry
    DELTAS for the StaleContext / TelemetryFresh deficit inputs. No threshold, no verdict.
  * CommitActuateJournal (§3.4)   — append-only record of commit/actuate event references;
    exposes the commit-before-actuate ordering FACT (not the frozen I5 verdict).
  * ExecutionContextRecord (§3.1) — immutable per-request snapshot referencing the readings
    used at decision time.

PRIME INVARIANT (spec §0). The RCL EXPOSES evidence; it NEVER decides. These objects own
SHAPE and OBSERVATION, never MEANING. They author no predicate, threshold, limit,
aggregation verdict, authority model, Gamma / SAFE_STATE / evaluate_decision call, or
policy interpretation, and they never read `Class` (spec §8 — the RCL sits inside the
Class-blind region). Every reading is a DELTA or an AGGREGATE; the comparison against a
bound/limit is the gate's/policy's job, not the RCL's.

Discipline (matching Commits 2.1/2.2):
  * Standard library only; Python 3.9 compatible.
  * NOT a time source — all timestamps are INJECTED parameters (no datetime.now()/time()).
  * Readings are the immutable Commit 2.1 EvidenceField (origin_plane = B); no new type.
  * Commit 2.3 is UNCONSUMED scaffolding: nothing imports this module. EvidenceBundle
    assembly is Commit 2.5, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .execution_evidence_bundle import (
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)

# Producer identifiers recorded in each reading's provenance (the RCL owns plane B).
_PRODUCER_WINDOW = "rcl.history_window"
_PRODUCER_CLOCK = "rcl.freshness_clock"
_PRODUCER_JOURNAL = "rcl.commit_actuate_journal"


def _reading(value, producer_id: str, observed_at: str) -> EvidenceField:
    """Build an immutable plane-B EvidenceField (Commit 2.1 type) for a produced reading.

    Records the value verbatim plus complete provenance. All plane-B readings are
    timestamp-derived and RCL-derived; the RCL never signs or attests them.
    """
    return EvidenceField(
        value=value,
        provenance=ProvenanceDescriptor(
            origin_plane=OriginPlane.B,
            producer_id=producer_id,
            evidence_quality=EvidenceQuality.PRESENT,
            observed_at=observed_at,
            verification_method=VerificationMethod.TIMESTAMP_DERIVED,
            trust_level=TrustLevel.DERIVED,
        ),
    )


def _stamp(observed_at: Optional[str], injected_time) -> str:
    """Deterministic provenance label. Never reads a wall clock: if the caller supplies no
    label, render the INJECTED time (a function of input, not a time source)."""
    return observed_at if observed_at is not None else str(injected_time)


# --------------------------------------------------------------------------- #
# §3.3 FreshnessClock — pure timestamp derivation (no state, no threshold)
# --------------------------------------------------------------------------- #
class FreshnessClock:
    """Expose context/telemetry freshness as timestamp DELTAS against the decision time.

    A pure function of injected timestamps. It emits magnitudes ONLY — it embeds no policy
    bound and returns NO fresh/stale boolean (spec §3.3: "the threshold to judge freshness
    lives in policy, not here"). The deficit judgement is made downstream by the predicate
    evaluator using a policy bound, never here.
    """

    def context_age(self, decision_time, context_capture_time,
                    observed_at: Optional[str] = None) -> EvidenceField:
        """Delta = decision_time − context_capture_time (how old the captured context is)."""
        return _reading(decision_time - context_capture_time,
                        _PRODUCER_CLOCK, _stamp(observed_at, decision_time))

    def telemetry_age(self, decision_time, heartbeat_time,
                      observed_at: Optional[str] = None) -> EvidenceField:
        """Delta = decision_time − heartbeat_time (telemetry heartbeat age)."""
        return _reading(decision_time - heartbeat_time,
                        _PRODUCER_CLOCK, _stamp(observed_at, decision_time))


# --------------------------------------------------------------------------- #
# §3.2 ExecutionHistoryWindow — bounded, GLOBAL rolling view (append + eviction)
# --------------------------------------------------------------------------- #
class ExecutionHistoryWindow:
    """Bounded rolling view of prior mediated requests, exposing velocity + ordering
    AGGREGATES a plane-B gate reads.

    GLOBAL only — the transaction source provides no subject key (spec §5 honest gap), so no
    per-subject window is exposable and none is faked. Count-bounded (deterministic without a
    wall clock): the oldest entry is evicted (FIFO) once ``max_size`` is exceeded. The window
    exposes aggregates; it NEVER compares them to a velocity/ordering limit (that is the
    gate/policy). Emitted readings are immutable scalars — stable even as the window evolves.
    """

    def __init__(self, max_size: int) -> None:
        if not isinstance(max_size, int) or max_size < 1:
            raise ValueError("ExecutionHistoryWindow max_size must be a positive int")
        self._max_size = max_size
        self._entries: List[Tuple[str, float]] = []  # (request_id, decision_time), FIFO

    def append(self, request_id: str, decision_time) -> None:
        """Append a sealed request's (id, decision_time); evict the oldest past the bound."""
        self._entries.append((request_id, decision_time))
        if len(self._entries) > self._max_size:
            self._entries.pop(0)

    def size(self) -> int:
        return len(self._entries)

    def velocity_reading(self, observed_at: Optional[str] = None) -> EvidenceField:
        """Velocity AGGREGATE = number of requests currently in the window (a count)."""
        latest = self._entries[-1][1] if self._entries else 0
        return _reading(len(self._entries), _PRODUCER_WINDOW, _stamp(observed_at, latest))

    def ordering_reading(self, observed_at: Optional[str] = None) -> EvidenceField:
        """Ordering AGGREGATE = count of temporal inversions among in-window entries
        (adjacent pairs whose decision_time decreases). A pure observation, not a verdict."""
        inversions = 0
        for i in range(1, len(self._entries)):
            if self._entries[i][1] < self._entries[i - 1][1]:
                inversions += 1
        latest = self._entries[-1][1] if self._entries else 0
        return _reading(inversions, _PRODUCER_WINDOW, _stamp(observed_at, latest))


# --------------------------------------------------------------------------- #
# §3.4 CommitActuateJournal — append-only commit/actuate event references
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _JournalEntry:
    """Immutable per-request commit/actuate event record (append-only; never overwritten)."""
    commit_time: Optional[float] = None
    commit_ref: Optional[str] = None
    actuate_time: Optional[float] = None
    actuate_ref: Optional[str] = None


class CommitActuateJournal:
    """Append-only journal of commit-log / actuation-log event references.

    Exposes the observed commit-before-actuate ORDERING FACT (spec §3.4). It does NOT define
    the ordering rule — the frozen ordering check (gamma_test_runner.py:918-924) remains the
    sole I5 authority; this only reports what the substrate recorded. Append-only: a recorded
    commit/actuate for a request is never overwritten (a re-record raises).
    """

    def __init__(self) -> None:
        self._entries: Dict[str, _JournalEntry] = {}

    def record_commit(self, request_id: str, commit_time, event_ref: Optional[str] = None) -> None:
        cur = self._entries.get(request_id, _JournalEntry())
        if cur.commit_time is not None:
            raise ValueError("append-only journal: commit already recorded for %r" % request_id)
        self._entries[request_id] = _JournalEntry(
            commit_time=commit_time, commit_ref=event_ref,
            actuate_time=cur.actuate_time, actuate_ref=cur.actuate_ref,
        )

    def record_actuate(self, request_id: str, actuate_time, event_ref: Optional[str] = None) -> None:
        cur = self._entries.get(request_id, _JournalEntry())
        if cur.actuate_time is not None:
            raise ValueError("append-only journal: actuate already recorded for %r" % request_id)
        self._entries[request_id] = _JournalEntry(
            commit_time=cur.commit_time, commit_ref=cur.commit_ref,
            actuate_time=actuate_time, actuate_ref=event_ref,
        )

    def _require(self, request_id: str) -> _JournalEntry:
        entry = self._entries.get(request_id)
        if entry is None:
            raise KeyError("no journal entry for request %r" % request_id)
        return entry

    def commit_reading(self, request_id: str, observed_at: Optional[str] = None) -> EvidenceField:
        """The recorded commit timestamp for a request (a fact, not a judgement)."""
        entry = self._require(request_id)
        return _reading(entry.commit_time, _PRODUCER_JOURNAL, _stamp(observed_at, entry.commit_time))

    def actuate_reading(self, request_id: str, observed_at: Optional[str] = None) -> EvidenceField:
        """The recorded actuation timestamp for a request (a fact, not a judgement)."""
        entry = self._require(request_id)
        return _reading(entry.actuate_time, _PRODUCER_JOURNAL, _stamp(observed_at, entry.actuate_time))

    def ordering_observation(self, request_id: str, observed_at: Optional[str] = None) -> EvidenceField:
        """Observed ordering fact: True iff the recorded commit precedes the recorded actuate.

        A PURE OBSERVATION over two recorded timestamps — NOT the frozen I5 verdict. Requires
        both events recorded; otherwise the ordering is unobservable and this raises.
        """
        entry = self._require(request_id)
        if entry.commit_time is None or entry.actuate_time is None:
            raise ValueError("ordering unobservable: both commit and actuate must be recorded")
        stamp = _stamp(observed_at, entry.actuate_time)
        return _reading(entry.commit_time < entry.actuate_time, _PRODUCER_JOURNAL, stamp)


# --------------------------------------------------------------------------- #
# §3.1 ExecutionContextRecord — immutable per-request snapshot
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ExecutionContextRecord:
    """Immutable snapshot of the runtime context at decision time (spec §3.1).

    Records the request id, the decision timestamp, and references to the plane-B readings
    used. Immutable once built (frozen; consistent with DET4 append-only). It is a snapshot,
    not an evidence value, and it carries no bundle envelope (sealing is Commit 2.5).
    """
    request_id: str
    decision_time: float
    readings: Tuple[EvidenceField, ...] = field(default_factory=tuple)

    @classmethod
    def snapshot(cls, *, request_id: str, decision_time,
                 readings: Tuple[EvidenceField, ...] = ()) -> "ExecutionContextRecord":
        """Build a sealed, immutable snapshot capturing the readings used at decision time."""
        return cls(request_id=request_id, decision_time=decision_time,
                   readings=tuple(readings))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "decision_time": self.decision_time,
            "readings": [ef.to_dict() for ef in self.readings],
        }
