"""Hermetic self-test for the Execution Evidence Bundle data contract (Commit 2.1).

Verifies the contract's OWN structural behaviour using in-memory objects only.
No repository state, no benchmark execution, standard library only, no pytest. Run either:
    python3 tests/test_execution_evidence_bundle.py      # standalone; exits 0 on success
    pytest tests/test_execution_evidence_bundle.py       # if pytest is later added
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context.execution_evidence_bundle import (  # noqa: E402
    SCHEMA_VERSION,
    OriginPlane, EvidenceQuality, TrustLevel, VerificationMethod,
    ProvenanceDescriptor, EvidenceField, EvidencePayload, ExecutionEvidenceBundle,
)


# --------------------------------------------------------------------------- #
# builders (hermetic; fixed values -> deterministic)
# --------------------------------------------------------------------------- #
def _pd(plane=OriginPlane.A):
    return ProvenanceDescriptor(
        origin_plane=plane, producer_id="producer.test",
        evidence_quality=EvidenceQuality.PRESENT, observed_at="2026-01-01T00:00:00.000Z",
        verification_method=VerificationMethod.FIELD_PRESENCE, trust_level=TrustLevel.DERIVED,
    )


def _ef(value, plane=OriginPlane.A):
    return EvidenceField(value=value, provenance=_pd(plane))


def _payload():
    return EvidencePayload(
        txn_amount=_ef(100.0, OriginPlane.A),
        txn_time=_ef(0.0, OriginPlane.A),
        txn_action_ref=_ef("action:test", OriginPlane.A),
        node_predicate_vector=(_ef(True, OriginPlane.C), _ef(True, OriginPlane.C)),
        harm_risk_score=_ef(0.01, OriginPlane.D),
        stale_context=_ef(False, OriginPlane.B),
        telemetry_fresh=_ef(True, OriginPlane.B),
        prior_ledger_link=_ef("GENESIS", OriginPlane.E_CACHED),
    )


def _bundle():
    return ExecutionEvidenceBundle.seal(
        bundle_id="b-1", created_at="2026-01-01T00:00:00.000Z", payload=_payload(),
    )


# --------------------------------------------------------------------------- #
# 1. field structure
# --------------------------------------------------------------------------- #
def test_field_structure() -> None:
    b = _bundle()
    assert isinstance(b.payload, EvidencePayload)
    assert isinstance(b.payload.txn_amount, EvidenceField)
    assert isinstance(b.payload.txn_amount.provenance, ProvenanceDescriptor)
    assert isinstance(b.payload.node_predicate_vector, tuple)
    assert len(b.payload.node_predicate_vector) == 2
    # optional fields default to None (not fabricated)
    assert b.payload.txn_feature_ref is None
    assert b.payload.actuation_observation is None
    # a complete bundle validates structurally
    b.validate_structure()


# 2. immutability after seal
def test_immutability_after_seal() -> None:
    b = _bundle()
    for target, attr in ((b, "bundle_id"), (b.payload, "txn_amount"),
                         (b.payload.txn_amount, "value"),
                         (b.payload.txn_amount.provenance, "producer_id")):
        try:
            setattr(target, attr, "mutated")
            raise AssertionError("expected FrozenInstanceError setting %s" % attr)
        except dataclasses.FrozenInstanceError:
            pass
    # the node vector is an immutable tuple (no append)
    assert isinstance(b.payload.node_predicate_vector, tuple)
    assert not hasattr(b.payload.node_predicate_vector, "append")


# 3. canonical serialization determinism
def test_canonical_serialization_determinism() -> None:
    a = _bundle().canonical_json()
    b = _bundle().canonical_json()
    assert a == b, "identical inputs must yield byte-identical canonical form"
    # sort_keys => envelope keys are alphabetical; deterministic separators => no spaces
    assert a.startswith('{"bundle_id":'), "keys must be sorted (bundle_id first)"
    assert ", " not in a and ": " not in a, "separators must be deterministic (no spaces)"


# 4. integrity digest recomputation
def test_integrity_digest_recompute() -> None:
    b = _bundle()
    assert len(b.integrity_digest) == 64
    assert b.verify_integrity() is True
    assert b.compute_integrity_digest() == b.integrity_digest
    # tampering with the digest is detected
    tampered = dataclasses.replace(b, integrity_digest="0" * 64)
    assert tampered.verify_integrity() is False


# 5. version metadata
def test_version_metadata() -> None:
    b = _bundle()
    assert b.schema_version == SCHEMA_VERSION
    assert SCHEMA_VERSION
    assert isinstance(b.method_version, str) and b.method_version


# 6. structural validation rejects an incomplete bundle (shape only)
def test_validate_structure_rejects_incomplete() -> None:
    bad_payload = dataclasses.replace(_payload(), node_predicate_vector=())
    bad = ExecutionEvidenceBundle.seal(
        bundle_id="b-2", created_at="2026-01-01T00:00:00.000Z", payload=bad_payload,
    )
    try:
        bad.validate_structure()
        raise AssertionError("expected ValueError for empty node_predicate_vector")
    except ValueError:
        pass


def _run_all() -> int:
    checks = [
        test_field_structure,
        test_immutability_after_seal,
        test_canonical_serialization_determinism,
        test_integrity_digest_recompute,
        test_version_metadata,
        test_validate_structure_rejects_incomplete,
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
    print("EEB data-contract self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
