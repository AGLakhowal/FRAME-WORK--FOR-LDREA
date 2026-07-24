"""Commit 5.2 Phase A — Class-blind runtime pipeline ACTIVATION self-test.

Verifies the end-to-end orchestrator wires the frozen components into one runnable path and that
the wired path is Class-blind, deterministic, replay-verifiable, ledger/quad-intact, and NEUTRAL
(touches no reported artifact; changes no metric). It redesigns nothing; every stage is frozen.

Checks:
  1. activation — the full chain runs end-to-end and produces reported records + a ledger head.
  2. class-blind — Class present/absent/differing -> byte-identical records.
  3. deterministic — re-run -> identical records + identical ledger head.
  4. reported artifact — records carry the ratified serialization fields + EEB provenance.
  5. replay PASS — the pipeline manifest verifies with the FROZEN independent verifier (exit 0).
  6. ledger + evidence-quad integrity — adjacency / ledger-bind / consistency failures == 0.
  7. neutral — the run writes only to a temp dir; repo reported artifacts are untouched.

Standard library + project modules; no pytest. Run (project venv):
    .venv/bin/python tests/test_class_blind_pipeline.py     # standalone; exits 0 on success
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context.class_blind_pipeline import run_pipeline, write_pipeline_manifest  # noqa: E402
from runtime_context.reported_artifact_emitter import GENESIS  # noqa: E402

_RUN = "CLASS_BLIND_PIPELINE_SELFTEST_001"
_REQS = [
    {"Amount": 149.62, "Time": 406, "V1": 0.1, "V2": 0.2},
    {"Amount": 12.0, "Time": 10, "V3": 0.3},
    {"Amount": 999.0, "Time": 200, "V1": 0.5},
]
_REPORTED = [ROOT / "gamma_replay_manifest.jsonl", ROOT / "gamma_summary.json",
             ROOT / "gamma_lab_v1_report.json", ROOT / "concurbench_full_report.json"]


def _run(reqs=None):
    return run_pipeline(reqs or _REQS, run_id=_RUN, policy_hash="0" * 64, method_version="m/1")


# 1. ACTIVATION: the wired chain runs end-to-end
def test_activation_end_to_end() -> None:
    res = _run()
    assert res["n"] == len(_REQS) and len(res["records"]) == len(_REQS)
    # credit-card arm with no declared policy => full-vector fail-closed (degenerate all-deny)
    assert all(d["decision"] == "SAFE_STATE" for d in res["decisions"]), \
        "no declared policy => Class-blind pipeline fail-closes (Gap-3(a))"
    assert res["ledger_head"] and res["records"][0]["HASH_prev"] == GENESIS


# 2. CLASS-BLIND: Class must not influence any record
def test_class_blind() -> None:
    base = _run([{"Amount": 149.62, "Time": 406, "V1": 0.1}])
    c0 = _run([{"Amount": 149.62, "Time": 406, "V1": 0.1, "Class": 0}])
    c1 = _run([{"Amount": 149.62, "Time": 406, "V1": 0.1, "Class": 1}])
    key = lambda r: json.dumps(r["records"], sort_keys=True)
    assert key(base) == key(c0) == key(c1), "Class must not influence the pipeline output"


# 3. DETERMINISTIC: identical inputs -> identical output
def test_deterministic() -> None:
    a, b = _run(), _run()
    assert json.dumps(a["records"], sort_keys=True) == json.dumps(b["records"], sort_keys=True)
    assert a["ledger_head"] == b["ledger_head"]


# 4. REPORTED ARTIFACT: ratified fields + provenance present
def test_reported_artifact_fields() -> None:
    rec = _run()["records"][0]
    for f in ("ProposalID", "PermitTokenID", "ERTuple_ID", "SubjectProfileID", "TimestampUTC",
              "CommitTimestamp", "ActuateTimestamp", "EnvironmentContext", "PolicyHash",
              "HASH_prev", "HASH_current", "LedgerCanon", "EvidenceBundleID", "EvidenceBundleDigest"):
        assert f in rec, "missing ratified field %s" % f
    assert "class=" not in rec["EnvironmentContext"], "EnvironmentContext must be Class-blind"
    assert rec["ActuateTimestamp"] == "", "SAFE_STATE row must not be actuated (decision-gated)"


# 5+6. REPLAY PASS + LEDGER/QUAD INTEGRITY via the FROZEN independent verifier
def test_replay_and_ledger_integrity() -> None:
    res = _run()
    with tempfile.TemporaryDirectory() as d:
        m = Path(d) / "pipeline_manifest.jsonl"
        summary = write_pipeline_manifest(res, m)
        assert summary["genesis_anchored"] and summary["adjacency_all_ok"]
        proc = subprocess.run(
            [sys.executable, str(ROOT / "gamma_replay_verify.py"), str(m),
             "--expect-sha256", summary["manifest_sha256"]],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout
        assert "RESULT              : PASS" in proc.stdout, proc.stdout
        assert "adjacency failures  : 0" in proc.stdout
        assert "ledger-bind failures: 0" in proc.stdout
        assert "consistency failures: 0" in proc.stdout


# 7. NEUTRAL: no repo reported artifact is touched by a pipeline run
def test_neutral_no_reported_artifact_touched() -> None:
    before = {p: (p.stat().st_mtime_ns if p.exists() else None) for p in _REPORTED}
    res = _run()
    with tempfile.TemporaryDirectory() as d:
        write_pipeline_manifest(res, Path(d) / "m.jsonl")     # writes only under the temp dir
    after = {p: (p.stat().st_mtime_ns if p.exists() else None) for p in _REPORTED}
    assert before == after, "Phase A must not modify any reported artifact"


def _run_all() -> int:
    checks = [
        test_activation_end_to_end,
        test_class_blind,
        test_deterministic,
        test_reported_artifact_fields,
        test_replay_and_ledger_integrity,
        test_neutral_no_reported_artifact_touched,
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
    print("class_blind_pipeline self-test: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
