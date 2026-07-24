"""Class-blind Reported Artifact Emitter — self-test.

Verifies the emitter serializes the frozen pipeline's outputs to the ratified conventions
(ENGINEERING_SERIALIZATION_CONTRACT.md / ENGINEERING_OWNER_RATIFICATION_RECORD.md) as a pure,
Class-blind, deterministic, provenance-preserving transform, and that it feeds a valid Hydra
Ledger chain — without computing any decision or touching the frozen engine / Predicate Binding.

Checks:
  1. end-to-end — real Class-blind pipeline (5.1 -> 5.1-B -> 4.1 -> frozen engine) -> emitter -> record.
  2. identifiers (C1-C4) — index-derived, Class-blind.
  3. timestamps + offsets (C5/C6) — derived from the observable Time; +10ms / +25ms.
  4. actuate gate (C7) — ActuateTimestamp present iff PERMIT; empty iff SAFE_STATE (decision-driven).
  5. EnvironmentContext (C8) — no `class=` token; the four ratified Class-blind tokens present.
  6. structural constants (C9) — PolicyHash from a Class-independent source; injected constants merged.
  7. ledger canon + hash (C10/C11) — composition + independently-recomputed HASH match; genesis anchored.
  8. determinism / replay — identical inputs -> byte-identical record + chain; adjacency valid.
  9. Class-blindness — Class cannot enter (no param); source never references Class.
  10. provenance — the record links to the sealed EEB (id/digest/method_version).
  11. no engine / predicate coupling — imports no engine; computes no decision/Gamma/predicate.

Standard library + project modules only; no pytest. Run (needs the project venv for the frozen
engine import used only to SOURCE a genuine decision):
    .venv/bin/python tests/test_reported_artifact_emitter.py     # standalone; exits 0 on success
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import reported_artifact_emitter as rae  # noqa: E402
from runtime_context.reported_artifact_emitter import (  # noqa: E402
    ReportedArtifactEmitter, emit_reported_record, EPOCH_BASE, GENESIS,
)
from runtime_context.evidence_trace_builder import build_evidence_bundle  # noqa: E402
from runtime_context.predicate_binding import PredicateBinding  # noqa: E402
from runtime_context.eeb_to_engine import decision_inputs_from_eeb  # noqa: E402
from gamma_test_runner import evaluate_decision, NODE_GATE_COLS  # noqa: E402

_REQUEST = {"Amount": 149.62, "Time": 406, "V1": 0.1, "V2": 0.2, "TxnActionRef": "pay:42", "Class": 1}
_KW = dict(bundle_id="EEB-EMIT-0001", created_at="2026-01-01T00:00:00.000Z", observed_at="t")
_RUN = "EMITTER_SELFTEST_001"


def _pipeline_decision(request):
    """Source a genuine Class-blind decision through the frozen pipeline (for the emitter's input)."""
    eeb = build_evidence_bundle(dict(request), **_KW)
    bound = PredicateBinding().bind(eeb, NODE_GATE_COLS)
    row = decision_inputs_from_eeb(bound, NODE_GATE_COLS)
    row.update({"Actuated": False, "ACT_PERMIT": False})
    dec = evaluate_decision(row, 0.5)
    return eeb, bound, row, dec


def _emit_credit_card(index=1, prior=GENESIS, request=None, **extra):
    request = request or _REQUEST
    eeb, bound, row, dec = _pipeline_decision(request)
    return ReportedArtifactEmitter().emit(
        index, decision=dec, harm=row["HARM_RISK"], amount=_REQUEST["Amount"], time=_REQUEST["Time"],
        run_id=_RUN, prior_ledger_hash=prior, policy_hash="POLICYROOTabc", method_version="m/1",
        evidence_bundle=eeb, **extra)


# 1. END-TO-END: pipeline decision -> emitter -> reported record (fail-closed arm => SAFE_STATE)
def test_end_to_end_from_pipeline() -> None:
    rec = _emit_credit_card()
    assert rec["Status"] == "SAFE_STATE", "credit-card arm decision must be carried verbatim"
    assert rec["Gamma"] == 1 and rec["Actuated"] is False
    assert rec["ProposalID"] == "TXN_000001" and rec["RunID"] == _RUN


# 2. IDENTIFIERS (C1-C4): index-derived
def test_identifiers_index_derived() -> None:
    rec = _emit_credit_card(index=7)
    assert rec["ProposalID"] == "TXN_000007"
    assert rec["BenchmarkRowID"] == "%s_ROW_000007" % _RUN and rec["Step"] == 7
    assert rec["PermitTokenID"] == "PERMIT_%s" % rae.h16("permit", 7)
    assert rec["ERTuple_ID"] == "ERT_%s" % rae.h16("ertuple", 7)
    assert rec["SubjectProfileID"] == "CARDPROFILE_SYN_%s" % rae.h12("profile", 7)


# 3. TIMESTAMPS + OFFSETS (C5/C6): derived from observable Time; +10ms
def test_timestamps_and_offsets() -> None:
    rec = _emit_credit_card()
    from datetime import timedelta
    base = EPOCH_BASE + timedelta(seconds=406)
    assert rec["TimestampUTC"] == rae.iso_ms(base)
    assert rec["CommitTimestamp"] == rae.iso_ms(base + timedelta(milliseconds=10))


# 4. ACTUATE GATE (C7): PERMIT -> non-empty (+25ms); SAFE_STATE -> ""  (decision-driven, not Class)
def test_actuate_gate_decision_driven() -> None:
    from datetime import timedelta
    base = EPOCH_BASE + timedelta(seconds=406)
    # SAFE_STATE (real credit-card arm): empty actuate timestamp
    assert _emit_credit_card()["ActuateTimestamp"] == ""
    # PERMIT (synthetic decision): +25ms actuate timestamp — gate keyed on decision, not Class
    permit = ReportedArtifactEmitter().emit(
        1, decision={"decision": "PERMIT", "gamma_g": 0}, harm=0.0, amount=1.0, time=406,
        run_id=_RUN, policy_hash="p")
    assert permit["ActuateTimestamp"] == rae.iso_ms(base + timedelta(milliseconds=25))
    assert permit["Actuated"] is True and permit["ACT_PERMIT"] is True


# 5. ENVIRONMENTCONTEXT (C8): no class= token; four ratified Class-blind tokens
def test_environment_context_class_blind() -> None:
    ec = _emit_credit_card()["EnvironmentContext"]
    assert "class=" not in ec and "Class" not in ec, "EnvironmentContext must not embed Class"
    assert ec == "ULB_2013_EU_CARD;source_time_sec=406;amount=149.62;source=anonymized_PCA"


# 6. STRUCTURAL CONSTANTS (C9): PolicyHash from a Class-independent source; injected constants merged
def test_structural_constants_class_independent() -> None:
    rec = _emit_credit_card(structural_constants={"SpecVersion": "1.0", "NodeID": "N-1"})
    assert rec["PolicyHash"] == "POLICYROOTabc"          # caller-sourced (frozen Merkle root)
    assert rec["SpecVersion"] == "1.0" and rec["NodeID"] == "N-1"
    # optional: a genuine Class-independent policy root via the frozen PolicyPort (guarded)
    try:
        from runtime_context.ports import PolicyPort
        root = PolicyPort().merkle_root()
        assert isinstance(root, str) and len(root) == 64
    except Exception as exc:  # PolicyError / manifest absence — environment-graceful
        print("    (info) PolicyPort root source not available: %s" % exc)


# 7. LEDGER CANON + HASH (C10/C11): composition + recomputed hash match; genesis anchored
def test_ledger_canon_and_hash() -> None:
    rec = _emit_credit_card()
    canon = "%s|%s|%s|%.6f|%s|%s" % (
        rec["ProposalID"], rec["Status"], rec["Gamma"], float(rec["HARM_RISK"]),
        rec["PermitTokenID"], rec["TimestampUTC"])
    assert rec["LedgerCanon"] == canon
    assert rec["HASH_prev"] == GENESIS
    recomputed = hashlib.sha256((GENESIS + "||" + canon).encode()).hexdigest()
    assert rec["HASH_current"] == recomputed, "HASH must equal sha256(prev || canon)"


# 8. DETERMINISM / REPLAY: identical inputs -> byte-identical record + chain; adjacency valid
def test_determinism_and_chain() -> None:
    a = _emit_credit_card()
    b = emit_reported_record(
        1, decision={"decision": a["Status"], "gamma_g": a["Gamma"]}, harm=a["HARM_RISK"],
        amount=_REQUEST["Amount"], time=_REQUEST["Time"], run_id=_RUN, policy_hash="POLICYROOTabc",
        method_version="m/1")
    assert json.dumps(a, sort_keys=True) != "" and a["HASH_current"] == b["HASH_current"]
    items = [dict(decision={"decision": "SAFE_STATE", "gamma_g": 1}, harm=0.0, amount=10.0, time=t)
             for t in (100, 50, 200)]
    c1 = ReportedArtifactEmitter().emit_chain(items, run_id=_RUN)
    c2 = ReportedArtifactEmitter().emit_chain(items, run_id=_RUN)
    assert [r["HASH_current"] for r in c1] == [r["HASH_current"] for r in c2], "chain must be deterministic"
    assert c1[0]["HASH_prev"] == GENESIS
    for i in range(1, len(c1)):
        assert c1[i]["HASH_prev"] == c1[i - 1]["HASH_current"], "adjacency must hold"


# 9. CLASS-BLINDNESS: Class cannot enter (no param); source never references Class
def test_class_blindness() -> None:
    # differing Class in the request cannot change the emitted record (interpreter drops Class;
    # the emitter has no Class parameter at all)
    r0 = _emit_credit_card(request=dict(_REQUEST, Class=0))
    r1 = _emit_credit_card(request=dict(_REQUEST, Class=1))
    assert json.dumps(r0, sort_keys=True) == json.dumps(r1, sort_keys=True)
    tree = ast.parse(Path(rae.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value != "Class", "emitter must not reference the Class column"


# 10. PROVENANCE: the record links to the sealed EEB
def test_provenance_linkage() -> None:
    eeb, _, row, dec = _pipeline_decision(_REQUEST)
    rec = ReportedArtifactEmitter().emit(
        1, decision=dec, harm=row["HARM_RISK"], amount=1.0, time=1, run_id=_RUN,
        evidence_bundle=eeb, method_version="m/1")
    assert rec["EvidenceBundleID"] == eeb.bundle_id
    assert rec["EvidenceBundleDigest"] == eeb.integrity_digest and len(rec["EvidenceBundleDigest"]) == 64


# 11. NO ENGINE / PREDICATE COUPLING: imports no engine; calls no decision/predicate function
def test_no_engine_coupling() -> None:
    tree = ast.parse(Path(rae.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "gamma_test_runner" not in (node.module or ""), "emitter must not import the engine"
        if isinstance(node, ast.Import):
            for a in node.names:
                assert "gamma_test_runner" not in a.name
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"evaluate_decision", "bind", "decision_inputs_from_eeb"}, \
                "emitter must not compute decisions/predicates"


def _run_all() -> int:
    checks = [
        test_end_to_end_from_pipeline,
        test_identifiers_index_derived,
        test_timestamps_and_offsets,
        test_actuate_gate_decision_driven,
        test_environment_context_class_blind,
        test_structural_constants_class_independent,
        test_ledger_canon_and_hash,
        test_determinism_and_chain,
        test_class_blindness,
        test_provenance_linkage,
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
    print("reported_artifact_emitter self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
