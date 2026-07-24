"""Phase 3A verification: L-DREA interception, two-layer manifests (OFFLINE, no LLM, no scoring).

Layer 1 = 7 immutable scientific manifests (root ce8c8467...). Layer 2 = Execution Binding Manifest
(sha a2b816e0...), derived from Layer 1. Integrity tests use temp copies + dependency injection so
the real frozen artifacts are never mutated.

Run: agentdojo_integration/.venv/bin/python agentdojo_integration/tests/test_interception.py
"""
import sys
import json
import shutil
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agentdojo.task_suite.load_suites import get_suites
from agentdojo_integration.interception.governed_runtime import GammaGovernedRuntime
from agentdojo_integration.interception.frozen_policy import ScientificPolicy, PolicyError, SCIENTIFIC_ROOT, DEFAULT_MANIFEST_DIR
from agentdojo_integration.interception.execution_binding import ExecutionBinding, BINDING_SHA
from agentdojo_integration.interception.gamma_bridge import GammaBridge
from agentdojo_integration.interception.predicate_evaluation import PredicateEvaluator, _ibans, _emails

FAILS = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def test_functional():
    print("=== functional (banking + workspace) ===")
    suite = get_suites("v1")["banking"]
    env = suite.load_and_inject_default_environment({})
    rt = GammaGovernedRuntime(suite.tools)
    check("Layer-1 scientific root == ce8c8467 (immutable)", rt.frozen_merkle_root == SCIENTIFIC_ROOT)
    check("Layer-2 binding sha == a2b816e0", rt.binding_sha == BINDING_SHA)

    _, err = rt.run_function(env, "get_balance", {})
    check("read-only get_balance passes through", err is None)
    good = sorted(_ibans(env))[0]
    n = len(env.bank_account.transactions)
    _, err = rt.run_function(env, "send_money", {"recipient": good, "amount": 10.0, "subject": "t", "date": "2026-01-01"})
    check("recognized IBAN + in balance -> PERMIT + executed", err is None and len(env.bank_account.transactions) == n + 1)
    n = len(env.bank_account.transactions)
    _, err = rt.run_function(env, "send_money", {"recipient": "DE00ATTACKER00000000000000000000", "amount": 10.0, "subject": "x", "date": "2026-01-01"})
    check("unrecognized IBAN -> SAFE_STATE + blocked", err and err.startswith("GammaSafeState") and len(env.bank_account.transactions) == n)
    n = len(env.bank_account.transactions)
    _, err = rt.run_function(env, "send_money", {"recipient": good, "amount": 1e9, "subject": "t", "date": "2026-01-01"})
    check("over env-balance threshold (Layer-2 directive) -> SAFE_STATE", err and err.startswith("GammaSafeState") and len(env.bank_account.transactions) == n)

    ws = get_suites("v1")["workspace"]
    wenv = ws.load_and_inject_default_environment({})
    wrt = GammaGovernedRuntime(ws.tools)
    gmail = (sorted(_emails(wenv)) or [wenv.inbox.account_email])[0]
    n = len(wenv.inbox.emails)
    _, err = wrt.run_function(wenv, "send_email", {"recipients": [gmail], "subject": "s", "body": "b"})
    check("workspace recognized recipient -> PERMIT + executed", err is None and len(wenv.inbox.emails) == n + 1)
    n = len(wenv.inbox.emails)
    _, err = wrt.run_function(wenv, "send_email", {"recipients": ["attacker@evil.example"], "subject": "x", "body": "s"})
    check("workspace unrecognized recipient -> SAFE_STATE", err and err.startswith("GammaSafeState") and len(wenv.inbox.emails) == n)


def test_unknown_tool():
    print("=== unknown tool (fail-closed) ===")
    suite = get_suites("v1")["banking"]
    env = suite.load_and_inject_default_environment({})
    rt = GammaGovernedRuntime(suite.tools)
    n = len(env.bank_account.transactions)
    _, err = rt.run_function(env, "totally_new_future_tool", {"x": 1})
    check("unknown tool -> SAFE_STATE", err and err.startswith("GammaSafeState") and "UNKNOWN" in err)
    check("unknown tool NOT executed", len(env.bank_account.transactions) == n)


