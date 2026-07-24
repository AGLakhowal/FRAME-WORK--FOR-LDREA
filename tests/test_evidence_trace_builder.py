"""Commit 5.1 (narrowed transport subset) — Class-blind evidence trace builder self-test.

ENGINEERING tests only (no engine decisions): deterministic bundle generation, replay stability,
Class-blindness, provenance preservation, and bundle sealing. Standard library + project modules
only; no pytest. Run:
    python3 tests/test_evidence_trace_builder.py     # standalone; exits 0 on success

The builder constructs a sealed evidence-only EEB and STOPS — it performs no predicate
generation / gate binding / thresholding and never feeds the frozen engine. These tests do NOT
exercise evaluate_decision / Gamma / SAFE_STATE.
"""
from __future__ import annotations

import ast
import hashlib
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import evidence_trace_builder as etb  # noqa: E402
from runtime_context.evidence_trace_builder import build_evidence_bundle  # noqa: E402
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    ExecutionEvidenceBundle, OriginPlane, EvidenceQuality,
)

# A fixed, fully-injected request + runtime (deterministic; no wall clock).
_REQUEST = {"Amount": 149.62, "Time": 406, "V1": 0.1, "V2": 0.2, "TxnActionRef": "pay:42"}
_RUNTIME = {
    "decision_time": 100, "context_capture_time": 70, "heartbeat_time": 90,
    "commit_time": 10, "actuate_time": 20, "request_id": "req-1",
}
_KW = dict(bundle_id="EEB-5_1-0001", created_at="2026-01-01T00:00:00.000Z",
           runtime=_RUNTIME, observed_at="t")


# 1. Deterministic bundle generation — identical inputs -> byte-identical bundle
def test_deterministic_generation() -> None:
    a = build_evidence_bundle(dict(_REQUEST), **_KW)
    b = build_evidence_bundle(dict(_REQUEST), **_KW)
    assert a.canonical_json() == b.canonical_json(), "identical inputs must yield identical bundles"
    assert a.integrity_digest == b.integrity_digest


# 2. Replay stability — persist -> reload -> byte-identical; digest recomputes (no deserializer)
def test_replay_stability() -> None:
    bundle = build_evidence_bundle(dict(_REQUEST), **_KW)
    canonical = bundle.canonical_json()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "trace.json"
        p.write_text(canonical, encoding="utf-8")
        reloaded = p.read_text(encoding="utf-8")
    assert reloaded == canonical, "persisted canonical form must reload byte-identical"
    assert hashlib.sha256(reloaded.encode("utf-8")).hexdigest() == bundle.integrity_digest


# 3. Class-blindness — Class present / absent / different -> identical bundle; Class never read
def test_class_blindness() -> None:
    base = build_evidence_bundle(dict(_REQUEST), **_KW)
    c0 = build_evidence_bundle(dict(_REQUEST, Class=0), **_KW)
    c1 = build_evidence_bundle(dict(_REQUEST, Class=1), **_KW)
    assert base.canonical_json() == c0.canonical_json() == c1.canonical_json(), \
        "Class must not influence the evidence bundle"
    # structural: the builder source never references Class
    src = Path(etb.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value != "Class", "builder must not reference the Class column"


# 4. Provenance preservation — each field keeps its producer's plane/quality
def test_provenance_preservation() -> None:
    p = build_evidence_bundle(dict(_REQUEST), **_KW).payload
    # plane A from the interpreter (present, self-reported)
    assert p.txn_amount.provenance.origin_plane == OriginPlane.A
    assert p.txn_amount.value == 149.62
    assert p.txn_amount.provenance.evidence_quality == EvidenceQuality.PRESENT
    # plane B freshness carried as a RAW DELTA (verbatim, not a boolean/threshold)
    assert p.stale_context.provenance.origin_plane == OriginPlane.B
    assert p.stale_context.value == 30 and not isinstance(p.stale_context.value, bool)
    assert p.telemetry_fresh.value == 10
    # plane C authority evidence — ABSENT
    assert p.node_predicate_vector[0].provenance.origin_plane == OriginPlane.C
    assert all(g.provenance.evidence_quality == EvidenceQuality.ABSENT
               for g in p.node_predicate_vector)
    # plane D governance hazard — ABSENT
    assert p.harm_risk_score.provenance.origin_plane == OriginPlane.D
    assert p.harm_risk_score.provenance.evidence_quality == EvidenceQuality.ABSENT
    # E-cached ledger link — ABSENT
    assert p.prior_ledger_link.provenance.origin_plane == OriginPlane.E_CACHED
    # no class-veto / actuation mapping performed (left absent)
    assert p.class_veto_evidence is None and p.actuation_observation is None


# 5. Bundle sealing — integrity verifies; structural validation passes
def test_bundle_sealing() -> None:
    bundle = build_evidence_bundle(dict(_REQUEST), **_KW)
    assert isinstance(bundle, ExecutionEvidenceBundle)
    bundle.validate_structure()  # shape + provenance completeness (no value judgement)
    assert bundle.verify_integrity() is True
    assert isinstance(bundle.integrity_digest, str) and len(bundle.integrity_digest) == 64


# 6. Absent plane-B when no runtime clocks are injected (honest, not fabricated)
def test_absent_plane_b_without_runtime() -> None:
    bundle = build_evidence_bundle(dict(_REQUEST), bundle_id="b", created_at="t")
    p = bundle.payload
    assert p.stale_context.provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.telemetry_fresh.provenance.evidence_quality == EvidenceQuality.ABSENT
    assert p.commit_timestamp is None and p.actuate_timestamp is None


# 7. No engine coupling: the builder must not import or call the frozen engine
def test_no_engine_coupling() -> None:
    tree = ast.parse(Path(etb.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "gamma_test_runner" not in (node.module or ""), "builder must not import the engine"
        if isinstance(node, ast.Import):
            for a in node.names:
                assert "gamma_test_runner" not in a.name
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"evaluate_decision"}, "builder must not call the engine"


def _run_all() -> int:
    checks = [
        test_deterministic_generation,
        test_replay_stability,
        test_class_blindness,
        test_provenance_preservation,
        test_bundle_sealing,
        test_absent_plane_b_without_runtime,
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
    print("evidence_trace_builder self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
