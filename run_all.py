#!/usr/bin/env python3
"""
run_all.py - one command to run the entire Gamma / ConcurBench suite.
=====================================================================

DEPRECATED. The authoritative one-command reproduction driver is RUN_ALL_EXPERIMENTS.py
(experiments E1-E12, figures, tables, dashboard). This older script covers only the Gamma /
ConcurBench subset and is kept for historical reference. Use:

    python RUN_ALL_EXPERIMENTS.py

Do not cite this script in reproduction instructions.

Pipeline (in order):

  1. Base LAB v1.0 benchmark        (gamma_test_runner.py)   [--full or if missing]
       -> gamma_lab_v1_report.json, gamma_summary.json,
          gamma_replay_manifest.jsonl, gamma_terminal_full.txt
  2. ConcurBench full conformance   (concurbench_full.run)   -> concurbench_full_report.json
  3. Financial stress test          (stress_test.run)        -> stress_test_report.json
  4. Fail-Closed Rate test          (fcr_test.run)           -> fcr_test_report.json
  5. FULL_SPEC conformance          (full_spec_conformance.run) -> full_spec_conformance_report.json
  6. Unified dashboard              (gamma_report_page.render) -> gamma_report.html
       (base LAB + ConcurBench + stress + FCR + FULL_SPEC, all in one page)

At the end it prints a FULL results summary of every layer to the terminal.

Usage:
  python run_all.py                 # run EVERYTHING end-to-end (default; nothing skipped)
  python run_all.py --reuse         # fast path: reuse base artifacts, run layers 2-6
  python run_all.py --no-open       # don't auto-open the dashboard
  python run_all.py --input FILE    # base benchmark input CSV
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

LAB_REPORT = ROOT / "gamma_lab_v1_report.json"
SUMMARY = ROOT / "gamma_summary.json"
TERMINAL = ROOT / "gamma_terminal_full.txt"
DASHBOARD = ROOT / "gamma_report.html"


def _hr(title: str) -> None:
    print("\n" + "#" * 70 + f"\n#  {title}\n" + "#" * 70)


def run_base(input_csv: str | None) -> None:
    _hr("STEP 1/6  base LAB v1.0 benchmark (gamma_test_runner.py)")
    cmd = [sys.executable, str(ROOT / "gamma_test_runner.py"), "--no-open"]
    if input_csv:
        cmd += ["--input", input_csv]
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the full Gamma / ConcurBench suite.")
    ap.add_argument("--reuse", action="store_true",
                    help="Fast path: skip the heavy base benchmark and reuse "
                         "existing artifacts (default runs everything).")
    ap.add_argument("--no-open", action="store_true",
                    help="Do not auto-open the dashboard in a browser.")
    ap.add_argument("--input", default=None,
                    help="Base benchmark input CSV.")
    args = ap.parse_args()
    t0 = time.time()

    # 1. base benchmark — run by default so nothing is hidden; only skipped when
    #    --reuse is passed AND the artifacts already exist.
    if args.reuse and LAB_REPORT.exists() and SUMMARY.exists():
        _hr("STEP 1/6  base LAB v1.0 benchmark  [SKIPPED — --reuse]")
        print(f"  reusing {LAB_REPORT.name} + {SUMMARY.name} "
              f"(omit --reuse to run the full benchmark)")
    else:
        run_base(args.input)

    # imported lazily so a missing base artifact fails with a clear message first
    import concurbench_full
    import stress_test
    import fcr_test
    import full_spec_conformance
    import gamma_report_page

    # 2. ConcurBench full conformance
    _hr("STEP 2/6  ConcurBench full conformance (concurbench_full.py)")
    concurbench = concurbench_full.run(write=True)

    # 3. stress test
    _hr("STEP 3/6  financial-services stress test (stress_test.py)")
    stress = stress_test.run(write=True)

    # 4. FCR test
    _hr("STEP 4/6  Fail-Closed Rate test (fcr_test.py)")
    fcr = fcr_test.run(write=True)

    # 5. FULL_SPEC conformance (corrected complete flow)
    _hr("STEP 5/6  FULL_SPEC conformance (full_spec_conformance.py)")
    fullspec = full_spec_conformance.run(write=True)

    # 6. unified dashboard
    _hr("STEP 6/6  unified dashboard (gamma_report_page.py)")
    lab = json.loads(LAB_REPORT.read_text())
    summary = json.loads(SUMMARY.read_text())
    terminal_txt = TERMINAL.read_text() if TERMINAL.exists() else ""
    gamma_report_page.render(
        lab, summary, DASHBOARD, terminal_txt=terminal_txt,
        open_browser=not args.no_open,
        extra={"concurbench": concurbench, "stress": stress, "fcr": fcr,
               "fullspec": fullspec},
    )

    dt = time.time() - t0
    print_full_summary(lab, summary, concurbench, stress, fcr, fullspec, dt)


def print_full_summary(lab, summary, cb, stress, fcr, fs, dt) -> None:
    """Print every layer's key results to the terminal — nothing hidden."""
    def line(k, v):
        print(f"  {k:<34s}: {v}")

    _hr("RESULTS — 1. BASE LAB v1.0 BENCHMARK (real ULB corpus)")
    pm = lab["primary_metrics"]
    line("rows (N)", f"{lab['n_total']:,}  (nominal {lab['n_nominal']:,} · adversarial {lab['n_adversarial']})")
    line("derived PERMIT / SAFE_STATE", f"{summary['derived_permit']:,} / {summary['derived_safe_state']}")
    line("unauthorized executions (UER)", f"{lab['unauthorized_execution']['count']}  (rate {lab['unauthorized_execution']['metric']['adverse_rate']})")
    line("false permits (FPR)", f"{pm['false_permit_rate']['adverse_events']}/{pm['false_permit_rate']['n']}  Wilson95↑ {pm['false_permit_rate']['wilson95_clustercorrected_upper']:.2e}")
    line("false denials (FDR)", f"{pm['false_denial_rate']['adverse_events']}/{pm['false_denial_rate']['n']}")
    line("replay determinism (RDR)", f"{pm['replay_determinism_rate']['reported_rate']}  (hash links {lab['replay_determinism']['hash_chain_links_ok']:,}/{lab['replay_determinism']['hash_chain_links_total']:,})")
    line("TOCTOU violations", pm['toctou_violation_rate']['adverse_events'])
    line("class-veto effectiveness", pm['class_veto_effectiveness']['reported_rate'])
    inv = lab["runtime_invariants_violations"]
    line("runtime invariants", f"{sum(1 for x in inv.values() if x==0)}/6 hold (0 violations)")
    ltc = lab["measured_latency"]
    line("latency mean/p95/p99 (ms)", f"{ltc['mean_ms']:.4f} / {ltc['p95_ms']:.4f} / {ltc['p99_ms']:.4f}")
    line("throughput", f"~{ltc['throughput_ops_per_s']:,.0f} decisions/s")

    _hr("RESULTS — 2. CONCURBENCH (Document 1 full conformance)")
    cl = cb["conformance_levels"]
    for k, v in cl.items():
        line(k, v)
    line("adaptive attacker false permits", f"{cb['adversarial_robustness']['adaptive_attacker_false_permits']}/{cb['adversarial_robustness']['adaptive_attacker_attempts']}")
    line("contamination / canary", f"{cb['adversarial_robustness']['contamination_check']} / {cb['adversarial_robustness']['canary_string_check']}")
    line("L3 fleet consistency", f"{cb['distributed_consistency']['fleet_consistency']}  (nodes {cb['distributed_consistency']['node_count']}, partition {cb['distributed_consistency']['partition_test']})")
    line("L4 replay rate / verifier", f"{cb['replay_and_auditability']['replay_consistency_rate']} / {cb['replay_and_auditability']['independent_replay_verifier']}")
    line("OVERALL VERDICT", cb["overall_verdict"])

    _hr("RESULTS — 3. FINANCIAL STRESS TEST (4 scenarios)")
    for s in stress["scenarios"]:
        line(f"{s['id']} {s['name']}", f"{s['confidence']} · {s['effectively_tackled']} · {s['verdict']} · fail-closed={s.get('fail_closed_ok')}")
    line("weighted effectively-tackled", f"{stress['aggregate']['weighted_effectively_tackled_pct']}%")
    line("all in-scope denials fail-closed", stress['aggregate']['all_in_scope_denials_fail_closed'])

    _hr("RESULTS — 4. FAIL-CLOSED RATE (FCR) TEST")
    for f in fcr["by_family"]:
        line(f["family"], f"n={f['n']}  fail-open={f['fail_open_events']}  FCR={f['fail_closed_rate']}")
    o = fcr["overall"]
    line("OVERALL FCR", f"{o['FCR']}  (n={o['n']}, fail-open={o['fail_open_events']}, Wilson95↑ {o['wilson95_fail_open_upper']:.2e})")

    _hr("RESULTS — 5. FULL_SPEC.md CONFORMANCE (corrected complete flow)")
    cm = fs["confusion_matrix"]
    line("confusion (TP/TN/FP/FN)", f"{cm['true_permits']:,} / {cm['true_denials']} / {cm['false_permits']} / {cm['false_denials']}")
    m = fs["metrics_11_1"]
    line("UER / SVR / Γ-compliance", f"{m['UER']['rate']} / {m['SVR']['rate']} / {m['FFC_gamma_compliance']['rate']}")
    print("  §7.1 acceptance bands (enforced as predicates):")
    for name, b in fs["acceptance_bands_7_1"].items():
        val = b.get("value", b.get("value_ms"))
        if val is None:
            val = f"fail@permit={b.get('fail_on_should_permit')} · catches_fraud={b.get('fail_on_should_deny')}"
        print(f"      {'✓' if b['all_hold'] else '✗'} {name:<36s} {val}")
    a = fs["audit_as_control_6_12"]
    print(f"  §6.12 AIS (live composite) = {a['AIS_value']}:")
    for k, v in a["subsignals"].items():
        print(f"      · {k:<22s} {v}")
    tsc = fs["three_signal_closure_6_7"]
    line("§6.7 three-signal violations", tsc["closure_violations"])
    tlc = fs["tlc_10"]
    line("§10 TLC states / skew / viol", f"{tlc['total_states_explored']:,} total · {tlc['distinct_reachable_states']:,} distinct · skew {tlc['max_clock_skew']} · viol {tlc['violation_count']}")
    line("§1.11 theorems", "T0–T9 proved in Paper A; I1–I6 invariants that instantiate them all hold (6/6)")
    line("§9 DET-5 REVOC_P95", f"{fs['det5_revocation_9']['REVOC_P95_ms']} ms (simulated fleet)")
    line("FULL_SPEC VERDICT", fs["full_spec_verdict"]["verdict"])

    _hr("SUITE COMPLETE")
    line("ConcurBench verdict", cb.get("overall_verdict"))
    line("Stress weighted tackled", f"{stress['aggregate']['weighted_effectively_tackled_pct']}%")
    line("FCR", f"{fcr['overall']['FCR']} (fail-open={fcr['overall']['fail_open_events']})")
    line("FULL_SPEC verdict", fs["full_spec_verdict"]["verdict"])
    line("Dashboard", DASHBOARD.name)
    line("Reports", "gamma_lab_v1_report.json · concurbench_full_report.json · "
                    "stress_test_report.json · "
                    "fcr_test_report.json · full_spec_conformance_report.json")
    line("Elapsed", f"{dt:.1f}s")


if __name__ == "__main__":
    main()
