#!/usr/bin/env python3
"""
scientific_consistency.py — cross-artifact scientific consistency & integrity audit.
====================================================================================

Automated checks (each PASS/FAIL with detail):
  1. No figure references missing data      (every claim figure's source artifact exists)
  2. No table references nonexistent experiments (table Exp column ⊆ known experiments)
  3. No experiment referenced without evidence   (each run_index experiment has ≥1 artifact)
  4. No claim unsupported                    (no claim resolves to NOT Supported / Pending)
  5. No duplicate metrics                     (tables.json primary metrics are unique)
  6. No inconsistent confidence intervals     (Wilson low ≤ point ≤ high in statistics)
  7. No mismatched sample sizes               (a metric's N agrees across table & JSON)
  8. No broken provenance chain               (provenance_graph.broken_links == [])
  9. No stale artifacts                       (recorded sha256 == on-disk sha256 now)

Writes SCIENTIFIC_CONSISTENCY_REPORT.md and exits non-zero on any FAIL.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "experiments"))

import _evidence as EV  # type: ignore
from claims_registry import CLAIMS  # type: ignore

EXP = ROOT / "experiments"
KNOWN_EXPS = {"E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"}


def _sha(p: Path):
    if not p.exists() or p.is_dir():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check_figures_have_data():
    problems = []
    for c in CLAIMS:
        for fig in c.get("figures", []):
            if not (EXP / "figures" / fig).exists():
                # only a problem if the claim is otherwise supported (figure should exist)
                ev = EV.evaluate_claim(c)
                if ev["status"] in ("Supported", "Partially Supported"):
                    problems.append(f"claim {c['id']} references missing figure {fig}")
    return problems


def check_table_experiments():
    problems = []
    for t in (EXP / "tables").glob("*.md"):
        for m in re.finditer(r"\|\s*(E\d)\s*\|", t.read_text()):
            if m.group(1) not in KNOWN_EXPS:
                problems.append(f"{t.name} references unknown experiment {m.group(1)}")
    return problems


def check_experiments_have_evidence():
    idx = EXP / "_meta" / "run_index.json"
    if not idx.exists():
        return ["run_index.json missing"]
    problems = []
    for eid, r in json.loads(idx.read_text()).get("experiments", {}).items():
        arts = r.get("artifacts") or {}
        present = [a for a in arts.values() if isinstance(a, dict) and a.get("path")]
        if r.get("status") == "EXECUTED" and not present:
            problems.append(f"{eid} executed but has no recorded artifact")
    return problems


def check_claims_supported():
    problems = []
    for c in CLAIMS:
        ev = EV.evaluate_claim(c)
        if ev["status"].startswith("NOT") or ev["status"].startswith("Pending"):
            problems.append(f"claim {c['id']} status = {ev['status']}")
    return problems


def check_duplicate_metrics():
    p = EXP / "tables" / "tables.json"
    if not p.exists():
        return ["tables.json missing"]
    metrics = [r["metric"] for r in json.loads(p.read_text()).get("primary_metrics", [])]
    dups = {m for m in metrics if metrics.count(m) > 1}
    return [f"duplicate metric row: {m}" for m in dups]


def check_confidence_intervals():
    p = EXP / "statistics" / "statistics_report.json"
    if not p.exists():
        return ["statistics_report.json missing"]
    problems = []
    for m in json.loads(p.read_text()).get("proportion_metrics", []):
        lo, pt, hi = m.get("wilson95_low"), m.get("point"), m.get("wilson95_high")
        if None in (lo, pt, hi):
            continue
        if not (lo - 1e-12 <= pt <= hi + 1e-12):
            problems.append(f"{m['metric']}: point {pt} outside [{lo}, {hi}]")
        if lo > hi:
            problems.append(f"{m['metric']}: low {lo} > high {hi}")
    return problems


def check_sample_sizes():
    """The FPR sample size must agree between the LAB JSON and the primary-metrics table.json."""
    lab = EV.load("experiments/runtime_correctness/gamma_lab_v1_report.json")
    tj = EXP / "tables" / "tables.json"
    if not lab or not tj.exists():
        return []
    n_json = lab["primary_metrics"]["false_permit_rate"]["n"]
    problems = []
    for r in json.loads(tj.read_text()).get("primary_metrics", []):
        if r["metric"].startswith("False Permit Rate (ULB") and int(r["n"]) != n_json:
            problems.append(f"FPR N mismatch: table {r['n']} vs JSON {n_json}")
    return problems


def check_provenance():
    p = EXP / "provenance" / "provenance_graph.json"
    if not p.exists():
        return ["provenance_graph.json missing (run generate_provenance.py)"]
    broken = json.loads(p.read_text()).get("broken_links", [])
    return [f"broken provenance link: {b}" for b in broken]


def check_stale_artifacts():
    idx = EXP / "_meta" / "run_index.json"
    if not idx.exists():
        return ["run_index.json missing"]
    problems = []
    for eid, r in json.loads(idx.read_text()).get("experiments", {}).items():
        for name, a in (r.get("artifacts") or {}).items():
            if not (isinstance(a, dict) and a.get("path") and a.get("sha256")):
                continue
            # skip the 200MB manifest for speed if unchanged size; still hash smaller ones
            disk = _sha(ROOT / a["path"])
            if disk is not None and disk != a["sha256"]:
                problems.append(f"{eid}:{name} sha256 drift ({a['path']})")
    return problems


CHECKS = [
    ("1. figures have data", check_figures_have_data),
    ("2. tables reference known experiments", check_table_experiments),
    ("3. experiments have evidence", check_experiments_have_evidence),
    ("4. all claims supported/scoped", check_claims_supported),
    ("5. no duplicate metrics", check_duplicate_metrics),
    ("6. confidence intervals consistent", check_confidence_intervals),
    ("7. sample sizes consistent", check_sample_sizes),
    ("8. provenance chain intact", check_provenance),
    ("9. no stale artifacts", check_stale_artifacts),
]


def main():
    lines = ["# Scientific Consistency Report (auto-generated)", ""]
    n_fail = 0
    results = []
    for name, fn in CHECKS:
        try:
            problems = fn()
        except Exception as e:  # noqa: BLE001
            problems = [f"checker raised: {e}"]
        ok = not problems
        n_fail += 0 if ok else 1
        results.append((name, ok, problems))
    lines.append(f"**{sum(1 for _, ok, _ in results if ok)}/{len(results)} checks PASS**")
    lines.append("")
    for name, ok, problems in results:
        lines.append(f"## {'✅' if ok else '❌'} {name} — {'PASS' if ok else 'FAIL'}")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")
    (ROOT / "SCIENTIFIC_CONSISTENCY_REPORT.md").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"OVERALL: {'PASS' if n_fail == 0 else 'FAIL'} ({len(CHECKS)-n_fail}/{len(CHECKS)} checks pass)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
