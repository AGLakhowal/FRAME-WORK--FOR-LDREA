# ARCHITECTURE — How Everything Connects

Diagrams first, then a file-by-file map. All diagrams are Mermaid (they render on GitHub and in most
Markdown viewers).

---

## 1. The runtime authorization pipeline (what happens to one action)

```mermaid
flowchart TD
    U[User / task] --> AG[AI Agent<br/>proposes an action]
    AG --> RI[Runtime Interceptor<br/>catches action before it executes]
    RI --> CLS{Known, mediated<br/>action?}
    CLS -- "unknown tool" --> SS0[SAFE_STATE<br/>fail-closed]
    CLS -- "read-only" --> PASS[pass through<br/>no external effect]
    CLS -- "externally-effective action" --> PE[Predicate Engine<br/>run every check]

    subgraph GAMMA["Gamma Authorization Core (frozen)"]
      PE --> RC[Runtime Context<br/>freshness / staleness]
      PE --> PRED[Node predicates<br/>token, recipient, amount, scope, ownership...]
      PRED --> GG["Gamma_G = MAX of deficits<br/>(non-compensatory)"]
      PRED --> GC["Gamma_class<br/>class-level veto"]
      GG --> DEC{"Gamma_G = 0<br/>AND Gamma_class = 0 ?"}
      GC --> DEC
    end

    DEC -- yes --> PERMIT[PERMIT<br/>action executes]
    DEC -- no --> SS[SAFE_STATE<br/>action blocked]

    PERMIT --> EV[Evidence Quad<br/>x, u, y, ledger-hash]
    SS --> EV
    EV --> HL[Hydra Ledger<br/>append-only hash chain]
    HL --> RP[Replay Verifier<br/>re-checks every decision]
    RP --> OUT[Evidence artifacts<br/>JSON / CSV]
    OUT --> TAB[Paper tables & figures]
```

**Read it as:** an action enters at the top, gets classified, runs through the predicate checks inside
Gamma, becomes **PERMIT** or **SAFE_STATE**, and — either way — is written to the tamper-evident ledger
that the replay verifier can later audit. Those audited records become the paper's numbers.

---

## 2. The two decision signals (why "one red flag = block")

```mermaid
flowchart LR
    subgraph checks["Node-level predicate checks"]
      P1[token valid?]
      P2[recipient known?]
      P3[amount within limit?]
      P4[scope ok?]
      P5[ownership ok?]
      P6[context fresh?]
    end
    checks --> MAX["Gamma_G = MAX(all deficits)<br/>1 failure => 1"]
    subgraph classlvl["Class-level pattern"]
      C1[velocity / Goodhart pattern?]
    end
    classlvl --> GC["Gamma_class<br/>1 if class rule violated"]
    MAX --> AND{"both are 0?"}
    GC --> AND
    AND -- yes --> PERMIT[PERMIT]
    AND -- no --> SAFE[SAFE_STATE]
```

The **MAX** (not average) is the whole point: averaging would let 5 good checks hide 1 bad one. With
MAX, a single deficit forces `Gamma_G = 1`, which blocks.

---

## 3. The whole repository, as layers

