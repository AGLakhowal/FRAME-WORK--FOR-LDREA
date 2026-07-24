"""Commit 5.1-B — Runtime Predicate Binding `B` self-test.

Verifies the binding layer implements EXACTLY the three admissible outcomes of
PREDICATE_BINDING_SCIENTIFIC_SPECIFICATION.md §3 — carry / absent->fail-closed / out-of-slice —
as a pure, Class-blind, deterministic, provenance-preserving transform, and that the resulting
bound EEB feeds the FROZEN Commit-4.1 adapter and the FROZEN evaluate_decision without changing
any scientific behaviour.

Checks:
  1. connection (fail-closed) — an authentic credit-card evidence-only trace -> B -> 4.1 adapter
     -> FROZEN evaluate_decision yields SAFE_STATE (Gap-3(a) full-vector fail-closed).
  2. connection (carry) — a fully-bound source vector is CARRIED verbatim; the frozen engine
     yields PERMIT. Proves B is a faithful transform, not hardcoded to deny.
  3. no-threshold — a PRESENT raw freshness DELTA is NOT carried into the boolean slot (B never
     thresholds); it fail-closes.
  4. Class-blindness — Class present/absent/different -> byte-identical bound EEB; B never refs Class.
  5. determinism / replay — identical inputs -> byte-identical bound EEB (canonical + digest).
  6. provenance + native-plane origin — carried fields keep their plane; fail-closed fields are
     tagged their native plane with quality ABSENT.
  7. sealing — the bound EEB validates structurally and its integrity digest verifies.
  8. no engine coupling — the module imports no engine and calls no decision function.

Standard library + project modules only; no pytest. Run (needs the project venv for pandas/numpy
via the frozen engine import):
    .venv/bin/python tests/test_predicate_binding.py     # standalone; exits 0 on success

The frozen decision logic (evaluate_decision) and the Commit-4.1 adapter are UNTOUCHED.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import predicate_binding as pb  # noqa: E402
from runtime_context.predicate_binding import PredicateBinding, bind_evidence_to_schema  # noqa: E402
from runtime_context.evidence_trace_builder import build_evidence_bundle  # noqa: E402
from runtime_context.assembler import ExecutionEvidenceBundleAssembler  # noqa: E402
from runtime_context.eeb_to_engine import (  # noqa: E402
    decision_inputs_from_eeb, HARM_COL, STALE_COL, FRESH_COL, VETO_COL,
)
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod, ExecutionEvidenceBundle,
)
from gamma_test_runner import evaluate_decision, NODE_GATE_COLS  # noqa: E402

# A fixed, fully-injected credit-card request (+ Class, which the interpreter must drop).
_REQUEST = {"Amount": 149.62, "Time": 406, "V1": 0.1, "V2": 0.2, "TxnActionRef": "pay:42", "Class": 1}
_KW = dict(bundle_id="EEB-5_1B-0001", created_at="2026-01-01T00:00:00.000Z", observed_at="t")


def _decision_from_bound(bound: ExecutionEvidenceBundle) -> dict:
    """Chain the bound EEB through the FROZEN 4.1 adapter + FROZEN engine (audit actuation
    fields are post-observation / absent -> not actuated; non-material to Gamma/Pi, Gap 1)."""
    row = decision_inputs_from_eeb(bound, NODE_GATE_COLS)
    row.update({"Actuated": False, "ACT_PERMIT": False})
    return evaluate_decision(row, 0.5)


# --------------------------------------------------------------------------- #
# TEST-ONLY helper: a fully-BOUND source EEB (10 PRESENT boolean gates), to exercise the CARRY
# path. This is a synthetic upstream-bound deployment, NOT the credit-card arm.
# --------------------------------------------------------------------------- #
def _ef(value, plane, quality=EvidenceQuality.PRESENT) -> EvidenceField:
    return EvidenceField(value, ProvenanceDescriptor(
        plane, "test-arm", quality, "t", VerificationMethod.FIELD_PRESENCE, TrustLevel.DERIVED))


def _bound_source(*, gates=True, harm=0.0, stale=False, fresh=True,
                  veto="CLASS_0_LEGITIMATE;ALL_GATES_PASS") -> ExecutionEvidenceBundle:
    return ExecutionEvidenceBundleAssembler().assemble(
        bundle_id="bound-src", created_at="t",
        txn_amount=_ef(1.0, OriginPlane.A), txn_time=_ef(1, OriginPlane.A),
        txn_action_ref=_ef("a", OriginPlane.A),
        node_predicate_vector=tuple(_ef(bool(gates), OriginPlane.C) for _ in NODE_GATE_COLS),
        harm_risk_score=_ef(harm, OriginPlane.D),
        stale_context=_ef(bool(stale), OriginPlane.B),
        telemetry_fresh=_ef(bool(fresh), OriginPlane.B),
        class_veto_evidence=_ef(veto, OriginPlane.D),
        prior_ledger_link=_ef(None, OriginPlane.E_CACHED, EvidenceQuality.ABSENT),
    )


# 1. CONNECTION (fail-closed): authentic credit-card evidence -> B -> 4.1 -> frozen engine = SAFE_STATE
def test_connection_failclosed_safe_state() -> None:
    evidence = build_evidence_bundle(dict(_REQUEST), **_KW)
    bound = PredicateBinding().bind(evidence, NODE_GATE_COLS)
    dec = _decision_from_bound(bound)
    assert dec["decision"] == "SAFE_STATE", "credit-card arm must fail-closed to SAFE_STATE"
    assert dec["pi"] == 0 and dec["gamma_g"] == 1, "full-vector fail-closed: Gamma_G=1, Pi=0"


# 2. CONNECTION (carry): a fully-bound source is carried verbatim; frozen engine yields PERMIT
def test_connection_carry_permit() -> None:
    bound = PredicateBinding().bind(_bound_source(), NODE_GATE_COLS)
    dec = _decision_from_bound(bound)
    assert dec["decision"] == "PERMIT" and dec["pi"] == 1, \
        "B must carry a permit-eligible bound schema verbatim (faithful transform, not deny-only)"
    # a single failed gate in the source must carry through to SAFE_STATE
    dec_deny = _decision_from_bound(PredicateBinding().bind(_bound_source(gates=False), NODE_GATE_COLS))
    assert dec_deny["decision"] == "SAFE_STATE"


# 3. NO-THRESHOLD: a PRESENT raw freshness delta is NOT carried into the boolean slot
def test_no_threshold_on_raw_delta() -> None:
    runtime = {"decision_time": 100, "context_capture_time": 70, "heartbeat_time": 90}
    evidence = build_evidence_bundle(dict(_REQUEST), runtime=runtime, **_KW)
    # sanity: the evidence trace carries a RAW numeric delta (30), not a boolean
    assert evidence.payload.stale_context.value == 30
    bound = PredicateBinding().bind(evidence, NODE_GATE_COLS)
    # B must fail-closed (True), never carry/threshold the number 30
    assert bound.payload.stale_context.value is True, "B must not carry/threshold a raw delta"
    assert bound.payload.telemetry_fresh.value is False


# 4. CLASS-BLINDNESS: Class present/absent/different -> identical bound EEB; source never refs Class
def test_class_blindness() -> None:
    b_none = PredicateBinding().bind(build_evidence_bundle({k: v for k, v in _REQUEST.items()
                                                            if k != "Class"}, **_KW), NODE_GATE_COLS)
    b0 = PredicateBinding().bind(build_evidence_bundle(dict(_REQUEST, Class=0), **_KW), NODE_GATE_COLS)
    b1 = PredicateBinding().bind(build_evidence_bundle(dict(_REQUEST, Class=1), **_KW), NODE_GATE_COLS)
    assert b_none.canonical_json() == b0.canonical_json() == b1.canonical_json(), \
        "Class must not influence the bound EEB"
    tree = ast.parse(Path(pb.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value != "Class", "binding must not reference the Class column"


# 5. DETERMINISM / REPLAY: identical inputs -> byte-identical bound EEB
def test_determinism() -> None:
    ev = build_evidence_bundle(dict(_REQUEST), **_KW)
    a = PredicateBinding().bind(ev, NODE_GATE_COLS)
    b = bind_evidence_to_schema(ev, NODE_GATE_COLS)
    assert a.canonical_json() == b.canonical_json(), "identical inputs must yield identical bundles"
    assert a.integrity_digest == b.integrity_digest


# 6. PROVENANCE + NATIVE-PLANE ORIGIN (fail-closed arm) and CARRY provenance preservation
def test_provenance_and_native_plane() -> None:
    p = PredicateBinding().bind(build_evidence_bundle(dict(_REQUEST), **_KW), NODE_GATE_COLS).payload
    # gates: authority-plane C, ABSENT, fail-closed False
    for g in p.node_predicate_vector:
        assert g.provenance.origin_plane == OriginPlane.C
        assert g.provenance.evidence_quality == EvidenceQuality.ABSENT and g.value is False
    # HARM: plane D, ABSENT, no-hazard placeholder
    assert p.harm_risk_score.provenance.origin_plane == OriginPlane.D
    assert p.harm_risk_score.provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.harm_risk_score.value == 0.0
    # freshness: plane B, fail-closed
    assert p.stale_context.provenance.origin_plane == OriginPlane.B and p.stale_context.value is True
    assert p.telemetry_fresh.provenance.origin_plane == OriginPlane.B and p.telemetry_fresh.value is False
    # class-veto: plane D, empty (Class never read)
    assert p.class_veto_evidence.provenance.origin_plane == OriginPlane.D
    assert p.class_veto_evidence.value == ""
    # plane-A observable carried VERBATIM (provenance + value preserved)
    assert p.txn_amount.provenance.origin_plane == OriginPlane.A and p.txn_amount.value == 149.62
    # CARRY path preserves the source provenance verbatim
    carried = PredicateBinding().bind(_bound_source(), NODE_GATE_COLS).payload
    assert all(g.value is True and g.provenance.evidence_quality == EvidenceQuality.PRESENT
               for g in carried.node_predicate_vector)


# 7. SEALING: the bound EEB validates structurally and its integrity verifies
def test_bound_bundle_sealing() -> None:
    bound = PredicateBinding().bind(build_evidence_bundle(dict(_REQUEST), **_KW), NODE_GATE_COLS)
    assert isinstance(bound, ExecutionEvidenceBundle)
    bound.validate_structure()
    assert bound.verify_integrity() is True
    assert len(bound.integrity_digest) == 64


# 8. NO ENGINE COUPLING: the module imports no engine and calls no decision function
def test_no_engine_coupling() -> None:
    tree = ast.parse(Path(pb.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "gamma_test_runner" not in (node.module or ""), "binding must not import the engine"
        if isinstance(node, ast.Import):
            for a in node.names:
                assert "gamma_test_runner" not in a.name
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"evaluate_decision"}, "binding must not call the engine"


def _run_all() -> int:
    checks = [
        test_connection_failclosed_safe_state,
        test_connection_carry_permit,
        test_no_threshold_on_raw_delta,
        test_class_blindness,
        test_determinism,
        test_provenance_and_native_plane,
        test_bound_bundle_sealing,
        test_no_engine_coupling,
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
    print("predicate_binding self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
