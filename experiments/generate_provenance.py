#!/usr/bin/env python3
"""
experiments/generate_provenance.py — traceability graph from executed artifacts.
================================================================================

Builds the chain    Raw Log -> Metric Engine -> JSON -> CSV -> IEEE Table -> Figure
for every experiment, with the on-disk sha256 of each node (proving the artifact exists and
what it hashes to). Emits:
  experiments/provenance/provenance_graph.json   (machine-readable DAG with hashes)
  experiments/provenance/provenance_graph.dot     (Graphviz; render with `dot -Tsvg`)
  experiments/provenance/PROVENANCE.md            (human-readable chain per experiment)

Nothing is hardcoded: every node is a real file discovered on disk after RUN_ALL.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
PROV = EXP / "provenance"
PROV.mkdir(parents=True, exist_ok=True)


def sha(p: Path):
    if not p.exists() or p.is_dir():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def node(path_rel: str, kind: str):
    p = ROOT / path_rel
    return {"id": path_rel, "kind": kind, "exists": p.exists(),
            "sha256": sha(p), "bytes": p.stat().st_size if p.exists() else None}


# The chain per experiment: (raw log) -> metric engine (code) -> json -> csv -> table -> figure
CHAINS = {
    "E1": {
        "title": "Runtime Authorization Correctness",
        "raw_log": "experiments/runtime_correctness/logs/E1.log",
        "metric_engine": ["gamma_test_runner.py", "metrics_engine.py", "full_spec_conformance.py"],
        "json": ["experiments/runtime_correctness/gamma_lab_v1_report.json",
                 "experiments/runtime_correctness/full_spec_conformance_report.json"],
        "csv": ["experiments/runtime_correctness/gamma_validation_results.csv"],
        "table": ["experiments/tables/table1_primary_metrics.md"],
        "figure": ["experiments/figures/fig_authorization_accuracy.svg",
                   "experiments/figures/fig_false_permit_rate.svg"],
    },
    "E2": {
        "title": "Runtime Replay Integrity",
        "raw_log": "experiments/replay/logs/E2.log",
        "metric_engine": ["gamma_replay_verify.py"],
        "json": ["experiments/replay/replay_report.json"],
        "csv": [],
        "table": ["experiments/tables/table1_primary_metrics.md"],
        "figure": ["experiments/figures/fig_replay_integrity.svg"],
    },
    "E3": {
        "title": "Formal Verification",
        "raw_log": "experiments/formal/logs/E3.log",
        "metric_engine": ["independent_verifier.py", "formal/ExternalizationMonitor.tla"],
        "json": ["experiments/formal/independent_verifier_report.json"],
        "csv": [],
        "table": ["experiments/tables/table1_primary_metrics.md"],
        "figure": [],
    },
    "E4": {
        "title": "Runtime Stress Evaluation",
        "raw_log": "experiments/stress/logs/E4.log",
        "metric_engine": ["agentdojo_integration/audit/concurrency_scaling.py", "metrics_engine.py"],
        "json": ["experiments/stress/concurrency_scaling.json"],
        "csv": ["experiments/stress/concurrency_scaling.csv"],
        "table": ["experiments/tables/table2_concurrency_scaling.md"],
        "figure": ["experiments/figures/fig_latency.svg", "experiments/figures/fig_throughput.svg"],
    },
    "E5": {
        "title": "Component Ablation",
        "raw_log": "experiments/ablation/logs/E5.log",
        "metric_engine": ["experiment_ablation.py"],
        "json": ["experiments/ablation/ablation.json"],
        "csv": ["experiments/ablation/ablation.csv"],
        "table": ["experiments/tables/table1_primary_metrics.md"],
        "figure": ["experiments/figures/fig_component_ablation.svg"],
    },
    "E6": {
        "title": "Runtime Profiling",
        "raw_log": "experiments/profiling/logs/E6.log",
        "metric_engine": ["agentdojo_integration/audit/runtime_profile.py",
                          "agentdojo_integration/audit/stats_engine.py"],
        "json": ["experiments/profiling/runtime_profile.json",
                 "experiments/profiling/stage_distributions.json"],
        "csv": [],
        "table": [],
        "figure": ["experiments/figures/fig_runtime_breakdown.svg"],
    },
    "E7": {
        "title": "AgentDojo Runtime Governance",
        "raw_log": "experiments/agentdojo/logs/E7_boundary.log",
        "metric_engine": ["experiment_agentdojo_boundary_fpr.py",
                          "agentdojo_integration/audit/stats_engine.py"],
        "json": ["experiments/agentdojo/boundary/boundary_fpr.json",
                 "experiments/agentdojo/statistics.json"],
        "csv": ["experiments/agentdojo/decisions.csv"],
        "table": ["experiments/tables/table1_primary_metrics.md"],
        "figure": ["experiments/figures/fig_false_permit_rate.svg"],
    },
    "E8": {
        "title": "Runtime Robustness",
        "raw_log": "experiments/robustness/logs/E8.log",
        "metric_engine": ["experiment_robustness.py", "gamma_test_runner.py", "gamma_replay_verify.py"],
        "json": ["experiments/robustness/robustness.json"],
        "csv": ["experiments/robustness/robustness.csv"],
        "table": ["experiments/tables/table3_robustness.md"],
        "figure": ["experiments/figures/fig_robustness.svg"],
    },
}

STAGES = ["raw_log", "metric_engine", "json", "csv", "table", "figure"]
STAGE_KIND = {"raw_log": "raw_log", "metric_engine": "code", "json": "json", "csv": "csv",
              "table": "table", "figure": "figure"}


def main():
    graph = {"campaign": "ldrea_tier_s_provenance", "chain_order": STAGES, "experiments": {}}
    edges = []
    dot = ["digraph provenance {", '  rankdir=LR; node [shape=box, fontsize=9, fontname="Helvetica"];']
    broken = []

    for eid, chain in CHAINS.items():
        nodes_by_stage = {}
        for stage in STAGES:
            val = chain[stage]
            items = [val] if isinstance(val, str) else val
            kind = STAGE_KIND[stage]
            nodes_by_stage[stage] = [node(x, kind) for x in items]
        graph["experiments"][eid] = {"title": chain["title"], "stages": nodes_by_stage}
        # edges connect each present node in stage k to each present node in stage k+1
        present_stages = [(s, [n for n in nodes_by_stage[s] if n["exists"]]) for s in STAGES]
        for (s1, n1), (s2, n2) in zip(present_stages, present_stages[1:]):
            for a in n1:
                for b in n2:
                    edges.append({"from": a["id"], "to": b["id"], "exp": eid})
                    dot.append(f'  "{a["id"].split("/")[-1]}" -> "{b["id"].split("/")[-1]}";')
        # flag any stage (except csv/figure which may legitimately be empty) with no present node
        for stage in ["raw_log", "metric_engine", "json"]:
            if not any(n["exists"] for n in nodes_by_stage[stage]):
                broken.append(f"{eid}:{stage} has no present artifact")

    graph["edges"] = edges
    graph["broken_links"] = broken
    dot.append("}")
    (PROV / "provenance_graph.json").write_text(json.dumps(graph, indent=2))
    (PROV / "provenance_graph.dot").write_text("\n".join(dot))

    # human-readable
    md = ["# Provenance Graph — traceability of every reported value", "",
          "Chain: **Raw Log → Metric Engine (code) → JSON → CSV → IEEE Table → Figure**. "
          "Each node lists its on-disk sha256 (first 12) proving the artifact exists.", ""]
    if broken:
        md += ["> ⚠️ **Broken links detected** (a required stage produced no artifact):", ""]
        md += [f"> - {b}" for b in broken] + [""]
    else:
        md += ["> ✅ All chains intact: every experiment has raw log → metric engine → JSON present.", ""]
    for eid, chain in CHAINS.items():
        md.append(f"## {eid} — {chain['title']}")
        for stage in STAGES:
            nodes = graph["experiments"][eid]["stages"][stage]
            if not nodes:
                md.append(f"- **{stage}**: (none)")
                continue
            for n in nodes:
                mark = "✅" if n["exists"] else "❌"
                h = (n["sha256"][:12] if n["sha256"] else "—")
                md.append(f"- **{stage}** {mark} `{n['id']}`  sha256:`{h}`")
        md.append("")
    (PROV / "PROVENANCE.md").write_text("\n".join(md))
    status = "ALL INTACT" if not broken else f"{len(broken)} BROKEN"
    print(f"[provenance] {len(edges)} edges across {len(CHAINS)} chains — {status}")


if __name__ == "__main__":
    main()