```mermaid
flowchart TD
    subgraph DATA["① Data & frozen policy"]
      CSV[GAMMA_G0_CREDITCARD_FULL_mapped.csv<br/>284,807 transactions]
      MAN[agentdojo_integration/manifests/*.json<br/>frozen predicates, thresholds, tool map]
    end

    subgraph ENGINE["② Frozen decision engine (never modified)"]
      GTR[gamma_test_runner.py<br/>evaluate_decision]
      GB[interception/gamma_bridge.py<br/>GammaBridge.decide]
      FP[interception/frozen_policy.py<br/>+ predicate_evaluation.py]
      ME[metrics_engine.py<br/>Wilson / bootstrap]
    end

    subgraph EXPS["③ Experiments (call the engine, never change it)"]
      E1[gamma_test_runner.py = E1 correctness]
      E2[gamma_replay_verify.py = E2 replay]
      E3[independent_verifier.py = E3 formal]
      E4[audit/concurrency_scaling.py = E4 stress]
      E5[experiment_ablation.py = E5 ablation]
      E6[audit/runtime_profile.py = E6 profiling]
      E7[experiment_agentdojo_boundary_fpr.py = E7 agents]
      E8[experiment_robustness.py = E8 robustness]
    end

    subgraph ORCH["④ Orchestrator + harness"]
      RUNALL[RUN_ALL_EXPERIMENTS.py]
      HARN[experiments/_harness.py<br/>metadata, hashing, packaging]
    end

    subgraph GEN["⑤ Auto-generators (read artifacts, hand-write nothing)"]
      GS[generate_statistics.py]
      GF[generate_figures.py]
      GT[generate_tables.py]
      GP[generate_provenance.py]
      GD[generate_publication_docs.py]
    end

    subgraph VAL["⑥ Validators"]
      VC[validate_paper_claims.py]
      SC[scientific_consistency.py]
    end

    subgraph OUT["⑦ Evidence outputs"]
      TREE[experiments/ tree<br/>json, csv, summary.md, figures, tables]
      DOCS[CLAIM_EVIDENCE_MATRIX.md, reviewer_mapping.md,<br/>THREATS, LIMITATIONS, REPRODUCIBILITY_AUDIT,<br/>evidence_manifest.json, FINAL_EVIDENCE_REPORT.md]
    end

    DATA --> ENGINE --> EXPS
    MAN --> ENGINE
    RUNALL --> EXPS
    HARN --> RUNALL
    EXPS --> TREE
    RUNALL --> GEN --> TREE
    GEN --> DOCS
    RUNALL --> VAL --> DOCS
    TREE --> VAL
```

**Golden rule visible here:** layers ② (engine) and ① (frozen policy) are **never modified** by the
experiment or evidence layers. Experiments *call* the engine; generators *read* artifacts; validators
*check* consistency. This one-way flow is what makes the results reproducible and trustworthy.

---

## 4. The giant end-to-end diagram (dataset → reviewer evidence)

```mermaid
flowchart LR
    DS[Dataset<br/>ULB 284,807 rows] --> BM[Benchmark harnesses<br/>LAB / ConcurBench / AgentDojo]
    BM --> EX[Experiments E1-E8]
    EX --> LOG[Raw logs<br/>experiments/*/logs/*.log]
    LOG --> JSON[JSON artifacts<br/>e.g. gamma_lab_v1_report.json]
    JSON --> STAT[Statistics<br/>Wilson CIs, effect sizes]
    JSON --> CSV[CSV artifacts]
    STAT --> TAB[IEEE Tables<br/>experiments/tables/*.md + *.tex]
    CSV --> TAB
    JSON --> FIG[Figures<br/>experiments/figures/*.svg]
    TAB --> PAPER[Paper manuscript]
    FIG --> PAPER
    JSON --> PROV[Provenance graph<br/>every value traced]
    PROV --> REV[Reviewer evidence<br/>claim matrix, validators, threats]
    PAPER --> REV
```

Every arrow is a real file dependency. Nothing skips a step: a number in the paper can always be walked
back **paper ← table ← JSON ← log ← experiment ← dataset**. The provenance graph
(`experiments/provenance/`) makes that walk-back machine-checkable.

---

## 5. Repository map (folder tree)

