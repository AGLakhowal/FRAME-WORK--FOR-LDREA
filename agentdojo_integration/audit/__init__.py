"""Scientific audit framework (ADDITIVE) for AgentDojo x L-DREA x Gamma.

This package only ADDS capabilities on top of the existing execution tracer. It never modifies
AgentDojo, the frozen interception package, gamma_test_runner.evaluate_decision, the runner, prompts,
attacks, tasks, or scoring. Every reported value originates from actual runtime execution captured in
per-episode `execution_trace.jsonl` files.

Modules:
  _util          shared hashing / json / statistics primitives (no external deps beyond numpy)
  integrity      frozen-file SHA256 snapshots + trace hash-chain / tamper detection (Phase H)
  replay_engine  ReplayEngine: reconstruct + re-verify from execution_trace.jsonl ONLY (Phase D)
  stats_engine   multi-episode statistical analysis with Wilson/bootstrap CIs (Phase B)
  batch_runner   multi-episode trace collection: batch, resume, organized output (Phase A)
  reviewer_reports  per-episode + master human-readable audit reports (Phase C)
  proof_generator   per-authorization scientific proof chains (Phase E)
  visualize      Mermaid / Graphviz DOT / inline-SVG / interactive HTML (Phases F)
  dashboard      publication SVG figures + CSV source + HTML dashboard (Phase G)
  summary        benchmark-wide summary (Phase I)
  supplementary  IEEE Access supplementary material generator (Phase J)
"""
__all__ = [
    "_util", "integrity", "replay_engine", "stats_engine", "batch_runner",
    "reviewer_reports", "proof_generator", "visualize", "dashboard", "summary", "supplementary",
]