def _copy(dst):
    dst.mkdir(parents=True, exist_ok=True)
    for f in DEFAULT_MANIFEST_DIR.glob("*.json"):
        shutil.copy(f, dst / f.name)
    return dst


def test_layer1_integrity():
    print("=== Layer-1 scientific integrity ===")
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m")
        check("clean copy verifies to ce8c8467", ScientificPolicy(manifest_dir=d).root == SCIENTIFIC_ROOT)
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m"); (d / "threshold_manifest.json").unlink()
        try: ScientificPolicy(manifest_dir=d); check("missing scientific manifest -> error", False)
        except PolicyError as e: check("missing scientific manifest -> error", "Missing Manifest" in str(e))
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m"); p = d / "predicate_manifest.json"
        o = json.loads(p.read_text()); o["note"] = "TAMPERED"; p.write_text(json.dumps(o))
        try: ScientificPolicy(manifest_dir=d); check("tampered scientific leaf -> error", False)
        except PolicyError as e: check("tampered scientific leaf -> error", "Invalid Merkle Root" in str(e))
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m"); p = d / "merkle_root.json"
        o = json.loads(p.read_text()); o["merkle_root"] = "0" * 64; p.write_text(json.dumps(o))
        try: ScientificPolicy(manifest_dir=d); check("corrupt recorded root -> error", False)
        except PolicyError as e: check("corrupt recorded root -> error", "Invalid Merkle Root" in str(e))
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m")
        try: ScientificPolicy(manifest_dir=d, expected_root="deadbeef" * 8); check("version mismatch -> error", False)
        except PolicyError as e: check("version mismatch -> error", "Version Mismatch" in str(e))


def test_layer2_integrity():
    print("=== Layer-2 binding integrity ===")
    with tempfile.TemporaryDirectory() as td:
        d = _copy(Path(td) / "m")
        check("clean binding verifies to a2b816e0", ExecutionBinding(manifest_dir=d).sha == BINDING_SHA)
    with tempfile.TemporaryDirectory() as td:  # missing binding
        d = _copy(Path(td) / "m"); (d / "Execution_Binding_Manifest.json").unlink()
        try: ExecutionBinding(manifest_dir=d); check("missing binding manifest -> error", False)
        except PolicyError as e: check("missing binding manifest -> error", "Missing binding" in str(e))
    with tempfile.TemporaryDirectory() as td:  # tampered binding -> sha mismatch
        d = _copy(Path(td) / "m"); p = d / "Execution_Binding_Manifest.json"
        o = json.loads(p.read_text()); o["family_metadata"]["GATE_amount_limit"]["gamma_slot"] = "Gate_A7"; p.write_text(json.dumps(o))
        try: ExecutionBinding(manifest_dir=d); check("tampered binding -> integrity error", False)
        except PolicyError as e: check("tampered binding -> integrity error", "Binding Integrity Failure" in str(e))
    with tempfile.TemporaryDirectory() as td:  # provenance break
        d = _copy(Path(td) / "m"); p = d / "Execution_Binding_Manifest.json"
        o = json.loads(p.read_text()); o["derived_from_scientific_root"] = "0" * 64; p.write_text(json.dumps(o))
        try: ExecutionBinding(manifest_dir=d, expected_sha=None); check("binding provenance break -> error", False)
        except PolicyError as e: check("binding provenance break -> error", "Provenance" in str(e))


def test_dependency_injection():
    print("=== dependency inversion (two layers) ===")
    suite = get_suites("v1")["banking"]
    sci = ScientificPolicy(); bind = ExecutionBinding()
    rt = GammaGovernedRuntime(suite.tools, scientific=sci, binding=bind, bridge=GammaBridge(bind), evaluator=PredicateEvaluator(bind))
    check("runtime accepts injected scientific + binding + bridge + evaluator", rt.scientific is sci and rt.binding is bind)


if __name__ == "__main__":
    test_functional()
    test_unknown_tool()
    test_layer1_integrity()
    test_layer2_integrity()
    test_dependency_injection()
    print()
    if FAILS:
        print(f"RESULT: FAIL ({len(FAILS)}): {FAILS}"); sys.exit(1)
    print("RESULT: ALL CHECKS PASS — Phase 3A two-layer (scientific immutable + binding derived) verified offline.")
