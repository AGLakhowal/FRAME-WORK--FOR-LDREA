"""Self-test for the plane-A Transaction Interpreter (Commit 2.4).

Verifies: plane-A population + provenance, Class-blindness by construction, unknown-field drop,
opaque feature carry, DEGRADED-on-malformed (no repair/normalize), optional-field absence,
reading immutability, EEB provenance validity, and the no-wall-clock discipline. Standard
library only; no pytest. Run:
    python3 tests/test_transaction_interpreter.py     # standalone; exits 0 on success
    pytest tests/test_transaction_interpreter.py      # if pytest is later added

Commit 2.4 is unconsumed scaffolding; bundle assembly is Commit 2.5, not here. The interpreter
reads the transaction REQUEST (plane A) only — it does not read the Commit 2.3 plane-B objects.
"""
from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context import transaction_interpreter as ti  # noqa: E402
from runtime_context.transaction_interpreter import (  # noqa: E402
    TransactionInterpreter, ALLOWLIST, FIELD_AMOUNT, FIELD_TIME, FIELD_ACTION_REF,
    FIELD_FEATURE_REF,
)
from runtime_context.execution_evidence_bundle import (  # noqa: E402
    EvidenceField, OriginPlane, EvidenceQuality, VerificationMethod, TrustLevel, _check_field,
)

_FIELD_NAMES = {FIELD_AMOUNT, FIELD_TIME, FIELD_ACTION_REF, FIELD_FEATURE_REF}


def _assert_plane_a(ef, quality) -> None:
    assert isinstance(ef, EvidenceField), "must be a Commit 2.1 EvidenceField"
    p = ef.provenance
    assert p.origin_plane == OriginPlane.A, "Transaction Interpreter owns plane A"
    assert p.producer_id == "transaction.interpreter"
    assert p.verification_method == VerificationMethod.FIELD_PRESENCE
    assert p.trust_level == TrustLevel.SELF_REPORTED
    assert p.evidence_quality == quality
    _check_field(ef, "reading")  # reuse EEB structural/provenance validation


# 1. Plane-A population: Amount/Time become provenanced plane-A readings
def test_plane_a_population() -> None:
    out = TransactionInterpreter().interpret({"Amount": 149.62, "Time": 406})
    assert out[FIELD_AMOUNT].value == 149.62
    assert out[FIELD_TIME].value == 406
    _assert_plane_a(out[FIELD_AMOUNT], EvidenceQuality.PRESENT)
    _assert_plane_a(out[FIELD_TIME], EvidenceQuality.PRESENT)


# 2. Class-blindness (mandated): Class never changes any output, present or absent
def test_class_blindness() -> None:
    base = {"Amount": 10.0, "Time": 1, "V1": 0.1, "V2": 0.2}
    out_absent = TransactionInterpreter().interpret(dict(base))
    out_c0 = TransactionInterpreter().interpret(dict(base, Class=0))
    out_c1 = TransactionInterpreter().interpret(dict(base, Class=1))
    assert out_absent == out_c0 == out_c1, "Class must not influence any interpreter output"
    # structural: Class is not on the allowlist, so it can never be read
    assert "Class" not in ALLOWLIST


# 3. Unknown-field dropped (mandated): non-allowlisted keys produce nothing
def test_unknown_field_dropped() -> None:
    out = TransactionInterpreter().interpret(
        {"Amount": 5.0, "Foo": 123, "Class": 1, "SubjectID": "x"})
    assert set(out.keys()) <= _FIELD_NAMES, "only EEB plane-A field names may be produced"
    assert set(out.keys()) == {FIELD_AMOUNT}, "unknown keys (Foo/Class/SubjectID) dropped"


# 4. Features are a SINGLE opaque reference — carried verbatim, never decomposed
def test_feature_opacity() -> None:
    req = {"V%d" % i: float(i) for i in range(1, 29)}
    out = TransactionInterpreter().interpret(req)
    ref = out[FIELD_FEATURE_REF]
    _assert_plane_a(ref, EvidenceQuality.PRESENT)
    assert isinstance(ref.value, tuple) and len(ref.value) == 28, "opaque V1..V28 vector"
    assert ref.value == tuple(float(i) for i in range(1, 29)), "carried verbatim, in order"
    # no per-feature predicate/field is ever emitted
    assert set(out.keys()) == {FIELD_FEATURE_REF}


