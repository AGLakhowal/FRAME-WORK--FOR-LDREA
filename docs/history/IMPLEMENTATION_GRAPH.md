# IMPLEMENTATION_GRAPH.md

**Phase 3 — Part F: implementation dependency graph.**
Every edge below was confirmed from actual `import` statements / call sites (read-only).

---

## F1. Runtime authorization dataflow (AgentDojo → Decision → Evidence)

```mermaid
flowchart TD
    ADJ["AgentDojo agent + task suite"] -->|tool call| RF["GammaGovernedRuntime.run_function()<br/>governed_runtime.py:50"]
    RF -->|classify| SP["ScientificPolicy.classify()<br/>frozen_policy.py:74<br/>(7 frozen manifests, root ce8c8467…)"]
    SP -->|mediated? eea_class? families?| RF
    RF -->|unknown class| DENYU["_deny → SAFE_STATE<br/>(fail closed, Def 2i / §0.10)"]
    RF -->|not mediated| PASS["super().run_function()<br/>read-only passthrough (Def 1)"]
    RF -->|mediated: families,args,env| PE["PredicateEvaluator.evaluate()<br/>predicate_evaluation.py:120"]
    PE -->|reads status/threshold| EB["ExecutionBinding<br/>execution_binding.py<br/>(binding sha a3861927…)"]
    PE -->|deficits {family:0/1}| BR["GammaBridge.decide()<br/>gamma_bridge.py:30"]
    BR -->|family→gamma_slot| EB
    BR -->|engine row| ED["evaluate_decision()<br/>gamma_test_runner.py:133<br/>(THE single LLC engine)"]
    ED -->|Γ_G, Γ_class, Π, decision| BR
    BR --> DEC{"decision == PERMIT ?"}
    DEC -->|PERMIT| EXEC["super().run_function() → execute"]
    DEC -->|SAFE_STATE| DENYM["_deny → SAFE_STATE denial"]
    RF -->|append per decision| LOG["gamma_decisions[] evidence log<br/>governed_runtime.py:57,69"]
    LOG --> EEB["Execution Evidence Bundle<br/>runtime_context/execution_evidence_bundle.py"]
```

**Key architectural facts (verified):**
- `gamma_bridge.py:19` — `evaluate_decision = _gamma.evaluate_decision` (imported, **not** reimplemented).
- `ScientificPolicy` and `ExecutionBinding` are **injected** into `GammaGovernedRuntime.__init__` (dependency inversion; `governed_runtime.py:32-38`).
- Provenance chain: `ExecutionBinding.derived_from_scientific_root` must equal `ScientificPolicy` root `ce8c8467…` or load fails.

## F2. Batch / benchmark + replay + paper-tables dataflow

```mermaid
flowchart TD
    CSV["GAMMA_G0_CREDITCARD_FULL_mapped.csv<br/>284,807 rows"] --> RB["run_benchmark()<br/>gamma_test_runner.py"]
    RB -->|vectorized LLC :914-947| DER["DerivedGammaG / GammaClass / Pi / Decision / ISB"]
    DER -->|Eq.7 :977-987| UNA["DerivedUnauthorized"]
    DER --> INV["6 runtime invariants :1028-1032…"]
    DER --> METR["LAB v1.0 metrics + Wilson CIs"]
    DER --> RM["gamma_replay_manifest.jsonl<br/>(hash-chained, per row)"]
    RM --> RV["gamma_replay_verify.py<br/>replay determinism"]
    METR --> SUM["gamma_summary.json / gamma_lab_v1_report.json"]
    SUM --> HTML["gamma_report.html (dashboard)"]
    SUM --> TBL["IEEE_TABLES_FINAL.md / paper tables"]
    RB -.single-row twin.-> ED["evaluate_decision() :133<br/>(timed latency path; same LLC)"]
    FSC["full_spec_conformance.py"] -->|§7.1 bands, AIS, 3-signal| FSCR["full_spec_conformance_report.json<br/>verdict: FULL_SPEC_CONFORMANT (Tier-S)"]
```

## F3. Verification overlay (this Phase-3 package)

```mermaid
flowchart LR
    PAPER["Paper eqs / README §7-§8"] --> IV["independent_verifier.py<br/>(from-scratch reimpl)"]
    IV -->|oracle only| ED["evaluate_decision()"]
    IV --> IVR["independent_verifier_report.json<br/>65,536 states · 0 mismatch"]
    ED --> IVR
    IVR --> D["STATE_SPACE_VERIFICATION.md"]
    IVR --> H["AUTHORIZATION_PROOF_REPORT.md"]
    IVR --> I["INDEPENDENT_VERIFIER_REPORT.md"]
```

## F4. Module import graph (interception package — verified from `import` lines)

```mermaid
flowchart TD
    GR["governed_runtime.py"] --> FP["frozen_policy.py (ScientificPolicy)"]
    GR --> EBm["execution_binding.py (ExecutionBinding)"]
    GR --> GB["gamma_bridge.py (GammaBridge)"]
    GR --> PEm["predicate_evaluation.py (PredicateEvaluator)"]
    GR --> ADR["agentdojo.functions_runtime.FunctionsRuntime"]
    EBm --> FP
    GB --> GTR["gamma_test_runner.py (evaluate_decision, NODE_GATE_COLS, METHOD_VERSION)"]
    PEm --> EBm
```

## F5. Linear dependency spine (as requested by the prompt)

```
AgentDojo
  → GammaGovernedRuntime.run_function            (governed_runtime.py:50)
    → ScientificPolicy.classify                  (frozen_policy.py:74)     [7 frozen manifests]
    → PredicateEvaluator.evaluate                (predicate_evaluation.py:120)
      → ExecutionBinding (status/threshold/slot)  (execution_binding.py)
    → GammaBridge.decide                         (gamma_bridge.py:30)
      → evaluate_decision                        (gamma_test_runner.py:133)   [THE engine]
        → Γ_G, Γ_class, Π → decision
    → PERMIT (execute) / SAFE_STATE (deny)
    → gamma_decisions[] evidence                 (governed_runtime.py:57,69)
      → Execution Evidence Bundle → replay manifest → paper tables
```

**Single-engine property (graph-level):** every decision edge terminates at the *one*
`evaluate_decision` node. No parallel authorization engine exists in the graph — statically
enforced by `tools/check_single_engine.py`.
