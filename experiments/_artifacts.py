#!/usr/bin/env python3
"""
experiments/_artifacts.py — the single source of truth for artifact locations.
==============================================================================

Every repo-relative path to an executed artifact is declared here exactly once. Before this module
existed the same eleven paths were repeated across claims_registry.py, _metrics_catalog.py and
dashboard_science.py, with one path carrying two different names (``A_CONC`` and ``A_STRESS`` both
pointed at concurrency_scaling.json). A path that is written down three times is a path that can
drift in two of them; a claim resolving against a stale copy would fail silently rather than loudly.

This module declares paths. It reads nothing, computes nothing, and imports nothing.
"""
from __future__ import annotations

# ---- Experiment 1 — runtime authorization correctness ----
A_LAB = "experiments/runtime_correctness/gamma_lab_v1_report.json"
A_FULLSPEC = "experiments/runtime_correctness/full_spec_conformance_report.json"
A_FCR = "experiments/runtime_correctness/fcr_test_report.json"
A_CONCUR = "experiments/runtime_correctness/concurbench_full_report.json"
A_STRESSFIN = "experiments/runtime_correctness/stress_test_report.json"
A_SUMMARY = "experiments/runtime_correctness/gamma_summary.json"
A_ROWCSV = "experiments/runtime_correctness/gamma_validation_results.csv"

# ---- Experiment 2 — replay integrity ----
A_REPLAY = "experiments/replay/replay_report.json"

# ---- Experiment 3 — formal verification ----
A_VERIFIER = "experiments/formal/independent_verifier_report.json"
A_TLC_LOG = "experiments/formal/logs/E3_tlc.log"

# ---- Experiment 4 — concurrency scaling ----
A_STRESS = "experiments/stress/concurrency_scaling.json"
A_CONC = A_STRESS  # historical alias used by claims_registry; same artifact, one definition

# ---- Experiment 5 — component ablation ----
A_ABL = "experiments/ablation/ablation.json"

# ---- Experiment 6 — runtime profiling ----
A_PROFILE = "experiments/profiling/runtime_profile.json"
A_STAGES = "experiments/profiling/stage_distributions.json"

# ---- Experiment 7 — AgentDojo ----
A_BOUNDARY = "experiments/agentdojo/boundary/boundary_fpr.json"
A_ADSTATS = "experiments/agentdojo/statistics.json"
A_E7METRICS = "experiments/agentdojo/e7_metrics.json"   # full runtime-governance metric suite
A_E7META = "experiments/agentdojo/metadata.json"        # authoritative E7 run status

# ---- Experiment 8 — runtime robustness ----
A_ROBUST = "fresh_evidence/robustness/robustness.json"

# ---- Experiment 9 — runtime predicate coverage ----
A_COVERAGE = "experiments/predicate_coverage/predicate_coverage.json"

# ---- Stage 10 — audit bundle export ----
A_AUDIT = "experiments/audit_bundle/audit_bundle_report.json"
A_BUNDLE_MANIFEST = "gamma_bundle/MANIFEST.json"

# ---- Cross-experiment generators ----
A_STATS = "experiments/statistics/statistics_report.json"
A_PROV = "experiments/provenance/provenance_graph.json"

# ---- Repository-root artifacts ----
A_MANIFEST = "evidence_manifest.json"
A_REPRO = "REPRODUCTION_MANIFEST.json"
A_TRANSCRIPT = "RUN_ALL_TRANSCRIPT.log"

# ConcurBench is copied into the E1 directory by RUN_ALL; the root copy is the fallback for a
# partial (--only) run that has not yet re-executed E1.
A_CONCUR_ALT = "concurbench_full_report.json"
