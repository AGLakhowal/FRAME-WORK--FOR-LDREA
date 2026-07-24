#!/usr/bin/env python3
"""Measurement Provenance Matrix — every headline number, traced to its source.

Each row is EXTRACTED from an artifact on disk at generation time. Nothing is transcribed by hand,
so the matrix cannot drift from the artifacts. A value that cannot be read is emitted as MISSING
rather than omitted or guessed.

    python experiments/generate_provenance_matrix.py

Emits: MEASUREMENT_PROVENANCE_MATRIX.md, measurement_provenance_matrix.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "MEASUREMENT_PROVENANCE_MATRIX.md"
JS = ROOT / "measurement_provenance_matrix.json"

MEASURED = "Measured Runtime"
DERIVED = "Derived From Measured"
SIMULATED = "Repository Simulation"
BENCH = "Benchmark Evidence"
NOTRUN = "Not Executed"

# metric, artifact, json pointer (dotted; [i] for list index), script, figure, table, card, level
ROWS = [
    ("Decision agreement (status)", "experiments/runtime_correctness/gamma_lab_v1_report.json",
     "decision_agreement.match_status_rate", "gamma_test_runner.py",
     "fig_authorization_accuracy.svg", "table1_primary_metrics.md", "Authorization", BENCH),
    ("False Permit Rate", "concurbench_full_report.json",
     "authorization_correctness.FPR", "concurbench_full.py",
     "fig_false_permit_rate.svg", "table1_primary_metrics.md", "Authorization", BENCH),
    ("FPR Wilson95 upper (cluster-corrected)", "concurbench_full_report.json",
     "authorization_correctness.FPR_metric.wilson95_clustercorrected_upper", "concurbench_full.py",
     "fig_false_permit_rate.svg", "table1_primary_metrics.md", "Authorization", BENCH),
    ("FPR should-deny denominator (n)", "concurbench_full_report.json",
     "authorization_correctness.FPR_metric.n", "concurbench_full.py", "-",
     "table1_primary_metrics.md", "Authorization", BENCH),
    ("Replay attempts", "concurbench_full_report.json",
     "replay_and_auditability.replay_attempts", "concurbench_full.py",
     "fig_replay_integrity.svg", "table_replay.md", "Replay", BENCH),
    ("Replay consistency rate", "concurbench_full_report.json",
     "replay_and_auditability.replay_consistency_rate", "concurbench_full.py",
     "fig_replay_integrity.svg", "table_replay.md", "Replay", BENCH),
    ("ERTuple count", "concurbench_full_report.json",
     "replay_and_auditability.ertuple_count", "concurbench_full.py", "-", "table_evidence.md",
     "Evidence", DERIVED),
    ("Ledger root hash", "concurbench_full_report.json",
     "replay_and_auditability.final_ledger_root_hash", "concurbench_full.py", "-",
     "table_evidence.md", "Evidence", DERIVED),
    ("Revocation latency p95 (fleet)", "concurbench_full_report.json",
     "distributed_consistency.revocation_latency_p95_ms", "concurbench_full.py", "-",
     "table_fleet.md", "Fleet", SIMULATED),
    ("Clock skew bound", "concurbench_full_report.json",
     "distributed_consistency.clock_skew_bound_ms", "concurbench_full.py", "-", "table_fleet.md",
     "Fleet", SIMULATED),
    ("Quorum rule", "concurbench_full_report.json",
     "distributed_consistency.quorum_rule", "concurbench_full.py", "-", "table_fleet.md",
     "Fleet", SIMULATED),
    ("Predicate coverage rate", "experiments/predicate_coverage/predicate_coverage.json",
     "predicate_coverage.coverage_rate", "experiment_predicate_coverage.py",
     "fig_predicate_coverage.svg", "table_predicates.md", "Predicates", BENCH),
    ("Single-deficit denial rate", "experiments/predicate_coverage/predicate_coverage.json",
     "single_deficit_isolation.denial_rate", "experiment_predicate_coverage.py",
     "fig_predicate_coverage.svg", "table_predicates.md", "Predicates", BENCH),
    ("Engine latency mean (ms)", "experiments/runtime_correctness/gamma_lab_v1_report.json",
     "measured_latency.mean_ms", "gamma_test_runner.py", "fig_latency.svg", "table_latency.md",
     "Latency", MEASURED),
    ("Engine latency p99 (ms)", "experiments/runtime_correctness/gamma_lab_v1_report.json",
     "measured_latency.p99_ms", "gamma_test_runner.py", "fig_latency.svg", "table_latency.md",
     "Latency", MEASURED),
    ("Full pipeline (ms/row, measured)", "experiments/profiling/runtime_profile.json",
     "full_pipeline_ms_per_row_measured", "experiments/generate_statistics.py", "fig_latency.svg",
     "table_latency.md", "Latency", MEASURED),
    ("Replay share of end-to-end (%)", "experiments/profiling/runtime_profile.json",
     "replay.pct_of_end_to_end", "experiments/generate_statistics.py", "fig_runtime_breakdown.svg",
     "table_latency.md", "Latency", MEASURED),
    ("Throughput @1 thread", "experiments/stress/concurrency_scaling.json",
     "levels[0].throughput_decisions_per_s", "concurbench_full.py", "fig_throughput.svg",
     "table_throughput.md", "Throughput", MEASURED),
    ("Throughput @64 threads", "experiments/stress/concurrency_scaling.json",
     "levels[6].throughput_decisions_per_s", "concurbench_full.py", "fig_throughput.svg",
     "table_throughput.md", "Throughput", MEASURED),
    ("Total false permits (scaling)", "experiments/stress/concurrency_scaling.json",
     "total_false_permits", "concurbench_full.py", "-", "table_throughput.md",
     "Throughput", MEASURED),
    ("Stress scenarios fail-closed", "stress_test_report.json",
     "aggregate.all_in_scope_denials_fail_closed", "stress_test.py", "-", "table_stress.md",
     "Stress", BENCH),
    ("Stress latency p99 (all)", "stress_latency_report.json",
     "aggregate.latency.p99_ms", "experiments/profile_stress_scenarios.py", "-",
     "table_stress.md", "Stress", MEASURED),
    ("Label-leaking engine inputs", "label_leakage_audit.json",
     "verdict.n_leaking_inputs", "experiments/audit_label_leakage.py", "-",
     "table_threats.md", "Threats", BENCH),
    ("Blind detection status", "runtime_detection_report.json",
     "status", "experiments/experiment_runtime_detection.py", "-", "table_runtime_detection.md",
     "Runtime Detection", NOTRUN),
    # ---- E12 production evidence layer -------------------------------------------------
    ("Permits issued", "production_evidence/production_evidence_summary.json",
     "counts.permits", "experiments/production_evidence_layer.py", "-", "table_tokens.md",
     "Tokens", DERIVED),
    ("Ed25519 signatures created", "production_evidence/signature_verification_report.json",
     "signatures_created", "experiments/production_evidence_layer.py", "-", "table_tokens.md",
     "Signatures", MEASURED),
    ("Signature verification success rate",
     "production_evidence/signature_verification_report.json", "verification_success_rate",
     "experiments/production_evidence_layer.py", "-", "table_tokens.md", "Signatures", MEASURED),
    ("Signature verify latency mean (ms)",
     "production_evidence/signature_verification_report.json", "verification_latency_ms.mean",
     "experiments/production_evidence_layer.py", "-", "table_latency.md", "Signatures", MEASURED),
    ("Negative signature tests rejected",
     "production_evidence/signature_verification_report.json", "all_negative_tests_rejected",
     "experiments/production_evidence_layer.py", "-", "table_tokens.md", "Signatures", MEASURED),
    ("Negative suite positive control",
     "production_evidence/signature_verification_report.json", "negative_suite_has_power",
     "experiments/production_evidence_layer.py", "-", "table_tokens.md", "Signatures", MEASURED),
    ("Single-use enforced", "production_evidence/permit_lifecycle_report.json",
     "single_use_verified", "experiments/production_evidence_layer.py", "-", "table_tokens.md",
     "Tokens", MEASURED),
    ("Double-use rejected", "production_evidence/permit_lifecycle_report.json",
     "double_use_rejected", "experiments/production_evidence_layer.py", "-", "table_tokens.md",
     "Tokens", MEASURED),
    ("False permits after revocation", "production_evidence/revocation_report.json",
     "false_permits_after_revocation", "experiments/production_evidence_layer.py", "-",
     "table_revocation.md", "Revocation", MEASURED),
    ("Revocation propagation p99 (ms)", "production_evidence/revocation_report.json",
     "propagation_latency_ms.p99", "experiments/production_evidence_layer.py", "-",
     "table_revocation.md", "Revocation", SIMULATED),
    ("TOCTOU window p95 (ms)", "production_evidence/runtime_timestamps_report.json",
     "toctou_window_ms.p95", "experiments/production_evidence_layer.py", "-", "table_latency.md",
     "Timestamps", MEASURED),
    ("Decision latency mean (ms)", "production_evidence/runtime_timestamps_report.json",
     "decision_latency_ms.mean", "experiments/production_evidence_layer.py", "-",
     "table_latency.md", "Timestamps", MEASURED),
    ("Ledger blocks", "production_evidence/ledger_summary.json", "blocks",
     "experiments/production_evidence_layer.py", "-", "table_evidence.md", "Ledger", DERIVED),
    ("Ledger hash continuity", "production_evidence/ledger_summary.json", "hash_continuity",
     "experiments/production_evidence_layer.py", "-", "table_evidence.md", "Ledger", DERIVED),
    ("Ledger tamper detection", "production_evidence/ledger_summary.json",
     "tamper_detection_verified", "experiments/production_evidence_layer.py", "-",
     "table_evidence.md", "Ledger", MEASURED),
    ("ISB pass rate", "production_evidence/ctr_report.json", "isb_pass_rate",
     "experiments/production_evidence_layer.py", "-", "table_evidence.md", "CTR", DERIVED),
    ("CTR invalid schema rejected", "production_evidence/ctr_report.json",
     "invalid_schema_rejected", "experiments/production_evidence_layer.py", "-",
     "table_evidence.md", "CTR", MEASURED),
    ("Watchdog timeouts", "production_evidence/watchdog_report.json", "timeouts",
     "experiments/production_evidence_layer.py", "-", "table_watchdog.md", "Watchdog", SIMULATED),
    ("Watchdog heartbeat mean (ms)", "production_evidence/watchdog_report.json",
     "heartbeat_interval_ms.mean", "experiments/production_evidence_layer.py", "-",
     "table_watchdog.md", "Watchdog", MEASURED),
    ("Clock skew max |offset| (ms)", "production_evidence/clock_skew_report.json",
     "max_abs_offset_ms", "experiments/production_evidence_layer.py", "-", "table_fleet.md",
     "Clock", SIMULATED),
]

SENTINEL = object()


def dig(obj, pointer):
    cur = obj
    for part in pointer.split("."):
        if part.endswith("]") and "[" in part:
            name, idx = part[:-1].split("[")
            if name:
                if not isinstance(cur, dict) or name not in cur:
                    return SENTINEL
                cur = cur[name]
            if not isinstance(cur, list) or int(idx) >= len(cur):
                return SENTINEL
            cur = cur[int(idx)]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return SENTINEL
            cur = cur[part]
    return cur


def fmt(v):
    if v is SENTINEL:
        return "**MISSING**"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, (int,)):
        return f"{v:,}"
    s = str(v)
    return s if len(s) <= 46 else s[:43] + "…"


def main() -> int:
    cache, rows, missing = {}, [], 0
    for metric, artifact, ptr, script, fig, tbl, card, level in ROWS:
        p = ROOT / artifact
        if artifact not in cache:
            try:
                cache[artifact] = json.loads(p.read_text()) if p.exists() else SENTINEL
            except Exception:
                cache[artifact] = SENTINEL
        doc = cache[artifact]
        val = SENTINEL if doc is SENTINEL else dig(doc, ptr)
        if val is SENTINEL:
            missing += 1
        rows.append({"metric": metric, "value": None if val is SENTINEL else val,
                     "value_rendered": fmt(val), "computed_from": artifact, "pointer": ptr,
                     "script": script, "figure": fig, "table": tbl, "dashboard_card": card,
                     "evidence_level": level, "resolved": val is not SENTINEL})

    by_level = {}
    for r in rows:
        by_level[r["evidence_level"]] = by_level.get(r["evidence_level"], 0) + 1

    JS.write_text(json.dumps({"rows": rows, "total": len(rows), "missing": missing,
                              "by_evidence_level": by_level}, indent=2) + "\n")

    out = ["# Measurement Provenance Matrix", "",
           "Every headline number in this repository, traced to the artifact it is read from.",
           "**This file is generated.** Each value is extracted from disk at generation time, so it",
           "cannot drift from the artifacts. A value that cannot be resolved is printed as",
           "`**MISSING**` rather than omitted.", "",
           f"Rows: **{len(rows)}** · unresolved: **{missing}**", "",
           "| Metric | Value | Computed From | Pointer | Script | Figure | Table | Card | Evidence Level |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['metric']} | `{r['value_rendered']}` | `{r['computed_from']}` | "
                   f"`{r['pointer']}` | `{r['script']}` | {r['figure']} | {r['table']} | "
                   f"{r['dashboard_card']} | {r['evidence_level']} |")
    out += ["", "## Evidence-level census", "",
            "| Evidence level | Rows |", "|---|---|"]
    for k, v in sorted(by_level.items(), key=lambda x: -x[1]):
        out.append(f"| {k} | {v} |")
    out += ["", "**Production Evidence: 0 rows.** No value in this repository is production",
            "evidence. **External Validation: 0 rows.**", ""]
    MD.write_text("\n".join(out) + "\n")

    print(f"[provenance-matrix] {len(rows)} rows, {missing} unresolved")
    for k, v in sorted(by_level.items(), key=lambda x: -x[1]):
        print(f"[provenance-matrix]   {k:24} {v}")
    print(f"[provenance-matrix] wrote {MD.name}, {JS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
