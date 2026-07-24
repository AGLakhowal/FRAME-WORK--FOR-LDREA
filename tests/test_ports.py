"""Self-test for the read-only Authority / Governance / Policy ports (Commit 2.2).

Verifies port behaviour only: Authority/Governance return evidence-absent; PolicyPort's
integrity read matches the frozen Merkle root. Standard library only; no pytest. Run:
    python3 tests/test_ports.py      # standalone; exits 0 on success
    pytest tests/test_ports.py       # if pytest is later added

The PolicyPort check reads the committed, deterministic frozen manifests (read-only).
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context.ports import AuthorityPort, GovernancePort, PolicyPort  # noqa: E402
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)
from agentdojo_integration.interception.frozen_policy import SCIENTIFIC_ROOT  # noqa: E402


def _assert_absent(ef, plane) -> None:
    assert isinstance(ef, EvidenceField), "port must return an EvidenceField"
    assert ef.value is None, "evidence-absent value must be None (no fabrication)"
    p = ef.provenance
    assert isinstance(p, ProvenanceDescriptor)
    assert p.evidence_quality == EvidenceQuality.ABSENT
    assert p.origin_plane == plane
    # HA-3: descriptor must be complete so it satisfies EEB provenance validation.
    assert p.producer_id and p.observed_at
    assert isinstance(p.verification_method, VerificationMethod)
    assert isinstance(p.trust_level, TrustLevel)


# 1. AuthorityPort (plane C) — every read is evidence-absent
def test_authority_port_absent() -> None:
    a = AuthorityPort()
    for ef in (a.token_valid(), a.authority_signature_valid(), a.authority_concurrence()):
        _assert_absent(ef, OriginPlane.C)


# 2. GovernancePort (plane D) — every read is evidence-absent
def test_governance_port_absent() -> None:
    g = GovernancePort()
    for ef in (g.harm_risk_score(), g.sanctions_clear()):
        _assert_absent(ef, OriginPlane.D)


# 3. Returned evidence is immutable (frozen EEB type)
def test_returned_evidence_immutable() -> None:
    ef = AuthorityPort().token_valid()
    try:
        setattr(ef, "value", "mutated")
        raise AssertionError("expected FrozenInstanceError on EvidenceField mutation")
    except dataclasses.FrozenInstanceError:
        pass


# 4. PolicyPort integrity read matches the frozen Merkle root (read-only)
def test_policy_port_merkle_root() -> None:
    p = PolicyPort()
    root = p.merkle_root()
    assert root == SCIENTIFIC_ROOT, "PolicyPort root must equal the frozen scientific root"
    assert root.startswith("ce8c8467"), "unexpected scientific root prefix"
    assert p.is_verified() is True
    # idempotent + read-only: repeated reads are stable
    assert p.merkle_root() == root


# 5. A caller-supplied observed_at is honoured (the port is not a time source)
def test_observed_at_passthrough() -> None:
    ef = GovernancePort().harm_risk_score(observed_at="2026-01-01T00:00:00.000Z")
    assert ef.provenance.observed_at == "2026-01-01T00:00:00.000Z"
    assert ef.provenance.evidence_quality == EvidenceQuality.ABSENT


def _run_all() -> int:
    checks = [
        test_authority_port_absent,
        test_governance_port_absent,
        test_returned_evidence_immutable,
        test_policy_port_merkle_root,
        test_observed_at_passthrough,
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
    print("ports self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
