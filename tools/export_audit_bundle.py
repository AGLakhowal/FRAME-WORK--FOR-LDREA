#!/usr/bin/env python3
"""
tools/export_audit_bundle.py — build and verify the L-DREA audit bundle (`gamma_bundle/`).
==========================================================================================

WHAT THIS CLOSES
----------------
ConcurBench Level 4 ("replay & auditability") tested `audit_packet_export`, and that check had never
been satisfiable because nothing in the repository ever produced an audit bundle. The result was a
standing `FAIL` and a `PARTIAL` Level-4 verdict caused by *missing engineering*, not by a scientific
deficiency. This module implements the missing export.

WHAT THE BUNDLE IS
------------------
A self-describing, checksummed archive that lets a third party re-verify the evaluation without this
repository's source tree and without the dataset:

    gamma_bundle/
      MANIFEST.json          bundle identity + every member file with sha256 + size + role
      CHECKSUMS.sha256       flat digest list (standard `shasum -c` format)
      VERIFY.md              exact commands a reviewer runs to re-verify
      evidence/              the executed experiment artifacts (E1..E9)
      replay_package/        the independent verifier + ledger anchor/terminus + ledger digest
      reproducibility/       host, run index, dataset fingerprint, claim + reviewer evidence
      formal/               the TLA+ spec, its .cfg, and the executed TLC log

HONESTY CONSTRAINTS
-------------------
* Nothing is computed here. Every file is copied verbatim from an executed artifact, and every digest
  is recomputed from the bytes actually written into the bundle.
* The 192 MB Hydra Ledger is included **by digest and anchor slice**, not by copy, unless `--full` is
  passed. `MANIFEST.json` states which mode was used. A digest reference is not silently presented as
  a full ledger copy.
* `verify_bundle()` is the criterion ConcurBench consumes. It re-reads the manifest, re-hashes every
  member, and confirms the ledger digest matches the live manifest. Mere existence of the directory
  is NOT sufficient — an empty or tampered bundle fails.

Usage:
    python tools/export_audit_bundle.py            # digest-reference ledger (default)
    python tools/export_audit_bundle.py --full     # embed the full 192 MB ledger
    python tools/export_audit_bundle.py --verify   # verify an existing bundle, exit 0/1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "gamma_bundle"
SCHEMA_VERSION = "gamma-audit-bundle/v1"

# Ledger anchor slice: the first and last N records are embedded so that the GENESIS anchor and the
# chain terminus are inside the bundle even in digest-reference mode.
ANCHOR_RECORDS = 64

# (repo-relative source, bundle-relative destination, role). Absent sources are recorded as MISSING
# in the manifest rather than skipped silently.
EVIDENCE = [
    ("experiments/runtime_correctness/gamma_lab_v1_report.json", "evidence/E1_gamma_lab_v1_report.json", "E1 primary metrics"),
    ("experiments/runtime_correctness/gamma_summary.json", "evidence/E1_gamma_summary.json", "E1 decision distribution"),
    ("experiments/runtime_correctness/full_spec_conformance_report.json", "evidence/E1_full_spec_conformance.json", "FULL_SPEC conformance"),
    ("experiments/runtime_correctness/fcr_test_report.json", "evidence/E1_fcr_test.json", "Fail-Closed Rate"),
    ("experiments/runtime_correctness/concurbench_full_report.json", "evidence/E1_concurbench.json", "ConcurBench L1-L4"),
    ("experiments/runtime_correctness/stress_test_report.json", "evidence/E1_financial_stress.json", "Financial stress P1-P4"),
    ("experiments/replay/replay_report.json", "evidence/E2_replay_report.json", "E2 replay integrity"),
    ("experiments/formal/independent_verifier_report.json", "evidence/E3_independent_verifier.json", "E3 exhaustive 2^16"),
    ("experiments/stress/concurrency_scaling.json", "evidence/E4_concurrency_scaling.json", "E4 concurrency"),
    ("experiments/ablation/ablation.json", "evidence/E5_ablation.json", "E5 component ablation"),
    ("experiments/profiling/runtime_profile.json", "evidence/E6_runtime_profile.json", "E6 profiling"),
    ("experiments/agentdojo/statistics.json", "evidence/E7_agentdojo_statistics.json", "E7 AgentDojo statistics"),
    ("experiments/agentdojo/boundary/boundary_fpr.json", "evidence/E7_boundary_fpr.json", "E7 boundary FPR"),
    ("fresh_evidence/robustness/robustness.json", "evidence/E8_robustness.json", "E8 fault injection"),
    ("fresh_evidence/predicate_coverage/predicate_coverage.json", "evidence/E9_predicate_coverage.json", "E9 predicate coverage"),
    ("experiments/statistics/statistics_report.json", "evidence/statistics_report.json", "Wilson / bootstrap / effect sizes"),
    ("experiments/provenance/provenance_graph.json", "evidence/provenance_graph.json", "Provenance chain"),
]

REPRODUCIBILITY = [
    ("experiments/_meta/host.json", "reproducibility/host.json", "Execution host + git commit + seed"),
    ("experiments/_meta/run_index.json", "reproducibility/run_index.json", "Per-experiment status + duration"),
    ("experiments/_meta/dataset_fingerprint.json", "reproducibility/dataset_fingerprint.json", "Dataset SHA-256"),
    ("evidence_manifest.json", "reproducibility/evidence_manifest.json", "Claim -> artifact -> pointer"),
    ("CLAIM_EVIDENCE_MATRIX.md", "reproducibility/CLAIM_EVIDENCE_MATRIX.md", "Claim evidence matrix"),
    ("reviewer_mapping.md", "reproducibility/reviewer_mapping.md", "Reviewer concern mapping"),
    ("LIMITATIONS_AND_NEGATIVE_RESULTS.md", "reproducibility/LIMITATIONS_AND_NEGATIVE_RESULTS.md", "Disclosed limitations"),
    ("THREATS_TO_VALIDITY.md", "reproducibility/THREATS_TO_VALIDITY.md", "Threats to validity"),
]

REPLAY = [
    ("gamma_replay_verify.py", "replay_package/gamma_replay_verify.py", "Independent replay verifier"),
]

FORMAL = [
    ("formal/ExternalizationMonitor.tla", "formal/ExternalizationMonitor.tla", "TLA+ specification"),
    ("formal/ExternalizationMonitor.cfg", "formal/ExternalizationMonitor.cfg", "TLC configuration"),
    ("experiments/formal/logs/E3_tlc.log", "formal/E3_tlc.log", "Executed TLC log"),
]

LEDGER = ROOT / "gamma_replay_manifest.jsonl"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy(src_rel: str, dst_rel: str, role: str, members: list) -> None:
    src = ROOT / src_rel
    dst = BUNDLE / dst_rel
    if not src.exists():
        members.append({"path": dst_rel, "role": role, "source": src_rel, "status": "MISSING",
                        "note": "source artifact absent at export time"})
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    members.append({"path": dst_rel, "role": role, "source": src_rel, "status": "PRESENT",
                    "sha256": sha256_file(dst), "bytes": dst.stat().st_size})


def _ledger_component(full: bool, members: list) -> dict:
    """Embed the ledger either fully or as digest + anchor/terminus slice. Never pretend."""
    if not LEDGER.exists():
        return {"mode": "ABSENT", "note": "gamma_replay_manifest.jsonl not present; run E1 first."}

    digest = sha256_file(LEDGER)
    n_bytes = LEDGER.stat().st_size

    if full:
        dst = BUNDLE / "replay_package" / LEDGER.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEDGER, dst)
        members.append({"path": f"replay_package/{LEDGER.name}", "role": "Hydra Ledger (full)",
                        "source": LEDGER.name, "status": "PRESENT",
                        "sha256": sha256_file(dst), "bytes": dst.stat().st_size})
        return {"mode": "EMBEDDED_FULL", "sha256": digest, "bytes": n_bytes,
                "note": "The complete hash-chained ledger is inside this bundle."}

    # digest-reference mode: embed the anchor (first N) and terminus (last N) records
    head, tail, total = [], [], 0
    with LEDGER.open("r") as f:
        for i, line in enumerate(f):
            total += 1
            if i < ANCHOR_RECORDS:
                head.append(line.rstrip("\n"))
            tail.append(line.rstrip("\n"))
            if len(tail) > ANCHOR_RECORDS:
                tail.pop(0)

    slice_path = BUNDLE / "replay_package" / "ledger_anchor_slice.jsonl"
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_path.write_text("\n".join(head + tail) + "\n")
    members.append({"path": "replay_package/ledger_anchor_slice.jsonl",
                    "role": f"Hydra Ledger anchor + terminus ({ANCHOR_RECORDS} records each end)",
                    "source": LEDGER.name, "status": "PRESENT",
                    "sha256": sha256_file(slice_path), "bytes": slice_path.stat().st_size})

    return {"mode": "DIGEST_REFERENCE", "sha256": digest, "bytes": n_bytes,
            "n_records": total, "anchor_records_embedded": min(ANCHOR_RECORDS, total),
            "terminus_records_embedded": len(tail),
            "note": ("The full ledger is referenced by SHA-256, not copied (192 MB). The GENESIS "
                     "anchor and the chain terminus ARE embedded. Re-export with --full to embed "
                     "the complete ledger.")}


def export(full: bool = False) -> dict:
    if BUNDLE.exists():
        shutil.rmtree(BUNDLE)
    BUNDLE.mkdir(parents=True)

    members: list = []
    for group in (EVIDENCE, REPRODUCIBILITY, REPLAY, FORMAL):
        for src, dst, role in group:
            _copy(src, dst, role, members)

    ledger = _ledger_component(full, members)

    lab = ROOT / "experiments" / "runtime_correctness" / "gamma_lab_v1_report.json"
    method_version = "unknown"
    if lab.exists():
        try:
            method_version = json.loads(lab.read_text()).get("method_version", "unknown")
        except Exception:
            pass
    host = {}
    hp = ROOT / "experiments" / "_meta" / "host.json"
    if hp.exists():
        try:
            host = json.loads(hp.read_text())
        except Exception:
            host = {}

    present = [m for m in members if m["status"] == "PRESENT"]
    missing = [m for m in members if m["status"] == "MISSING"]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": hashlib.sha256(
            json.dumps(sorted(m.get("sha256", m["path"]) for m in present)).encode()).hexdigest(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method_version": method_version,
        "git_commit": host.get("git_head"),
        "eval_seed": host.get("eval_seed"),
        "producer": "tools/export_audit_bundle.py",
        "ledger": ledger,
        "counts": {"members_present": len(present), "members_missing": len(missing),
                   "total_bytes": sum(m.get("bytes", 0) for m in present)},
        "members": members,
        "verification": {
            "checksums": "CHECKSUMS.sha256",
            "command": "shasum -a 256 -c CHECKSUMS.sha256",
            "programmatic": "python tools/export_audit_bundle.py --verify",
            "replay": "python replay_package/gamma_replay_verify.py <path-to-gamma_replay_manifest.jsonl>",
        },
        "scope_note": ("This bundle contains executed artifacts only. It does not contain the "
                       "430 MB source dataset; the dataset is identified by SHA-256 in "
                       "reproducibility/dataset_fingerprint.json."),
        "self_reference": {
            "member": "evidence/E1_concurbench.json",
            "explanation": (
                "ConcurBench's Level-4 `audit_packet_export` check verifies THIS bundle, and the "
                "resulting report is then packaged INTO the bundle. The embedded report therefore "
                "records the verification of the immediately preceding bundle generation, and this "
                "manifest's `bundle_id` was recomputed after that report was sealed. This is the "
                "ordinary self-reference of any signed release whose checksum file cannot checksum "
                "itself. It is stated here rather than left for a reviewer to discover."),
            "what_a_reviewer_can_still_check_independently": [
                "shasum -a 256 -c CHECKSUMS.sha256   (every member re-hashes)",
                "python tools/export_audit_bundle.py --verify   (manifest + ledger binding)",
                "python replay_package/gamma_replay_verify.py <ledger>   (no engine, no dataset)",
            ],
        },
    }
    (BUNDLE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

    lines = [f"{m['sha256']}  {m['path']}" for m in present]
    (BUNDLE / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n")

    (BUNDLE / "VERIFY.md").write_text(f"""# Verifying this audit bundle

