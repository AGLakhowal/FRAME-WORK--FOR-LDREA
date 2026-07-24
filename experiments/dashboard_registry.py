#!/usr/bin/env python3
"""
experiments/dashboard_registry.py — presentation metadata for the scientific dashboard.
=======================================================================================

PURELY DESCRIPTIVE. This file changes NOTHING about Gamma, L-DREA, the experiments, the metrics, the
statistics, or any paper value. It only tells the dashboard how to *describe* each experiment: its
plain-English purpose, the scientific motivation, the reviewer concern it addresses, which benchmark
it uses, what it calculates / loads / generates / reuses, which paper artifacts it feeds, and how a
reader should interpret the result.

Every experiment's actual numbers are read live from its executed JSON artifact by _dashboard.py —
nothing numeric is stored here. Descriptive keys added for the expanded dashboard:

    motivation        why the experiment is scientifically necessary
    why_exists        the specific gap in the evidence it closes
    paper_sections    where its results appear in the paper
    tables_produced   IEEE tables it feeds
    figures_produced  figures it feeds
    metrics_produced  the metric names it computes (values resolved live)
    outputs           every artifact path it writes (existence checked live)
    interpretation    how to read the result, including what it does NOT show
"""
from __future__ import annotations

# Execution order; also drives the "Next experiment" pointer in the dashboard.
ORDER = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]

