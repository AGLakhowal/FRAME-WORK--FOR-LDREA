"""Fixture-loader smoke test for Commit 0.1 (Engineering Migration Roadmap, Phase 0).

Purpose (Commit 0.1 ONLY): confirm the frozen baseline regression fixtures are
present, parseable, and internally consistent with their recorded SHA-256 manifest.

This is a SMOKE TEST for the fixtures themselves. It deliberately does NOT compare
the fixtures against freshly regenerated pipeline outputs -- that enforced parity gate
is Commit 6.3, not this commit. Nothing here touches Gamma, predicates, LAB,
ConcurBench, AgentDojo, the RCL, or the EEB.

Runnable two ways (pytest is not installed in this repo's envs):
    python3 tests/test_baseline_fixtures.py      # standalone; exits 0 on success
    pytest tests/test_baseline_fixtures.py       # if pytest is later added
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASELINE_DIR = Path(__file__).resolve().parent / "fixtures" / "baseline"

# The active-pipeline report outputs frozen by Commit 0.1 (JSON, byte-copied).
REPORT_FIXTURES = [
    "gamma_lab_v1_report.json",
    "gamma_summary.json",
    "concurbench_full_report.json",
    "stress_test_report.json",
    "fcr_test_report.json",
    "full_spec_conformance_report.json",
]
# The replay manifest is captured by SHA only (the manifest itself is ~200 MB).
REPLAY_SHA_FILE = "gamma_replay_manifest.sha256"
MANIFEST_FILE = "MANIFEST.sha256"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_manifest() -> dict:
    """Read MANIFEST.sha256 ('<sha>  <name>' per line) into {name: sha}."""
    entries = {}
    for line in (BASELINE_DIR / MANIFEST_FILE).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        sha, name = line.split(None, 1)
        entries[name.strip()] = sha.strip()
    return entries


def test_baseline_dir_exists() -> None:
    assert BASELINE_DIR.is_dir(), f"missing baseline fixtures dir: {BASELINE_DIR}"


def test_report_fixtures_present_and_valid_json() -> None:
    for name in REPORT_FIXTURES:
        p = BASELINE_DIR / name
        assert p.is_file(), f"missing baseline fixture: {name}"
        obj = json.loads(p.read_text())
        assert obj, f"baseline fixture is empty: {name}"


def test_replay_sha_recorded() -> None:
    p = BASELINE_DIR / REPLAY_SHA_FILE
    assert p.is_file(), f"missing replay SHA fixture: {REPLAY_SHA_FILE}"
    parts = p.read_text().split()
    assert len(parts) >= 2, "replay SHA file malformed (expected '<sha>  <name>')"
    sha = parts[0]
    assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), \
        "replay SHA is not a 64-hex SHA-256"


def test_manifest_matches_fixture_contents() -> None:
    """Every JSON fixture's on-disk SHA must equal its recorded manifest SHA."""
    manifest = _parse_manifest()
    for name in REPORT_FIXTURES:
        assert name in manifest, f"{name} absent from MANIFEST.sha256"
        actual = _sha256(BASELINE_DIR / name)
        assert actual == manifest[name], (
            f"SHA mismatch for {name}: fixture={actual} manifest={manifest[name]}"
        )
    # The replay manifest SHA line must also be present in the index.
    assert "gamma_replay_manifest.jsonl" in manifest, \
        "replay manifest SHA absent from MANIFEST.sha256"


def _run_all() -> int:
    checks = [
        test_baseline_dir_exists,
        test_report_fixtures_present_and_valid_json,
        test_replay_sha_recorded,
        test_manifest_matches_fixture_contents,
    ]
    failures = 0
    for fn in checks:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
    print("-" * 60)
    print(f"baseline fixture smoke test: {len(checks) - failures}/{len(checks)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
