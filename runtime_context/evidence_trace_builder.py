#!/usr/bin/env python3
"""Class-blind evidence-only trace builder (Commit 5.1 — NARROWED transport subset).

Constructs a sealed, Class-blind, deterministic Execution Evidence Bundle from the already-built
producers and STOPS. This is an INFRASTRUCTURE commit only:

    Transaction Interpreter (A)  +  Runtime Context Layer (B)
      +  Authority Port (C, absent)  +  Governance Port (D, absent)
                              │
                              ▼
                   Execution Evidence Bundle  ->  seal()  ->  STOP

It carries EVIDENCE verbatim into the immutable EEB contract. It performs NO predicate
generation, NO gate binding, NO thresholding, NO HARM_RISK proxy, NO freshness threshold, NO
class-veto mapping, NO engine-schema generation, NO authorization, and it never feeds the frozen
engine or reads `Class`. Freshness observations are carried as RAW DELTAS (never converted to
booleans). The full evidence->predicate binding (θ, limits, gate→plane, HARM proxy) is a GATED
scientific decision (roadmap 5.2 precondition) and is deliberately OUT of this commit's scope.

Discipline (matching 2.1–2.5 / 4.1): standard library + the RCL producers only; Python 3.9;
NOT a time source (all timestamps injected); reuses the 2.1 EvidenceField (no new type);
Commit 5.1 is UNCONSUMED scaffolding — nothing imports this module by default.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .execution_evidence_bundle import (
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod, ExecutionEvidenceBundle,
)
from .assembler import ExecutionEvidenceBundleAssembler
from .transaction_interpreter import (
    TransactionInterpreter, FIELD_AMOUNT, FIELD_TIME, FIELD_ACTION_REF, FIELD_FEATURE_REF,
)
from .context_objects import FreshnessClock, CommitActuateJournal
from .ports import AuthorityPort, GovernancePort

_PRODUCER = "rcl.evidence_trace_builder"
_STAMP = "unobserved"


def _absent(plane: OriginPlane, observed_at: str = _STAMP) -> EvidenceField:
    """Evidence-absent field for a required slot with no producer in this arm (a fact of
    availability, not a fabricated value; mirrors the ports' pattern)."""
    return EvidenceField(
        value=None,
        provenance=ProvenanceDescriptor(
            origin_plane=plane, producer_id=_PRODUCER, evidence_quality=EvidenceQuality.ABSENT,
            observed_at=observed_at, verification_method=VerificationMethod.FIELD_PRESENCE,
            trust_level=TrustLevel.DERIVED,
        ),
    )


def build_evidence_bundle(request: Mapping[str, Any], *, bundle_id: str, created_at: str,
                          runtime: Optional[Mapping[str, Any]] = None,
                          observed_at: Optional[str] = None,
                          subject_ref: Optional[str] = None,
                          method_version: Optional[str] = None) -> ExecutionEvidenceBundle:
    """Assemble and seal a Class-blind evidence-only EEB from the existing producers.

    `request`  — observable transaction request (Amount/Time/features/…); read via the plane-A
                 interpreter, which drops `Class`.
    `runtime`  — optional injected runtime observations for plane B (decision_time,
                 context_capture_time, heartbeat_time, commit_time, actuate_time, request_id).
                 Where absent, the corresponding plane-B fields are evidence-absent.
    Envelope (`bundle_id`/`created_at`/`observed_at`) is injected — this builder is NOT a time
    source. Returns a sealed, immutable bundle. It computes no decision and feeds no engine.
    """
    obs = observed_at if observed_at is not None else _STAMP
    runtime = dict(runtime or {})

    interp = TransactionInterpreter().interpret(request, observed_at=obs)
    authority = AuthorityPort()
    governance = GovernancePort()
    clock = FreshnessClock()

    # -- plane A (Transaction Interpreter): carry what it produced; absent for unproduced req'd -- #
    txn_amount = interp.get(FIELD_AMOUNT) or _absent(OriginPlane.A, obs)
    txn_time = interp.get(FIELD_TIME) or _absent(OriginPlane.A, obs)
    txn_action_ref = interp.get(FIELD_ACTION_REF) or _absent(OriginPlane.A, obs)
    txn_feature_ref = interp.get(FIELD_FEATURE_REF)  # optional

    # -- plane B (RCL FreshnessClock): RAW DELTAS carried verbatim; absent without injected clocks -- #
    if "decision_time" in runtime and "context_capture_time" in runtime:
        stale_context = clock.context_age(runtime["decision_time"],
                                          runtime["context_capture_time"], observed_at=obs)
    else:
        stale_context = _absent(OriginPlane.B, obs)
    if "decision_time" in runtime and "heartbeat_time" in runtime:
        telemetry_fresh = clock.telemetry_age(runtime["decision_time"],
                                              runtime["heartbeat_time"], observed_at=obs)
    else:
        telemetry_fresh = _absent(OriginPlane.B, obs)

    # -- plane B (RCL CommitActuateJournal): optional ordering facts, only if events injected -- #
    commit_timestamp = actuate_timestamp = commit_before_actuate = None
    if "commit_time" in runtime or "actuate_time" in runtime:
        journal = CommitActuateJournal()
        rid = str(runtime.get("request_id", bundle_id))
        if "commit_time" in runtime:
            journal.record_commit(rid, runtime["commit_time"])
            commit_timestamp = journal.commit_reading(rid, observed_at=obs)
        if "actuate_time" in runtime:
            journal.record_actuate(rid, runtime["actuate_time"])
            actuate_timestamp = journal.actuate_reading(rid, observed_at=obs)
        if "commit_time" in runtime and "actuate_time" in runtime:
            commit_before_actuate = journal.ordering_observation(rid, observed_at=obs)

    # -- plane C (Authority Port): authority-plane evidence, all ABSENT in the bare arm. This
    #    TRANSPORTS the AuthorityPort's outputs into the node-predicate slot; it binds NO
    #    observable (amount/velocity/harm) gate — the gate→plane binding is gated (5.2). -------- #
    node_predicate_vector = (
        authority.token_valid(obs),
        authority.authority_signature_valid(obs),
        authority.authority_concurrence(obs),
    )

    # -- plane D (Governance Port): hazard score, ABSENT (no risk service in this arm) -- #
    harm_risk_score = governance.harm_risk_score(obs)

    # -- plane E-cached: prior ledger link absent (no Evidence Collector bound here) -- #
    prior_ledger_link = _absent(OriginPlane.E_CACHED, obs)

    # class_veto_evidence / actuation_observation are deliberately left absent (None): mapping
    # them is class-veto / actuation binding, which is gated and out of Commit 5.1 scope.
    return ExecutionEvidenceBundleAssembler().assemble(
        bundle_id=bundle_id, created_at=created_at, subject_ref=subject_ref,
        method_version=method_version,
        txn_amount=txn_amount, txn_time=txn_time, txn_action_ref=txn_action_ref,
        txn_feature_ref=txn_feature_ref,
        node_predicate_vector=node_predicate_vector,
        harm_risk_score=harm_risk_score,
        stale_context=stale_context, telemetry_fresh=telemetry_fresh,
        commit_timestamp=commit_timestamp, actuate_timestamp=actuate_timestamp,
        commit_before_actuate=commit_before_actuate,
        prior_ledger_link=prior_ledger_link,
    )
