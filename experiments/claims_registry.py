#!/usr/bin/env python3
"""
experiments/claims_registry.py — declarative registry of scientific claims and reviewer concerns.
=================================================================================================

This is the DATA backbone the evidence generators read. It declares, for each claim, WHERE its
supporting value lives (artifact + JSON pointer) and the RELATION that must hold. It does NOT store
any metric value — every value is resolved live from the executed artifacts at generation time, so
nothing here can go stale or fabricate a number. If an artifact is missing or a relation fails, the
generators derive the status accordingly (never silently "Supported").

A claim's evidence entry:
  {"artifact": <repo-relative json>, "pointer": <dotted path, list-index ok>, "relation": <spec>}
relation specs (evaluated against the resolved value v):
  "==0" "==1.0" "==True" ">0" ">=1" "exists" "is_zero" "eq:<literal>" "ge:<num>" "le:<num>"
"""
from __future__ import annotations

# ---- artifact locations (all produced by RUN_ALL_EXPERIMENTS.py) ----
# Declared once in experiments/_artifacts.py so a path cannot drift between registries.
try:
    from experiments._artifacts import (A_ABL, A_ADSTATS, A_AUDIT, A_BOUNDARY, A_CONC, A_COVERAGE,
                                        A_FCR, A_FULLSPEC, A_LAB, A_PROFILE, A_REPLAY, A_ROBUST,
                                        A_VERIFIER)
    from experiments._artifacts import A_CONCUR as A_CONCURBENCH
except ImportError:  # pragma: no cover - direct-on-path import
    from _artifacts import (A_ABL, A_ADSTATS, A_AUDIT, A_BOUNDARY, A_CONC, A_COVERAGE,  # type: ignore
                            A_FCR, A_FULLSPEC, A_LAB, A_PROFILE, A_REPLAY, A_ROBUST, A_VERIFIER)
    from _artifacts import A_CONCUR as A_CONCURBENCH  # type: ignore


A_CMB_ABL = "experiments/combined_ablation/combined_ablation.json"

