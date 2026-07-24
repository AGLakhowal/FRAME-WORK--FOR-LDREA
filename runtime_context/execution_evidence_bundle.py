#!/usr/bin/env python3
"""Execution Evidence Bundle (EEB) — immutable DATA CONTRACT (Commit 2.1).

Transport-only structure per EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §2. The bundle
CARRIES evidence and its provenance; it performs NO authorization, evaluation, predicate
computation, inference, classification, risk scoring, Gamma execution, SAFE_STATE
computation, or policy interpretation. It owns STRUCTURE, never SEMANTICS.

Commit 2.1 is a NO-CONSUMER contract: nothing in the repository imports this module yet.
It defines structure only; a future consumer (Commit 4.1) supplies the real values.

Discipline:
  * Standard library only (hashlib, json, dataclasses, enum, typing). No pandas/numpy.
  * Python 3.9 compatible.
  * Deep immutability: frozen dataclasses + tuples; no exposed mutable list/dict/set.
  * Structural operations only: seal / validate_structure / canonical serialization /
    integrity digest / version metadata. No evaluate/authorize/compute/score/classify.
  * Canonical serialization = JSON with sort_keys=True and deterministic separators;
    integrity digest = SHA-256.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple

# ---- version metadata (spec §2.1) ---------------------------------------- #
SCHEMA_VERSION = "eeb/1.0"
# Neutral placeholder: the real engine/method tag is supplied by a future consumer
# (Commit 4.1). Keeping it a local constant means this contract imports nothing from Gamma.
DEFAULT_METHOD_VERSION = "eeb-contract/unbound"


# ---- provenance enums (spec §2.3) ---------------------------------------- #
class OriginPlane(Enum):
    A = "A"                # Transaction Evidence
    B = "B"                # Runtime Context
    C = "C"                # Authority Infrastructure
    D = "D"                # External Governance
    E_CACHED = "E-cached"  # Derived Runtime Output (cached, e.g. prior ledger link)


class EvidenceQuality(Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    DEGRADED = "DEGRADED"
    EXPIRED = "EXPIRED"


class TrustLevel(Enum):
    ATTESTED = "attested"
    SELF_REPORTED = "self-reported"
    DERIVED = "derived"


class VerificationMethod(Enum):
    SIGNATURE_VERIFIED = "signature-verified"
    TIMESTAMP_DERIVED = "timestamp-derived"
    SERVICE_ATTESTED = "service-attested"
    DIGEST_RECOMPUTE = "digest-recompute"
    FIELD_PRESENCE = "field-presence"


# ---- provenance descriptor (spec §2.3) ----------------------------------- #
@dataclass(frozen=True)
class ProvenanceDescriptor:
    """Describes a carried evidence value. Records quality; makes no pass/fail judgement."""
    origin_plane: OriginPlane
    producer_id: str
    evidence_quality: EvidenceQuality
    observed_at: str
    verification_method: VerificationMethod
    trust_level: TrustLevel

    def to_dict(self) -> dict:
        return {
            "origin_plane": self.origin_plane.value,
            "producer_id": self.producer_id,
            "evidence_quality": self.evidence_quality.value,
            "observed_at": self.observed_at,
            "verification_method": self.verification_method.value,
            "trust_level": self.trust_level.value,
        }


@dataclass(frozen=True)
class EvidenceField:
    """A carried evidence value + its provenance descriptor (spec §2.2/§2.3).

    `value` is a scalar transported verbatim (bool / number / str / None). The contract
    never interprets it.
    """
    value: Any
    provenance: ProvenanceDescriptor

    def to_dict(self) -> dict:
        return {"value": self.value, "provenance": self.provenance.to_dict()}


# ---- evidence payload (spec §2.2) ---------------------------------------- #
@dataclass(frozen=True)
class EvidencePayload:
    """The Predicate-Evaluator input fields, each with provenance.

    Required fields are EvidenceField; optional fields default to None. The node predicate
    vector is an immutable tuple of provenanced booleans. Derived-output fields
    (decision / Gamma / SAFE_STATE / ReasonCodes) are deliberately ABSENT (spec §2.2).
    """
    txn_amount: EvidenceField
    txn_time: EvidenceField
    txn_action_ref: EvidenceField
    node_predicate_vector: Tuple[EvidenceField, ...]
    harm_risk_score: EvidenceField
    stale_context: EvidenceField
    telemetry_fresh: EvidenceField
    prior_ledger_link: EvidenceField
    txn_feature_ref: Optional[EvidenceField] = None
    class_veto_evidence: Optional[EvidenceField] = None
    commit_timestamp: Optional[EvidenceField] = None
    actuate_timestamp: Optional[EvidenceField] = None
    commit_before_actuate: Optional[EvidenceField] = None
    actuation_observation: Optional[EvidenceField] = None

    def to_dict(self) -> dict:
        def enc(ef):
            return None if ef is None else ef.to_dict()
        return {
            "txn_amount": enc(self.txn_amount),
            "txn_time": enc(self.txn_time),
            "txn_action_ref": enc(self.txn_action_ref),
            "txn_feature_ref": enc(self.txn_feature_ref),
            "node_predicate_vector": [ef.to_dict() for ef in self.node_predicate_vector],
            "harm_risk_score": enc(self.harm_risk_score),
            "class_veto_evidence": enc(self.class_veto_evidence),
            "stale_context": enc(self.stale_context),
            "telemetry_fresh": enc(self.telemetry_fresh),
            "commit_timestamp": enc(self.commit_timestamp),
            "actuate_timestamp": enc(self.actuate_timestamp),
            "commit_before_actuate": enc(self.commit_before_actuate),
            "actuation_observation": enc(self.actuation_observation),
            "prior_ledger_link": enc(self.prior_ledger_link),
        }


_REQUIRED_PAYLOAD = (
    "txn_amount", "txn_time", "txn_action_ref", "node_predicate_vector",
    "harm_risk_score", "stale_context", "telemetry_fresh", "prior_ledger_link",
)
_OPTIONAL_PAYLOAD = (
    "txn_feature_ref", "class_veto_evidence", "commit_timestamp",
    "actuate_timestamp", "commit_before_actuate", "actuation_observation",
)


# ---- canonical helpers --------------------------------------------------- #
def _content_dict(bundle_id, schema_version, method_version, created_at, subject_ref, payload) -> dict:
    """Canonical CONTENT the integrity digest covers (everything EXCEPT integrity_digest)."""
    return {
        "bundle_id": bundle_id,
        "schema_version": schema_version,
        "method_version": method_version,
        "created_at": created_at,
        "subject_ref": subject_ref,
        "payload": payload.to_dict(),
    }


def _canonical_json(content: dict) -> str:
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ---- the bundle (spec §2.1 envelope + §2 whole) -------------------------- #
@dataclass(frozen=True)
class ExecutionEvidenceBundle:
    """Immutable transport contract. Sealed at construction via ``seal(...)``.

    Structural operations only. This class NEVER decides, evaluates, or scores.
    """
    bundle_id: str
    schema_version: str
    method_version: str
    created_at: str
    subject_ref: Optional[str]
    payload: EvidencePayload
    integrity_digest: str

    # -- construction / sealing -- #
    @classmethod
    def seal(cls, *, bundle_id: str, created_at: str, payload: EvidencePayload,
             subject_ref: Optional[str] = None,
             schema_version: str = SCHEMA_VERSION,
             method_version: str = DEFAULT_METHOD_VERSION) -> "ExecutionEvidenceBundle":
        """Build a sealed, immutable bundle with a computed SHA-256 integrity digest."""
        content = _content_dict(bundle_id, schema_version, method_version,
                                created_at, subject_ref, payload)
        digest = hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()
        return cls(
            bundle_id=bundle_id, schema_version=schema_version,
            method_version=method_version, created_at=created_at,
            subject_ref=subject_ref, payload=payload, integrity_digest=digest,
        )

    # -- canonical serialization -- #
    def canonical_content(self) -> dict:
        return _content_dict(self.bundle_id, self.schema_version, self.method_version,
                             self.created_at, self.subject_ref, self.payload)

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_content())

    def to_dict(self) -> dict:
        d = self.canonical_content()
        d["integrity_digest"] = self.integrity_digest
        return d

    # -- integrity -- #
    def compute_integrity_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        return self.compute_integrity_digest() == self.integrity_digest

    # -- structural validation (shape + provenance only; NO thresholds/semantics) -- #
    def validate_structure(self) -> None:
        """Raise ValueError on a structural/provenance defect. Never inspects evidence content."""
        for name in ("bundle_id", "schema_version", "method_version", "created_at"):
            if not getattr(self, name):
                raise ValueError("EEB structural error: missing envelope field '%s'" % name)
        if not (isinstance(self.integrity_digest, str) and len(self.integrity_digest) == 64):
            raise ValueError("EEB structural error: integrity_digest is not a 64-hex SHA-256")
        if not isinstance(self.payload, EvidencePayload):
            raise ValueError("EEB structural error: payload is not an EvidencePayload")
        for name in _REQUIRED_PAYLOAD:
            val = getattr(self.payload, name)
            if name == "node_predicate_vector":
                if not isinstance(val, tuple) or not val:
                    raise ValueError("EEB structural error: node_predicate_vector must be a non-empty tuple")
                for ef in val:
                    _check_field(ef, name)
            else:
                _check_field(val, name)
        for name in _OPTIONAL_PAYLOAD:
            val = getattr(self.payload, name)
            if val is not None:
                _check_field(val, name)


def _check_field(ef, name) -> None:
    if not isinstance(ef, EvidenceField):
        raise ValueError("EEB structural error: field '%s' is not an EvidenceField" % name)
    prov = ef.provenance
    if not isinstance(prov, ProvenanceDescriptor):
        raise ValueError("EEB structural error: field '%s' missing ProvenanceDescriptor" % name)
    if not (isinstance(prov.origin_plane, OriginPlane)
            and isinstance(prov.evidence_quality, EvidenceQuality)
            and isinstance(prov.verification_method, VerificationMethod)
            and isinstance(prov.trust_level, TrustLevel)):
        raise ValueError("EEB structural error: field '%s' has an invalid provenance enum" % name)
    if not prov.producer_id or not prov.observed_at:
        raise ValueError("EEB structural error: field '%s' has incomplete provenance" % name)
