# PAPER TRACEABILITY — Where Every Number Comes From (+ One Full Example)

This is the "prove it" document. It shows the pipeline from raw data to a paper number, then walks **one
single authorization** all the way through the real architecture so you can see the whole machine work on
a concrete case.

---

## 1. The value pipeline (every paper number follows this)

```mermaid
flowchart TD
    DS["DATASET<br/>GAMMA_G0_CREDITCARD_FULL_mapped.csv — one row = one proposed action"]
    DS --> EXP["EXPERIMENT<br/>e.g. gamma_test_runner.py (E1) reads the row"]
    EXP --> LOG["LOGS<br/>row-level decision CSV + the replay manifest (append-only ledger)"]
    LOG --> ST["STATISTICS<br/>metrics_engine.py: count events, Wilson 95% bounds, cluster correction"]
    ST --> JS["JSON<br/>gamma_lab_v1_report.json — the single source of truth for the numbers"]
    JS --> CS["CSV<br/>gamma_validation_results.csv — same data, spreadsheet form"]
    JS --> TB["TABLES<br/>generate_tables.py → table1_primary_metrics.md (+ .tex)"]
    JS --> FG["FIGURES<br/>generate_figures.py → fig_false_permit_rate.svg, ..."]
    TB --> PP["PAPER<br/>you paste the generated table / figure into the manuscript"]
    FG --> PP
    JS --> PV["PROVENANCE<br/>generate_provenance.py records the chain + SHA-256 of each node"]
    PV --> RV["REVIEWER EVIDENCE<br/>validate_paper_claims.py: JSON = table = figure = manifest"]
```

**The guarantee:** no number is typed by a human. The experiment writes JSON; the generators *read* that
JSON and format it into tables/figures; the validators *prove* the formatted value equals the JSON value;
the provenance graph records the SHA-256 of every file so nothing can be swapped silently.

### Concrete example of the chain for one metric — "False Permit Rate"
| Stage | Concrete artifact | The value |
|-------|-------------------|-----------|
| Dataset | 492 "should-deny" rows in the ULB corpus | (the adversarial population) |
| Experiment | `gamma_test_runner.py` adjudicates each | 0 of them permitted |
| JSON | `gamma_lab_v1_report.json ▷ primary_metrics.false_permit_rate` | `adverse_events: 0, n: 492` |
| Statistics | `metrics_engine.py` Wilson upper bound | `wilson95_clustercorrected_upper ≈ 1.31e-02` |
| Table | `experiments/tables/table1_primary_metrics.md` | `False Permit Rate (ULB) \| 0/492 \| Wilson95↑ 1.31e-02` |
| Figure | `experiments/figures/fig_false_permit_rate.svg` | a bar at 0 with the CI whisker |
| Validator | `PAPER_CLAIM_VALIDATION.md` claim **C2** | `PASS — JSON ✓ table ✓ figure ✓ manifest ✓` |

---

## 2. One complete authorization, end to end

Let's follow a single proposed action: **an AI agent tries to transfer money to account `X`.**
We'll show both possible outcomes so you see the guard actually decide.

### Step 0 — the proposal
The agent proposes: `send_money(recipient="US133...121212", amount=5000)`.
In the AgentDojo path this is a real tool call; in the ULB path it's a row with the equivalent fields.

### Step 1 — interception
```mermaid
flowchart LR
    A["agent: send_money(recipient=X, amount=5000)"] --> I["governed_runtime.run_function<br/>catches it BEFORE execution"]
    I --> K{"is send_money a known,<br/>mediated action?"}
    K -- "no" --> D0["SAFE_STATE (unknown tool → fail closed)"]
    K -- "yes, it's a FUNDS_TRANSFER" --> P["evaluate its predicates"]
```
`send_money` is in the frozen tool map as a `FUNDS_TRANSFER`, so it must be adjudicated.

### Step 2 — predicate evaluation (turn the action into pass/fail checks)
The predicate evaluator reads the environment and checks each relevant predicate:

| Predicate | Question | Case A (attack) | Case B (legit) |
|-----------|----------|-----------------|----------------|
| `GATE_recipient_recognition` | Is `X` a known/recognized account? | **X is NOT in the recognized set → deficit = 1** | recipient is known → 0 |
| `GATE_amount_limit` | Is 5000 within the available limit? | 0 | 0 |
| `AUTH_TOKEN` | Is the permit token valid & fresh? | 0 | 0 |
| `GATE_scope`, `GATE_ownership`, `CTR_ISB`, `TRACE`, `INTERLOCK` | structural checks | 0 | 0 |