Bundle id: `{manifest['bundle_id']}`
Created:   {manifest['created_utc']}
Method:    `{method_version}`
Ledger:    {ledger.get('mode')} · sha256 `{ledger.get('sha256', 'n/a')}`

## 1. Verify every member checksum

```bash
cd gamma_bundle
shasum -a 256 -c CHECKSUMS.sha256
```

Every line must report `OK`. {len(present)} files are covered.

## 2. Verify the bundle programmatically

```bash
python tools/export_audit_bundle.py --verify
```

This re-reads `MANIFEST.json`, re-hashes every member from its bytes, and confirms the recorded
ledger digest still matches the live `gamma_replay_manifest.jsonl`. Exit code 0 means the bundle is
internally consistent and bound to the ledger it claims.

## 3. Re-verify the ledger independently

```bash
python replay_package/gamma_replay_verify.py gamma_replay_manifest.jsonl
```

The verifier shares no code with the authorization engine and never reads the dataset. Exit 0 = PASS.

## What is NOT in this bundle

* The 430 MB source dataset. It is identified by SHA-256 in
  `reproducibility/dataset_fingerprint.json`.
* {"Nothing else — the full ledger is embedded." if ledger.get('mode') == 'EMBEDDED_FULL' else
  "The full 192 MB ledger. It is referenced by SHA-256; the GENESIS anchor and chain terminus are embedded in `replay_package/ledger_anchor_slice.jsonl`. Re-export with `--full` to embed it."}
