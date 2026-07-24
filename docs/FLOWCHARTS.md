# FLOWCHARTS — What Actually Happens, Step by Step

Two flows matter most: (1) what happens when you run the main command, and (2) how a dataset row turns
into a number in the paper.

---

## 1. What happens when you type `RUN_ALL_EXPERIMENTS.py`

```mermaid
flowchart TD
    START(["you run:<br/>./.venv/bin/python RUN_ALL_EXPERIMENTS.py"]) --> META[capture host info<br/>CPU, RAM, Python, git commit, seed, timestamp<br/>→ experiments/_meta/host.json]
    META --> E1

    subgraph PHASE1["PHASE 1 — run the 8 experiments in order"]
      E1[E1 correctness<br/>gamma_test_runner on 284,807 rows] --> E2[E2 replay<br/>verify the ledger]
      E2 --> E3[E3 formal<br/>2^16 check + TLC]
      E3 --> E4[E4 stress<br/>1-64 threads]
      E4 --> E5[E5 ablation<br/>remove components]
      E5 --> E6[E6 profiling<br/>per-stage timing]
      E6 --> E7[E7 AgentDojo<br/>boundary FPR, no LLM]
      E7 --> E8[E8 robustness<br/>16 fault types]
    end

    E8 --> PACK[each experiment writes into experiments/&lt;name&gt;/:<br/>logs/  ·  *.json  ·  *.csv  ·  summary.md  ·  metadata.json  ·  REPRODUCE.md]
    PACK --> IDX[write experiments/_meta/run_index.json<br/>master record of the run]

    IDX --> GEN
    subgraph PHASE2["PHASE 2 — generators (read artifacts only)"]
      GEN[generate_statistics.py] --> GF[generate_figures.py]
      GF --> GT[generate_tables.py]
      GT --> GP[generate_provenance.py]
      GP --> GD[generate_publication_docs.py]
    end

    GD --> VAL
    subgraph PHASE3["PHASE 3 — validators"]
      VAL[validate_paper_claims.py<br/>every number consistent?] --> SC[scientific_consistency.py<br/>9 integrity checks]
    end

    SC --> DONE(["DONE — prints a summary table:<br/>E1..E8 EXECUTED, validators PASS"])
```

**In words:** it records *where and when* it ran, runs all 8 experiments (each one packaged into its own
folder), writes a master index, then the generators turn those artifacts into statistics, figures,
tables, a provenance graph, and all the reviewer documents, and finally two validators confirm every
number is consistent and every chain unbroken. If anything fails, it says so — it never invents a value.

### What files appear, by phase

```mermaid
flowchart LR
    P1[PHASE 1<br/>experiments] --> O1["experiments/*/*.json<br/>experiments/*/*.csv<br/>experiments/*/logs/*.log<br/>experiments/*/summary.md<br/>gamma_replay_manifest.jsonl"]
    P2[PHASE 2<br/>generators] --> O2["experiments/statistics/*<br/>experiments/figures/*.svg<br/>experiments/tables/*.md + *.tex<br/>experiments/provenance/*<br/>CLAIM_EVIDENCE_MATRIX.md, reviewer_mapping.md,<br/>THREATS, LIMITATIONS, REPRODUCIBILITY_AUDIT,<br/>evidence_manifest.json, FINAL_EVIDENCE_REPORT.md"]
    P3[PHASE 3<br/>validators] --> O3["PAPER_CLAIM_VALIDATION.md<br/>SCIENTIFIC_CONSISTENCY_REPORT.md"]
```

---

## 2. What happens when you type `run_all.py` (the older dashboard suite)

```mermaid
flowchart TD
    S(["./.venv/bin/python run_all.py"]) --> B1[Step 1: LAB v1.0 base benchmark<br/>gamma_test_runner.py → gamma_lab_v1_report.json]
    B1 --> B2[Step 2: ConcurBench conformance → concurbench_full_report.json]
    B2 --> B3[Step 3: financial stress test → stress_test_report.json]
    B3 --> B4[Step 4: Fail-Closed Rate → fcr_test_report.json]
    B4 --> B5[Step 5: FULL_SPEC conformance → full_spec_conformance_report.json]
    B5 --> B6[Step 6: build the dashboard → gamma_report.html]
    B6 --> P[prints a full results summary to the terminal]
```

Use this when you want the **interactive HTML dashboard**. Use `RUN_ALL_EXPERIMENTS.py` when you want the
**reproducible reviewer package**.

---

## 3. How a dataset row becomes a paper number (the traceability chain)

```mermaid
flowchart TD
    D["DATASET<br/>one row of GAMMA_G0_CREDITCARD_FULL_mapped.csv<br/>(gates, token, amount, context, expected outcome)"]
    D --> EXP["EXPERIMENT<br/>gamma_test_runner.py feeds the row to evaluate_decision()"]
    EXP --> DEC["DECISION<br/>PERMIT or SAFE_STATE + evidence quad"]
    DEC --> LOG["LOGS<br/>row-level CSV + the append-only replay manifest (ledger)"]
    LOG --> STAT["STATISTICS<br/>metrics_engine.py counts events, computes Wilson 95% bounds"]
    STAT --> JSON["JSON<br/>gamma_lab_v1_report.json (all metrics, machine-readable)"]
    JSON --> TAB["TABLES<br/>generate_tables.py → experiments/tables/table1_primary_metrics.md (+ .tex)"]
    JSON --> FIG["FIGURES<br/>generate_figures.py → experiments/figures/fig_*.svg"]
    TAB --> PAPER["PAPER<br/>you paste the table / figure into the manuscript"]
    FIG --> PAPER
    JSON --> PROV["PROVENANCE<br/>generate_provenance.py records the whole chain + SHA-256 of each file"]
    PROV --> REV["REVIEWER EVIDENCE<br/>validators confirm JSON = table = figure = manifest"]
```

**Why this matters:** a reviewer can pick any number in the paper and follow the arrows *backwards* all
the way to a raw dataset row and the exact command that produced it. There is no step where a human types
a number by hand — the generators read the JSON and format it, and the validators prove the formatted
value equals the JSON value.

---

## 4. Inside one decision (the engine's own mini-flow)

```mermaid
flowchart TD
    ROW["input row / action"] --> G1{"any node gate failed?<br/>(token, recipient, amount, scope, ownership...)"}
    ROW --> G2{"harm risk over threshold?"}
    ROW --> G3{"context stale or telemetry not fresh?"}
    ROW --> G4{"class-level rule violated?<br/>(ReasonCodes has CLASS_1 / GOODHART)"}
    G1 -- yes --> DEF["Gamma_G = 1 (deficit)"]
    G2 -- yes --> DEF
    G3 -- yes --> DEF
    G4 -- yes --> GC["Gamma_class = 1"]
    DEF --> V{"Gamma_G = 0 AND Gamma_class = 0 ?"}
    GC --> V
    G1 -- no --> V
    V -- yes --> P["PERMIT (pi = 1)"]
    V -- no --> S["SAFE_STATE (pi = 0)"]
    P --> QUAD["evidence quad: (x input, u decision, y result, ledger hash)"]
    S --> QUAD
```

This is exactly what `evaluate_decision()` does for every single action — deterministically, with no
randomness, which is why replay always reproduces it.