# 5. DEGRADED on malformed — no infer/repair/normalize; value carried verbatim
def test_degraded_on_malformed() -> None:
    # numeric-looking STRING must NOT be normalized to a number
    out = TransactionInterpreter().interpret({"Amount": "149.62", "Time": None})
    assert out[FIELD_AMOUNT].provenance.evidence_quality == EvidenceQuality.DEGRADED
    assert out[FIELD_AMOUNT].value == "149.62", "malformed value carried verbatim, not repaired"
    assert out[FIELD_TIME].provenance.evidence_quality == EvidenceQuality.DEGRADED
    assert out[FIELD_TIME].value is None
    # bool is not a number
    b = TransactionInterpreter().interpret({"Amount": True})
    assert b[FIELD_AMOUNT].provenance.evidence_quality == EvidenceQuality.DEGRADED


# 6. Optional / absent fields are simply not produced
def test_absent_fields_not_produced() -> None:
    out = TransactionInterpreter().interpret({"Amount": 1.0})
    assert FIELD_TIME not in out and FIELD_ACTION_REF not in out and FIELD_FEATURE_REF not in out


# 7. Optional action reference: opaque string when present, DEGRADED if malformed
def test_action_ref_optional() -> None:
    ok = TransactionInterpreter().interpret({"TxnActionRef": "pay:merchant:42"})
    _assert_plane_a(ok[FIELD_ACTION_REF], EvidenceQuality.PRESENT)
    assert ok[FIELD_ACTION_REF].value == "pay:merchant:42"
    bad = TransactionInterpreter().interpret({"TxnActionRef": 999})
    assert bad[FIELD_ACTION_REF].provenance.evidence_quality == EvidenceQuality.DEGRADED
    assert bad[FIELD_ACTION_REF].value == 999


# 8. Returned readings are immutable (frozen EEB type)
def test_reading_immutable() -> None:
    ef = TransactionInterpreter().interpret({"Amount": 1.0})[FIELD_AMOUNT]
    try:
        setattr(ef, "value", 2.0)
        raise AssertionError("expected FrozenInstanceError on reading mutation")
    except dataclasses.FrozenInstanceError:
        pass


# 9. Every produced field satisfies EEB provenance validation (plane A)
def test_eeb_provenance_valid() -> None:
    out = TransactionInterpreter().interpret(
        {"Amount": 1.0, "Time": 2, "TxnActionRef": "a", "V1": 0.5})
    for name, ef in out.items():
        _check_field(ef, name)
        assert ef.provenance.origin_plane == OriginPlane.A


# 10. Class-blindness passthrough: even an explicit Class value is never accessed as output
def test_class_value_never_surfaces() -> None:
    out = TransactionInterpreter().interpret({"Amount": 7.0, "Class": 1})
    for ef in out.values():
        assert ef.value != 1 or ef is out[FIELD_AMOUNT], "no output derives from Class"
    assert set(out.keys()) == {FIELD_AMOUNT}


# 11. No wall clock: the module reads no ambient time (AST-based, like Commit 2.3)
def test_no_wall_clock() -> None:
    import ast
    tree = ast.parse(Path(ti.__file__).read_text(encoding="utf-8"))
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


# 12. Interpreter reads ONLY the plane-A allowlist (no signature exposes a Class channel)
def test_no_class_channel_in_signature() -> None:
    params = set(inspect.signature(TransactionInterpreter.interpret).parameters)
    assert not (params & {"class", "class_", "label", "y", "target", "ground_truth"})


def _run_all() -> int:
    checks = [
        test_plane_a_population,
        test_class_blindness,
        test_unknown_field_dropped,
        test_feature_opacity,
        test_degraded_on_malformed,
        test_absent_fields_not_produced,
        test_action_ref_optional,
        test_reading_immutable,
        test_eeb_provenance_valid,
        test_class_value_never_surfaces,
        test_no_wall_clock,
        test_no_class_channel_in_signature,
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
    print("transaction_interpreter self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
