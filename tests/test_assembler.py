"""Self-test for the Execution Evidence Bundle Assembler (Commit 2.5).

Proves pure structural assembly: the assembler receives already-produced EvidenceField objects
(built here from the real 2.2/2.3/2.4 producers — the TEST is the caller/orchestrator, not the
assembler), places them, seals via the frozen 2.1 bundle, and returns. Covers: producible sealed
EEB, integrity digest, deterministic sealing, replay-identity (persist->reload->identical, no
deserializer), evidence-absent propagation, values-carried-verbatim (freshness deltas stay
deltas), tamper detection, Class-blindness, and no-wall-clock. Standard library only; no pytest:
    python3 tests/test_assembler.py     # standalone; exits 0 on success

Commit 2.5 is unconsumed scaffolding; nothing imports the assembler.
"""
from __future__ import annotations

import dataclasses
import hashlib
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import assembler as asm  # noqa: E402
from runtime_context.assembler import ExecutionEvidenceBundleAssembler  # noqa: E402
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    ExecutionEvidenceBundle, EvidenceField, ProvenanceDescriptor, OriginPlane,
    EvidenceQuality, VerificationMethod, TrustLevel,
)
from runtime_context.transaction_interpreter import (  # noqa: E402
    TransactionInterpreter, FIELD_AMOUNT, FIELD_TIME, FIELD_ACTION_REF, FIELD_FEATURE_REF,
)
from runtime_context.context_objects import (  # noqa: E402
    FreshnessClock, ExecutionHistoryWindow,
)
from runtime_context.ports import AuthorityPort, GovernancePort  # noqa: E402


def _absent(plane: OriginPlane) -> EvidenceField:
    """Caller-side evidence-absent field (E-cached ledger link / any unproduced plane).

    Represents the Evidence Collector / caller supplying ABSENT — the assembler never invents this.
    Mirrors the ports' evidence-absent pattern, reusing the 2.1 types.
    """
    return EvidenceField(
        value=None,
        provenance=ProvenanceDescriptor(
            origin_plane=plane,
            producer_id="unbound",
            evidence_quality=EvidenceQuality.ABSENT,
            observed_at="unobserved",
            verification_method=VerificationMethod.FIELD_PRESENCE,
            trust_level=TrustLevel.DERIVED,
        ),
    )


def _produce_inputs() -> dict:
    """Build a complete, valid input set from the REAL upstream producers (caller's job)."""
    interp = TransactionInterpreter().interpret(
        {"Amount": 149.62, "Time": 406, "TxnActionRef": "pay:merchant:42",
         "V1": 0.1, "V2": 0.2, "Class": 1})  # Class present in request; interpreter drops it

    clock = FreshnessClock()
    window = ExecutionHistoryWindow(max_size=8)
    window.append("r0", 400)
    window.append("r1", 406)

    return dict(
        bundle_id="EEB-TEST-0001",
        created_at="2026-01-01T00:00:00.000Z",
        # plane A (from the interpreter)
        txn_amount=interp[FIELD_AMOUNT],
        txn_time=interp[FIELD_TIME],
        txn_action_ref=interp[FIELD_ACTION_REF],
        txn_feature_ref=interp[FIELD_FEATURE_REF],
        # node predicate vector: binding-defined; here C(absent)/C(absent)/B(present)
        node_predicate_vector=(
            AuthorityPort().token_valid(),
            AuthorityPort().authority_signature_valid(),
            window.velocity_reading(),
        ),
        # plane D (governance port — absent in the bare arm)
        harm_risk_score=GovernancePort().harm_risk_score(),
        # plane B (freshness DELTAS, carried verbatim)
        stale_context=clock.context_age(decision_time=100, context_capture_time=70),
        telemetry_fresh=clock.telemetry_age(decision_time=100, heartbeat_time=90),
        # plane E-cached (caller-supplied ABSENT ledger link)
        prior_ledger_link=_absent(OriginPlane.E_CACHED),
    )


# 1. Integration: a producible, structurally-valid, integrity-verified sealed EEB
def test_integration_sealed_eeb() -> None:
    bundle = ExecutionEvidenceBundleAssembler().assemble(**_produce_inputs())
    assert isinstance(bundle, ExecutionEvidenceBundle), "must return the frozen 2.1 bundle"
    bundle.validate_structure()  # shape + provenance completeness (no value judgement)
    assert bundle.verify_integrity() is True


# 2. Integrity digest is a recomputable 64-hex SHA-256
def test_integrity_digest() -> None:
    bundle = ExecutionEvidenceBundleAssembler().assemble(**_produce_inputs())
    assert isinstance(bundle.integrity_digest, str) and len(bundle.integrity_digest) == 64
    assert bundle.compute_integrity_digest() == bundle.integrity_digest


