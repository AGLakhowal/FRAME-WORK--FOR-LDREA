#!/usr/bin/env python3
"""Regression suite for Gamma Hardening v1 (Operation Break Gamma exploits E-1..E-8).

Each test asserts the exploit is BLOCKED. Run directly:
    ./.venv/bin/python tests/test_gamma_hardening_v1.py
or under pytest if available.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamma_test_runner import evaluate_decision, NODE_GATE_COLS, classify_reasoncodes
from gamma_ledger_integrity import generate_key, sign_record, verify_record, load_key

PY = sys.executable


def _clean_permit_row():
    r = {g: True for g in NODE_GATE_COLS}
    r.update({"HARM_RISK": 0.0, "StaleContext": False, "TelemetryFresh": True,
              "ReasonCodes": "CLASS_0_LEGITIMATE;ALL_GATES_PASS", "Actuated": True,
              "ACT_PERMIT": True})
    return r


# ---- Engine exploits -------------------------------------------------------
def test_e1_veto_not_bypassable_by_relabelled_text():
    r = _clean_permit_row()
    r["ReasonCodes"] = "C1_FRAUD;attacker_relabelled_evidence"  # no valid CLASS_<n>_
    assert evaluate_decision(r, 0.5)["decision"] == "SAFE_STATE"  # fail-closed


def test_e2_class10_not_falsely_vetoed():
    r = _clean_permit_row()
    r["ReasonCodes"] = "CLASS_10_LOW_RISK_LEGITIMATE"
    assert evaluate_decision(r, 0.5)["decision"] == "PERMIT"
    assert classify_reasoncodes("CLASS_10_X") == (0, True)


def test_e3_goodhart_in_freetext_does_not_deny():
    r = _clean_permit_row()
    r["ReasonCodes"] = "CLASS_0_LEGITIMATE; note: see GOODHART's-law memo attached"
    assert evaluate_decision(r, 0.5)["decision"] == "PERMIT"


def test_e3b_real_goodhart_token_still_vetoes():
    # A genuine standalone GOODHART marker must still deny (no regression).
    assert classify_reasoncodes("CLASS_0_LEGITIMATE;GOODHART_PROXY_GAMING") == (1, True)
    assert classify_reasoncodes("CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL") == (1, True)


def test_e4_null_reasoncodes_fails_closed():
    r = _clean_permit_row()
    r["ReasonCodes"] = None
    assert evaluate_decision(r, 0.5)["decision"] == "SAFE_STATE"


def test_e5_missing_predicate_key_fails_closed_not_crash():
    r = _clean_permit_row()
    del r["Gate_A3"]
    out = evaluate_decision(r, 0.5)  # must not raise
    assert out["decision"] == "SAFE_STATE"
    assert out["fail_closed_reason"].startswith("MISSING_EVIDENCE")


def test_e6_threshold_deterministic_across_ulp():
    decs = {evaluate_decision({**_clean_permit_row(), "HARM_RISK": hv}, 0.5)["decision"]
            for hv in (0.5, 0.5 + 5e-16, 0.5 - 5e-16)}
    assert decs == {"PERMIT"}  # no knife-edge flip from float round-trip


def test_no_regression_on_real_legit_and_fraud_tokens():
    legit = _clean_permit_row()
    assert evaluate_decision(legit, 0.5)["decision"] == "PERMIT"
    fraud = _clean_permit_row()
    fraud["ReasonCodes"] = "CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL;SAFE_STATE_DENIAL"
    assert evaluate_decision(fraud, 0.5)["decision"] == "SAFE_STATE"


# ---- Ledger exploits (E-7 forgery, E-8 tamper) -----------------------------
def _write(path, recs):
    Path(path).write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def _verify(path, key_path):
    r = subprocess.run([PY, str(ROOT / "gamma_replay_verify.py"), str(path),
                        "--key", str(key_path)], capture_output=True, text=True)
    return r.returncode


def _dec(seq, prev, cur, dec, gg, gc, pi, pid):
    return {"record": "decision", "seq": seq, "proposal_id": pid, "policy_hash": "x",
            "hash_prev": prev, "hash_current": cur, "decision": dec, "gamma_g": gg,
            "gamma_class": gc, "pi": pi,
            "evidence_quad": {"decision": dec, "method_version": "v", "policy_hash": "x",
                              "ledger_hash": cur}}


def test_e7_forged_ledger_rejected(tmpdir="/tmp/gamma_htest"):
    os.makedirs(tmpdir, exist_ok=True)
    kp = Path(tmpdir) / "k.key"
    if kp.exists():
        kp.unlink()
    key = generate_key(kp)
    forged = [{"record": "header", "method_version": "v", "n_records": 2,
               "genesis_anchor": "GENESIS"},
              _dec(0, "GENESIS", "HA", "PERMIT", 0, 0, 1, "FRAUD_1"),  # unsigned!
              _dec(1, "HA", "HB", "PERMIT", 0, 0, 1, "FRAUD_2")]
    p = Path(tmpdir) / "forged.jsonl"
    _write(p, forged)
    assert _verify(p, kp) != 0  # BLOCKED


def test_e8_tampered_signed_record_rejected(tmpdir="/tmp/gamma_htest"):
    os.makedirs(tmpdir, exist_ok=True)
    kp = Path(tmpdir) / "k.key"
    key = generate_key(kp)
    recs = [{"record": "header", "method_version": "v", "n_records": 2,
             "genesis_anchor": "GENESIS"},
            sign_record(_dec(0, "GENESIS", "H0", "PERMIT", 0, 0, 1, "T1"), key),
            sign_record(_dec(1, "H0", "H1", "SAFE_STATE", 1, 0, 0, "T2"), key)]
    p = Path(tmpdir) / "signed.jsonl"
    _write(p, recs)
    assert _verify(p, kp) == 0  # legit signed -> PASS
    # tamper: flip a PERMIT to SAFE_STATE, keep the old signature
    recs[1]["decision"] = "SAFE_STATE"
    recs[1]["evidence_quad"]["decision"] = "SAFE_STATE"
    _write(p, recs)
    assert _verify(p, kp) != 0  # BLOCKED


def test_e8b_verify_record_unit():
    key = os.urandom(32)
    rec = sign_record(_dec(0, "GENESIS", "H0", "PERMIT", 0, 0, 1, "T1"), key)
    assert verify_record(rec, key)
    rec["decision"] = "SAFE_STATE"
    assert not verify_record(rec, key)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}  {e}")
        except Exception as e:
            print(f"ERROR {t.__name__}  {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} regression tests passed")
    sys.exit(0 if passed == len(tests) else 1)