""")

    return manifest


def verify_bundle(bundle: Path = BUNDLE) -> dict:
    """The criterion ConcurBench consumes. Existence is necessary but far from sufficient."""
    result = {"bundle_present": bundle.exists(), "checks": {}, "status": "FAIL"}
    if not bundle.exists():
        result["reason"] = "gamma_bundle/ does not exist; run tools/export_audit_bundle.py"
        return result

    mpath = bundle / "MANIFEST.json"
    if not mpath.exists():
        result["reason"] = "MANIFEST.json missing"
        return result
    try:
        man = json.loads(mpath.read_text())
    except Exception as e:  # noqa: BLE001
        result["reason"] = f"MANIFEST.json unparseable: {e}"
        return result

    result["bundle_id"] = man.get("bundle_id")
    result["schema_version"] = man.get("schema_version")

    present = [m for m in man.get("members", []) if m.get("status") == "PRESENT"]
    result["checks"]["schema_known"] = man.get("schema_version") == SCHEMA_VERSION
    result["checks"]["has_members"] = len(present) > 0
    result["checks"]["checksums_file"] = (bundle / "CHECKSUMS.sha256").exists()
    result["checks"]["verify_doc"] = (bundle / "VERIFY.md").exists()

    # every member must exist and re-hash to its recorded digest
    bad = []
    for m in present:
        p = bundle / m["path"]
        if not p.exists():
            bad.append({"path": m["path"], "issue": "absent"})
            continue
        if sha256_file(p) != m["sha256"]:
            bad.append({"path": m["path"], "issue": "digest mismatch"})
    result["checks"]["all_member_digests_match"] = not bad
    result["member_failures"] = bad
    result["members_verified"] = len(present) - len(bad)

    # required roles must be represented
    paths = {m["path"] for m in present}
    required = ["MANIFEST.json"]  # checked separately
    need_prefix = ["evidence/", "reproducibility/", "replay_package/", "formal/"]
    result["checks"]["all_sections_present"] = all(
        any(p.startswith(pre) for p in paths) for pre in need_prefix)

    # the recorded ledger digest must still match the live ledger
    led = man.get("ledger", {})
    if LEDGER.exists() and led.get("sha256"):
        live = sha256_file(LEDGER)
        result["checks"]["ledger_digest_matches_live"] = (live == led["sha256"])
        result["ledger_sha256_recorded"] = led["sha256"]
        result["ledger_sha256_live"] = live
    else:
        result["checks"]["ledger_digest_matches_live"] = False
        result["ledger_note"] = "live ledger absent; cannot bind bundle to it"

    result["checks"]["no_missing_members"] = man.get("counts", {}).get("members_missing", 1) == 0
    result["status"] = "PASS" if all(result["checks"].values()) else "FAIL"
    if result["status"] == "FAIL":
        result["reason"] = "failing checks: " + ", ".join(k for k, v in result["checks"].items() if not v)
    return result


def main():
    ap = argparse.ArgumentParser(description="Build or verify the L-DREA audit bundle.")
    ap.add_argument("--full", action="store_true", help="embed the complete 192 MB ledger")
    ap.add_argument("--verify", action="store_true", help="verify an existing bundle and exit")
    args = ap.parse_args()

    if args.verify:
        r = verify_bundle()
        print(json.dumps(r, indent=2))
        print(f"[audit-bundle] verification: {r['status']}")
        return 0 if r["status"] == "PASS" else 1

    man = export(full=args.full)
    r = verify_bundle()
    c = man["counts"]
    print(f"[audit-bundle] wrote gamma_bundle/  ({c['members_present']} members, "
          f"{c['members_missing']} missing, {c['total_bytes'] / 1e6:.1f} MB)")
    print(f"[audit-bundle] ledger: {man['ledger'].get('mode')}")
    print(f"[audit-bundle] self-verification: {r['status']}")
    if r["status"] != "PASS":
        print(f"[audit-bundle] reason: {r.get('reason')}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