# Order matches RUN_ALL_EXPERIMENTS.py execution order.
EXPERIMENTS = {
    "E1": {
        "num": "1/8", "key": "correctness",
        "title": "Runtime Authorization Correctness",
        "purpose": ("Push every transaction in the ULB stream through the frozen authorization engine "
                    "and confirm each action is permitted or denied correctly. This is the core "
                    "reference-monitor claim: the guard makes the right PERMIT/SAFE_STATE call on real "
                    "data, fails closed, and leaves a replayable record."),
        "question": "Does L-DREA authorize/deny runtime actions correctly on a realistic stream?",
        "motivation": ("A reference monitor is only credible if it is exercised on a realistic, "
                       "author-independent input distribution rather than on hand-picked cases. The ULB "
                       "credit-card corpus supplies 284,807 transactions with a heavily imbalanced "
                       "should-deny population (492 rows), which is exactly the regime where a guard "
                       "that fails open would be hardest to catch."),
        "why_exists": ("Without this experiment, every downstream claim (replay, ablation, robustness) "
                       "would rest on an engine whose basic decision correctness was never established "
                       "at scale on real data."),
        "reviewer": {"id": "R1", "quote": "Authorization correctness is not demonstrated on realistic "
                     "data.", "comment": "Comment #1"},
        "benchmark": ["LAB v1.0", "ConcurBench", "FULL_SPEC", "Fail-Closed Rate"],
        "input": ["Dataset : GAMMA_G0_CREDITCARD_FULL_mapped.csv (284,807 transactions)",
                  "Should-deny (adversarial) population : 492 rows",
                  "Engine   : gamma_test_runner.evaluate_decision (frozen), theta = 0.5"],
        "calculated": ["Authorization accuracy / confusion matrix", "False Permit Rate + Wilson bound",
                       "False Denial Rate", "Unauthorized Execution Rate", "Replay Determinism Rate",
                       "Class-veto effectiveness", "TOCTOU violations", "Latency mean/p95/p99",
                       "6 runtime invariants"],
        "loaded": ["ULB corpus + golden-trace expected outcomes", "frozen predicate/threshold manifests"],
        "generated": ["gamma_lab_v1_report.json", "gamma_summary.json", "gamma_validation_results.csv",
                      "gamma_replay_manifest.jsonl (the Hydra Ledger)"],
        "reused": ["ULB dataset (input stream)"],
        "progress": ["Loading dataset", "Scoring every transaction", "Enforcing conjunctive gate",
                     "Computing statistics (Wilson bounds)", "Writing ledger + report"],
        "paper": ["Table I (primary metrics)", "fig_authorization_accuracy.svg", "fig_false_permit_rate.svg"],
        "paper_sections": ["IX-B (correctness)", "Table I", "§11.1 (metric definitions)"],
        "tables_produced": ["table1_primary_metrics.md", "table1_primary_metrics.tex"],
        "figures_produced": ["fig_authorization_accuracy.svg", "fig_false_permit_rate.svg"],
        "metrics_produced": ["Authorization Accuracy", "UER", "FPR", "FDR", "DR", "SVR", "FCR",
                            "Γ-Compliance", "Class-Veto Effectiveness", "TOCTOU Violation Rate",
                            "Revocation Compliance", "Replay Determinism Rate", "Runtime Invariants I1–I6",
                            "Latency mean/p50/p95/p99/max", "Wilson 95% bounds (naive + cluster-corrected)"],
        "outputs": ["experiments/runtime_correctness/gamma_lab_v1_report.json",
                    "experiments/runtime_correctness/gamma_summary.json",
                    "experiments/runtime_correctness/gamma_validation_results.csv",
                    "experiments/runtime_correctness/full_spec_conformance_report.json",
                    "experiments/runtime_correctness/fcr_test_report.json",
                    "experiments/runtime_correctness/stress_test_report.json",
                    "experiments/runtime_correctness/concurbench_full_report.json",
                    "experiments/runtime_correctness/summary.md",
                    "experiments/runtime_correctness/metadata.json",
                    "experiments/runtime_correctness/REPRODUCE.md",
                    "gamma_replay_manifest.jsonl"],
        "interpretation": ("Zero false permits on the should-deny population establishes soundness on this "
                           "corpus; the Wilson 95% upper bound (not the point estimate of 0) is the honest "
                           "ceiling given n=492. Zero false denials establishes that soundness was not "
                           "bought by denying everything. This experiment does NOT establish generalisation "
                           "beyond ULB — that is E7's job."),
    },
    "E2": {
        "num": "2/8", "key": "replay",
        "title": "Runtime Replay Integrity",
        "purpose": ("Independently re-verify every decision straight from the tamper-evident ledger — "
                    "without the dataset or the engine. Proves the evidence chain is auditable by a "
                    "third party and that no record was altered."),
        "question": "Can every authorization decision be re-verified from evidence alone?",
        "motivation": ("Auditability is the difference between a system that claims it decided correctly "
                       "and one a regulator can check. The verifier deliberately shares no code with the "
                       "engine and never reads the dataset, so a passing verification is independent "
                       "evidence rather than a self-consistency check."),
        "why_exists": ("Closes the gap between 'the engine logged a decision' and 'the logged decision is "
                       "provably the one that was made, in the order it was made, unaltered since.'"),
        "reviewer": {"id": "R2", "quote": "Replay determinism / evidence integrity is not proven.",
                     "comment": "Comment #2"},
        "benchmark": ["Hydra Ledger replay verifier"],
        "input": ["Ledger : gamma_replay_manifest.jsonl (284,807 chained decision records)",
                  "Verifier : gamma_replay_verify.py (independent; no pandas, no dataset)"],
        "calculated": ["Hash-chain adjacency failures", "Ledger-bind failures",
                       "Self-consistency failures", "Recomputed manifest SHA-256"],
        "loaded": ["the Hydra Ledger produced by E1"],
        "generated": ["replay_report.json"],
        "reused": ["Hydra Ledger (from E1)"],
        "progress": ["Reading ledger", "Re-deriving hash chain", "Checking ledger binding",
                     "Checking self-consistency", "Recomputing manifest hash"],
        "paper": ["Table I (replay rows)", "fig_replay_integrity.svg"],
        "paper_sections": ["IX (replay determinism)", "Table I", "§6.10 (window identifier)"],
        "tables_produced": ["table1_primary_metrics.md"],
        "figures_produced": ["fig_replay_integrity.svg"],
        "metrics_produced": ["Decision records verified", "Hash-chain adjacency failures",
                            "Ledger-bind failures", "Self-consistency failures", "Manifest SHA-256",
                            "Genesis anchor", "Verifier verdict"],
        "outputs": ["experiments/replay/replay_report.json", "experiments/replay/summary.md",
                    "experiments/replay/metadata.json", "experiments/replay/REPRODUCE.md",
                    "experiments/replay/logs/E2.log"],
        "interpretation": ("A PASS means the ledger is internally consistent, genesis-anchored, and "
                           "byte-identical to the SHA-256 recorded at write time. It does NOT prove the "
                           "engine's decisions were *correct* (that is E1/E3); it proves they were not "
                           "altered after the fact."),
    },
    "E3": {
        "num": "3/8", "key": "formal",
        "title": "Formal Verification (Exhaustive + Model Check)",
        "purpose": ("Prove the decision logic is mathematically correct: an independently written "
                    "reference implementation must agree with the engine on EVERY one of the 2^16 "
                    "possible input states, and the Execution-Sovereignty invariant is TLC "
                    "model-checked over the Appendix-D specification."),
        "question": "Is the decision logic provably correct, not merely tested on samples?",
        "motivation": ("Testing samples the input space; exhaustive enumeration eliminates it. Because the "
                       "decision function has 16 boolean inputs, the entire space is only 65,536 states — "
                       "small enough to check completely, which converts an empirical claim into a "
                       "closed-form one over that abstraction."),
        "why_exists": ("Answers the reviewer objection that passing 284,807 real rows still leaves "
                       "untested corners of the decision table."),
        "reviewer": {"id": "R3", "quote": "Correctness rests on testing, not formal guarantees.",
                     "comment": "Comment #3"},
        "benchmark": ["Exhaustive state-space verifier", "TLA+ / TLC"],
        "input": ["State space : 2^16 = 65,536 enumerated input states (complete, not sampled)",
                  "TLA+ model  : formal/ExternalizationMonitor.tla (+ .cfg)"],
        "calculated": ["Decision-equivalence over all 65,536 states", "Field mismatches (must be 0)",
                       "TLC reachable-state count + invariant violations"],
        "loaded": ["formal/ExternalizationMonitor.tla / .cfg"],
        "generated": ["independent_verifier_report.json", "TLC console log"],
        "reused": ["the frozen engine as the oracle"],
        "progress": ["Enumerating 2^16 states", "Comparing reference vs engine",
                     "Model-checking Appendix-D invariant (TLC)"],
        "paper": ["Table I (formal rows)", "Appendix D (TLA+)"],
        "paper_sections": ["VI (decision logic)", "Appendix D (TLA+ specification)", "Table I"],
        "tables_produced": ["table1_primary_metrics.md"],
        "figures_produced": [],
        "metrics_produced": ["States enumerated / expected", "Coverage completeness",
                            "Per-field mismatch counts", "PERMIT vs SAFE_STATE partition",
                            "TLC states generated", "TLC distinct reachable states",
                            "TLC invariant violations", "TLC deadlocks", "TLC search depth"],
        "outputs": ["experiments/formal/independent_verifier_report.json",
                    "experiments/formal/ExternalizationMonitor.tla",
                    "experiments/formal/ExternalizationMonitor.cfg",
                    "experiments/formal/logs/E3_tlc.log", "experiments/formal/logs/E3.log",
                    "experiments/formal/summary.md", "experiments/formal/metadata.json"],
        "interpretation": ("IDENTICAL over 65,536 states means the engine implements the specified decision "
                           "table exactly, for every input. The TLC run checks three safety invariants over "
                           "a BOUNDED instantiation (3 tokens, 2 epochs, skew ≤ 1) — it is a finite-state "
                           "proof for that configuration, not an unbounded theorem. No liveness property is "
                           "declared or checked."),
    },
    "E4": {
        "num": "4/8", "key": "stress",
        "title": "Runtime Stress Evaluation (Concurrency Scaling)",
        "purpose": ("Drive a large decision workload across 1-64 threads and confirm the safety "
                    "properties hold at every level, while honestly characterizing throughput, "
                    "latency, queue delay, CPU and memory."),
        "question": "Does safety hold under concurrency, and how does performance scale?",
        "motivation": ("Concurrency is where reference monitors classically fail: races between check and "
                       "use, interleaved ledger writes, and torn state. Safety must be shown to be a "
                       "property of the decision path, not an accident of single-threaded execution."),
        "why_exists": ("Separates two claims reviewers conflate: (a) is the guard still SOUND under load, "
                       "and (b) does it scale in throughput. The answer to (a) is yes; the answer to (b) is "
                       "no under CPython, and that negative result is reported rather than buried."),
        "reviewer": {"id": "R4/R5", "quote": "System scalability and behaviour under load were not "
                     "demonstrated.", "comment": "Comment #4"},
        "benchmark": ["Concurrency Scaling (frozen decision path)"],
        "input": ["Workload : 200,000 deterministic decisions per thread level",
                  "Thread levels : 1, 2, 4, 8, 16, 32, 64",
                  "Total decisions : 1,400,000 across all levels"],
        "calculated": ["Throughput per level", "Latency p50/p95/p99", "Queue delay", "CPU utilization",
                       "Peak RSS", "False permits / denials", "Ledger + replay consistency", "Speedup"],
        "loaded": ["reference ledger hash for cross-check"],
        "generated": ["concurrency_scaling.json", "concurrency_scaling.csv", "latency/throughput SVGs"],
        "reused": ["the frozen GammaBridge decision path"],
        "progress": ["Building 200k workload", "Running 1->64 threads", "Measuring latency/throughput",
                     "Verifying safety at each level"],
        "paper": ["Table II (concurrency scaling)", "fig_latency.svg", "fig_throughput.svg"],
        "paper_sections": ["IX (scalability)", "IX (limitation — throughput)", "Table II"],
        "tables_produced": ["table2_concurrency_scaling.md"],
        "figures_produced": ["fig_latency.svg", "fig_throughput.svg"],
        "metrics_produced": ["Throughput per thread level", "Speedup vs 1 thread", "Scaling efficiency",
                            "Latency p50/p95/p99/mean/max", "Queue delay mean/p95/max",
                            "CPU time + utilisation", "Peak RSS", "False permits / denials per level",
                            "Ledger consistency", "Replay consistency"],
        "outputs": ["experiments/stress/concurrency_scaling.json",
                    "experiments/stress/concurrency_scaling.csv",
                    "experiments/stress/summary.md", "experiments/stress/metadata.json",
                    "experiments/stress/REPRODUCE.md", "experiments/stress/logs/E4.log"],
        "interpretation": ("Read the safety columns first: authorization correctness, false permits and "
                           "false denials are invariant across all thread levels. Throughput DEGRADES above "
                           "4 threads. The artifact attributes this to the CPython GIL "
                           "(concurrency_model = 'python threads (GIL-bound reference decision path)'), "
                           "corroborated by CPU utilisation never exceeding ~1.7 of 10 available cores. "
                           "This is a limitation of the reference IMPLEMENTATION's runtime, not evidence "
                           "about the ARCHITECTURE's parallelisability — which this experiment does not test."),
    },
    "E5": {
        "num": "5/8", "key": "ablation",
        "title": "Component Ablation",
        "purpose": ("Remove each structural control one at a time and measure how many denials it "
                    "converts into permits ('leaked permits'). This is the causal evidence that every "
                    "component contributes to safety and none is redundant."),
        "question": "Is every architectural component necessary?",
        "motivation": ("Layered safety architectures invite the objection that the layers are decorative. "
                       "An ablation converts that from an aesthetic argument into a measurement: remove a "
                       "control, count the unsafe actions that now get through."),
        "why_exists": ("Supplies the counterfactual that a single end-to-end pass cannot: how many permits "
                       "would have leaked WITHOUT each component."),
        "reviewer": {"id": "R6", "quote": "The architecture may be over-engineered; component "
                     "necessity is unproven.", "comment": "Comment #5"},
        "benchmark": ["Ablation harness (frozen engine, controlled deficit workload)"],
        "input": ["Workload : 60,000 deterministic decisions per configuration",
                  "Configurations : baseline, -class-veto, -non-compensatory-Gamma, -authorization-layer"],
        "calculated": ["Leaked permits per removed component", "Leak rate + Wilson CI",
                       "Throughput per config", "Replay consistency per config"],
        "loaded": [],
        "generated": ["ablation.json", "ablation.csv", "ablation_log.jsonl"],
        "reused": ["the frozen evaluate_decision as the baseline"],
        "progress": ["Building deficit workload", "Running each ablated config", "Counting leaked permits"],
        "paper": ["Table I (ablation rows)", "fig_component_ablation.svg"],
        "paper_sections": ["IX (ablation)", "Table I (ablation rows)"],
        "tables_produced": ["table1_primary_metrics.md"],
        "figures_produced": ["fig_component_ablation.svg"],
        "metrics_produced": ["Permits / denials per configuration", "Leaked permits vs baseline",
                            "Leak rate + Wilson 95% CI", "Risk difference", "Cohen's h",
                            "Throughput per configuration", "Full latency distribution per configuration",
                            "Replay consistency per configuration"],
        "outputs": ["experiments/ablation/ablation.json", "experiments/ablation/ablation.csv",
                    "experiments/ablation/ablation_log.jsonl", "experiments/ablation/summary.md",
                    "experiments/ablation/metadata.json", "experiments/ablation/REPRODUCE.md"],
        "interpretation": ("A non-zero leak count is direct causal evidence that the removed component was "
                           "load-bearing on this workload. A zero leak count does NOT prove a component is "
                           "useless — the replay layer leaks 0 permits because it is an audit control, not "
                           "a decision gate; its contribution is provenance (E2), not leakage prevention. "
                           "The contrasts are deterministic, so the risk difference is exact and no "
                           "significance test applies."),
    },
    "E6": {
        "num": "6/8", "key": "profiling",
        "title": "Runtime Profiling",
        "purpose": ("Measure the per-stage cost of the governance layer — the Runtime-Context plane, "
                    "the Replay plane, and the full pipeline — plus per-stage latency distributions "
                    "from the recorded agent traces, to quantify overhead."),
        "question": "What is the runtime overhead of the authorization layer, stage by stage?",
        "motivation": ("A guard nobody can afford to deploy is not a guard. Attributing cost to specific "
                       "planes shows which parts of the architecture dominate, and whether the overhead is "
                       "in the decision itself or in the evidence machinery around it."),
        "why_exists": ("Turns 'overhead is low' into a per-stage number a systems reviewer can audit."),
        "reviewer": {"id": "R7", "quote": "The overhead of the governance layer is not quantified.",
                     "comment": "Comment #6"},
        "benchmark": ["Runtime profiler (frozen planes)"],
        "input": ["Workload : 5,000-row synthetic pipeline (35,000 RCL calls)",
                  "Per-stage source : recorded AgentDojo execution traces"],
        "calculated": ["Runtime-Context ms/row + % of end-to-end", "Replay ms/row + %",
                       "Full pipeline ms/row", "Per-stage mean/median/p95/p99/std"],
        "loaded": ["recorded AgentDojo execution traces"],
        "generated": ["runtime_profile.json", "stage_distributions.json"],
        "reused": ["frozen FreshnessClock / CommitActuateJournal / replay writer (timers only)"],
        "progress": ["Timing Runtime-Context plane", "Timing Replay plane",
                     "Deriving per-stage distributions"],
        "paper": ["fig_runtime_breakdown.svg"],
        "paper_sections": ["IX (overhead)"],
        "tables_produced": [],
        "figures_produced": ["fig_runtime_breakdown.svg"],
        "metrics_produced": ["Runtime-Context plane ms/row + % of end-to-end",
                            "Replay plane ms/row + % of end-to-end", "Full pipeline ms/row",
                            "End-to-end incl. replay ms/row",
                            "Per-stage count/mean/median/std/q3/max from recorded traces"],
        "outputs": ["experiments/profiling/runtime_profile.json",
                    "experiments/profiling/stage_distributions.json",
                    "experiments/profiling/summary.md", "experiments/profiling/metadata.json",
                    "experiments/profiling/REPRODUCE.md", "experiments/profiling/logs/E6.log"],
        "interpretation": ("The plane percentages are shares of a synthetic 5,000-row pipeline on this host, "
                           "not of a production workload. Per-stage figures come from recorded AgentDojo "
                           "traces and are descriptive statistics: q3 and max are reported as such, NOT "
                           "relabelled as p95/p99, because the raw sample vectors needed for true "
                           "percentiles are not persisted."),
    },
    "E7": {
        "num": "7/8", "key": "agentdojo",
        "title": "AgentDojo Runtime Governance",
        "purpose": ("Test the guard on a third-party adversarial benchmark. Every real prompt-injection "
                    "attack target is submitted straight to the frozen boundary (no LLM needed) to "
                    "measure whether any genuinely-foreign attacker target is ever permitted, and "
                    "recorded episodes are re-analyzed for permit/deny/stability/overhead."),
        "question": "Does the guard stay sound on an external, author-independent adversarial corpus?",
        "motivation": ("Results on a corpus the authors mapped themselves are weak evidence of "
                       "generalisation. AgentDojo is an external benchmark with attacks the authors did "
                       "not design, which makes a zero false-permit result on its attacker targets a "
                       "genuinely independent soundness measurement."),
        "why_exists": ("Answers the strongest reviewer objection: that L-DREA is tuned to ULB."),
        "reviewer": {"id": "R8", "quote": "Results may not generalize beyond the authors' own dataset.",
                     "comment": "Comment #7"},
        "benchmark": ["AgentDojo (workspace, banking, slack, travel)"],
        "input": ["Adversarial corpus : 27 injection tasks across 4 suites",
                  "Recorded episodes : 33 (permit/deny re-derivation, no LLM)",
                  "Boundary probe : every attacker target adjudicated by the frozen engine"],
        "calculated": ["Boundary FPR on genuinely-foreign targets", "Recognized-identifier sends",
                       "Permit rate + Wilson CI (recorded)", "Authorization stability", "Gamma overhead"],
        "loaded": ["33 recorded AgentDojo episodes", "frozen tool/predicate manifests"],
        "generated": ["boundary_fpr.json", "statistics.json", "decisions.csv"],
        "reused": ["recorded episodes (no fresh LLM calls)"],
        "progress": ["Re-deriving metrics from recorded episodes", "Adjudicating attacker targets",
                     "Computing boundary FPR"],
        "paper": ["Table I (boundary FPR)", "fig_false_permit_rate.svg"],
        "paper_sections": ["IX-E (external validation)", "Table I (boundary FPR)"],
        "tables_produced": ["table1_primary_metrics.md"],
        "figures_produced": ["fig_false_permit_rate.svg"],
        "metrics_produced": ["Boundary FPR on genuinely-foreign attacker targets + Wilson 95%",
                            "Recognized-identifier sends (correct-by-policy)",
                            "All-gated-actions FPR (unfiltered, see caveat)",
                            "Per-suite and per-target-type breakdown",
                            "Permit / denial rate + Wilson CI over recorded episodes",
                            "Authorization stability", "Decision entropy",
                            "Γ decision overhead (descriptive stats)", "Predicate + tool frequency"],
        "outputs": ["experiments/agentdojo/boundary/boundary_fpr.json",
                    "experiments/agentdojo/statistics.json", "experiments/agentdojo/decisions.csv",
                    "experiments/agentdojo/predicates.csv", "experiments/agentdojo/summary.md",
                    "experiments/agentdojo/metadata.json", "experiments/agentdojo/REPRODUCE.md"],
        "interpretation": ("soundness_foreign_targets.FPR is THE soundness figure: attacker-chosen targets "
                           "that are genuinely foreign to the user's environment. The higher "
                           "all_gated_actions FPR is NOT a failure — it counts sends to identifiers the "
                           "policy already recognises (the user's own contacts), which are correct-by-policy "
                           "permits. Fresh end-to-end Utility / attack-success-rate numbers are BLOCKED on a "
                           "missing LLM backend and are reported as such, never substituted."),
        "blocked_note": "Fresh end-to-end episodes (Utility / attack-success rate) require Ollama + "
                        "llama3.1:8b and are the one documented BLOCKED item; the boundary FPR runs "
                        "without an LLM.",
    },
    "E8": {
        "num": "8/8", "key": "robustness",
        "title": "Runtime Robustness (Fault Injection)",
        "purpose": ("Inject 16 realistic runtime faults — missing/delayed/corrupted/conflicting "
                    "predicates, stale context, clock skew, replay/ledger corruption, reordering, "
                    "duplication, timeouts, partial failure, races — ONLY into the harness, and confirm "
                    "safety still holds: decision-path faults fail closed, integrity faults are detected."),
        "question": "Do safety properties survive when the runtime environment misbehaves?",
        "motivation": ("Real deployments do not present clean inputs. A guard whose safety depends on its "
                       "environment behaving correctly has merely relocated the trust assumption. Faults "
                       "are injected into the harness only; the engine and the verifier are untouched, so "
                       "the result measures the engine's response, not a modified engine."),
        "why_exists": ("Distinguishes fail-closed behaviour (decision-path faults must yield SAFE_STATE) "
                       "from tamper-evidence (integrity faults must be DETECTED, not silently tolerated)."),
        "reviewer": {"id": "R9", "quote": "Behaviour under faults / adversarial runtime conditions is "
                     "not evaluated.", "comment": "Comment #8"},
        "benchmark": ["Synthetic Fault-Injection Suite (16 families)"],
        "input": ["Fault families : 16 (11 decision-path, 5 integrity/ordering)",
                  "Engine + verifier : UNCHANGED; faults injected only into the harness input"],
        "calculated": ["False permits per fault family (must be 0)", "SAFE_STATE rate",
                       "Corruption-detection rate", "Per-family safety verdict"],
        "loaded": ["a slice of the real ledger (for integrity-fault tests)"],
        "generated": ["robustness.json", "robustness.csv", "robustness_log.jsonl"],
        "reused": ["frozen evaluate_decision + stable gamma_replay_verify"],
        "progress": ["Control: clean proposal permits?", "Injecting decision-path faults",
                     "Injecting integrity/ordering faults", "Verifying safety holds"],
        "paper": ["Table III (robustness)", "fig_robustness.svg"],
        "paper_sections": ["IX (Experiment 8 — robustness)", "Table III"],
        "tables_produced": ["table3_robustness.md"],
        "figures_produced": ["fig_robustness.svg"],
        "metrics_produced": ["False permits per fault family", "SAFE_STATE count per family",
                            "Actuations flagged unauthorized", "Corruption detection per integrity family",
                            "Per-family safety verdict", "Aggregate false permits across all faults"],
        "outputs": ["experiments/robustness/robustness.json", "experiments/robustness/robustness.csv",
                    "experiments/robustness/robustness_log.jsonl", "experiments/robustness/summary.md",
                    "experiments/robustness/metadata.json", "experiments/robustness/REPRODUCE.md"],
        "interpretation": ("The control row matters: a clean proposal must still PERMIT, otherwise "
                           "'0 false permits' would be trivially achieved by denying everything. Mechanism A "
                           "and C families must fail closed (SAFE_STATE); mechanism B families must be "
                           "DETECTED by the independent verifier. Trial counts are small (51 total), so the "
                           "Wilson upper bound — not the point estimate of 0 — is the defensible claim."),
    },
    "E9": {
        "num": "9/10", "key": "coverage",
        "title": "Runtime Predicate Coverage & Single-Deficit Isolation",
        "purpose": ("Drive the frozen engine with a deterministic synthetic suite in which every "
                    "runtime predicate is falsified exactly once, in isolation, while all others "
                    "concur. Establishes that each predicate is correctly wired into the decision "
                    "and that a single deficit denies even when nine predicates agree."),
        "question": "Is every runtime predicate exercised, and does each one alone deny?",
        "motivation": ("E1 adjudicates the real ULB corpus, but that corpus only ever falsifies four "
                       "of the thirteen runtime predicates; the rest are TRUE on all 284,807 rows, so "
                       "their runtime behaviour is never exercised. E3 closes the gap formally by "
                       "comparing an independent reference function against the engine over the whole "
                       "2^16 abstraction, but it does not drive the engine's own runtime path. E9 "
                       "closes it empirically, on the engine itself."),
        "why_exists": ("Converts a documented coverage limitation of the evaluation into a measured "
                       "result, without touching the engine and without altering any E1 metric. It is "
                       "also the sharpest possible per-predicate test of non-compensatory soundness: "
                       "one deficit, nine concurring predicates, must still deny."),
        "reviewer": {"id": "R3", "quote": "Correctness rests on testing, not formal guarantees.",
                     "comment": "Comment #3 (coverage aspect)"},
        "benchmark": ["Deterministic synthetic predicate-isolation suite"],
        "input": ["Cases : 23 synthetic proposals (1 control + 10 node gates + 3 derived deficits "
                  "+ 2 class-veto tokens + 4 ISB conjuncts + 3 Eq.7 checks)",
                  "Engine : gamma_test_runner.evaluate_decision (frozen, imported not modified)",
                  "theta = 0.5; no randomness, no seed required"],
        "calculated": ["Predicate coverage rate", "Per-predicate single-deficit denial + Wilson CI",
                       "Class-veto isolation (Gamma_G = 0 yet deny)", "ISB conjunct isolation",
                       "Eq.7 unauthorized-execution detection (with negative control)",
                       "Per-case adjudication latency"],
        "loaded": [],
        "generated": ["predicate_coverage.json", "predicate_coverage.csv", "predicate_coverage_log.jsonl"],
        "reused": ["the frozen evaluate_decision entry point"],
        "progress": ["Building the clean control proposal", "Falsifying each node gate in isolation",
                     "Triggering each derived deficit in isolation", "Isolating the class-level veto",
                     "Isolating each ISB conjunct", "Checking Eq.7 detection + its negative control"],
        "paper": ["Table IV (predicate coverage)", "fig_predicate_coverage.svg"],
        "paper_sections": ["IX (Experiment 9 — predicate coverage)", "Table IV"],
        "tables_produced": ["table4_predicate_coverage.md"],
        "figures_produced": ["fig_predicate_coverage.svg"],
        "metrics_produced": ["Predicate coverage rate (covered / total)",
                            "Single-deficit denial rate + Wilson 95% CI",
                            "Class-veto denials with Gamma_G = 0",
                            "ISB conjuncts driving ISB to 0",
                            "Eq.7 cases passed (incl. clean-actuated negative control)",
                            "Per-case latency min/mean/median/max"],
        "outputs": ["experiments/predicate_coverage/predicate_coverage.json",
                    "experiments/predicate_coverage/predicate_coverage.csv",
                    "experiments/predicate_coverage/predicate_coverage_log.jsonl",
                    "experiments/predicate_coverage/summary.md",
                    "experiments/predicate_coverage/metadata.json",
                    "experiments/predicate_coverage/REPRODUCE.md"],
        "interpretation": ("100% predicate coverage here means every predicate is observed in both "
                           "polarities against the real engine, and each alone denies. It does NOT mean "
                           "the ULB corpus exercises them — that remains a disclosed limitation of E1, "
                           "and the two facts are reported separately. The clean-proposal control is "
                           "load-bearing: without it, an engine that denied everything would score 100%. "
                           "The class-veto cases are the Goodhart-resistance result: Gamma_G = 0, every "
                           "node gate concurs, and the action is still denied."),
    },
    "E10": {
        "num": "10/10", "key": "audit_bundle",
        "title": "Audit Bundle Export (ConcurBench Level 4)",
        "purpose": ("Package every executed artifact into a self-describing, checksummed bundle that a "
                    "third party can verify without this repository's source tree and without the "
                    "dataset, and bind that bundle cryptographically to the live ledger."),
        "question": "Can the execution evidence leave this machine and still be verifiable?",
        "motivation": ("Auditability that cannot be exported is auditability that only the authors can "
                       "exercise. ConcurBench Level 4 tests exactly this, and the check had never been "
                       "satisfiable because no bundle exporter existed."),
        "why_exists": ("Closes a standing engineering FAIL. `audit_packet_export` was a bare "
                       "directory-existence test that nothing in the repository ever satisfied. The "
                       "export is now implemented, and the check was strengthened at the same time: it "
                       "re-hashes every member from its bytes and confirms the recorded ledger digest "
                       "still matches the live ledger. An empty or tampered bundle FAILS."),
        "reviewer": {"id": "R2", "quote": "Replay determinism / evidence integrity is not proven.",
                     "comment": "Comment #2 (exportability aspect)"},
        "benchmark": ["ConcurBench Level 4 — replay & auditability"],
        "input": ["Artifacts : E1-E9 executed outputs, provenance graph, statistics report",
                  "Ledger    : gamma_replay_manifest.jsonl (digest-referenced; anchor + terminus embedded)",
                  "Formal    : ExternalizationMonitor.tla/.cfg + the executed TLC log"],
        "calculated": ["SHA-256 of every bundle member", "Bundle id over member digests",
                       "Ledger digest binding (recorded vs live)", "Member-digest re-verification"],
        "loaded": ["all executed experiment artifacts"],
        "generated": ["gamma_bundle/MANIFEST.json", "gamma_bundle/CHECKSUMS.sha256",
                      "gamma_bundle/VERIFY.md", "audit_bundle_report.json"],
        "reused": ["the artifacts produced by E1-E9 (packaged, never recomputed)"],
        "progress": ["Copying evidence + reproducibility + replay + formal members",
                     "Hashing every member", "Writing MANIFEST + CHECKSUMS + VERIFY",
                     "Re-scoring ConcurBench Level 4 against the bundle",
                     "Re-exporting so the bundle carries the final report",
                     "Self-verification (re-hash all members, bind to live ledger)"],
        "paper": ["ConcurBench Level 4"],
        "paper_sections": ["IX (auditability)", "ConcurBench Level 4"],
        "tables_produced": [],
        "figures_produced": [],
        "metrics_produced": ["Bundle members present / missing", "Members verified",
                            "Ledger digest match (recorded vs live)", "ConcurBench Level-4 verdict",
                            "Bundle id", "Total bundle bytes"],
        "outputs": ["experiments/audit_bundle/audit_bundle_report.json",
                    "experiments/audit_bundle/summary.md",
                    "experiments/audit_bundle/metadata.json",
                    "experiments/audit_bundle/REPRODUCE.md",
                    "gamma_bundle/MANIFEST.json", "gamma_bundle/CHECKSUMS.sha256",
                    "gamma_bundle/VERIFY.md"],
        "interpretation": ("A PASS means the bundle is internally consistent (every member re-hashes) "
                           "and externally bound (its recorded ledger digest matches the live ledger). "
                           "It does NOT mean a third party has audited the evidence — only that they "
                           "now can, offline. The bundle contains executed artifacts only; the 430 MB "
                           "dataset is identified by SHA-256, not copied. The 192 MB ledger is "
                           "digest-referenced with its GENESIS anchor and chain terminus embedded; "
                           "`--full` embeds it entirely. ConcurBench's report is packaged into the "
                           "bundle it verifies; that self-reference is disclosed in MANIFEST.json."),
    },
}

