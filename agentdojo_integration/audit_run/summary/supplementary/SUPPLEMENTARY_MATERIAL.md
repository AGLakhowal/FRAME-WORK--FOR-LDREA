# Supplementary Material — L-DREA × AgentDojo × Gamma Runtime Audit

## S1. Runtime architecture

AgentDojo drives an LLM agent; every candidate tool call is intercepted at the sole chokepoint `FunctionsRuntime.run_function` by the frozen `GammaGovernedRuntime`. Read-only tools pass through; externally-effective actions (EEAs) are adjudicated by the reused Gamma engine (`gamma_test_runner.evaluate_decision`) via a two-layer manifest binding.
- Frozen scientific root: `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618`
- Frozen binding sha: `a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1`
- Method version: `gamma_test_runner/LAB-v1.0/2.0`

## S2. Γ and Π equations

```
deficit_i = 1  iff predicate i fails its threshold directive (binary)
Γ_global  = max_i deficit_i          # non-compensatory / OR aggregation (Law of Concurrence)
Γ_class   = 1 iff ReasonCodes ∈ {CLASS_1, GOODHART}   # class-level veto
Π         = 1 iff (Γ_global == 0 ∧ Γ_class == 0)
decision  = PERMIT if Π == 1 else SAFE_STATE          # fail-closed
```

## S3. Event definitions

| event_type | meaning |
|---|---|
| `LLM_REQUEST` | A chat-completion request is issued to the model. |
| `LLM_RESPONSE` | The model's response (finish reason, text, tool calls). |
| `TOOL_CALL_PROPOSED` | The agent proposes a tool call (candidate action). |
| `GAMMA_INTERCEPT` | L-DREA intercepts the candidate at FunctionsRuntime.run_function. |
| `PREDICATE_EXTRACTION` | Per-family evidence extraction from the environment/action. |
| `PREDICATE_EVALUATION` | Per-family deficit (0/1) and evaluation status. |
| `GLOBAL_POLICY_EVALUATION` | Node-gate / max-aggregation deficit layer (Γ_global). |
| `CLASS_POLICY_EVALUATION` | Class-veto layer (Γ_class). |
| `Γ COMPUTATION` | Law-of-Concurrence quantities Γ_global, Γ_class. |
| `Π COMPUTATION` | Permission indicator Π. |
| `PERMIT_DECISION` | Authorization = PERMIT (Π=1). |
| `DENY_DECISION` | Authorization = SAFE_STATE (Π=0), fail-closed. |
| `TOOL_EXECUTION` | The tool executes (PERMIT) or is blocked (SAFE_STATE). |
| `TOOL_RESULT` | Tool success/error and returned value preview. |
| `OBSERVATION_RETURNED` | Observation content hash + size returned to the agent. |
| `LLM_NEXT_CONTEXT` | Conversation length / appended tool outputs for the next turn. |
| `EPISODE_FINISHED` | Episode end with AgentDojo utility and security. |

## S4. Predicate definitions (families)

Predicate families are read from the frozen manifests (Layer 1) and bound per tool by the Execution Binding Manifest (Layer 2). Recognized-set (recipient recognition) families are membership predicates over env-derived sets; amount families are env_upper_bound; structural families are reported `EXCLUDED_BY_POLICY_TIER_S`; `GAMMA` is the aggregator (not a node predicate). Deficits are the only inputs to Γ.

## S5. Methodologies

- **Validation:** for a fixed candidate action the authorization layer is deterministic (DET-1); the traced runtime's decisions are compared byte-for-byte against a clean uninstrumented `GammaGovernedRuntime` replay and against re-derivation from recorded deficits.
- **Replay:** `ReplayEngine` consumes only `execution_trace.jsonl` and re-derives Γ/Π/decision from recorded predicate deficits, with no AgentDojo/LLM/frozen-runtime interaction.
- **Proof:** each authorization emits a chain Predicate→Deficit→Γ_global→Γ_class→Π→Authorization→Execution→Environment→Evidence→Replay→Verification.
- **Integrity:** frozen files are SHA256-snapshotted before/after each episode; traces are hash-chained (append-only, tamper-evident) with event-order and timestamp checks.

## S6. Artifact description & directory layout

```
trace/<suite>/<user_task>__<injection_task>/
    execution_trace.jsonl        # append-only event log (authoritative)
    execution_trace.csv          # flat core columns
    execution_summary.json       # per-episode summary
    execution_graph.json         # event graph
    episode_timeline.md          # timeline + embedded Mermaid sequence
    episode_sequence.mmd         # standalone Mermaid
    decision_tree.json / predicate_log.json / gamma_log.json
    authorization_log.json / tool_execution_log.json / llm_messages.json
    validation_report.json       # deterministic non-invasiveness proof
    frozen_integrity.json / trace_integrity.json
summary/
    statistics.json / statistics_tables.md / decisions.csv / predicates.csv
    reviewer/episodes/*.md + MASTER_REPORT.md
    proofs/*.md + *.json + all_proofs.json
    figures/*.svg + figures/csv/*.csv + dashboard.html
    graphs/*.dot + *.mmd + explorer.html
    BENCHMARK_SUMMARY.md/json + supplementary/
```

## S7. Reproduction instructions

```bash
export LOCAL_LLM_PORT=11434   # Ollama serving llama3.1:8b
agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py \
    --suites workspace banking --max-user-tasks 3 --outdir agentdojo_integration/audit_run
```

## S8. Limitations

- Local-model non-determinism (temperature 0) ⇒ episode utility/security vary; the authorization layer is deterministic given a fixed candidate action.
- Ground-truth per-action labels are absent, so false-permit/deny rates are reported null.
- Reported corpus is a bounded batch; full-corpus scaling is runtime-budget only.