#!/usr/bin/env python3
"""Execution Evidence Bundle Assembler — pure structural assembler (Commit 2.5).

Assembles a sealed Execution Evidence Bundle from evidence ALREADY PRODUCED by the four planes,
per EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §5 and RUNTIME_EVIDENCE_ARCHITECTURE.md §4. It is
the union point of the RCL substrate: plane-A (Transaction Interpreter, 2.4), plane-B (RCL
producers, 2.3), plane-C/D (Authority/Governance ports, 2.2), plus caller-supplied Envelope and
the E-cached ledger link.

The assembler performs ONLY:  receive -> place -> seal -> return.

Binding architectural constraints (approved for Commit 2.5):
  1. It does NOT produce evidence and does NOT invoke producers. It RECEIVES already-produced
     EvidenceField objects as inputs and assembles them only.
  2. Envelope metadata (bundle_id, created_at, method_version, subject_ref) and prior_ledger_link
     are CALLER-SUPPLIED inputs. The assembler never invents them (it is not a time source, not a
     bundle-id source, not a ledger).
  3. Freshness observations remain RAW DELTAS. The assembler never converts them into booleans or
     thresholds. Values are carried VERBATIM.
  4. Required-but-unproduced fields remain EvidenceQuality = ABSENT (supplied by the ports /
     caller). The assembler adds no default, no inferred value, no repair.
  5. It reuses the existing ExecutionEvidenceBundle and seal() (Commit 2.1). It introduces no
     second bundle model, no deserializer, and no duplicate serialization.
  6. Nothing else: no authorization, no predicates, no Gamma, no SAFE_STATE, no policy evaluation,
     no runtime interpretation, no transaction interpretation, no benchmark execution, no consumer.

seal() computes the canonical SHA-256 integrity digest — a structural tamper-evidence hash, not a
decision. `Class` has no field, no port, and no producer; the assembled bundle is Class-blind by
construction. Commit 2.5 is UNCONSUMED scaffolding: nothing imports this module.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .execution_evidence_bundle import (
    EvidenceField, EvidencePayload, ExecutionEvidenceBundle,
)


class ExecutionEvidenceBundleAssembler:
    """Pure structural assembler: place received EvidenceField objects into the frozen
    EvidencePayload slots and seal. Stateless. It reads no evidence value, applies no threshold,
    coerces nothing, and decides nothing.
    """

    def assemble(
        self,
        *,
        # -- Envelope (caller-supplied; never invented) -- #
        bundle_id: str,
        created_at: str,
        # -- Plane A (Transaction Interpreter, 2.4) -- #
        txn_amount: EvidenceField,
        txn_time: EvidenceField,
        txn_action_ref: EvidenceField,
        # -- Node predicate vector (binding-defined, caller-supplied; non-empty tuple) -- #
        node_predicate_vector: Tuple[EvidenceField, ...],
        # -- Plane D (Governance port, 2.2) -- #
        harm_risk_score: EvidenceField,
        # -- Plane B (RCL FreshnessClock, 2.3; deltas carried verbatim) -- #
        stale_context: EvidenceField,
        telemetry_fresh: EvidenceField,
        # -- Plane E-cached (Evidence Collector; caller-supplied) -- #
        prior_ledger_link: EvidenceField,
        # -- Envelope options -- #
        subject_ref: Optional[str] = None,
        method_version: Optional[str] = None,
        # -- Optional payload fields (placed only when supplied) -- #
        txn_feature_ref: Optional[EvidenceField] = None,
        class_veto_evidence: Optional[EvidenceField] = None,
        commit_timestamp: Optional[EvidenceField] = None,
        actuate_timestamp: Optional[EvidenceField] = None,
        commit_before_actuate: Optional[EvidenceField] = None,
        actuation_observation: Optional[EvidenceField] = None,
    ) -> ExecutionEvidenceBundle:
        """Receive already-produced EvidenceField objects, place them into the payload, seal.

        Every argument is an EvidenceField produced upstream (or an Envelope/ledger value supplied
        by the caller). This method neither reads nor transforms any evidence value; it only puts
        each field into its named slot and calls the frozen seal().
        """
        # -- place -- #
        payload = EvidencePayload(
            txn_amount=txn_amount,
            txn_time=txn_time,
            txn_action_ref=txn_action_ref,
            node_predicate_vector=node_predicate_vector,
            harm_risk_score=harm_risk_score,
            stale_context=stale_context,
            telemetry_fresh=telemetry_fresh,
            prior_ledger_link=prior_ledger_link,
            txn_feature_ref=txn_feature_ref,
            class_veto_evidence=class_veto_evidence,
            commit_timestamp=commit_timestamp,
            actuate_timestamp=actuate_timestamp,
            commit_before_actuate=commit_before_actuate,
            actuation_observation=actuation_observation,
        )

        # -- seal (reuse the frozen 2.1 implementation; it computes the integrity digest) -- #
        seal_kwargs = dict(
            bundle_id=bundle_id,
            created_at=created_at,
            payload=payload,
            subject_ref=subject_ref,
        )
        if method_version is not None:
            seal_kwargs["method_version"] = method_version

        # -- return -- #
        return ExecutionEvidenceBundle.seal(**seal_kwargs)
