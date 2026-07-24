"""Hermetic self-test for the single-authorization-engine guardrail (Commit 0.2).

Verifies the guardrail's OWN behaviour using in-memory strings and temp dirs only.
It does NOT assert anything about the live repository tree (so it stays green as
Commits 1.1/3.1/5.2 later remove the pending-defect warnings).

Standard library only; no pytest, no CI, no repository modification. Run either way:
    python3 tests/test_single_engine_guardrail.py      # standalone; exits 0 on success
    pytest tests/test_single_engine_guardrail.py       # if pytest is later added
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import check_single_engine as guard  # noqa: E402


# 1. A planted competing implementation is detected.
def test_planted_competing_detected() -> None:
    heuristic = "gamma_g = 1 if sensitivity == 'high' else 0\n"
    assert guard.analyze_source(heuristic), "heuristic gamma_g assignment must be flagged"

    selection = 'decision = "SAFE_STATE" if risky else "PERMIT"\n'
    kinds = {f.kind for f in guard.analyze_source(selection)}
    assert "decision_literal_selection" in kinds, "decision-literal selection must be flagged"

    authoring = 'row["Status"] = "SAFE_STATE"\n'
    kinds = {f.kind for f in guard.analyze_source(authoring)}
    assert "decision_literal_assignment" in kinds, "bare decision-literal authoring must be flagged"


# 2. evaluate_decision() usage is NOT flagged (reuse of the frozen engine).
def test_engine_usage_not_flagged() -> None:
    reuse = "dec = evaluate_decision(row, 0.5)\nout = dec['decision']\n"
    assert guard.analyze_source(reuse) == [], "reuse via evaluate_decision must not be flagged"

    # Even when the target name is an auth-output name, an engine-sourced RHS is reuse.
    reuse_named = "pi = evaluate_decision(row, 0.5)['pi']\n"
    assert guard.analyze_source(reuse_named) == [], "engine-sourced auth value must not be flagged"


# 3. Comments / strings / docstrings cannot trip the AST detector.
def test_comments_and_strings_not_flagged() -> None:
    noise = (
        '"""permit = 1 if x else 0 in a docstring."""\n'
        "# gamma_g = 1 if y else 0  -- a comment\n"
        "note = 'the decision is PERMIT or SAFE_STATE here'\n"
    )
    assert guard.analyze_source(noise) == [], "tokens in comments/strings must not be flagged"


# 4. Registry exemptions work (path-level suppression), and exempt_paths parses correctly.
def test_registry_exemption() -> None:
    competing = "permit = (gamma == 0)\n"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "exempt_me.py").write_text(competing)
        (root / "flag_me.py").write_text(competing)

        registry = {
            "schema_version": "1.0", "registry_version": "test",
            "sites": [{"path": "exempt_me.py", "exempt": True}],
        }
        exempt = guard.exempt_paths(registry)
        assert exempt == {"exempt_me.py"}

        results = guard.scan_tree(root, exempt)
        assert "flag_me.py" in results, "non-exempt competing file must be flagged"
        assert "exempt_me.py" not in results, "exempt path must be suppressed"


# 5. Exit code is ALWAYS 0, even when violations are present (warn-only).
def test_exit_code_always_zero() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "violator.py").write_text('d = "PERMIT" if x else "SAFE_STATE"\n')
        reg_path = root / "reg.json"
        reg_path.write_text(json.dumps({"schema_version": "1.0", "registry_version": "t", "sites": []}))
        rc = guard.main(["--root", str(root), "--registry", str(reg_path), "--quiet"])
        assert rc == 0, "guardrail must always exit 0 (warn-only)"


# 6. The shipped registry loads and is structurally well-formed.
def test_shipped_registry_wellformed() -> None:
    reg = guard.load_registry(ROOT / "tools" / "authorization_registry.json")
    assert reg.get("schema_version") and reg.get("registry_version")
    assert reg.get("generated_from"), "registry must record generated_from provenance"
    for site in reg.get("sites", []):
        for key in ("path", "classification", "reason", "authoritative_source", "status", "exempt"):
            assert key in site, "registry entry missing '%s': %s" % (key, site.get("path"))


def _run_all() -> int:
    checks = [
        test_planted_competing_detected,
        test_engine_usage_not_flagged,
        test_comments_and_strings_not_flagged,
        test_registry_exemption,
        test_exit_code_always_zero,
        test_shipped_registry_wellformed,
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
    print("guardrail self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