# Benchmarks shown in the final dashboard (label -> which experiment/verdict source)
BENCHMARKS = [
    ("LAB v1.0", "E1"), ("ConcurBench", "E1"), ("FULL_SPEC", "E1"), ("Fail-Closed Rate", "E1"),
    ("Formal Verification", "E3"), ("Concurrency Scaling", "E4"), ("Component Ablation", "E5"),
    ("Runtime Profiling", "E6"), ("AgentDojo", "E7"), ("Fault Injection", "E8"),
    ("Predicate Coverage", "E9"), ("Audit Bundle Export", "E10"),
]

# Runtime rules / invariants shown in the dashboard, mapped to the lab report invariant keys.
RUNTIME_RULES = [
    ("Execution Sovereignty", "I1_execution_sovereignty"),
    ("Non-Bypassability", "I2_non_bypassability"),
    ("Non-Compensatory Soundness", "I3_non_compensatory_soundness"),
    ("Class-Level Veto Adequacy", "I4_class_level_veto"),
    ("TOCTOU State-Consistency", "I5_toctou_state_consistency"),
    ("Runtime Sovereignty (composed)", "I6_runtime_sovereignty"),
]

# ---------------------------------------------------------------------------------------------
# Descriptive context for the per-component ablation report (Part 7). The leak counts, rates and
# Wilson bounds are read live from ablation.json — only the prose lives here.
ABLATION_COMPONENTS = {
    "baseline_full_LDREA": {
        "removed": "nothing (reference configuration)",
        "reason": "Establishes the denial baseline every other configuration is differenced against.",
        "meaning": "All controls active. Any permit here is a true permit by construction of the workload.",
        "claim": "C10", "reviewer": "R6",
    },
    "remove_class_veto": {
        "removed": "class-level veto (Γ_class)",
        "reason": ("The class veto forces SAFE_STATE whenever a class-1 / Goodhart reason code is present, "
                   "independent of the node-gate scores. Removing it tests whether the node gates alone "
                   "would have caught those actions."),
        "meaning": ("Leaked permits are actions that only the class veto was stopping — the node gates "
                    "scored them acceptable. This is the non-redundancy evidence for Γ_class."),
        "claim": "C10", "reviewer": "R6",
    },
    "remove_noncompensatory_gamma": {
        "removed": "non-compensatory Γ aggregation (max-deficit rule)",
        "reason": ("Replaces Γ = max(1-gᵢ) with a compensatory weighted sum, so a strong score on one "
                   "predicate can mask a deficit on another."),
        "meaning": ("Leaked permits quantify exactly the masking that compensatory aggregation permits. "
                    "This is the causal evidence for the non-compensatory design choice."),
        "claim": "C10", "reviewer": "R6",
    },
    "remove_authorization_layer": {
        "removed": "the authorization layer entirely",
        "reason": "The degenerate control: no guard at all. Upper-bounds the leakage the layer prevents.",
        "meaning": ("Every action the workload proposes is externalized. The gap between this and baseline "
                    "is the total safety contribution of L-DREA on this workload."),
        "claim": "C10", "reviewer": "R6",
    },
}

