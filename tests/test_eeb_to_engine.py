"""Commit 4.1 — EEB -> engine input adapter: zero-logic-diff verification.

Proves the opt-in EEB input path introduces ZERO scientific change:
  1. ZERO-LOGIC-DIFF — for real/synthetic rows, the frozen evaluate_decision() yields identical
     gamma_g / pi / decision whether fed the raw CSV row or the values CONSUMED from an EEB.
  2. PURE CONSUMER — the production adapter (eeb_to_engine) NEVER constructs an EEB; it only
     extracts values out of an EEB. The EEB CONSTRUCTION helpers used for this equivalence test
     live HERE, in the test suite (not in the production adapter).
  3. NO IMPORT CYCLE / verbatim carry (booleans stay booleans; ReasonCodes carried verbatim).

Standard library + project modules only; no pytest. Run:
    python3 tests/test_eeb_to_engine.py     # standalone; exits 0 on success

The decision logic (evaluate_decision, the vectorized block) is frozen and untouched.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from runtime_context import eeb_to_engine as adp  # noqa: E402
from runtime_context.eeb_to_engine import (  # noqa: E402
    decision_inputs_from_eeb, overlay_decision_inputs, HARM_COL, STALE_COL, FRESH_COL, VETO_COL,
)
from runtime_context.assembler import ExecutionEvidenceBundleAssembler  # noqa: E402
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)
from gamma_test_runner import evaluate_decision, NODE_GATE_COLS, BOOL_COLS, to_bool  # noqa: E402

MAPPED = ROOT / "GAMMA_G0_CREDITCARD_FULL_mapped.csv"
_DECISION_KEYS = list(NODE_GATE_COLS) + [HARM_COL, STALE_COL, FRESH_COL, VETO_COL]


# --------------------------------------------------------------------------- #
# EEB CONSTRUCTION helpers — TEST-ONLY (equivalence scaffold; NOT in the adapter)
# --------------------------------------------------------------------------- #
def _ef(value, plane, quality=EvidenceQuality.PRESENT) -> EvidenceField:
    return EvidenceField(value, ProvenanceDescriptor(
        plane, "eeb-test-arm", quality, "unobserved",
        VerificationMethod.FIELD_PRESENCE, TrustLevel.DERIVED))


def build_eeb_for_row(row):
    """Build a sealed EEB carrying one row's decision-consumed values VERBATIM (test-only)."""
    asm = ExecutionEvidenceBundleAssembler()
    return asm.assemble(
        bundle_id="eeb-test-arm", created_at="unobserved",
        txn_amount=_ef(None, OriginPlane.A, EvidenceQuality.ABSENT),
        txn_time=_ef(None, OriginPlane.A, EvidenceQuality.ABSENT),
        txn_action_ref=_ef(None, OriginPlane.A, EvidenceQuality.ABSENT),
        node_predicate_vector=tuple(_ef(bool(row[g]), OriginPlane.C) for g in NODE_GATE_COLS),
        harm_risk_score=_ef(row[HARM_COL], OriginPlane.D),
        stale_context=_ef(bool(row[STALE_COL]), OriginPlane.B),
        telemetry_fresh=_ef(bool(row[FRESH_COL]), OriginPlane.B),
        class_veto_evidence=_ef(str(row[VETO_COL]), OriginPlane.D),
        prior_ledger_link=_ef(None, OriginPlane.E_CACHED, EvidenceQuality.ABSENT),
    )


def _eebs_for(df):
    return [build_eeb_for_row(df.iloc[i]) for i in range(len(df))]


def _decision(row: dict) -> tuple:
    d = evaluate_decision(row, 0.5)
    return (d["gamma_g"], d["pi"], d["decision"])


def _full_row(**overrides) -> dict:
    r = {g: True for g in NODE_GATE_COLS}
    r.update({
        HARM_COL: 0.0, STALE_COL: False, FRESH_COL: True,
        "TOKEN_VALID": True, "AuthoritySignatureValid": True,
        "Actuated": False, "ACT_PERMIT": False,
        VETO_COL: "CLASS_0_LEGITIMATE;ALL_GATES_PASS",
    })
    r.update(overrides)
    return r


