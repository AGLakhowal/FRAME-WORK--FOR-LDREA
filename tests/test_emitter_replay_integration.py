"""Class-blind emitter -> existing replay pipeline: ONE integration test.

Generates a small deterministic ledger chain with the Class-Blind Reported Artifact Emitter,
feeds that chain through the EXISTING replay pipeline (the FROZEN `write_replay_manifest` emitter
and the FROZEN independent verifier `gamma_replay_verify.py`), and verifies:

  * replay PASS (independent verifier exit 0, RESULT: PASS)
  * ledger adjacency preserved (genesis-anchored; hash_prev[i] == hash_current[i-1])
  * deterministic hashes (re-emit -> byte-identical manifest + identical SHA-256)
  * provenance preserved (each record links to its sealed EEB; evidence_quad.ledger_hash binds)
  * no benchmark changes (writes only to a temp dir; repo reported artifacts untouched)

Modifies NO implementation logic and NO frozen component. Standard library + project modules; no
pytest. Run (project venv, for pandas + the frozen replay emitter):
    .venv/bin/python tests/test_emitter_replay_integration.py     # standalone; exits 0 on success
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from runtime_context.reported_artifact_emitter import ReportedArtifactEmitter, GENESIS  # noqa: E402
from runtime_context.evidence_trace_builder import build_evidence_bundle  # noqa: E402
from runtime_context.predicate_binding import PredicateBinding  # noqa: E402
from runtime_context.eeb_to_engine import decision_inputs_from_eeb  # noqa: E402
from runtime_context.assembler import ExecutionEvidenceBundleAssembler  # noqa: E402
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)
from gamma_test_runner import evaluate_decision, write_replay_manifest, NODE_GATE_COLS  # noqa: E402

_RUN = "EMITTER_REPLAY_INTEG_001"
# Repo reported artifacts that MUST NOT be touched by this test (benchmark-stability guard).
_REPORTED = [ROOT / "gamma_replay_manifest.jsonl", ROOT / "gamma_summary.json",
             ROOT / "gamma_lab_v1_report.json"]


def _ef(value, plane, quality=EvidenceQuality.PRESENT):
    return EvidenceField(value, ProvenanceDescriptor(
        plane, "integ-arm", quality, "t", VerificationMethod.FIELD_PRESENCE, TrustLevel.DERIVED))


def _permit_source_eeb():
    """A fully-bound source EEB (10 PRESENT True gates) -> the frozen engine yields PERMIT."""
    return ExecutionEvidenceBundleAssembler().assemble(
        bundle_id="permit-src", created_at="t",
        txn_amount=_ef(1.0, OriginPlane.A), txn_time=_ef(5, OriginPlane.A),
        txn_action_ref=_ef("a", OriginPlane.A),
        node_predicate_vector=tuple(_ef(True, OriginPlane.C) for _ in NODE_GATE_COLS),
        harm_risk_score=_ef(0.0, OriginPlane.D),
        stale_context=_ef(False, OriginPlane.B), telemetry_fresh=_ef(True, OriginPlane.B),
        class_veto_evidence=_ef("CLASS_0_LEGITIMATE;ALL_GATES_PASS", OriginPlane.D),
        prior_ledger_link=_ef(None, OriginPlane.E_CACHED, EvidenceQuality.ABSENT))


def _decision_for(eeb):
    """Run the frozen pipeline (5.1-B -> 4.1 -> engine) to source a genuine decision for `eeb`."""
    bound = PredicateBinding().bind(eeb, NODE_GATE_COLS)
    row = decision_inputs_from_eeb(bound, NODE_GATE_COLS)
    row.update({"Actuated": False, "ACT_PERMIT": False})
    return evaluate_decision(row, 0.5), row["HARM_RISK"]


def _build_rows():
    """Deterministic mixed chain: three SAFE_STATE (credit-card evidence) + one PERMIT (bound src)."""
    rows = []
    for t in (100, 50, 200):
        eeb = build_evidence_bundle({"Amount": 10.0 + t, "Time": t, "V1": 0.1, "Class": 1},
                                    bundle_id="EEB-%d" % t, created_at="c", observed_at="o")
        dec, harm = _decision_for(eeb)
        rows.append((dec, harm, 10.0 + t, t, eeb))
    peeb = _permit_source_eeb()
    pdec, pharm = _decision_for(peeb)
    rows.append((pdec, pharm, 1.0, 5, peeb))
    return rows


def _policy_hash():
    try:
        from runtime_context.ports import PolicyPort
        return PolicyPort().merkle_root()                      # Class-independent frozen Merkle root
    except Exception:
        return "0" * 64                                        # environment-graceful deterministic fallback


def _emit_chain(rows, policy_hash):
    items = [dict(decision=dec, harm=harm, amount=amt, time=t, policy_hash=policy_hash,
                  method_version="m/1", evidence_bundle=eeb)
             for (dec, harm, amt, t, eeb) in rows]
    return ReportedArtifactEmitter().emit_chain(items, run_id=_RUN)


def _manifest_df(chain, rows):
    """Assemble the columns the FROZEN write_replay_manifest reads: chain hashes/ids/policy from the
    emitter; decision-derived columns from the frozen engine output."""
    dec = [r[0] for r in rows]
    return pd.DataFrame({
        "HASH_prev": [c["HASH_prev"] for c in chain],
        "HASH_current": [c["HASH_current"] for c in chain],
        "ProposalID": [c["ProposalID"] for c in chain],
        "ERTuple_ID": [c["ERTuple_ID"] for c in chain],
        "PolicyHash": [c["PolicyHash"] for c in chain],
        "DerivedDecision": [d["decision"] for d in dec],
        "DerivedGammaG": [d["gamma_g"] for d in dec],
        "DerivedGammaClass": [d["gamma_class"] for d in dec],
        "DerivedPi": [d["pi"] for d in dec],
        "DerivedChainLinked": [True] * len(dec),
        "DerivedUnauthorized": [d["unauthorized"] for d in dec],
    })


def test_emitter_chain_through_replay_pipeline() -> None:
    # -- benchmark-stability guard: snapshot repo reported artifacts' mtimes BEFORE -- #
    before = {p: (p.stat().st_mtime_ns if p.exists() else None) for p in _REPORTED}

    rows = _build_rows()
    policy_hash = _policy_hash()

    # -- generate the deterministic emitter chain -- #
    chain = _emit_chain(rows, policy_hash)
    assert [c["Status"] for c in chain] == ["SAFE_STATE", "SAFE_STATE", "SAFE_STATE", "PERMIT"], \
        "decisions must be carried verbatim from the frozen engine"

    # -- ledger adjacency preserved (in-memory) -- #
    assert str(chain[0]["HASH_prev"]).upper() == GENESIS, "chain must be genesis-anchored"
    for i in range(1, len(chain)):
        assert chain[i]["HASH_prev"] == chain[i - 1]["HASH_current"], "adjacency must hold"

    # -- provenance preserved: each record links to its sealed EEB -- #
    for c, (_, _, _, _, eeb) in zip(chain, rows):
        assert c["EvidenceBundleID"] == eeb.bundle_id
        assert c["EvidenceBundleDigest"] == eeb.integrity_digest and len(c["EvidenceBundleDigest"]) == 64
        assert c["PolicyHash"] == policy_hash

    with tempfile.TemporaryDirectory() as d:
        m1 = Path(d) / "emitter_chain_manifest.jsonl"
        m2 = Path(d) / "emitter_chain_manifest_rerun.jsonl"

        # -- feed the emitter chain through the FROZEN replay-manifest emitter -- #
        s1 = write_replay_manifest(_manifest_df(chain, rows), m1)
        assert s1["genesis_anchored"] and s1["adjacency_all_ok"], "frozen emitter: adjacency must hold"

        # -- deterministic hashes: re-emit the chain -> byte-identical manifest + identical SHA -- #
        s2 = write_replay_manifest(_manifest_df(_emit_chain(rows, policy_hash), rows), m2)
        assert s1["manifest_sha256"] == s2["manifest_sha256"], "re-emitted manifest SHA must match"
        assert m1.read_bytes() == m2.read_bytes(), "re-emitted manifest must be byte-identical"

        # -- feed the manifest into the EXISTING independent verifier (frozen) -- #
        proc = subprocess.run(
            [sys.executable, str(ROOT / "gamma_replay_verify.py"), str(m1),
             "--expect-sha256", s1["manifest_sha256"]],
            capture_output=True, text=True)
        assert proc.returncode == 0, "independent replay verifier must exit 0\n%s" % proc.stdout
        assert "RESULT              : PASS" in proc.stdout, proc.stdout
        assert "adjacency failures  : 0" in proc.stdout and "ledger-bind failures: 0" in proc.stdout
        assert "consistency failures: 0" in proc.stdout
        assert "expected SHA-256    : MATCH" in proc.stdout, "manifest SHA must match (deterministic)"

    # -- no benchmark changes: repo reported artifacts untouched -- #
    after = {p: (p.stat().st_mtime_ns if p.exists() else None) for p in _REPORTED}
    assert before == after, "test must not modify any repo reported artifact"


def _run_all() -> int:
    failures = 0
    for fn in (test_emitter_chain_through_replay_pipeline,):
        try:
            fn()
            print("  PASS  %s" % fn.__name__)
        except AssertionError as exc:
            failures += 1
            print("  FAIL  %s: %s" % (fn.__name__, exc))
    print("-" * 60)
    print("emitter_replay_integration: %d/%d passed" % (1 - failures, 1))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