# How ablation severity is expressed. Stated explicitly so it is auditable and can never be mistaken
# for an independently measured quantity. Note what is deliberately absent: no LOW/MODERATE/HIGH
# label, because impact severity is a judgement this experiment does not measure.
ABLATION_SEVERITY_RULE = (
    "Severity is reported as two arithmetic facts derived from the ablation's own measured leak "
    "rates: (1) the ordinal RANK of this configuration among the ablated ones, and (2) the leak "
    "rate as a share of the no-guard upper bound (removing the authorization layer entirely). "
    "No LOW/MODERATE/HIGH label is emitted — that would encode an operational-impact judgement "
    "which this experiment does not measure.")

# Fault-injection mechanism legend (Part 8). Mechanism codes come from robustness.json.
FAULT_MECHANISMS = {
    "A": ("decision-path", "Fault corrupts the engine's input. Required behaviour: fail closed "
                           "(SAFE_STATE, actuation flagged unauthorized). Measured by false permits."),
    "B": ("integrity/ordering", "Fault tampers with the evidence chain. Required behaviour: the "
                                "independent verifier DETECTS the break. Measured by corruption_detected."),
    "C": ("temporal", "Fault violates the freshness bound. Required behaviour: stale context forces "
                      "SAFE_STATE. Measured by false permits."),
}

PAPER_VERSION = "L-DREA R4 (IEEE Access) — Tier-S reference framing"
REVIEWER_PROFILE = "IEEE Access reviewers R1-R11 (see reviewer_mapping.md)"