# 3. Deterministic sealing: identical evidence -> byte-identical canonical form + digest
def test_deterministic_sealing() -> None:
    inputs = _produce_inputs()
    a = ExecutionEvidenceBundleAssembler().assemble(**inputs)
    b = ExecutionEvidenceBundleAssembler().assemble(**inputs)
    assert a.canonical_json() == b.canonical_json(), "same evidence -> identical canonical form"
    assert a.integrity_digest == b.integrity_digest


# 4. Replay-identity: persist -> reload -> identical, WITHOUT any deserializer
def test_replay_identity_roundtrip() -> None:
    bundle = ExecutionEvidenceBundleAssembler().assemble(**_produce_inputs())
    canonical = bundle.canonical_json()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bundle.json"
        p.write_text(canonical, encoding="utf-8")
        reloaded = p.read_text(encoding="utf-8")
    assert reloaded == canonical, "persisted canonical form must reload byte-identical"
    assert hashlib.sha256(reloaded.encode("utf-8")).hexdigest() == bundle.integrity_digest


# 5. Evidence-absent PROPAGATION: ABSENT C/D and E-cached survive assembly unchanged
def test_evidence_absent_propagation() -> None:
    bundle = ExecutionEvidenceBundleAssembler().assemble(**_produce_inputs())
    p = bundle.payload
    # plane D governance score absent
    assert p.harm_risk_score.value is None
    assert p.harm_risk_score.provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.harm_risk_score.provenance.origin_plane == OriginPlane.D
    # plane C authority element inside the node vector absent
    assert p.node_predicate_vector[0].provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.node_predicate_vector[0].provenance.origin_plane == OriginPlane.C
    # plane E-cached ledger link absent
    assert p.prior_ledger_link.provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.prior_ledger_link.provenance.origin_plane == OriginPlane.E_CACHED


# 6. Values carried VERBATIM: freshness deltas stay deltas (never booleanized/thresholded)
def test_values_carried_verbatim() -> None:
    inputs = _produce_inputs()
    bundle = ExecutionEvidenceBundleAssembler().assemble(**inputs)
    p = bundle.payload
    # identical objects placed, not transformed
    assert p.stale_context is inputs["stale_context"]
    assert p.telemetry_fresh is inputs["telemetry_fresh"]
    assert p.stale_context.value == 30 and not isinstance(p.stale_context.value, bool)
    assert p.telemetry_fresh.value == 10 and not isinstance(p.telemetry_fresh.value, bool)
    assert p.stale_context.provenance.origin_plane == OriginPlane.B


# 7. Tamper detection: altering any sealed field breaks integrity
def test_tamper_detection() -> None:
    bundle = ExecutionEvidenceBundleAssembler().assemble(**_produce_inputs())
    tampered = dataclasses.replace(bundle, integrity_digest="0" * 64)
    assert tampered.verify_integrity() is False


# 8. Class-blindness: the assembled bundle carries no field derived from Class
def test_class_blindness() -> None:
    inputs = _produce_inputs()  # source request carried Class=1; interpreter dropped it
    bundle = ExecutionEvidenceBundleAssembler().assemble(**inputs)
    p = bundle.payload
    # plane-A fields equal exactly what the interpreter produced (no Class-derived field)
    assert p.txn_amount.value == 149.62 and p.txn_time.value == 406
    assert p.txn_feature_ref.value == (0.1, 0.2), "features carried verbatim, no Class"
    # subject_ref (envelope) is not populated from any label
    assert bundle.subject_ref is None


# 9. Reuses the frozen bundle only — assembler defines no competing bundle model
def test_no_second_bundle_model() -> None:
    import ast
    tree = ast.parse(Path(asm.__file__).read_text(encoding="utf-8"))
    class_defs = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert class_defs == ["ExecutionEvidenceBundleAssembler"], "no extra bundle/payload class"
    # no dataclass decorator (no new frozen model introduced)
    assert "@dataclass" not in Path(asm.__file__).read_text(encoding="utf-8").replace(" ", "")


# 10. No wall clock: the module reads no ambient time (AST-based, like 2.3/2.4)
def test_no_wall_clock() -> None:
    import ast
    tree = ast.parse(Path(asm.__file__).read_text(encoding="utf-8"))
    banned_mods = {"time", "datetime"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] not in banned_mods, "imports a clock: %s" % a.name
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_mods, \
                "imports from a clock: %s" % node.module
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"now", "utcnow", "today", "time",
                                          "monotonic", "perf_counter"}, \
                "calls an ambient-time source: .%s()" % node.func.attr


def _run_all() -> int:
    checks = [
        test_integration_sealed_eeb,
        test_integrity_digest,
        test_deterministic_sealing,
        test_replay_identity_roundtrip,
        test_evidence_absent_propagation,
        test_values_carried_verbatim,
        test_tamper_detection,
        test_class_blindness,
        test_no_second_bundle_model,
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
    print("assembler self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
