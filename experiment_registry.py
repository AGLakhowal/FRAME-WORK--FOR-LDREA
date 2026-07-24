#!/usr/bin/env python3
"""
experiment_registry.py — the declarative catalogue of every experiment the paper depends on.
=============================================================================================

Each experiment declares: name · purpose · input datasets · benchmark · expected outputs ·
output directory · required metrics · paper tables produced · how to (re)run it · what it requires.

`runner` is one of:
  * ("subprocess", [argv...])         — a standalone script, re-run with the repo venv
  * ("callable", "module:function")   — an in-process entrypoint (called with its outdir)
`requires` names any external resource an experiment needs to REGENERATE RAW data. Metric
RE-DERIVATION from already-recorded logs never requires these — only fresh raw-data generation does.
No experiment requires an external API credential. E7 (agentdojo_eval) runs fully offline; its
optional live arm regenerates episodes through a LOCAL Ollama server, never a hosted provider.

This module fabricates nothing: it maps experiments to the artifacts they emit and the tables those
artifacts feed. `status()` reports, per experiment, whether its outputs are present on disk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADI = ROOT / "agentdojo_integration"
AUDIT_SUMMARY = ADI / "audit_run" / "summary"


@dataclass(frozen=True)
class Experiment:
    name: str
    purpose: str
    input_datasets: list[str]
    benchmark: str
    expected_outputs: list[str]          # repo-relative paths
    output_dir: str
    required_metrics: list[str]
    paper_tables: list[str]
    runner: tuple                        # ("subprocess", argv) | ("callable", "mod:fn")
    requires: list[str] = field(default_factory=list)   # external resources for RAW regeneration
    rederivable_from_logs: bool = True   # can metrics be recomputed from recorded logs w/o `requires`?

    def outputs_present(self) -> dict:
        present = {p: (ROOT / p).exists() for p in self.expected_outputs}
        return {"all_present": all(present.values()), "detail": present}


# --------------------------------------------------------------------------- #
EXPERIMENTS: list[Experiment] = [
    Experiment(
        name="lab_v1_base",
        purpose="Law-of-Concurrence LAB v1.0 benchmark on the real ULB credit-card corpus: "
                "PERMIT/SAFE_STATE, UER, FPR, FDR, RDR, class-veto, invariants, latency.",
        input_datasets=["GAMMA_G0_CREDITCARD_FULL_mapped.csv"],
        benchmark="gamma_test_runner.py (LAB v1.0)",
        expected_outputs=["gamma_lab_v1_report.json", "gamma_summary.json",
                          "gamma_replay_manifest.jsonl"],
        output_dir=".",
        required_metrics=["compute_authorization_accuracy", "compute_false_permit_rate",
                          "compute_false_deny_rate", "compute_class_veto_rate",
                          "compute_replay_rate", "compute_hash_chain_integrity",
                          "compute_zero_event_upper_bound", "compute_latency",
                          "compute_p95", "compute_p99"],
        paper_tables=["Table:LAB_primary_metrics", "Table:runtime_invariants",
                      "Table:latency"],
        runner=("subprocess", ["gamma_test_runner.py", "--no-html", "--no-open"]),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="concurbench_full",
        purpose="ConcurBench Document-1 conformance levels L1–L4 + adversarial robustness + "
                "distributed consistency + replay/auditability.",
        input_datasets=["GAMMA_G0_CREDITCARD_FULL_mapped.csv (via lab_v1_base)"],
        benchmark="concurbench_full.py",
        expected_outputs=["concurbench_full_report.json"],
        output_dir=".",
        required_metrics=["compute_replay_rate", "compute_queue_delay"],
        paper_tables=["Table:concurbench_conformance", "Table:distributed_consistency"],
        runner=("callable", "concurbench_full:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="stress_test",
        purpose="Financial-services adversarial stress scenarios; fail-closed behaviour.",
        input_datasets=["synthetic adversarial scenarios (in-script, deterministic)"],
        benchmark="stress_test.py",
        expected_outputs=["stress_test_report.json"],
        output_dir=".",
        required_metrics=["compute_class_veto_rate"],
        paper_tables=["Table:stress_scenarios"],
        runner=("callable", "stress_test:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="fcr_test",
        purpose="Fail-Closed Rate over predicate families (SAFE_STATE | should-deny OR uncertain).",
        input_datasets=["492 real fraud rows + synthetic uncertain cases (deterministic)"],
        benchmark="fcr_test.py",
        expected_outputs=["fcr_test_report.json"],
        output_dir=".",
        required_metrics=["compute_wilson_upper_bound", "compute_zero_event_upper_bound"],
        paper_tables=["Table:fail_closed_rate"],
        runner=("callable", "fcr_test:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="full_spec_conformance",
        purpose="FULL_SPEC corrected flow: §7.1 acceptance bands, AIS, 3-signal closure, SVR/FFC.",
        input_datasets=["GAMMA_G0_CREDITCARD_FULL_mapped.csv (telemetry columns)"],
        benchmark="full_spec_conformance.py",
        expected_outputs=["full_spec_conformance_report.json"],
        output_dir=".",
        required_metrics=["compute_authorization_accuracy"],
        paper_tables=["Table:full_spec_bands", "Table:full_spec_metrics"],
        runner=("callable", "full_spec_conformance:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="agentdojo_eval",
        purpose="External validation on upstream agentdojo==0.1.35 under L-DREA interposition. "
                "AgentDojo is the independent WORKLOAD GENERATOR; the evaluation target is L-DREA, "
                "not the language model. Measures FPR/FDR, replay determinism, predicate pass rate, "
                "evidence-quad completeness, hash-chain and ledger integrity, and latency.",
        input_datasets=["agentdojo suites: workspace, banking, slack, travel"],
        benchmark="experiment_agentdojo_metrics.py + experiment_agentdojo_boundary_fpr.py",
        expected_outputs=["experiments/agentdojo/e7_metrics.json",
                          "experiments/agentdojo/boundary/boundary_fpr.json",
                          "agentdojo_integration/audit_run/summary/statistics.json",
                          "agentdojo_integration/audit_run/summary/replay_validation.json"],
        output_dir="experiments/agentdojo",
        required_metrics=["compute_permit_rate", "compute_safe_state_rate",
                          "compute_gamma_decision_rate", "compute_replay_rate",
                          "compute_runtime_overhead"],
        paper_tables=["Table:agentdojo_evaluation"],
        runner=("subprocess", ["experiment_agentdojo_metrics.py"]),
        # Runs fully OFFLINE: no LLM in the loop, no external API credential. The optional live arm
        # (fresh episodes -> agent-side utility / attack-success rate) uses a local Ollama server via
        # AgentDojo's `vllm_parsed` provider; no L-DREA metric depends on it.
        requires=[],
        rederivable_from_logs=True,   # Table 11 metrics recomputable from execution_trace.jsonl
    ),
    Experiment(
        name="agentdojo_fpr_fdr",
        purpose="Independent false-permit / false-deny labeling (attacker targets from injection "
                "GOALs vs benign recognized-set).",
        input_datasets=["agentdojo_integration/audit_run/trace/**/execution_trace.jsonl"],
        benchmark="agentdojo_integration/audit/fpr_fdr_labeling.py",
        expected_outputs=["agentdojo_integration/audit_run/summary/fpr_fdr/fpr_fdr.json"],
        output_dir="agentdojo_integration/audit_run/summary/fpr_fdr",
        required_metrics=["compute_false_permit_rate", "compute_false_deny_rate"],
        paper_tables=["Table:agentdojo_evaluation"],
        runner=("callable", "agentdojo_integration.audit.fpr_fdr_labeling:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="concurrency_scaling",
        purpose="Thread-scaling of the frozen decision path (throughput, speedup, p50/p95/p99, "
                "queue delay, RSS, correctness/ledger). NO LLM.",
        input_datasets=["synthetic 200k-decision workload (deterministic)"],
        benchmark="agentdojo_integration/audit/concurrency_scaling.py",
        expected_outputs=["agentdojo_integration/audit_run/summary/concurrency/concurrency_scaling.json",
                          "agentdojo_integration/audit_run/summary/concurrency/concurrency_scaling.csv"],
        output_dir="agentdojo_integration/audit_run/summary/concurrency",
        required_metrics=["compute_throughput", "compute_p95", "compute_p99",
                          "compute_queue_delay"],
        paper_tables=["Table:concurrency_scaling"],
        runner=("callable", "agentdojo_integration.audit.concurrency_scaling:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="runtime_profile",
        purpose="Per-stage latency incl. Runtime Context + Replay planes (frozen path timers). NO LLM.",
        input_datasets=["synthetic 5000-row workload (deterministic)"],
        benchmark="agentdojo_integration/audit/runtime_profile.py",
        expected_outputs=["agentdojo_integration/audit_run/summary/runtime_profile/runtime_profile.json"],
        output_dir="agentdojo_integration/audit_run/summary/runtime_profile",
        required_metrics=["compute_latency", "compute_runtime_overhead"],
        paper_tables=["Table:combined_ablation"],
        runner=("callable", "agentdojo_integration.audit.runtime_profile:run"),
        requires=[], rederivable_from_logs=True,
    ),
    Experiment(
        name="decision_state_space",
        purpose="Exhaustive formal verification of evaluate_decision over the full 2^16 state space.",
        input_datasets=["(enumerated; none)"],
        benchmark="independent_verifier.py",
        expected_outputs=["independent_verifier_report.json"],
        output_dir=".",
        required_metrics=[],
        paper_tables=["Table:formal_state_space"],
        runner=("subprocess", ["independent_verifier.py"]),
        requires=[], rederivable_from_logs=True,
    ),
]

BY_NAME = {e.name: e for e in EXPERIMENTS}


def status() -> list[dict]:
    """Report presence of each experiment's expected outputs."""
    out = []
    for e in EXPERIMENTS:
        pres = e.outputs_present()
        out.append({"name": e.name, "benchmark": e.benchmark,
                    "requires": e.requires, "outputs_present": pres["all_present"],
                    "paper_tables": e.paper_tables, "detail": pres["detail"]})
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(status(), indent=2))
