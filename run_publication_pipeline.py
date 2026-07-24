#!/usr/bin/env python3
"""
run_publication_pipeline.py — one command: execute everything, regenerate every artifact.
=========================================================================================

    python3 run_publication_pipeline.py            # full (publication grade)
    python3 run_publication_pipeline.py --fast     # quick smoke run (smaller n / row limits)
    python3 run_publication_pipeline.py --skip-experiments   # regenerate outputs from existing runs

Stages (each is a real execution; a failing stage is REPORTED, never silently skipped):

    1  combined ablation (E5b)        experiment_combined_ablation.py      -> configs, interactions, statistics
    2  threshold sensitivity          experiment_threshold_sensitivity.py  -> +/-20% conclusion stability
    3  cross-dataset ablation         experiment_cross_dataset_ablation.py -> ULB / IEEE-CIS / UNSW-NB15
    4  IEEE LaTeX tables              generate_paper_tables.py
    5  publication figures            generate_paper_figures.py            -> SVG + PDF + PNG
    6  threats to validity            generate_threats_to_validity.py
    7  provenance metadata            generate_provenance_metadata.py      -> git/dataset/seed/env hashes
    8  dashboards                     generate_dashboard_html.py + generate_runtime_eval_dashboard.py
    9  publication package            build_publication_package.py         -> PUBLICATION_PACKAGE/ + FINAL validation
    10 regression tests               unittest discover
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def stage(n, title, argv, results, optional=False):
    print(f"\n{'='*78}\n[{n}] {title}\n{'='*78}")
    t0 = time.time()
    if not (ROOT / argv[0]).exists() and not argv[0].startswith("-"):
        print(f"  SKIPPED — {argv[0]} not found")
        results.append({"stage": n, "title": title, "status": "MISSING_SCRIPT",
                        "script": argv[0], "seconds": 0})
        return
    rc = subprocess.run([PY] + argv, cwd=ROOT).returncode
    dt = round(time.time() - t0, 1)
    status = "OK" if rc == 0 else ("OPTIONAL_FAIL" if optional else "FAILED")
    results.append({"stage": n, "title": title, "status": status, "rc": rc, "seconds": dt})
    print(f"  -> {status} ({dt}s)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--skip-experiments", action="store_true",
                    help="regenerate tables/figures/package from existing experiment outputs")
    a = ap.parse_args()
    fast = ["--fast"] if a.fast else []
    t0 = time.time()
    results: list[dict] = []

    if not a.skip_experiments:
        stage(1, "Combined ablation (E5b)", ["experiment_combined_ablation.py"] + fast, results)
        stage(2, "Threshold sensitivity (±10%, ±20%)",
              ["experiment_threshold_sensitivity.py"] + fast, results)
        stage(3, "Cross-dataset ablation (ULB / IEEE-CIS / UNSW-NB15)",
              ["experiment_cross_dataset_ablation.py"] + fast, results)
    else:
        print("[pipeline] --skip-experiments: reusing existing experiment outputs")

    stage(4, "IEEE LaTeX tables", ["generate_paper_tables.py"], results)
    stage(5, "Publication figures (SVG + PDF + PNG)", ["generate_paper_figures.py"], results)
    stage(6, "Threats to validity", ["generate_threats_to_validity.py"], results)
    stage(7, "Provenance metadata", ["generate_provenance_metadata.py"], results)
    stage(8, "Scientific dashboard", ["experiments/generate_dashboard_html.py"], results)
    stage(8, "Runtime evaluation dashboard", ["experiments/generate_runtime_eval_dashboard.py"], results)
    # provenance again, now that figures/threats exist, so the manifest is complete
    stage(7, "Provenance metadata (re-run: figures + threats now exist)",
          ["generate_provenance_metadata.py"], results)
    stage(9, "Publication package + FINAL validation", ["build_publication_package.py"], results)
    stage(10, "Regression tests", ["-m", "unittest", "discover", "-s", "tests",
                                   "-p", "test_combined_ablation*", "-v"], results, optional=True)

    print(f"\n{'='*78}\nPIPELINE SUMMARY ({round(time.time()-t0,1)}s)\n{'='*78}")
    ok = True
    for r in results:
        mark = {"OK": "✅", "FAILED": "❌", "OPTIONAL_FAIL": "⚠️ ", "MISSING_SCRIPT": "⚠️ "}[r["status"]]
        print(f"  {mark} [{r['stage']:>2}] {r['title']:<52} {r['status']:<14} {r['seconds']}s")
        if r["status"] == "FAILED":
            ok = False
    print(f"\n{'✅ PIPELINE COMPLETE' if ok else '❌ PIPELINE HAD FAILURES (see above)'}")
    print("   -> PUBLICATION_PACKAGE/  ·  FINAL_PUBLICATION_VALIDATION.md")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
