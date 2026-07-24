#!/usr/bin/env python3
"""
Independent ERTuple replay-manifest verifier
============================================

Re-checks a per-item replay manifest produced by gamma_test_runner.py WITHOUT
pandas, the original dataset, or the runner itself — the whole point of the
manifest is that a third party can audit every decision from this one file.

For each decision record it re-derives:

  * hash-chain adjacency : rec[i].hash_prev == rec[i-1].hash_current
                           (rec[0] must be GENESIS-anchored)
  * evidence-quad ledger : rec.evidence_quad.ledger_hash == rec.hash_current
  * self-consistency     : decision == evidence_quad.decision, pi/gamma agree

It also recomputes the manifest's own SHA-256 (over the exact bytes of every
line) so you can confirm the file has not been altered since it was emitted.

Usage:
  python gamma_replay_verify.py gamma_replay_manifest.jsonl
  python gamma_replay_verify.py gamma_replay_manifest.jsonl --expect-sha256 <hex>

Exit code 0 iff every check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys


GENESIS_TOKENS = {"GENESIS", "0", "NONE", ""}


def main() -> int:
    ap = argparse.ArgumentParser(description="Independently verify a GAMMA G-0 replay manifest.")
    ap.add_argument("manifest", help="Path to the JSONL replay manifest.")
    ap.add_argument(
        "--expect-sha256",
        default=None,
        help="If given, assert the manifest's recomputed SHA-256 equals this value.",
    )
    args = ap.parse_args()

    manifest_hash = hashlib.sha256()
    header = None
    n_decisions = 0
    adjacency_fail = 0
    ledger_fail = 0
    consistency_fail = 0
    prev_current = None
    first_seen = False

    with open(args.manifest, "rb") as fh:
        for raw in fh:
            manifest_hash.update(raw)
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("record") == "header":
                header = rec
                continue
            if rec.get("record") != "decision":
                continue

            n_decisions += 1
            hp = str(rec["hash_prev"])
            hc = str(rec["hash_current"])

            # 1. adjacency / genesis anchoring
            if not first_seen:
                adj = hp.upper() in GENESIS_TOKENS
                first_seen = True
            else:
                adj = (hp == prev_current)
            if not adj:
                adjacency_fail += 1
                if adjacency_fail <= 5:
                    print(f"  [adjacency] seq={rec.get('seq')} "
                          f"hash_prev={hp[:16]}.. != prev hash_current="
                          f"{(prev_current or '')[:16]}..")
            prev_current = hc

            # 2. evidence-quad ledger binding
            quad = rec.get("evidence_quad", {})
            if str(quad.get("ledger_hash")) != hc:
                ledger_fail += 1
                if ledger_fail <= 5:
                    print(f"  [ledger] seq={rec.get('seq')} "
                          f"evidence_quad.ledger_hash != hash_current")

            # 3. self-consistency of the record
            if quad.get("decision") != rec.get("decision"):
                consistency_fail += 1
            else:
                pi = rec.get("pi")
                gg = rec.get("gamma_g")
                gc = rec.get("gamma_class")
                expect_permit = (gg == 0 and gc == 0)
                if (pi == 1) != expect_permit or (rec.get("decision") == "PERMIT") != (pi == 1):
                    consistency_fail += 1

    manifest_sha = manifest_hash.hexdigest()
    ok = (adjacency_fail == 0 and ledger_fail == 0 and consistency_fail == 0)

    print("=" * 60)
    print("  GAMMA G-0 replay-manifest verification")
    print("=" * 60)
    print(f"manifest            : {args.manifest}")
    if header:
        print(f"method_version      : {header.get('method_version')}")
        print(f"declared n_records  : {header.get('n_records')}")
        print(f"genesis anchor      : {header.get('genesis_anchor')}")
    print(f"decision records    : {n_decisions}")
    print(f"adjacency failures  : {adjacency_fail}")
    print(f"ledger-bind failures: {ledger_fail}")
    print(f"consistency failures: {consistency_fail}")
    print(f"manifest SHA-256    : {manifest_sha}")

    if header and header.get("n_records") not in (None, n_decisions):
        print(f"[warn] header n_records={header.get('n_records')} "
              f"!= counted {n_decisions}")
        ok = False

    if args.expect_sha256:
        if args.expect_sha256.lower() == manifest_sha:
            print("expected SHA-256    : MATCH")
        else:
            print(f"expected SHA-256    : MISMATCH (wanted {args.expect_sha256})")
            ok = False

    print("-" * 60)
    print("RESULT              :", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
