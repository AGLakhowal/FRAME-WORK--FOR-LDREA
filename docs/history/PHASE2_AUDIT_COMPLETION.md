# Phase 2 — Scientific Audit Framework: Completion Report

**Date:** 2026-07-09
**Nature:** fully additive. No modification to AgentDojo, the frozen interception package
(`GammaGovernedRuntime`, `GammaBridge`, `PredicateEvaluator`, `ScientificPolicy`, `ExecutionBinding`),
`gamma_test_runner.evaluate_decision`, `run_benchmark.py`, the execution tracer, prompts, attacks,
tasks, or scoring. The existing single-episode tracer continues to work unchanged.
**Frozen-integrity check:** 19 frozen files SHA256-verified **unchanged** across the run (0 changed).

---

## 1. New files (14 — all additive)

| File | Phase | Role |
|---|---|---|
| `agentdojo_integration/audit/__init__.py` | — | package |
| `agentdojo_integration/audit/_util.py` | — | hashing / JSON / Wilson / bootstrap / descriptive stats (numpy) |
| `agentdojo_integration/audit/integrity.py` | H | frozen SHA256 snapshots + trace hash-chain / tamper / ordering checks |
| `agentdojo_integration/audit/replay_engine.py` | D | `ReplayEngine`: reconstruct + re-derive Γ/Π/decision from `execution_trace.jsonl` only |
| `agentdojo_integration/audit/stats_engine.py` | B | multi-episode statistics + Wilson/bootstrap CIs; CSV/JSON/MD/tables |
| `agentdojo_integration/audit/batch_runner.py` | A | batch/resume/organized multi-episode trace collection |
| `agentdojo_integration/audit/reviewer_reports.py` | C | per-episode + master human-readable audit reports |
| `agentdojo_integration/audit/proof_generator.py` | E | per-authorization scientific proof chains (MD + JSON) |
| `agentdojo_integration/audit/visualize.py` | F | Mermaid / Graphviz DOT / interactive explorer HTML |
| `agentdojo_integration/audit/dashboard.py` | G | dependency-free SVG figures + CSV source + dashboard HTML |
| `agentdojo_integration/audit/summary.py` | I | benchmark-wide summary + conclusions/limitations/reproducibility |
| `agentdojo_integration/audit/supplementary.py` | J | IEEE Access supplementary material + JSON/CSV schemas |
| `agentdojo_integration/audit/tests/test_audit.py` | — | 21 unit tests for the deterministic modules (no LLM) |
| `agentdojo_integration/run_audit.py` | orchestrator | runs A→J end-to-end + completion report |

## 2. Executed run (genuine, bounded batch — real data only)

12 real episodes under `agentdojo_integration/audit_run/` (6 read-only tasks + 6 EEA-inducing tasks:
workspace calendar mutations, banking `send_money`). **5 Gamma authorization decisions** were exercised
and audited: **4 PERMIT, 1 SAFE_STATE**.

- `send_money` → PERMIT ×2 (recognized IBAN, all gates pass, Π=1)
- `reschedule_calendar_event` → PERMIT ×2
- `add_calendar_event_participants` → **SAFE_STATE ×1** (`GATE_recipient_recognition` deficit=1, Γ_global=1, Π=0)
- Permit rate (Wilson 95%): **0.80 [0.376, 0.964]**, n=5
- Policy utilization: FUNDS_TRANSFER 2, CALENDAR_MUTATION 3
- **Gamma-decision overhead: mean 0.0153 ms** (median 0.0135, max 0.0262) — sub-millisecond, cleanly
  separated from ~2.1 s mean LLM latency. This is the real runtime cost of the authorization boundary.
- Decision entropy 0.722 bits; authorization stability 1.0 (each tool-class group unanimous).

## 3. Generated artifacts (all from real execution)

Per episode (`audit_run/trace/<suite>/<task>__<injection>/`): `execution_trace.jsonl` (+ chained
sidecar), `.csv`, `execution_summary.json`, `execution_graph.json`, `episode_timeline.md`,
`episode_sequence.mmd`, `decision_tree.json`, `predicate_log.json`, `gamma_log.json`,
`authorization_log.json`, `tool_execution_log.json`, `llm_messages.json`, `validation_report.json`,
`frozen_integrity.json`, `trace_integrity.json`, `replay_report.json`.

