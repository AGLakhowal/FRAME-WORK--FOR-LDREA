"""L-DREA runtime interception layer for the real AgentDojo benchmark (Phase 3A).

Interposition ONLY at the approved execution boundary (FunctionsRuntime.run_function),
via AgentDojo's own `runtime_class` injection parameter. No AgentDojo source is modified.
The authorization decision reuses the existing Gamma engine (gamma_test_runner.evaluate_decision);
no second authorization engine is created. Predicate families are INSTANTIATED from the frozen
Phase-2B manifests (Merkle root ce8c8467...f618); none are invented.

Phase 3A scope: interception + Gamma decision (PERMIT / SAFE_STATE) ONLY.
Explicitly NOT in this phase: Evidence Quad emission, Hydra Ledger, replay, metrics, reports,
dashboards, benchmark execution.
"""