CLAIMS = [
    {
        "id": "C1", "category": "correctness", "paper_section": "IX-B / Table (correctness)",
        "statement": "Runtime authorization prevents unauthorized execution on a realistic "
                     "transaction stream (0 unauthorized externalizations).",
        "experiments": ["E1"],
        "evidence": [{"artifact": A_LAB, "pointer": "unauthorized_execution.count", "relation": "==0"}],
        "figures": ["fig_authorization_accuracy.svg"], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C2", "category": "correctness", "paper_section": "IX-B",
        "statement": "The authorization decision is sound: zero false permits on the should-deny "
                     "population of the ULB stream.",
        "experiments": ["E1"],
        "evidence": [{"artifact": A_LAB, "pointer": "primary_metrics.false_permit_rate.adverse_events",
                      "relation": "==0"}],
        "figures": ["fig_false_permit_rate.svg"], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C3", "category": "safety", "paper_section": "VI (Invariant 4) / IX",
        "statement": "The class-level veto is fully effective: every adversarial (should-deny) "
                     "transaction transitions to SAFE_STATE.",
        "experiments": ["E1"],
        "evidence": [{"artifact": A_LAB, "pointer": "primary_metrics.class_veto_effectiveness.reported_rate",
                      "relation": "==1.0"}],
        "figures": [], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C4", "category": "safety", "paper_section": "III / IX",
        "statement": "Fail-closed semantics: across uncertain/should-deny predicate families the "
                     "Fail-Closed Rate is 1.0 (no fail-open events).",
        "experiments": ["E1"],
        "evidence": [{"artifact": A_FCR, "pointer": "overall.FCR", "relation": "==1.0"},
                     {"artifact": A_FCR, "pointer": "overall.fail_open_events", "relation": "==0"}],
        "figures": [], "tables": [],
    },
    {
        "id": "C5", "category": "determinism", "paper_section": "IX (RDR)",
        "statement": "Authorization decisions are deterministically replayable (Replay Determinism "
                     "Rate = 100%).",
        "experiments": ["E1", "E2"],
        "evidence": [{"artifact": A_LAB, "pointer": "primary_metrics.replay_determinism_rate.reported_rate",
                      "relation": "==1.0"}],
        "figures": ["fig_replay_integrity.svg"], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C6", "category": "integrity", "paper_section": "IX (replay/audit)",
        "statement": "Execution provenance is tamper-evident: every decision record re-verifies "
                     "(0 hash-chain, ledger-bind, or consistency failures).",
        "experiments": ["E2"],
        "evidence": [{"artifact": A_REPLAY, "pointer": "hash_chain_adjacency_failures", "relation": "==0"},
                     {"artifact": A_REPLAY, "pointer": "ledger_bind_failures", "relation": "==0"},
                     {"artifact": A_REPLAY, "pointer": "self_consistency_failures", "relation": "==0"},
                     {"artifact": A_REPLAY, "pointer": "result", "relation": "eq:PASS"}],
        "figures": ["fig_replay_integrity.svg"], "tables": [],
    },
    {
        "id": "C7", "category": "formal", "paper_section": "VI / Appendix D",
        "statement": "The decision logic is mathematically correct: an independent reference "
                     "implementation is bitwise-equivalent to the engine over the entire 2^16 input space.",
        "experiments": ["E3"],
        "evidence": [{"artifact": A_VERIFIER, "pointer": "total_field_mismatches", "relation": "==0"},
                     {"artifact": A_VERIFIER, "pointer": "coverage_complete", "relation": "==True"},
                     {"artifact": A_VERIFIER, "pointer": "verdict", "relation": "eq:IDENTICAL"}],
        "figures": [], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C8", "category": "safety", "paper_section": "IX (scalability)",
        "statement": "Runtime safety is preserved under concurrency: 0 false permits and 0 false "
                     "denials at every thread level (1-64).",
        "experiments": ["E4"],
        "evidence": [{"artifact": A_CONC, "pointer": "total_false_permits", "relation": "==0"},
                     {"artifact": A_CONC, "pointer": "total_false_denials", "relation": "==0"},
                     {"artifact": A_CONC, "pointer": "all_authorization_correct", "relation": "==True"}],
        "figures": ["fig_latency.svg", "fig_throughput.svg"], "tables": ["table2_concurrency_scaling.md"],
    },
    {
        "id": "C9", "category": "performance-negative", "paper_section": "IX (scalability, limitation)",
        "statement": "Throughput does NOT scale with threads on the pure-Python decision path "
                     "(GIL-bound); this is reported as a limitation, not a scaling claim.",
        "experiments": ["E4"],
        "evidence": [{"artifact": A_CONC, "pointer": "levels.-1.speedup_vs_1thread", "relation": "le:1.0"}],
        "figures": ["fig_throughput.svg"], "tables": ["table2_concurrency_scaling.md"],
        "expected_status": "Supported (negative result)",
    },
    {
        "id": "C10b", "category": "ablation", "paper_section": "IX (combined ablation)",
        "statement": "Interaction effects between runtime components are measured, not assumed: the "
                     "combined ablation executes every pairwise and representative higher-order "
                     "removal through the full runtime and classifies each interaction. NOTE: E5b "
                     "reports BLIND-detection metrics (Undetected Risk Rate URR = FN/(TP+FN)), which "
                     "are a DIFFERENT construct from the authorization False Permit Rate of C2/C12 "
                     "(0/492, 0/62) and never replace it.",
        "experiments": ["E5b"],
        "evidence": [{"artifact": A_CMB_ABL, "pointer": "n_configurations", "relation": "ge:8"},
                     {"artifact": A_CMB_ABL, "pointer": "baseline_runtime_integrity_score", "relation": "==1.0"}],
    },
    {
        "id": "C10", "category": "ablation", "paper_section": "IX (ablation)",
        "statement": "Each structural component is necessary: removing the authorization layer leaks "
                     "the entire deniable population (causal contribution to safety).",
        "experiments": ["E5"],
        "evidence": [{"artifact": A_ABL, "pointer": "configs.3.leaked_permits_vs_baseline", "relation": ">0"},
                     {"artifact": A_ABL, "pointer": "configs.0.leaked_permits_vs_baseline", "relation": "==0"}],
        "figures": ["fig_component_ablation.svg"], "tables": ["table1_primary_metrics.md"],
    },
    {
        "id": "C11", "category": "overhead", "paper_section": "IX (overhead)",
        "statement": "Per-decision runtime overhead is low: the Runtime-Context and Replay planes are "
                     "a small fraction of end-to-end pipeline time.",
        "experiments": ["E6"],
        "evidence": [{"artifact": A_PROFILE, "pointer": "runtime_context.pct_of_end_to_end", "relation": "le:25"},
                     {"artifact": A_PROFILE, "pointer": "replay.pct_of_end_to_end", "relation": "le:25"}],
        "figures": ["fig_runtime_breakdown.svg"], "tables": [],
    },
    {
        "id": "C12", "category": "domain-independence", "paper_section": "IX-E (AgentDojo)",
        "statement": "AgentDojo integration preserves authorization correctness: 0 false permits on "
                     "genuinely-foreign attacker targets at the boundary (no LLM).",
        "experiments": ["E7"],
        "evidence": [{"artifact": A_BOUNDARY, "pointer": "soundness_foreign_targets.permitted", "relation": "==0"}],
        "figures": ["fig_false_permit_rate.svg"], "tables": ["table1_primary_metrics.md"],
        "expected_status": "Partially Supported",
        # The claim itself (boundary soundness, no LLM) is fully MEASURED and E7 is EXECUTED offline.
        # It stays "Partially Supported" for one honest reason only: the recognition-set coverage
        # boundary below. Agent-side Utility/TASR is a different quantity and does not bear on it.
        "partial_reason": "Boundary FPR is measured offline (no LLM, no API credential) and E7 is "
                          "EXECUTED. The residual caveat is the recognition-set coverage boundary: "
                          "structural-only mediated tools have n=0 adjudicated actions, so soundness "
                          "there is undefined rather than demonstrated. Two recognition-set "
                          "limitations documented.",
    },
    {
        "id": "C13", "category": "robustness", "paper_section": "IX (robustness, Exp 8)",
        "statement": "Safety properties hold under runtime fault injection: across all fault families "
                     "there are 0 false permits and every integrity corruption is detected.",
        "experiments": ["E8"],
        "evidence": [{"artifact": A_ROBUST, "pointer": "aggregate.total_false_permits", "relation": "==0"},
                     {"artifact": A_ROBUST, "pointer": "aggregate.all_safety_properties_hold", "relation": "==True"}],
        "figures": ["fig_robustness.svg"], "tables": ["table3_robustness.md"],
    },
    {
        "id": "C15", "category": "coverage", "paper_section": "IX (Exp 9, predicate coverage)",
        "statement": "Every runtime predicate is exercised and each, in isolation, denies: a "
                     "deterministic synthetic suite drives the frozen engine so that all 13 runtime "
                     "predicates are observed in both polarities, and a single deficit among nine "
                     "concurring predicates always yields SAFE_STATE (per-predicate I3).",
        "experiments": ["E9"],
        "evidence": [{"artifact": A_COVERAGE, "pointer": "predicate_coverage.coverage_rate", "relation": "==1.0"},
                     {"artifact": A_COVERAGE, "pointer": "single_deficit_isolation.false_permits", "relation": "==0"},
                     {"artifact": A_COVERAGE, "pointer": "control.clean_proposal_permits", "relation": "==True"},
                     {"artifact": A_COVERAGE, "pointer": "aggregate.all_cases_pass", "relation": "==True"}],
        "figures": ["fig_predicate_coverage.svg"], "tables": ["table4_predicate_coverage.md"],
    },
    {
        "id": "C16", "category": "auditability", "paper_section": "IX (auditability) / ConcurBench L4",
        "statement": "Execution evidence is exportable as an independently verifiable audit bundle: "
                     "every member re-hashes to its recorded digest and the bundle is cryptographically "
                     "bound to the live ledger, satisfying ConcurBench Level 4.",
        "experiments": ["E10"],
        "evidence": [{"artifact": A_AUDIT, "pointer": "verification.status", "relation": "eq:PASS"},
                     {"artifact": A_AUDIT, "pointer": "concurbench_level4", "relation": "eq:PASS"},
                     {"artifact": A_CONCURBENCH, "pointer": "replay_and_auditability.audit_packet_export",
                      "relation": "eq:PASS"}],
        "figures": [], "tables": [],
    },
    {
        "id": "C14", "category": "scope", "paper_section": "V-G / XII (scope)",
        "statement": "Hardware (Tier-H FPGA/SGX/HSM) deployment.",
        "experiments": [],
        "evidence": [],
        "figures": [], "tables": [],
        "expected_status": "Not Claimed",
        "partial_reason": "Under the Tier-S reference framing hardware deployment is explicitly out of "
                          "scope; no hardware claim is made and none is evaluated.",
    },
]


