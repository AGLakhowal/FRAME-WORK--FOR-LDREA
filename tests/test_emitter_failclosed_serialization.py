"""H4 regression lock — emitter fail-closed serialization on absent/malformed observables.

Locks the minimal H4 fix: the Reported Artifact Emitter must SERIALIZE (never raise) when a plane-A
observable is ABSENT (None) or DEGRADED (non-numeric), coercing it to the existing 0.0 fail-closed
fallback — while keeping well-formed output byte-identical. Verified through the wired pipeline so
the whole path (decision + serialization) is fail-closed end-to-end.

Standard library + project modules; no pytest. Run:
    .venv/bin/python tests/test_emitter_failclosed_serialization.py     # exits 0 on success
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_context.class_blind_pipeline import run_pipeline, write_pipeline_manifest  # noqa: E402
from runtime_context.reported_artifact_emitter import _num, environment_context, _base_ts, EPOCH_BASE  # noqa: E402

_BAD = {
    "malformed_amount_str": {"Amount": "abc", "Time": 406, "V1": 0.1},
    "malformed_time_str": {"Amount": 10.0, "Time": "xyz"},
    "missing_time": {"Amount": 149.62, "V1": 0.1},
    "missing_amount": {"Time": 406, "V1": 0.1},
    "empty_request": {},
}


def _manifest_sha(res):
    with tempfile.TemporaryDirectory() as d:
        return write_pipeline_manifest(res, Path(d) / "m.jsonl")["manifest_sha256"]


# 1. _num coercion: absent/malformed/NaN -> 0.0; well-formed unchanged
def test_num_coercion() -> None:
    assert _num(None) == 0.0 and _num("abc") == 0.0 and _num(float("nan")) == 0.0
    assert _num(406) == 406.0 and _num(149.62) == 149.62 and _num("12.5") == 12.5


# 2. helpers never raise on absent/malformed and use the 0.0 fallback
def test_helpers_failclosed() -> None:
    assert _base_ts(None) == EPOCH_BASE and _base_ts("bad") == EPOCH_BASE
    ec = environment_context(None, None)
    assert ec == "ULB_2013_EU_CARD;source_time_sec=0;amount=0;source=anonymized_PCA"
    assert "class=" not in ec


# 3. full pipeline fail-closes end-to-end on every bad case (no raise; SAFE_STATE; valid replay)
def test_pipeline_failclosed_end_to_end() -> None:
    for name, req in _BAD.items():
        res = run_pipeline([req], run_id="H4LOCK", policy_hash="0" * 64)          # must not raise
        rec = res["records"][0]
        assert rec["Status"] == "SAFE_STATE", "%s must fail-closed" % name
        assert rec["HASH_prev"] == "GENESIS" and len(rec["HASH_current"]) == 64
        assert "class=" not in rec["EnvironmentContext"]
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.jsonl"
            s = write_pipeline_manifest(res, m)
            p = subprocess.run(
                [sys.executable, str(ROOT / "gamma_replay_verify.py"), str(m),
                 "--expect-sha256", s["manifest_sha256"]], capture_output=True, text=True)
        assert p.returncode == 0 and "RESULT              : PASS" in p.stdout, "%s replay" % name
        # deterministic
        assert _manifest_sha(run_pipeline([req], run_id="H4LOCK", policy_hash="0" * 64)) == s["manifest_sha256"]


# 4. well-formed output byte-identical (fix must not perturb the well-formed path)
def test_well_formed_byte_identical() -> None:
    reqs = [{"Amount": 100.0 + i, "Time": i * 3, "V1": (i % 7) * 0.1, "V2": (i % 3) * 0.2}
            for i in range(1, 25)]
    r = run_pipeline(reqs, run_id="B", policy_hash="0" * 64, method_version="m/1")
    rec_sha = hashlib.sha256(json.dumps(r["records"], sort_keys=True).encode()).hexdigest()
    assert rec_sha == "0e71f595053c1ccebbb44684551bfe55555251a49e4588cd5316ea145e7325a4", "records changed"
    assert _manifest_sha(r) == "ca1ab9fc9d6bd24f3d343506647f34553aacdd21c1065358d3f21a4ad1151134", "manifest changed"


def _run_all() -> int:
    checks = [test_num_coercion, test_helpers_failclosed,
              test_pipeline_failclosed_end_to_end, test_well_formed_byte_identical]
    failures = 0
    for fn in checks:
        try:
            fn()
            print("  PASS  %s" % fn.__name__)
        except AssertionError as exc:
            failures += 1
            print("  FAIL  %s: %s" % (fn.__name__, exc))
    print("-" * 60)
    print("emitter_failclosed_serialization: %d/%d passed" % (len(checks) - failures, len(checks)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