Benchmark-wide (`audit_run/summary/`): `statistics.json`, `statistics_tables.md`, `decisions.csv`,
`predicates.csv`; `reviewer/MASTER_REPORT.md` + `reviewer/episodes/*`; `proofs/*.md|json` +
`all_proofs.json`; `figures/*.svg` (6) + `figures/csv/*`; `graphs/*.dot|*.mmd`; `dashboard.html`,
`explorer.html`; `BENCHMARK_SUMMARY.md|json`; `supplementary/SUPPLEMENTARY_MATERIAL.md` +
`trace_event.schema.json` + `csv_schema.json`; `frozen_integrity.json`, `trace_integrity_all.json`,
`replay_validation.json`; `COMPLETION_REPORT.md|json`; `batch_manifest.json`.

## 4. Validations performed (all PASS)

| Validation | Result | Evidence |
|---|---|---|
| Unit tests (deterministic core) | **21/21 PASS** | `test_audit.py` (Wilson, bootstrap determinism, entropy, hash-chain determinism + tamper detection, replay re-derivation + inconsistency flagging, stats) |
| Full benchmark execution | 6/6 completed, 0 errors | `batch_manifest.json` |
| Traces generated | 12 episodes | `trace/**` |
| Replay generated + verified | all consistent | `replay_validation.json` (ReplayEngine re-derives Γ_global=OR(deficits), Π, decision from jsonl only) |
| Authorization replay identical (traced vs clean runtime) | True | per-episode `validation_report.json` |
| Statistics generated | real, no fabrication | `statistics.json` |
| Reviewer reports | 12 episodes + master | `reviewer/` |
| Proofs consistent | all consistent | `all_proofs.json` |
| Supplementary material | generated | `supplementary/` |
| Frozen integrity | **19 files unchanged** | `frozen_integrity.json` |
| Trace integrity (hash-chain, ordering, timestamps) | all OK | `trace_integrity_all.json` |

## 5. Scientific integrity guarantees

- **No fabricated statistics.** Every value derives from recorded events. Metrics needing external
  ground-truth labels (`false_permit_rate`, `false_deny_rate`) are reported **null with an explicit
  reason**, never invented.
- **No mocked runtime values.** Γ/Π/deficits come from the frozen engine via the tracer; the audit
  layer only reads them and independently *re-derives* them for verification.
- **Tamper-evident.** Traces are hash-chained; the tests prove a single flipped field changes the
  chain root, and that an internally inconsistent trace is flagged by the ReplayEngine.

## 6. Limitations & future work

- **Local-model non-determinism** (`llama3.1:8b`, temp 0): episode utility/security and *which* tasks
  emit an EEA vary run-to-run. The authorization layer is deterministic given a fixed candidate action
  (validated). Consequently the demo corpus mixes episodes with and without adjudications.
- **Bounded corpus.** The executed batch is 12 episodes (5 adjudications); scaling to the full
  AgentDojo corpus is a **runtime-budget** matter and needs no code change — `run_audit.py` supports
  `--suites`, `--max-user-tasks`, `--episodes`, and **resume**.
- **Figures are SVG (+CSV source).** matplotlib/scipy/graphviz are absent in this environment, so
  figures are hand-rolled SVG (vector master) and DOT/Mermaid text; PNG/PDF are derivable from SVG via
  any converter (not fabricated here). CIs use closed-form Wilson + numpy bootstrap (no scipy).
- **Ground-truth labels** for per-action correctness would enable true FPR/FDR; currently out of scope.
- **Parallel execution** is implemented as safe sequential by default (shared Ollama server) to
  preserve reproducibility; a worker pool can be added if a concurrent server is available.

## 7. Reproduction

```bash
export LOCAL_LLM_PORT=11434   # Ollama serving llama3.1:8b
agentdojo_integration/.venv/bin/python agentdojo_integration/audit/tests/test_audit.py   # unit tests
agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py \
    --episodes workspace:user_task_6 workspace:user_task_7 workspace:user_task_8 \
               workspace:user_task_20 banking:user_task_3 banking:user_task_4 \
    --outdir agentdojo_integration/audit_run
```

**Final status: PHASE 2 COMPLETE — all phases (A–J) implemented additively, executed on genuine data,
and validated. No frozen component modified. No values fabricated.**