```
Independent Benchmark and Reviewer-Closure Framework for L-DREA/
│
├── GAMMA_G0_CREDITCARD_FULL_mapped.csv   ← the 451 MB transaction stream (input data)
├── gamma_replay_manifest.jsonl           ← 200 MB tamper-evident ledger (produced by E1)
│
├── gamma_test_runner.py        ← ★ FROZEN ENGINE. evaluate_decision(); runs E1 (LAB benchmark)
├── metrics_engine.py           ← statistics helpers (Wilson, bootstrap) — engine-adjacent, frozen
├── gamma_replay_verify.py      ← E2: independently re-verifies the ledger
├── independent_verifier.py     ← E3: exhaustive 2^16 equivalence check
├── experiment_ablation.py      ← E5: remove each component, measure leaked permits
├── experiment_robustness.py    ← E8: inject 16 fault types (NEW)
├── experiment_agentdojo_boundary_fpr.py ← E7: adjudicate AgentDojo attacks (no LLM)
│
├── concurbench_full.py, stress_test.py, fcr_test.py, full_spec_conformance.py
│                              ← supplementary conformance checks (run inside E1)
├── run_all.py                 ← OLDER "run everything" → HTML dashboard (gamma_report.html)
├── RUN_ALL_EXPERIMENTS.py     ← ★ NEWER "run everything" → experiments/ package (USE THIS)
│
├── validate_paper_claims.py   ← validator: every number consistent across JSON/table/figure/manifest
├── scientific_consistency.py  ← validator: 9 integrity checks (provenance, CIs, stale files...)
│
├── formal/                    ← ExternalizationMonitor.tla/.cfg (the TLA+ model for E3's TLC step)
│
├── agentdojo_integration/
│   ├── interception/          ← ★ the live authorization layer plugged into AgentDojo
│   │   ├── frozen_policy.py        (loads 7 immutable manifests, Merkle-root verified)
│   │   ├── gamma_bridge.py         (GammaBridge.decide → calls evaluate_decision)
│   │   ├── predicate_evaluation.py (turns env state into pass/fail predicates)
│   │   ├── execution_binding.py    (maps predicate families to engine slots)
│   │   └── governed_runtime.py     (the interception point; unknown tool → SAFE_STATE)
│   ├── manifests/             ← frozen policy JSON (predicates, thresholds, tool map, Merkle root)
│   ├── audit/                 ← analysis tools: concurrency_scaling (E4), runtime_profile (E6),
│   │                            stats_engine, fpr_fdr_labeling, replay_engine, _util (Wilson/bootstrap)
│   └── audit_run/trace/       ← 33 recorded AgentDojo episodes (used by E7, no LLM needed to re-derive)
│
├── runtime_context/           ← the "Runtime Context Layer": freshness/velocity/ordering OBSERVERS
│                                (they measure evidence but never decide — decisions stay in the engine)
│
├── experiments/               ← ★ THE REPRODUCIBLE EVIDENCE PACKAGE (produced by RUN_ALL_EXPERIMENTS)
│   ├── _harness.py                 (runs each experiment, records host/seed/time/sha256)
│   ├── claims_registry.py          (declares claims C1-C14 + reviewer concerns R1-R11)
│   ├── _evidence.py                (resolves claim → artifact → value, live)
│   ├── generate_statistics.py      (Wilson CIs, effect sizes)
│   ├── generate_figures.py         (pure-SVG figures — no matplotlib)
│   ├── generate_tables.py          (IEEE tables + LaTeX)
│   ├── generate_provenance.py      (the traceability graph)
│   ├── generate_publication_docs.py(claim matrix, reviewer map, threats, limitations, final report)
│   ├── runtime_correctness/  replay/  formal/  stress/  ablation/  profiling/  agentdojo/  robustness/
│   │                              ← one folder per experiment: logs, json, csv, summary.md, metadata.json
│   ├── figures/  tables/  statistics/  provenance/  _meta/
│   └── _meta/run_index.json        (the master record of the last full run)
│
└── docs/                      ← ★ THIS documentation set
```

The `★` items are the ones a newcomer touches first. Everything else is called *by* those.

---

## 6. Who calls whom (dependency direction)

```mermaid
flowchart TD
    RUNALL[RUN_ALL_EXPERIMENTS.py] --> HARN[_harness.py]
    RUNALL --> E1 & E2 & E3 & E4 & E5 & E6 & E7 & E8
    E1[gamma_test_runner] --> ENG[evaluate_decision]
    E5[experiment_ablation] --> ENG
    E8[experiment_robustness] --> ENG
    E8 --> VERI[gamma_replay_verify]
    E7[boundary_fpr] --> BRIDGE[GammaBridge / frozen_policy] --> ENG
    RUNALL --> GENS[generators] --> ART[(experiments/ artifacts)]
    RUNALL --> VALS[validators] --> ART
    GENS --> REG[claims_registry.py]
    VALS --> REG
```

Arrows point from "caller" to "callee/dependency." Notice the engine (`evaluate_decision`) is a **leaf**
— everything depends on it, it depends on nothing above it. That is by design.
