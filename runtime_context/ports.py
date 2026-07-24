#!/usr/bin/env python3
"""Read-only Authority / Governance / Policy ports (Commit 2.2).

Typed, read-only ports per EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §4. They EXPOSE
evidence; they NEVER authorize, evaluate, compute predicates / Gamma / SAFE_STATE, invoke
evaluate_decision, run benchmark or runtime logic, bind producers, consume ports, or
assemble a bundle.

  * AuthorityPort  (plane C) — evidence-absent by default (no producer bound in this arm)
  * GovernancePort (plane D) — evidence-absent by default
  * PolicyPort               — reuses the existing frozen ScientificPolicy, READ-ONLY
                               (no writes; no duplicate Merkle verification — the policy
                               loader verifies at construction, this only reads the root)

No module consumes these ports (Commit 2.2 is unconsumed scaffolding). Dependencies: the
Commit 2.1 EEB types and the existing frozen policy loader only. Standard library otherwise.
"""
from __future__ import annotations

from .execution_evidence_bundle import (
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)
from agentdojo_integration.interception import frozen_policy as _frozen_policy

# Sentinels for an evidence-absent descriptor. A port is NOT a time source; a caller may
# pass a real `observed_at`, otherwise this non-empty sentinel is used so the EEB
# provenance-completeness check (2.1) is satisfied.
_ABSENT_PRODUCER = "unbound"
_ABSENT_OBSERVED_AT = "unobserved"


def _absent(plane: OriginPlane, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
    """Build an evidence-absent EvidenceField for `plane`, reusing the Commit 2.1 types.

    The value is None (no producer); the provenance records evidence_quality = ABSENT.
    This is a fact about availability, not a decision.
    """
    return EvidenceField(
        value=None,
        provenance=ProvenanceDescriptor(
            origin_plane=plane,
            producer_id=_ABSENT_PRODUCER,
            evidence_quality=EvidenceQuality.ABSENT,
            observed_at=observed_at,
            verification_method=VerificationMethod.FIELD_PRESENCE,
            trust_level=TrustLevel.DERIVED,
        ),
    )


class AuthorityPort:
    """Plane C (Authority Infrastructure). Read-only; evidence-absent by default.

    No token store / HSM / approval producer is bound in this arm, so every read honestly
    reports absence rather than fabricating a value.
    """

    def token_valid(self, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
        return _absent(OriginPlane.C, observed_at)

    def authority_signature_valid(self, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
        return _absent(OriginPlane.C, observed_at)

    def authority_concurrence(self, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
        return _absent(OriginPlane.C, observed_at)


class GovernancePort:
    """Plane D (External Governance). Read-only; evidence-absent by default.

    No risk / AML / sanctions producer is bound in this arm.
    """

    def harm_risk_score(self, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
        return _absent(OriginPlane.D, observed_at)

    def sanctions_clear(self, observed_at: str = _ABSENT_OBSERVED_AT) -> EvidenceField:
        return _absent(OriginPlane.D, observed_at)


class PolicyPort:
    """Read-only view over the existing frozen ScientificPolicy (Layer 1).

    Reuses the frozen loader; performs NO writes and NO duplicate Merkle verification
    (ScientificPolicy verifies the seven manifests at construction). This port only reads
    the already-verified root. The policy is constructed lazily on first use.
    """

    def __init__(self) -> None:
        self._policy = None

    def _ensure(self):
        if self._policy is None:
            self._policy = _frozen_policy.default_scientific_policy()
        return self._policy

    def merkle_root(self) -> str:
        """Return the verified scientific Merkle root (read from the verified policy)."""
        return self._ensure().root

    def is_verified(self) -> bool:
        """True iff the frozen policy's verified root equals the recorded scientific root."""
        return self._ensure().root == _frozen_policy.SCIENTIFIC_ROOT