# Reviewer concern -> experiment(s) -> evidence -> paper section -> status (status derived from claims)
REVIEWER_CONCERNS = [
    {"id": "R1", "concern": "Where is authorization correctness demonstrated on realistic data?",
     "claims": ["C1", "C2"], "paper_section": "IX-B", "artifact_hint": A_LAB,
     "figure": "fig_authorization_accuracy.svg"},
    # R2 additionally carries C16: evidence is not merely replayable in situ, it is exportable as an
    # independently verifiable audit bundle (ConcurBench Level 4).
    {"id": "R2", "concern": "Where is replay determinism proven?",
     "claims": ["C5", "C6", "C16"], "paper_section": "IX (replay)", "artifact_hint": A_REPLAY,
     "figure": "fig_replay_integrity.svg"},
    # R3 additionally carries C15: the 2^16 exhaustive check compares an independent reference
    # function; E9 drives the engine's own runtime path over every predicate in isolation.
    {"id": "R3", "concern": "Is the decision logic formally correct, or only tested?",
     "claims": ["C7", "C15"], "paper_section": "VI / Appendix D", "artifact_hint": A_VERIFIER,
     "figure": None},
    {"id": "R4", "concern": "Does the system remain safe under concurrency / load?",
     "claims": ["C8"], "paper_section": "IX (scalability)", "artifact_hint": A_CONC,
     "figure": "fig_latency.svg"},
    {"id": "R5", "concern": "Does it actually scale in throughput?",
     "claims": ["C9"], "paper_section": "IX (limitation)", "artifact_hint": A_CONC,
     "figure": "fig_throughput.svg"},
    {"id": "R6", "concern": "Are all components necessary, or is this over-engineered?",
     "claims": ["C10"], "paper_section": "IX (ablation)", "artifact_hint": A_ABL,
     "figure": "fig_component_ablation.svg"},
    {"id": "R6-ext", "concern": "Where is the evidence of INTERACTION EFFECTS between runtime "
                                "components (pairwise / higher-order)? [E5b reports blind-detection "
                                "metrics — URR/BFR — NOT the authorization FPR of R1/R8]",
     "claims": ["C10b"], "paper_section": "IX (combined ablation)", "artifact_hint": A_CMB_ABL,
     "figure": "fig_combined_ablation_heatmap.svg"},
    {"id": "R7", "concern": "What is the runtime overhead of the governance layer?",
     "claims": ["C11"], "paper_section": "IX (overhead)", "artifact_hint": A_PROFILE,
     "figure": "fig_runtime_breakdown.svg"},
    {"id": "R8", "concern": "Does the approach generalize beyond one dataset (agents)?",
     "claims": ["C12"], "paper_section": "IX-E", "artifact_hint": A_BOUNDARY,
     "figure": "fig_false_permit_rate.svg"},
    {"id": "R9", "concern": "How does it behave under faults / adversarial runtime conditions?",
     "claims": ["C13"], "paper_section": "IX (Exp 8)", "artifact_hint": A_ROBUST,
     "figure": "fig_robustness.svg"},
    {"id": "R10", "concern": "Are the zero-event claims statistically justified given sample sizes?",
     "claims": ["C2", "C12"], "paper_section": "IX (statistics)",
     "artifact_hint": "experiments/statistics/statistics_report.json", "figure": None},
    {"id": "R11", "concern": "Are hardware results being over-claimed?",
     "claims": ["C14"], "paper_section": "V-G / XII", "artifact_hint": None, "figure": None},
]
