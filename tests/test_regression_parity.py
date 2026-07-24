"""Commit 6.3 — regression parity gates against the frozen 0.1 baseline fixtures.

Enforces that the current pipeline's deterministic outputs still match the frozen baseline,
gating on scientifically-meaningful, environment-independent content:

  * LAB       — gamma_summary.json equal after normalizing the machine-specific `input_file`
                (the LAB report gamma_lab_v1_report.json is NOT gated: its measured_latency/* are
                wall-clock and vary run-to-run — see Commit 4.1 finding).
  * ConcurBench — concurbench_full_report.json byte-parity.
  * FCR         — fcr_test_report.json byte-parity (seeded, deterministic).
  * FULL_SPEC   — numeric-substance parity (robust to the Commit 6.2 labeling metadata).
  * Replay      — manifest SHA-256 == baseline + independent verifier RESULT: PASS.
  * AgentDojo   — interception test run if the external `agentdojo` package is importable;
                  otherwise SKIPPED with notice (environment-graceful).

Compares the CURRENT working-tree artifacts (regenerate via run_all first for a full check).
Standard library only; no pytest. Run:
    python3 tests/test_regression_parity.py     # standalone; exits 0 on success

Verification only — introduces no scientific change.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tests" / "fixtures" / "baseline"

# LAB summary keys that are environment-specific (not scientific) and excluded from parity.
_ENV_KEYS = {"input_file"}


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _strip(d: dict, keys) -> dict:
    return {k: v for k, v in d.items() if k not in keys}


# 1. LAB summary parity (env-normalized; excludes wall-clock LAB report)
def test_lab_summary_parity() -> None:
    cur = _strip(_load(ROOT / "gamma_summary.json"), _ENV_KEYS)
    base = _strip(_load(BASE / "gamma_summary.json"), _ENV_KEYS)
    assert cur == base, "gamma_summary.json drifted from baseline (excluding input_file)"


# 2. ConcurBench byte-parity
def test_concurbench_parity() -> None:
    cur = (ROOT / "concurbench_full_report.json").read_text(encoding="utf-8")
    base = (BASE / "concurbench_full_report.json").read_text(encoding="utf-8")
    assert cur == base, "concurbench_full_report.json is not byte-identical to baseline"


# 3. FCR byte-parity
def test_fcr_parity() -> None:
    cur = (ROOT / "fcr_test_report.json").read_text(encoding="utf-8")
    base = (BASE / "fcr_test_report.json").read_text(encoding="utf-8")
    assert cur == base, "fcr_test_report.json is not byte-identical to baseline"


# 4. FULL_SPEC numeric-substance parity (robust to Commit 6.2 labeling metadata)
def _fullspec_numeric(d: dict) -> dict:
    m = d.get("metrics_11_1", {})
    return {
        "confusion_matrix": d.get("confusion_matrix"),
        "all_acceptance_bands_hold": d.get("all_acceptance_bands_hold"),
        "UER": m.get("UER", {}).get("rate"),
        "SVR": m.get("SVR", {}).get("rate"),
        "gamma_compliance": m.get("FFC_gamma_compliance", {}).get("rate"),
        "verdict": d.get("full_spec_verdict", {}).get("verdict"),
    }


def test_full_spec_numeric_parity() -> None:
    cur = _fullspec_numeric(_load(ROOT / "full_spec_conformance_report.json"))
    base = _fullspec_numeric(_load(BASE / "full_spec_conformance_report.json"))
    assert cur == base, "FULL_SPEC numeric substance drifted from baseline: %r vs %r" % (cur, base)


# 5. Replay SHA parity + independent verifier
def _baseline_sha() -> str:
    text = (BASE / "gamma_replay_manifest.sha256").read_text(encoding="utf-8")
    m = re.search(r"[0-9a-fA-F]{64}", text)
    assert m, "no 64-hex SHA in baseline gamma_replay_manifest.sha256"
    return m.group(0).lower()


def test_replay_sha_and_verifier() -> None:
    manifest = ROOT / "gamma_replay_manifest.jsonl"
    if not manifest.exists():
        print("    SKIP test_replay_sha_and_verifier (manifest not present — regenerate via run_all)")
        return
    cur_sha = hashlib.sha256(manifest.read_bytes()).hexdigest().lower()
    assert cur_sha == _baseline_sha(), "replay manifest SHA-256 drifted from baseline"
    r = subprocess.run([sys.executable, str(ROOT / "gamma_replay_verify.py"), str(manifest)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "RESULT" in r.stdout and "PASS" in r.stdout, \
        "independent replay verifier did not report PASS"


# 6. AgentDojo interception test (environment-graceful)
def _agentdojo_python() -> str:
    """Resolve the interpreter that actually owns the pinned AgentDojo install.

    AgentDojo requires Python >= 3.11 and lives in the dedicated venv
    ``agentdojo_integration/.venv``. The parity suite itself may run under the
    repository's Python 3.9 interpreter, where ``agentdojo`` is (correctly) absent.
    Probing ``sys.executable`` there yields a false "not installed" result — the
    root cause of the stale ``6_agentdojo: NOT_EXECUTABLE`` status. Prefer the
    dedicated venv; fall back to ``sys.executable`` only if it is missing.
    """
    candidate = ROOT / "agentdojo_integration" / ".venv" / "bin" / "python"
    return str(candidate) if candidate.exists() else sys.executable


def test_agentdojo_interception() -> None:
    test = ROOT / "agentdojo_integration" / "tests" / "test_interception.py"
    if not test.exists():
        print("    SKIP test_agentdojo_interception (test not present)")
        return
    r = subprocess.run([_agentdojo_python(), str(test)], capture_output=True, text=True)
    combined = r.stdout + r.stderr
    if "No module named 'agentdojo'" in combined or "ModuleNotFoundError" in combined:
        print("    SKIP test_agentdojo_interception (external 'agentdojo' package not installed "
              "in agentdojo_integration/.venv — provision the Python 3.11 environment)")
        return
    assert r.returncode == 0, "AgentDojo interception test failed:\n%s" % combined[-500:]


def _run_all() -> int:
    checks = [
        test_lab_summary_parity,
        test_concurbench_parity,
        test_fcr_parity,
        test_full_spec_numeric_parity,
        test_replay_sha_and_verifier,
        test_agentdojo_interception,
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
    print("regression parity gates: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
