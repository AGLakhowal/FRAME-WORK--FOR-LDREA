#!/usr/bin/env python3
"""
experiments/generate_tables.py — publication-ready IEEE tables from executed artifacts only.
============================================================================================

Every row carries: Metric · Value · 95% CI · Sample Size · Experiment · Reproduction Command.
All values are read from the experiment JSON produced by RUN_ALL_EXPERIMENTS.py — nothing is
hardcoded. Emits Markdown (experiments/tables/*.md), a machine-readable tables.json, and a
LaTeX booktabs version (experiments/tables/*.tex) for direct paper inclusion.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments"
TAB = EXP / "tables"
TAB.mkdir(parents=True, exist_ok=True)

REPRO = {
    "E1": "./.venv/bin/python gamma_test_runner.py --no-html --no-open",
    "E2": "./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl",
    "E3": "./.venv/bin/python independent_verifier.py",
    "E4": "./.venv/bin/python -c \"from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress',200000,[1,2,4,8,16,32,64])\"",
    "E5": "./.venv/bin/python experiment_ablation.py",
    "E6": "./.venv/bin/python -c \"from agentdojo_integration.audit import runtime_profile as r; r.run('experiments/profiling',5000)\"",
    "E7": "agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py",
    "E8": "./.venv/bin/python experiment_robustness.py",
}


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def ci_str(lo, hi, fmt="{:.3e}"):
    if lo is None or hi is None:
        return "—"
    return f"[{fmt.format(lo)}, {fmt.format(hi)}]"


def build_rows():
    """Return list of dict rows for the master metrics table."""
    rows = []

    lab = load(EXP / "runtime_correctness" / "gamma_lab_v1_report.json")
    fs = load(EXP / "runtime_correctness" / "full_spec_conformance_report.json")
    if lab:
        pm = lab["primary_metrics"]
        fpr = pm["false_permit_rate"]
        rows.append(dict(metric="False Permit Rate (ULB)", value=f"{fpr['adverse_events']}/{fpr['n']}",
                         ci=f"Wilson95↑ {fpr['wilson95_clustercorrected_upper']:.3e}", n=fpr["n"],
                         exp="E1", repro=REPRO["E1"]))
        fdr = pm["false_denial_rate"]
        rows.append(dict(metric="False Denial Rate (ULB)", value=f"{fdr['adverse_events']}/{fdr['n']}",
                         ci="—", n=fdr["n"], exp="E1", repro=REPRO["E1"]))
        rows.append(dict(metric="Unauthorized Executions (UER)",
                         value=f"{lab['unauthorized_execution']['count']}/{lab['n_total']}",
                         ci="—", n=lab["n_total"], exp="E1", repro=REPRO["E1"]))
        rdr = pm["replay_determinism_rate"]
        rows.append(dict(metric="Replay Determinism Rate", value=f"{rdr['reported_rate']}",
                         ci="—", n=lab["n_total"], exp="E1", repro=REPRO["E1"]))
        cv = pm["class_veto_effectiveness"]
        rows.append(dict(metric="Class-Veto Effectiveness", value=f"{cv['reported_rate']}",
                         ci="—", n=lab.get("n_adversarial"), exp="E1", repro=REPRO["E1"]))
        lt = lab["measured_latency"]
        rows.append(dict(metric="Decision latency mean (ms)", value=f"{lt['mean_ms']:.4f}",
                         ci=f"p95 {lt['p95_ms']:.4f} / p99 {lt['p99_ms']:.4f}", n=lab["n_total"],
                         exp="E1", repro=REPRO["E1"]))
    if fs:
        cm = fs["confusion_matrix"]
        tot = sum(cm[k] for k in ("true_permits", "true_denials", "false_permits", "false_denials"))
        acc = (cm["true_permits"] + cm["true_denials"]) / tot if tot else 0
        rows.append(dict(metric="Authorization Accuracy", value=f"{acc:.6f}",
                         ci=f"TP {cm['true_permits']}/TN {cm['true_denials']}/FP {cm['false_permits']}/FN {cm['false_denials']}",
                         n=tot, exp="E1", repro=REPRO["E1"]))

    rp = load(EXP / "replay" / "replay_report.json")
    if rp:
        rows.append(dict(metric="Replay hash-chain adjacency failures",
                         value=str(rp["hash_chain_adjacency_failures"]), ci="—",
                         n=rp["decision_records_verified"], exp="E2", repro=REPRO["E2"]))
        rows.append(dict(metric="Replay ledger-bind failures", value=str(rp["ledger_bind_failures"]),
                         ci="—", n=rp["decision_records_verified"], exp="E2", repro=REPRO["E2"]))

    iv = load(EXP / "formal" / "independent_verifier_report.json")
    if iv:
        rows.append(dict(metric="Formal state-space coverage",
                         value=f"{iv['total_states_enumerated']}/{iv['expected_states']}",
                         ci="complete" if iv["coverage_complete"] else "partial",
                         n=iv["expected_states"], exp="E3", repro=REPRO["E3"]))
        rows.append(dict(metric="Decision-equivalence field mismatches",
                         value=str(iv["total_field_mismatches"]), ci=f"verdict {iv['verdict']}",
                         n=iv["expected_states"], exp="E3", repro=REPRO["E3"]))

    cs = load(EXP / "stress" / "concurrency_scaling.json")
    if cs:
        one = next(L for L in cs["levels"] if L["n_threads"] == 1)
        top = cs["levels"][-1]
        rows.append(dict(metric=f"Throughput @1 / @{top['n_threads']} threads (dec/s)",
                         value=f"{one['throughput_decisions_per_s']:,.0f} / {top['throughput_decisions_per_s']:,.0f}",
                         ci=f"speedup {top['speedup_vs_1thread']:.3f}×", n=cs["workload"]["n_decisions"],
                         exp="E4", repro=REPRO["E4"]))
        rows.append(dict(metric="False permits/denials under load (all levels)",
                         value=f"{cs['total_false_permits']}/{cs['total_false_denials']}",
                         ci=f"all-correct {cs['all_authorization_correct']}",
                         n=cs["workload"]["n_decisions"] * len(cs["levels"]), exp="E4", repro=REPRO["E4"]))

    ab = load(EXP / "ablation" / "ablation.json")
    if ab:
        for c in ab["configs"]:
            w = c.get("leaked_permit_wilson95", {})
            rows.append(dict(metric=f"Leaked permits: {c['config']}",
                             value=f"{c['leaked_permits_vs_baseline']}/{c['workload_n']}",
                             ci=ci_str(w.get("low"), w.get("high"), "{:.4f}"),
                             n=c["workload_n"], exp="E5", repro=REPRO["E5"]))

    bf = load(EXP / "agentdojo" / "boundary" / "boundary_fpr.json")
    if bf:
        g = bf["soundness_foreign_targets"]
        rows.append(dict(metric="AgentDojo boundary FPR (foreign targets)",
                         value=f"{g['permitted']}/{g['n']}",
                         ci=f"Wilson95↑ {g['wilson95']['high']:.3e}", n=g["n"], exp="E7", repro=REPRO["E7"]))
    st = load(EXP / "agentdojo" / "statistics.json")
    if st:
        pr = st["permit_rate_wilson"]
        rows.append(dict(metric="AgentDojo permit rate (recorded episodes)",
                         value=f"{pr['p']:.3f}", ci=ci_str(pr["low"], pr["high"], "{:.3f}"),
                         n=pr["n"], exp="E7", repro=REPRO["E7"]))

    rob = load(ROOT / "fresh_evidence" / "robustness" / "robustness.json")
    if rob:
        a = rob["aggregate"]
        rows.append(dict(metric="Robustness: false permits across all faults",
                         value=f"{a['total_false_permits']}/{a['total_trials']}",
                         ci=f"safety holds {a['families_where_safety_holds']}/{a['n_families_evaluable']} families",
                         n=a["total_trials"], exp="E8", repro=REPRO["E8"]))
    return rows


def build_scaling_table():
    cs = load(EXP / "stress" / "concurrency_scaling.json")
    if not cs:
        return None
    return cs


def render_md(rows):
    out = ["# Table I — L-DREA Tier-S Reference Evaluation: Primary Metrics", "",
           "All values produced by executing the stable engine code; none are hardcoded. "
           "CI = 95% confidence (Wilson for rates; bracket = interval, ↑ = one-sided upper bound).", "",
           "| Metric | Value | 95% CI | N | Exp | Reproduction command |",
           "|--------|-------|--------|---|-----|----------------------|"]
    for r in rows:
        out.append(f"| {r['metric']} | {r['value']} | {r['ci']} | {r['n']:,} | {r['exp']} | `{r['repro']}` |"
                   if isinstance(r["n"], int) else
                   f"| {r['metric']} | {r['value']} | {r['ci']} | {r['n']} | {r['exp']} | `{r['repro']}` |")
    return "\n".join(out)


def render_scaling_md(cs):
    out = ["# Table II — Concurrency Scaling (Exp 4)", "",
           f"Workload: {cs['workload']['n_decisions']:,} decisions/level · model: {cs['concurrency_model']}", "",
           "| Threads | Throughput (dec/s) | p50 (ms) | p95 (ms) | p99 (ms) | Queue mean (ms) | RSS (MB) | FP | FD | Correct | Speedup |",
           "|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|--:|"]
    for L in cs["levels"]:
        out.append(f"| {L['n_threads']} | {L['throughput_decisions_per_s']:,.0f} | {L['latency_ms']['p50']:.5f} | "
                   f"{L['latency_ms']['p95']:.5f} | {L['latency_ms']['p99']:.5f} | {L['queue_delay_ms']['mean']:.2f} | "
                   f"{L['peak_rss_bytes']/1e6:.1f} | {L['false_permits']} | {L['false_denials']} | "
                   f"{str(L['authorization_correct'])[0]} | {L['speedup_vs_1thread']:.3f} |")
    return "\n".join(out)


def build_robustness_table():
    return load(ROOT / "fresh_evidence" / "robustness" / "robustness.json")


def render_robustness_md(rob):
    a = rob["aggregate"]
    out = ["# Table III — Runtime Robustness under Fault Injection (Exp 8)", "",
           f"Control: a clean actuated proposal PERMITs = {rob['control']['clean_proposal_permits']}. "
           f"Faults injected into the harness only; engine unchanged. "
           f"Total false permits across all faults: **{a['total_false_permits']}**. "
           f"Safety holds in **{a['families_where_safety_holds']}/{a['n_families_evaluable']}** families.", "",
           "| Fault family | Mechanism | Trials | False permits / Detected | Safety holds |",
           "|--------------|-----------|-------:|--------------------------|:------------:|"]
    for f in rob["fault_families"]:
        if f["mechanism"] == "B":
            outcome = f"detected={f.get('corruption_detected')}"
        else:
            outcome = f"fp={f.get('false_permits')}"
        out.append(f"| {f['family']} | {f['mechanism']} | {f['n_trials']} | {outcome} | "
                   f"{'✓' if f['safety_holds'] else '✗'} |")
    return "\n".join(out)


def render_latex(rows):
    esc = lambda s: str(s).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("↑", r"$\uparrow$").replace("×", r"$\times$")
    lines = [r"\begin{table}[t]", r"\centering", r"\caption{L-DREA Tier-S primary metrics (executed).}",
             r"\label{tab:ldrea_primary}", r"\begin{tabular}{llrl}", r"\hline",
             r"Metric & Value & N & Exp \\", r"\hline"]
    for r in rows:
        n = f"{r['n']:,}" if isinstance(r["n"], int) else str(r["n"])
        lines.append(f"{esc(r['metric'])} & {esc(r['value'])} & {n} & {r['exp']} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def build_coverage_table():
    return load(ROOT / "experiments" / "predicate_coverage" / "predicate_coverage.json")


def render_coverage_md(pc):
    cov, iso = pc["predicate_coverage"], pc["single_deficit_isolation"]
    veto, isb = pc["class_veto_isolation"], pc["isb_conjunct_isolation"]
    out = ["# Table IV — Runtime Predicate Coverage & Single-Deficit Isolation (Exp 9)", "",
           "Deterministic synthetic suite over the frozen `evaluate_decision`. Each case falsifies "
           "exactly ONE predicate while every other predicate concurs.", "",
           f"Predicate coverage: **{cov['covered']}/{cov['total_predicates']} "
           f"({cov['coverage_rate'] * 100:.1f}%)** · uncovered: "
           f"{', '.join(cov['uncovered']) if cov['uncovered'] else 'none'}", "",
           f"Single-deficit denial (per-predicate I3): **{iso['denied']}/{iso['n']}** · "
           f"false permits **{iso['false_permits']}** · "
           f"Wilson95 [{iso['wilson95']['low']:.4f}, {iso['wilson95']['high']:.4f}]", "",
           f"Class-veto isolation (I4): **{veto['denied_with_gamma_g_zero']}/{veto['n']}** deny with "
           f"Gamma_G = 0 · ISB conjuncts driving ISB to 0: **{isb['isb_zeroed']}/{isb['n']}**", "",
           "| Case | Category | Predicate | Mutation | Decision | deficits | G_G | G_class | ISB | Unauth | Result |",
           "|------|----------|-----------|----------|----------|---------:|----:|--------:|----:|:------:|:------:|"]
    for c in pc["cases"]:
        out.append(f"| {c['case_id']} | {c['category']} | `{c['predicate']}` | {c['mutation']} | "
                   f"{c['decision']} | {c['deficit_count']} | {c['gamma_g']} | {c['gamma_class']} | "
                   f"{c['isb']} | {'Y' if c['unauthorized'] else 'N'} | "
                   f"{'PASS' if c['passed'] else 'FAIL'} |")
    out += ["",
            "**Control.** The clean proposal (C001) PERMITs. Without it, an engine that denied "
            "everything would score 100% coverage.", "",
            "**Scope.** Synthetic and deterministic. Establishes that every predicate is correctly "
            "wired into the decision and that each alone denies. Does NOT claim the ULB corpus "
            "exercises them; that limitation of E1 remains separately disclosed.", ""]
    return "\n".join(out)


def main():
    rows = build_rows()
    (TAB / "table1_primary_metrics.md").write_text(render_md(rows))
    (TAB / "table1_primary_metrics.tex").write_text(render_latex(rows))
    cs = build_scaling_table()
    if cs:
        (TAB / "table2_concurrency_scaling.md").write_text(render_scaling_md(cs))
    rob = build_robustness_table()
    if rob:
        (TAB / "table3_robustness.md").write_text(render_robustness_md(rob))
    pc = build_coverage_table()
    if pc:
        (TAB / "table4_predicate_coverage.md").write_text(render_coverage_md(pc))
    (TAB / "tables.json").write_text(json.dumps({"primary_metrics": rows}, indent=2))
    print(f"[tables] wrote table1 ({len(rows)} rows), table2, "
          f"{'table3, ' if rob else ''}{'table4, ' if pc else ''}tables.json, LaTeX")


if __name__ == "__main__":
    main()
