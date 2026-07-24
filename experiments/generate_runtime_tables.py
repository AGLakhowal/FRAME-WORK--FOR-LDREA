#!/usr/bin/env python3
"""Publication tables for the runtime evidence stack (Objective 8).

Every row is read from a production_evidence/*.json artifact at generation time — never hardcoded.
Emits Markdown + LaTeX for each table into paper_tables/ and a combined runtime_tables.json.

    python experiments/generate_runtime_tables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PE = ROOT / "production_evidence"
OUT = ROOT / "paper_tables"
JS = ROOT / "runtime_tables.json"


def load(name):
    p = PE / name
    return json.loads(p.read_text()) if p.exists() else None


def dig(d, ptr, default=None):
    cur = d
    for k in ptr.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def fmt(v):
    if v is None:
        return "MISSING"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


# (metric, artifact, pointer, units, sample-size pointer or literal, paper section)
TABLES = {
    "runtime_revocation": ("Runtime Revocation", [
        ("Permits revoked", "revocation_report_live.json", "permits_revoked", "count", "permits_revoked", "VI-A"),
        ("Acknowledgements received", "revocation_report_live.json", "acks_received", "count", "acks_expected", "VI-A"),
        ("Acknowledgement rate", "revocation_report_live.json", "acknowledgement_rate", "ratio", "acks_expected", "VI-A"),
        ("Compliance rate", "revocation_report_live.json", "compliance_rate", "ratio", "false_permit_probe_size", "VI-A"),
        ("Propagation p50", "revocation_report_live.json", "propagation_latency_ms.p50", "ms", "permits_revoked", "VI-A"),
        ("Propagation p95", "revocation_report_live.json", "propagation_latency_ms.p95", "ms", "permits_revoked", "VI-A"),
        ("Propagation p99", "revocation_report_live.json", "propagation_latency_ms.p99", "ms", "permits_revoked", "VI-A"),
        ("False permits after revocation", "revocation_report_live.json", "false_permits_after_revocation", "count", "false_permit_probe_size", "VI-A"),
        ("Revocations/sec", "revocation_report_live.json", "revocations_per_s", "1/s", "total_revocation_events", "VI-A"),
    ]),
    "runtime_watchdog": ("Runtime Watchdog", [
        ("Heartbeats", "watchdog_summary.json", "heartbeats", "count", "heartbeats", "VI-B"),
        ("Heartbeat latency mean", "watchdog_summary.json", "heartbeat_latency_ms.mean", "ms", "heartbeats", "VI-B"),
        ("Stall threshold", "watchdog_summary.json", "stall_threshold_ms", "ms", "1", "VI-B"),
        ("Injected stalls detected", "watchdog_summary.json", "stalls_detected_on_injected_worker", "count", "injected_stalls", "VI-B"),
        ("Detection rate", "watchdog_summary.json", "detection_rate", "ratio", "injected_stalls", "VI-B"),
        ("False triggers", "watchdog_summary.json", "false_triggers", "count", "heartbeats", "VI-B"),
        ("Recovery latency p95", "watchdog_summary.json", "recovery_latency_ms.p95", "ms", "injected_stalls", "VI-B"),
    ]),
    "runtime_fleet": ("Fleet Runtime", [
        ("Worker processes", "fleet_summary.json", "nodes", "count", "nodes", "VI-C"),
        ("Throughput", "fleet_summary.json", "throughput_decisions_per_s", "1/s", "requests", "VI-C"),
        ("Queue delay p95", "fleet_summary.json", "queue_delay_ms.p95", "ms", "requests", "VI-C"),
        ("Busy fraction mean", "fleet_summary.json", "utilization.busy_fraction_mean", "ratio", "nodes", "VI-C"),
        ("Busy fraction peak", "fleet_summary.json", "utilization.busy_fraction_peak", "ratio", "nodes", "VI-C"),
        ("Load imbalance (CV)", "fleet_summary.json", "utilization.load_imbalance_cv", "ratio", "nodes", "VI-C"),
    ]),
    "runtime_risk_detection": ("Runtime Risk Detection (attack injection)", [
        ("Attack families", "runtime_risk_detection_report.json", "families", "count", "families", "VII-A"),
        ("Total attacks", "runtime_risk_detection_report.json", "total_attacks", "count", "total_attacks", "VII-A"),
        ("Attacks detected", "runtime_risk_detection_report.json", "attacks_detected", "count", "total_attacks", "VII-A"),
        ("Detection rate", "runtime_risk_detection_report.json", "detection_rate", "ratio", "total_attacks", "VII-A"),
        ("Detection precision", "runtime_risk_detection_report.json", "detection_precision", "ratio", "total_attacks", "VII-A"),
        ("Suite has power (control)", "runtime_risk_detection_report.json", "suite_has_power", "bool", "1", "VII-A"),
        ("Response latency p99", "runtime_risk_detection_report.json", "response_latency_ms.p99", "ms", "total_attacks", "VII-A"),
    ]),
    "runtime_clock": ("Runtime Clock Consistency (NOT PTP)", [
        ("Timestamp resolution", "runtime_clock_consistency_report.json", "timestamp_resolution_ns", "ns", "samples", "VI-D"),
        ("Sampling jitter p95", "runtime_clock_consistency_report.json", "sampling_jitter_ns.p95", "ns", "samples", "VI-D"),
        ("Sampling jitter p99", "runtime_clock_consistency_report.json", "sampling_jitter_ns.p99", "ns", "samples", "VI-D"),
        ("Monotonic consistency", "runtime_clock_consistency_report.json", "monotonic_consistency", "bool", "samples", "VI-D"),
        ("Wall-vs-monotonic drift", "runtime_clock_consistency_report.json", "wall_vs_monotonic_drift_ppm", "ppm", "1", "VI-D"),
    ]),
    "runtime_detection_synth": ("Blind Runtime Detection (Synthetic)", [
        ("Precision", "runtime_detection_report_synthetic.json", "precision", "ratio", "stream.evaluated", "VII-B"),
        ("Recall", "runtime_detection_report_synthetic.json", "recall_detection_rate", "ratio", "stream.evaluated", "VII-B"),
        ("F1", "runtime_detection_report_synthetic.json", "f1", "ratio", "stream.evaluated", "VII-B"),
        ("MCC", "runtime_detection_report_synthetic.json", "matthews_corrcoef", "ratio", "stream.evaluated", "VII-B"),
        ("AUROC", "runtime_detection_report_synthetic.json", "auroc", "ratio", "stream.evaluated", "VII-B"),
        ("AUPRC", "runtime_detection_report_synthetic.json", "auprc", "ratio", "stream.evaluated", "VII-B"),
        ("Balanced accuracy", "runtime_detection_report_synthetic.json", "balanced_accuracy", "ratio", "stream.evaluated", "VII-B"),
    ]),
    "execution_timeline": ("Execution Timeline", [
        ("Executions", "execution_timeline_report.json", "executions", "count", "executions", "VI-E"),
        ("Permits issued", "execution_timeline_report.json", "permits_issued", "count", "executions", "VI-E"),
        ("End-to-end mean", "execution_timeline_report.json", "end_to_end_ms.mean", "ms", "executions", "VI-E"),
        ("End-to-end p95", "execution_timeline_report.json", "end_to_end_ms.p95", "ms", "executions", "VI-E"),
        ("Execution mean", "execution_timeline_report.json", "execution_ms.mean", "ms", "executions", "VI-E"),
    ]),
}


def _ci(art, ptr):
    """Attach a Wilson CI where the artifact already carries one for this metric; else n/a."""
    w = dig(art, ptr.rsplit(".", 1)[0] + ".wilson95") if "." in ptr else None
    if isinstance(w, dict) and "low" in w and "high" in w:
        return f"[{w['low']:.4f}, {w['high']:.4f}]"
    return "n/a"


def _dataset_comparison_table():
    """Table — Dataset comparison. Read from the E12 summary; one row per discovered dataset."""
    summ_path = PE / "datasets" / "dataset_eval_summary.json"
    if not summ_path.exists():
        return None
    summ = json.loads(summ_path.read_text())
    md = ["# Table — Dataset Comparison (Measured Runtime, blind)", "",
          "| Dataset | Domain | Eval rows | Prevalence | Precision | Recall | F1 | MCC | AUROC | Evidence |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    tex = ["\\begin{tabular}{llrrrrrrrl}", "\\hline",
           "Dataset & Domain & Rows & Prev & P & R & F1 & MCC & AUROC & Level \\\\", "\\hline"]
    jrows = []
    for s in summ.get("summaries", []):
        prev = f"{(s.get('prevalence') or 0)*100:.2f}\\%"
        row = [s["dataset"], s.get("domain", ""), f"{s.get('evaluated_rows', 0):,}", prev,
               fmt(s.get("precision")), fmt(s.get("recall")), fmt(s.get("f1")),
               fmt(s.get("mcc")), fmt(s.get("auroc")), s.get("evidence_level", "?")]
        md.append("| " + " | ".join(str(x) for x in row) + " |")
        tex.append(" & ".join(str(x) for x in row) + " \\\\")
        jrows.append({"dataset": s["dataset"], "precision": s.get("precision"),
                      "recall": s.get("recall"), "auroc": s.get("auroc"),
                      "evidence_source": f"production_evidence/datasets/{s['dataset'].lower().replace('-','_')}_eval.json",
                      "resolved": s.get("auroc") is not None})
    tex += ["\\hline", "\\end{tabular}"]
    (OUT / "table_dataset_comparison.md").write_text("\n".join(md) + "\n")
    (OUT / "table_dataset_comparison.tex").write_text("\n".join(tex) + "\n")
    return {"title": "Dataset Comparison", "rows": jrows}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    cache, combined, missing = {}, {}, 0
    dc = _dataset_comparison_table()
    if dc:
        combined["dataset_comparison"] = dc
    for key, (title, rows) in TABLES.items():
        md = [f"# Table — {title}", "",
              "| Metric | Value | Units | 95% CI | Sample size | Evidence source | Paper § |",
              "|---|---|---|---|---|---|---|"]
        tex = ["\\begin{tabular}{lllllll}", "\\hline",
               "Metric & Value & Units & 95\\% CI & n & Source & Sec \\\\", "\\hline"]
        jrows = []
        for metric, art_name, ptr, units, n_ptr, sec in rows:
            if art_name not in cache:
                cache[art_name] = load(art_name)
            art = cache[art_name]
            val = dig(art, ptr) if art else None
            if val is None:
                missing += 1
            n = dig(art, n_ptr) if (art and not str(n_ptr).isdigit()) else n_ptr
            ci = _ci(art, ptr) if art else "n/a"
            level = dig(art, "evidence_level") if art else "Not Executed"
            src = f"production_evidence/{art_name}::{ptr}"
            md.append(f"| {metric} | {fmt(val)} | {units} | {ci} | {fmt(n)} | `{src}` | {sec} |")
            tex.append(f"{metric} & {fmt(val)} & {units} & {ci} & {fmt(n)} & \\texttt{{{art_name}}} & {sec} \\\\")
            jrows.append({"metric": metric, "value": val, "units": units, "ci": ci,
                          "sample_size": n, "evidence_source": src, "evidence_level": level,
                          "paper_section": sec, "resolved": val is not None})
        tex += ["\\hline", "\\end{tabular}"]
        (OUT / f"table_{key}.md").write_text("\n".join(md) + "\n")
        (OUT / f"table_{key}.tex").write_text("\n".join(tex) + "\n")
        combined[key] = {"title": title, "rows": jrows}

    JS.write_text(json.dumps({"tables": combined, "total_rows": sum(len(t["rows"]) for t in combined.values()),
                              "missing": missing}, indent=2) + "\n")
    total = sum(len(t["rows"]) for t in combined.values())
    print(f"[runtime-tables] {len(TABLES)} tables, {total} rows, {missing} unresolved")
    print(f"[runtime-tables] wrote paper_tables/table_runtime_*.{{md,tex}} and {JS.name}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