_SAMPLE = [
    _full_row(),
    _full_row(**{NODE_GATE_COLS[2]: False}),
    _full_row(TOKEN_VALID=False),
    _full_row(HARM_RISK=0.51),
    _full_row(HARM_RISK=0.50),
    _full_row(StaleContext=True),
    _full_row(TelemetryFresh=False),
    _full_row(ReasonCodes="CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL"),
    _full_row(ReasonCodes="GOODHART_PROXY"),
    _full_row(HARM_RISK=0.9, StaleContext=True, ReasonCodes="CLASS_1"),
]


def _prep(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = to_bool(df[col])
    return df


# 1. ZERO-LOGIC-DIFF on synthetic representative rows (build EEBs -> consume -> compare)
def test_zero_logic_diff_sample() -> None:
    df = _prep(_SAMPLE)
    rt = overlay_decision_inputs(df, _eebs_for(df), NODE_GATE_COLS)
    for i in range(len(df)):
        assert _decision(df.iloc[i].to_dict()) == _decision(rt.iloc[i].to_dict()), \
            "row %d: EEB-consumed decision != CSV decision" % i


# 2. ZERO-LOGIC-DIFF on a real corpus sample (guarded on corpus presence)
def test_zero_logic_diff_real_corpus() -> None:
    if not MAPPED.exists():
        print("    SKIP test_zero_logic_diff_real_corpus (corpus not present)")
        return
    df = pd.read_csv(MAPPED, nrows=2000)
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = to_bool(df[col])
    rt = overlay_decision_inputs(df, _eebs_for(df), NODE_GATE_COLS)
    mismatches = sum(
        1 for i in range(len(df))
        if _decision(df.iloc[i].to_dict()) != _decision(rt.iloc[i].to_dict()))
    assert mismatches == 0, "%d/%d rows diverged" % (mismatches, len(df))


# 3. PURE CONSUMER — decision columns carried verbatim; freshness stays boolean
def test_pure_consumer_verbatim() -> None:
    df = _prep(_SAMPLE)
    rt = overlay_decision_inputs(df, _eebs_for(df), NODE_GATE_COLS)
    for c in _DECISION_KEYS:
        assert list(rt[c]) == list(df[c]), "column %s not carried verbatim" % c
    assert rt[STALE_COL].dtype == bool or set(map(type, rt[STALE_COL])) <= {bool}
    assert list(rt["Actuated"]) == list(df["Actuated"])  # non-decision column untouched


# 4. Extraction is a pure remap of .value
def test_decision_inputs_extract_value() -> None:
    df = _prep([_full_row(HARM_RISK=0.7, StaleContext=True)])
    eeb = build_eeb_for_row(df.iloc[0])
    vals = decision_inputs_from_eeb(eeb, NODE_GATE_COLS)
    assert vals[HARM_COL] == 0.7
    assert vals[STALE_COL] is True and vals[FRESH_COL] is True
    assert vals[VETO_COL] == "CLASS_0_LEGITIMATE;ALL_GATES_PASS"
    assert all(vals[g] is True for g in NODE_GATE_COLS)


# 5. The production ADAPTER is a PURE CONSUMER: it never constructs an EEB and never imports the engine
def test_adapter_is_pure_consumer() -> None:
    src = Path(adp.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    # no construction: the adapter must not import the assembler or the EEB field/provenance types
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "gamma_test_runner" not in mod, "adapter must not import the engine (cycle)"
            if mod.endswith("assembler"):
                raise AssertionError("pure consumer must not import the assembler (construction)")
            if mod.endswith("execution_evidence_bundle"):
                imported = {a.name for a in node.names}
                forbidden = {"EvidenceField", "ProvenanceDescriptor", "EvidenceQuality"}
                assert not (imported & forbidden), \
                    "pure consumer must not import EEB construction types: %s" % (imported & forbidden)
    # no .assemble(...) / .seal(...) calls anywhere in the adapter
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"assemble", "seal"}, \
                "pure consumer must not construct/seal an EEB"


def _run_all() -> int:
    checks = [
        test_zero_logic_diff_sample,
        test_zero_logic_diff_real_corpus,
        test_pure_consumer_verbatim,
        test_decision_inputs_extract_value,
        test_adapter_is_pure_consumer,
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
    print("eeb_to_engine self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