### Step 3 — Gamma (the decision core)
```mermaid
flowchart TD
    subgraph CASEA["Case A — attacker recipient"]
      DA["deficits = {recipient:1, others:0}"] --> GA["Gamma_G = MAX(deficits) = 1"]
      GA --> VA{"Gamma_G=0 AND Gamma_class=0?"}
      VA -- "no (Gamma_G=1)" --> SA["SAFE_STATE — blocked"]
    end
    subgraph CASEB["Case B — known recipient"]
      DB["deficits = all 0"] --> GB["Gamma_G = 0, Gamma_class = 0"]
      GB --> VB{"both 0?"}
      VB -- "yes" --> PB["PERMIT — executes"]
    end
```
The non-compensatory MAX is decisive: in Case A, four checks passing cannot offset the one failing
recipient check — `Gamma_G = 1`, so the transfer is **blocked (SAFE_STATE)**. In Case B everything passes,
so **PERMIT**.

### Step 4 — evidence + ledger
Either way, an **evidence quad** is written: `(x = the input, u = the decision, y = the result, ledger
hash)`. It is appended to the **Hydra Ledger** (`gamma_replay_manifest.jsonl`), each record chained to the
previous by hash — so any later tampering breaks the chain.

```mermaid
flowchart LR
    R1["record N-1<br/>hash_current = h1"] --> R2["record N<br/>hash_prev = h1<br/>decision = SAFE_STATE<br/>hash_current = h2"]
    R2 --> R3["record N+1<br/>hash_prev = h2<br/>..."]
```

### Step 5 — replay (audit later, from evidence alone)
`gamma_replay_verify.py` walks the ledger and re-checks: does `record[N].hash_prev == record[N-1].hash_current`?
Does each record's ledger hash bind its evidence quad? Is the decision self-consistent? For our transfer,
all checks pass → the decision is provably deterministic and untampered.

### Step 6 — statistics
Across the whole run, `metrics_engine.py` counts: how many should-deny actions were permitted (false
permits)? Our Case-A transfer contributes to the "correctly denied" count. With 0 false permits over 492
should-deny actions, the Wilson 95% upper bound on the false-permit rate is computed (~1.31e-02).

### Step 7 — into the paper
That count and bound land in `gamma_lab_v1_report.json`, which `generate_tables.py` formats into Table I
and `generate_figures.py` draws as `fig_false_permit_rate.svg`, which you paste into the manuscript — and
which `validate_paper_claims.py` confirms is consistent everywhere.

### The whole example in one picture
```mermaid
flowchart TD
    P["agent proposes send_money(X, 5000)"] --> INT["intercept (governed_runtime)"]
    INT --> PRE["predicates: recipient recognized?"]
    PRE --> GAM["Gamma_G = MAX(deficits)"]
    GAM --> DEC{"decision"}
    DEC -- "attacker X → Gamma_G=1" --> BLK["SAFE_STATE (blocked)"]
    DEC -- "known X → all 0" --> OK["PERMIT (executes)"]
    BLK --> LED["evidence quad → Hydra Ledger"]
    OK --> LED
    LED --> REP["replay verify (audit)"]
    REP --> STA["statistics (Wilson CI)"]
    STA --> JSN["gamma_lab_v1_report.json"]
    JSN --> TBL["Table I + fig_false_permit_rate.svg"]
    TBL --> PAP["paper + reviewer evidence"]
```

---

## 3. How to verify traceability yourself (no coding)

1. Open `experiments/provenance/PROVENANCE.md` — it lists, per experiment, the chain **raw log → metric
   engine → JSON → CSV → table → figure** with each file's SHA-256.
2. Open `PAPER_CLAIM_VALIDATION.md` — every claim shows `JSON ✓ table ✓ figure ✓ manifest ✓`.
3. Open `SCIENTIFIC_CONSISTENCY_REPORT.md` — 9 checks incl. "provenance chain intact" and "no stale
   artifacts."
4. Pick any row in `experiments/tables/table1_primary_metrics.md`: its **Reproduction command** column
   tells you the exact command that regenerates it from scratch.

If all three reports say PASS, every number in the paper is backed by an executed, reproducible artifact.
