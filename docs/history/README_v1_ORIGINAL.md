# Gamma G‑0 / L‑DREA — Credit‑Card Authorization Benchmark

A reproducible, **deterministic runtime‑enforcement** benchmark that takes the public
Kaggle/ULB credit‑card fraud dataset, treats every transaction as an *externally
effective action proposal*, and independently re‑derives the **authorization decision**
(PERMIT vs SAFE_STATE) using the **L‑DREA externalization‑monitor** rule set — then scores
itself against the **LAB v1.0** benchmark methodology.

> **One‑line claim of this repo:** on all **284,807** real ULB transactions, the monitor
> produced **0 unauthorized executions**, **0 false permits**, **0 false denials**,
> held **all 492 fraud rows** in SAFE_STATE, kept a **fully linked SHA‑256 hash chain**
> (284,807/284,807), and satisfied **all six runtime invariants** — at a measured
> **~0.02 ms/decision** (pure software on this host).

---

## Table of contents

1. [What we do](#1-what-we-do)
2. [Why we do it](#2-why-we-do-it--the-paper-link)
3. [How it maps to the paper](#3-how-it-maps-to-the-paper-section-by-section)
4. [Repository map — which file is which](#4-repository-map--which-file-is-which)
5. [The data: from Kaggle to golden trace](#5-the-data-from-kaggle-to-golden-trace)
6. [End‑to‑end pipeline (flowchart)](#6-end-to-end-pipeline-flowchart)
7. [The decision logic (flowchart)](#7-the-decision-logic-law-of-concurrence-flowchart)
8. [The benchmark rules](#8-the-benchmark-rules-lab-v10)
9. [How to run it](#9-how-to-run-it)
10. [Results we actually got](#10-results-we-actually-got)
    - [Real-Dataset Golden-Trace Validation](#real-dataset-golden-trace-validation)
    - [Metric Denominator Discipline](#metric-denominator-discipline)
11. [The webpage / dashboard](#11-the-webpage--dashboard)
12. [Independent verification: TLC, replay manifest, reproducibility bundle](#12-independent-verification-tlc-replay-manifest-reproducibility-bundle)
13. [Honesty notes & scope](#13-honesty-notes--scope)
14. [ConcurBench conformance, stress test & FCR (one command)](#14-concurbench-conformance-stress-test--fcr-one-command)

---

## 1. What we do

Autonomous AI agents increasingly hold **execution authority** — they move funds, dispatch
orders, actuate devices. Content filters and alignment shape *what an agent proposes*; they
are **not a reference monitor over what actually executes**. The L‑DREA paper generalizes
Anderson's 1972 reference monitor from *data access* to *externally effective action*.

This repository is a **concrete, runnable instantiation** of that idea on a real, well‑known
dataset:

- We take **`creditcard.csv`** (Kaggle ULB, 284,807 European card transactions, 492 fraud).
- We treat **each transaction as an action proposal** crossing an *externalization boundary*
  ("should this payment be allowed to execute?").
- We **map** it into a 112‑column *golden‑trace* schema (gates, tokens, hash chain, timestamps).
- We **re‑derive** the authorization decision from first principles using the **Law of
  Concurrence** (non‑compensatory `max` aggregation + class‑level veto).
- We **score** the run against the **LAB v1.0** benchmark: six metrics with Wilson 95%
  confidence bounds, six runtime invariants, a negative control, replay‑determinism, and
  measured latency.
- We **render** the whole thing as an animated **HTML dashboard**.

## 2. Why we do it — the paper link

This codebase is the empirical companion to:

> A. Gill‑Lakhowal, **"Deterministic Runtime Enforcement for Autonomous AI Agents: A
> Substrate‑Neutral Reference Monitor for the Execution Boundary"**, IEEE Access, 2026
> (and the companion *L‑DREA: A Substrate‑Neutral Reference Monitor for the Action Boundary*).

The paper's headline empirical claim is a **zero‑event** result (no unauthorized
externalizations) on 1.2M synthetic proposals with a cluster‑corrected Wilson upper bound
`< 1.4 × 10⁻⁵`. The paper's evaluation is **synthetic and author‑controlled**, which the
paper itself flags as a circularity risk (§IX‑E).

**This repo answers a narrower, independently checkable question:** *does the same
deterministic rule set behave correctly on a real, third‑party, labelled dataset where the
ground truth is not ours to invent?* The ground truth here is the ULB **`Class`** column
(0 = legitimate, 1 = fraud), not a number we made up.

## 3. How it maps to the paper (section by section)

Every mechanism implemented in [gamma_test_runner.py](gamma_test_runner.py) traces directly
to a section of the paper:

| Paper section | Concept | Where it lives in the code |
|---|---|---|
| §IV‑A, Def. 2 | Externalization monitor (5 structural properties) | whole runner |
| §IV‑B (Law of Concurrence) | `Γ_G = maxᵢ dᵢ`, `dᵢ = max(0, mᵢ−θᵢ)`, non‑compensatory | [gamma_test_runner.py:407‑434](gamma_test_runner.py#L407-L434) |
| §V‑C | Class‑level veto `Γ_class`, `max(Γ_G, Γ_class)=0` | [gamma_test_runner.py:425‑434](gamma_test_runner.py#L425-L434) |
| §V‑B | Interpretive‑sufficiency bit `ISB` | [gamma_test_runner.py:438‑444](gamma_test_runner.py#L438-L444) |
| §V‑F, §VI‑B Inv. 5 | Commit‑before‑actuate / TOCTOU ordering | [gamma_test_runner.py:457‑467](gamma_test_runner.py#L457-L467) |
| App. A | SHA‑256 hash‑chain replay determinism | [gamma_test_runner.py:446‑455](gamma_test_runner.py#L446-L455) |
| §VIII‑C / IX‑C, Eq. 7 | Operational definition of Unauthorized Execution | [gamma_test_runner.py:469‑484](gamma_test_runner.py#L469-L484) |
| §VI‑B Inv. 1–6 | Six runtime invariants as pass/fail checks | [gamma_test_runner.py:520‑544](gamma_test_runner.py#L520-L544) |
| Corollary 2 | Negative control: compensatory weighted‑sum aggregator | [gamma_test_runner.py:546‑568](gamma_test_runner.py#L546-L568) |
| §VIII‑G / IX‑G | Six metrics + Wilson 95% + cluster correction (`N_eff = N/DE`) | [gamma_test_runner.py:277‑322](gamma_test_runner.py#L277-L322) |
| §VIII‑D | LAB‑A1…A5 scenario taxonomy | [gamma_test_runner.py:336‑353](gamma_test_runner.py#L336-L353) |
| §IX‑G | Measured per‑decision latency + throughput | [gamma_test_runner.py:623‑714](gamma_test_runner.py#L623-L714) |
| App. D | TLC attestation **verified** (consistency + zero violations + optional source binding) | [`verify_tlc()`](gamma_test_runner.py#L445) |
| App. A / README | Per‑item **ERTuple replay manifest** + independent verifier | [`write_replay_manifest()`](gamma_test_runner.py#L539), [gamma_replay_verify.py](gamma_replay_verify.py) |
| README | **Evidence Quad** per decision (method · policy · ledger hash) | [gamma_test_runner.py:974](gamma_test_runner.py#L974) |
| — | Full lab **reproducibility bundle** (digests · env · command · MANIFEST) | [`write_repro_bundle()`](gamma_test_runner.py#L618) |

**What is taken from the paper:** the *rules and definitions* (the aggregation law, the veto,
Eq. 7, the invariants, the metric/CI methodology, the LAB scenario classes).
**What is NOT taken from the paper:** the paper's *numbers*. Every value in our reports is
computed by the runner on the real dataset — see [Honesty notes](#13-honesty-notes--scope).

## 4. Repository map — which file is which

```
carddataset/
├── creditcard.csv                          # INPUT  — raw Kaggle/ULB dataset (Time,V1..V28,Amount,Class)
├── gamma_map_raw.py                         # STEP 1 — maps raw CSV → 112-col golden-trace schema
├── GAMMA_G0_..._sample_master112_1000.csv   #          1,000-row schema/constants TEMPLATE (112 cols)
├── GAMMA_G0_CREDITCARD_FULL_mapped.csv      #          full mapped golden trace (284,807 rows) [generated]
│
├── gamma_test_runner.py   ◀── MAIN FILE     # STEP 2 — re-derives decisions + runs LAB v1.0 benchmark
├── gamma_validation_results.csv             #          row-level decision output (incl. EvidenceQuad) [generated]
├── gamma_summary.json                       #          summary report [generated]
├── gamma_lab_v1_report.json                 #          full LAB v1.0 report (metrics, invariants, latency, TLC) [generated]
├── gamma_replay_manifest.jsonl              #          per-item ERTuple replay manifest [generated]
│
├── gamma_replay_verify.py                   # STEP 2b — stdlib-only independent replay-manifest verifier
├── gamma_bundle/                            #          reproducibility bundle (MANIFEST.json, REPRODUCE.md, env) [generated]
│
├── gamma_report_page.py                     # STEP 3 — renders the JSON reports into an HTML dashboard
├── gamma_report.html                        #          self-contained animated dashboard [generated]
├── gamma_terminal_full.txt                  #          captured console output (embedded verbatim in the page)
├── *_full.json                              #          a second report set used by the dashboard
│
├── run_all.py            ◀── ONE COMMAND    # runs base benchmark + all layers below + dashboard
├── concurbench_full.py                      # ConcurBench "Document 1" full conformance packet (all levels)
├── concurbench_full_report.json             #          §18 top-level conformance object [generated]
├── stress_test.py                           # 4 financial-services stress scenarios (P1–P4) vs Γ engine
├── stress_test_report.json                  #          per-condition pass/fail + verdicts [generated]
├── fcr_test.py                              # dedicated Fail-Closed Rate test over real corpus + uncertainty
├── fcr_test_report.json                     #          FCR + per-family Wilson bounds [generated]
├── full_spec_conformance.py                 # FULL_SPEC.md corrected flow — enforces §7.1 bands, AIS, 3-signal, SVR/FFC
├── full_spec_conformance_report.json        #          FULL_SPEC conformance object [generated]
└── concurbench_conformance_check.py         # audits report vs Document-1 required fields (exit 0 = all matched)
```

**The main file is [gamma_test_runner.py](gamma_test_runner.py)** — it is the reference
externalization monitor and the benchmark harness in one. `gamma_map_raw.py` prepares its
input; `gamma_report_page.py` visualizes its output. **[run_all.py](run_all.py)** is the single
entry point that chains the base benchmark, the ConcurBench conformance packet, the stress
test, the Fail-Closed Rate test, and the unified dashboard (see §14).

## 5. The data: https://drive.google.com/drive/folders/1_Al3Tq0wQo9fMH29YECGeWkkhBqfBj5x?usp=sharing
- from Kaggle to golden trace

The raw [creditcard.csv](creditcard.csv) has the standard ULB columns:https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
`Time, V1…V28 (PCA-anonymized features), Amount, Class`.

[gamma_map_raw.py](gamma_map_raw.py) transforms each raw row into one **112‑column
golden‑trace** row that the monitor can evaluate. The mapping is **driven by the real
`Class` label**:

| Raw `Class` | Meaning | Golden‑trace effect |
|---|---|---|
| `0` | legitimate | all gates pass, `HARM_RISK` low (≤0.05), `Γ=0` → **PERMITTED / actuated** |
| `1` | fraud | `Gate_A3`, `Gate_A7`, `Lambda_G` fail, `HARM_RISK=0.8`, `Γ=1` → **SAFE_STATE / denied** |

Genuinely computed during mapping (not faked):
- the **SHA‑256 hash chain** `HASH_prev → HASH_current`, GENESIS‑anchored, over the canonical
  core record;
- per‑row deterministic token / evidence IDs;
- timestamps with `CommitTimestamp < ActuateTimestamp` (commit‑before‑actuate ordering).

Structural constants (PolicyHash, SpecVersion, TLC hashes, substrate IDs) are copied from the
bundled 1,000‑row template so the emitted file is schema‑identical to a real golden trace. The
TLC attestation is **not blindly trusted** — the runner independently verifies it (consistency
across all rows, non‑trivial state space, zero safety violations, and optional cryptographic
binding to the actual `.tla`/`.cfg` source); see [§12](#12-independent-verification-tlc-replay-manifest-reproducibility-bundle).

> **Key honesty point:** the authorization *outcome* is a function of the real fraud label and
> the real per‑row crypto/ordering — the runner re‑derives PERMIT/SAFE_STATE itself and then
> checks its derivation against the labels. Match rate = **100%**, false permits = **0**.

## 6. End‑to‑end pipeline (flowchart)

```mermaid
flowchart LR
    A["creditcard.csv<br/>Kaggle ULB<br/>284,807 rows"] -->|gamma_map_raw.py| B["GAMMA_G0_..._FULL_mapped.csv<br/>112-col golden trace"]
    T["sample_master112_1000.csv<br/>schema + constants template"] -.->|provides schema| B
    B -->|gamma_test_runner.py<br/>MAIN| C{"L-DREA<br/>externalization<br/>monitor"}
    C --> D["gamma_validation_results.csv<br/>per-row decisions"]
    C --> E["gamma_summary.json"]
    C --> F["gamma_lab_v1_report.json<br/>metrics + invariants + latency"]
    F -->|gamma_report_page.py| G["gamma_report.html<br/>animated dashboard"]
    E --> G
    H["gamma_terminal_full.txt"] -.->|embedded verbatim| G
```

## 7. The decision logic (Law of Concurrence, flowchart)

For each transaction the monitor computes a deficit vector, aggregates it
**non‑compensatorily**, applies the class‑level veto, and only then permits.

```mermaid
flowchart TD
    R["Transaction row"] --> P["Per-predicate deficits d_i<br/>Gate_A1..A7, Lambda_G, TOKEN_VALID,<br/>AuthoritySignatureValid, HARM_RISK&gt;θ,<br/>StaleContext, TelemetryStale"]
    P --> G["Γ_G = max_i d_i<br/>(non-compensatory: ANY deficit ⇒ Γ_G=1)"]
    R --> V["Γ_class = 1 if ReasonCodes ∈ {CLASS_1, GOODHART}<br/>(class-level veto)"]
    G --> M{"max(Γ_G, Γ_class) == 0 ?"}
    V --> M
    M -->|yes| PERMIT["Π = 1 → PERMIT<br/>(commit-before-actuate, then execute)"]
    M -->|no| SAFE["Π = 0 → SAFE_STATE<br/>(deny, hold last good state)"]
    PERMIT --> U{"Eq.7 Unauthorized?<br/>Execute ∧ (¬Valid ∨ Γ&gt;0 ∨ ISB=0 ∨ chain broken)"}
    U -->|never observed| OK["legitimate externalization"]
```

The crucial property — and the reason a compensatory metric is *unsafe* — is **Corollary 2**:
a weighted‑sum aggregator lets a surplus on clean predicates mask a single real deficit. The
runner demonstrates this with a built‑in **negative control** (see below).

## 8. The benchmark rules (LAB v1.0)

The runner implements the LAB v1.0 protocol from the paper. The rules it enforces:

**Decision rule.** `PERMIT iff Π = 1`, where `Π = [ max(Γ_G, Γ_class) == 0 ]`.
`Γ_G = maxᵢ dᵢ` (non‑compensatory). A single deficit denies regardless of all other predicates.

**Node predicates that must all concur** (deficit ⇒ denial):
`Gate_A1…A7, Lambda_G, TOKEN_VALID, AuthoritySignatureValid`,
plus derived deficits `HARM_RISK > θ` (θ=0.5), `StaleContext`, `TelemetryFresh == FALSE`.

**Class‑level veto.** `Γ_class = 1` when `ReasonCodes` contains `CLASS_1` or `GOODHART` —
forces SAFE_STATE even when every node predicate concurs (Goodhart resistance).

**Unauthorized Execution (Eq. 7).**
`Unauth = Execute ∧ ( ¬TOKEN_VALID ∨ max(Γ_G,Γ_class) > 0 ∨ ISB = 0 ∨ hash‑chain link broken )`.

**Commit‑before‑actuate.** Any actuated op must have `CommitTimestamp ≤ ActuateTimestamp`
and `CommitBeforeActuate = TRUE`; otherwise a TOCTOU/ordering violation is recorded.

**Replay determinism.** Row *i*'s `HASH_prev` must equal row *(i‑1)*'s `HASH_current`,
GENESIS‑anchored. Any broken link is a replay divergence.

**Ground truth.** The real ULB `Class` label — `Class=1 ⇒` must deny; `Class=0 ⇒` may permit.

**Headline UER + six primary metrics** (each with naïve **and** cluster‑corrected Wilson 95%
upper bounds, `N_eff = N / DE`, default `DE = 1.7`). **Each rate is taken over the population at
risk of that event — not blindly over all rows:**

| Metric | Adverse event counted | Denominator (population) |
|---|---|---|
| **Unauthorized Execution Rate (UER)** | any row that externalizes without authority (Eq. 7) | **all rows** |
| False Permit Rate (FPR) | permit something ground truth denies | **should‑deny** rows only |
| False Denial Rate (FDR) | deny something ground truth permits | **should‑permit** rows only |
| Replay Determinism Rate (RDR) | broken hash‑chain link | all rows |
| Revocation Compliance | authority‑required row lacking revocation freshness | all rows |
| TOCTOU Violation Rate | ordering inversion on an actuated op | all at‑risk rows |
| Class‑Veto Effectiveness | class‑1 deficit not held in SAFE_STATE | class‑1 rows only |

> UER is the correct name for a "0 events over all N" rate; **FPR must use the should‑deny
> denominator** (a permit can only be "false" where the truth is deny). The smaller denominator
> produces a wider, more honest Wilson bound — the runner reports both.

**Six runtime invariants** (violation count must be 0):
I1 Execution Sovereignty · I2 Non‑Bypassability · I3 Non‑Compensatory Soundness ·
I4 Class‑Level Veto · I5 TOCTOU State‑Consistency · I6 Runtime Sovereignty (composition).

**Negative control (Corollary 2) — two DISTINCT probes.** These are *not* contradictory; one runs
the compensatory rule on the data as‑is, the other is a counterfactual transform:

1. **Actual dataset baseline** — run the compensatory weighted‑sum rule
   (`Γ_w = mean deficit`, permit if `Γ_w < τ`, τ=0.15) **as‑is** on every mapped row. Result on
   this corpus: **0** false permits vs LLC, because every adversarial row fails *multiple* hard
   predicates, so its weighted score stays ≥ τ.
2. **Corollary 2 counterfactual** — reduce each adversarial row to a **single isolated deficit**
   (score `1/13 ≈ 0.077 < τ`). A compensatory gate would then *mask* the failure → **492
   counterfactual false permits**, while the non‑compensatory LLC still denies all. This is the
   structural argument for why non‑compensation matters.

## 9. How to run it

Requirements: Python 3.9+ and `pandas`.

### The one command (recommended) — runs everything, nothing skipped

```bash
pip install pandas

# runs the base LAB v1.0 benchmark + ConcurBench conformance + stress test
# + Fail-Closed Rate test, then builds and opens the unified dashboard.
python3 run_all.py
```

This is the entry point for anyone landing on the repo: by default it runs the **entire**
pipeline end-to-end (base benchmark included, with its full console output), produces
`gamma_report.html` with every section, and **prints a complete results summary of every
layer to the terminal** (base LAB metrics, ConcurBench L1–L4, the 4 stress scenarios, the
FCR families, and the FULL_SPEC §7.1 bands + AIS sub-signals + verdict). Flags:
`--reuse` (fast path — skip the heavy base benchmark and reuse existing artifacts),
`--no-open` (don't open a browser), `--input FILE` (base benchmark input CSV).
Full details of the added layers are in [§14](#14-concurbench-conformance-stress-test--fcr-one-command).

> Note: `run_all.py` expects the mapped golden-trace CSV
> (`GAMMA_G0_CREDITCARD_FULL_mapped.csv`) to exist. On a fresh clone, generate it first with
> the mapping step below (STEP 1), then run `python3 run_all.py`.

### Or run each stage manually

```bash
# STEP 1 — map the raw Kaggle dataset into the golden-trace schema
python gamma_map_raw.py --raw creditcard.csv --out GAMMA_G0_CREDITCARD_FULL_mapped.csv

# STEP 2 — run the monitor + LAB v1.0 benchmark (MAIN).
# This also generates gamma_report.html and AUTO-OPENS it in your browser.
python gamma_test_runner.py \
  --input   GAMMA_G0_CREDITCARD_FULL_mapped.csv \
  --output  gamma_validation_results.csv \
  --summary gamma_summary.json \
  --lab-report gamma_lab_v1_report.json

# STEP 3 — the added conformance layers (each writes its own JSON report)
python concurbench_full.py     # ConcurBench "Document 1" full conformance packet
python stress_test.py          # 4 financial-services stress scenarios (P1–P4)
python fcr_test.py             # dedicated Fail-Closed Rate test
python full_spec_conformance.py # FULL_SPEC.md corrected flow (enforces §7.1 bands, AIS, 3-signal, SVR/FFC)
python concurbench_conformance_check.py  # audit report vs Document-1 fields (exit 0 = all matched)
```

The runner builds [gamma_report.html](gamma_report.html) from the exact results it just
computed (the dashboard's terminal panel is this run's console output) and opens it in your
default browser. Control this with:
`--html <path>` (dashboard output path, default `gamma_report.html`),
`--no-open` (generate the page but don't open a browser),
`--no-html` (skip the dashboard entirely).

The runner auto‑discovers a `GAMMA_*.csv` if `--input` is omitted. Other useful flags:
`--harm-threshold` (θ, default 0.5), `--design-effect` (DE, default 1.7),
`--latency-limit-ms` (default 100), `--latency-sample` (cap timed rows; correctness always
uses all rows), `--no-wal` (CPU‑only latency, skip the WAL fsync).

**Independent‑verification flags** (see [§12](#12-independent-verification-tlc-replay-manifest-reproducibility-bundle)):
`--replay-manifest <path>` (per‑item ERTuple manifest, default `gamma_replay_manifest.jsonl`),
`--no-replay-manifest` (skip it), `--tla-spec <spec.tla>` / `--tla-cfg <cfg.cfg>`
(cryptographically bind the TLC attestation to source → tier 1), `--tlc-log <log>` /
`--tlc-run-command "<cmd>"` (cross‑check the TLC console log → tier 2), and `--bundle <dir>`
(emit the full reproducibility bundle). Full one‑shot run:

```bash
python gamma_test_runner.py \
  --input GAMMA_G0_CREDITCARD_FULL_mapped.csv \
  --replay-manifest gamma_replay_manifest.jsonl \
  --tla-spec spec.tla --tla-cfg spec.cfg \
  --bundle gamma_bundle

# STEP 2b — independently re-verify every decision (no pandas, no dataset)
python gamma_replay_verify.py gamma_replay_manifest.jsonl
```

**Regenerate the dashboard on its own** (without re-running the benchmark) straight from the
JSON reports — this also auto‑opens it:

```bash
python gamma_report_page.py \
  --lab-report gamma_lab_v1_report.json \
  --summary    gamma_summary.json \
  --out        gamma_report.html        # add --no-open to suppress the browser
```

-----------------------------------------------------------------------

## Generator vs Independent Verifier

The benchmark intentionally separates **generation** from
**verification**.

  -----------------------------------------------------------------------
  Component                      Responsibility
  ------------------------------ ----------------------------------------
  `gamma_test_runner.py`         Executes the benchmark, derives
                                 authorization decisions, computes
                                 metrics, generates reports, replay
                                 manifest, and reproducibility bundle.

  `gamma_replay_verify.py`       Independently verifies the replay
                                 manifest using only the emitted JSONL
                                 file. It requires neither the original
                                 dataset nor the benchmark
                                 implementation.
  -----------------------------------------------------------------------

This separation enables third-party auditors to validate execution
integrity without trusting the benchmark runner itself.

------------------------------------------------------------------------

## Replay Manifest Integrity Guarantees

The replay verifier establishes four independent guarantees:

-   **GENESIS anchoring** -- the first decision is correctly anchored.
-   **Replay determinism** -- every record links to the previous SHA-256
    hash.
-   **Ledger integrity** -- each Evidence Quad ledger hash matches the
    recorded hash chain.
-   **Decision consistency** -- Π, Γ_G, Γ_class and PERMIT/SAFE_STATE
    remain internally consistent.

Any violation causes the verifier to fail.

------------------------------------------------------------------------

## Manifest Authenticity

After validating every decision, the verifier recomputes the SHA-256
digest of the complete replay manifest.

When an expected digest is supplied, the verifier confirms the manifest
has not been modified after generation.

``` bash
python gamma_replay_verify.py \
    gamma_replay_manifest.jsonl \
    --expect-sha256 <expected_sha256>
```

------------------------------------------------------------------------

## Replay Integrity

Every authorization decision extends a SHA-256 hash chain.

Changing any historical decision changes every downstream hash, making
post-generation modification immediately detectable.

This provides tamper-evident execution history without requiring the
original dataset.

------------------------------------------------------------------------

## Independent Third-Party Audit

The replay verifier has no dependency on:

-   pandas
-   the benchmark runner
-   the mapped dataset
-   benchmark source code

Any independent reviewer can validate the replay manifest using only the
emitted JSONL file.

------------------------------------------------------------------------

## Exit Codes

The verifier exits with:

-   **Exit Code 0** --- every replay integrity check passed.
-   **Exit Code 1** --- one or more replay integrity violations were
    detected.

------------------------------------------------------------------------

## Internal Verification Checklist

The verifier independently checks:

-   Hash-chain adjacency
-   GENESIS anchor
-   Evidence Quad ledger binding
-   Decision consistency
-   Π consistency
-   Γ_G consistency
-   Γ_class consistency
-   Manifest SHA-256 integrity

------------------------------------------------------------------------

## Reproducibility Statement

Unlike the benchmark runner, the replay verifier does not regenerate
decisions from the dataset.

Instead, it validates that the emitted execution ledger is
cryptographically and logically self-consistent, allowing deterministic
third-party auditing from the replay manifest alone.


## 10. Results we actually got

From [gamma_lab_v1_report.json](gamma_lab_v1_report.json) and
[gamma_summary.json](gamma_summary.json) on the full **284,807‑row** mapped trace:

| Result | Value |
|---|---|
| Rows (N) | 284,807 (nominal 284,315 · adversarial/fraud 492) |
| Derived PERMIT / SAFE_STATE | 284,315 / 492 |
| Match vs ground‑truth `Status` | **100%** |
| **Unauthorized Execution Rate (UER)** — over **all** rows | 0 / 284,807 — Wilson 95% cc upper `< 2.29 × 10⁻⁵` |
| **False Permit Rate (FPR)** — over **should‑deny** rows only | 0 / **492** — Wilson 95% cc upper `< 1.31 × 10⁻²` |
| **False Denial Rate (FDR)** — over **should‑permit** rows only | 0 / **284,315** — Wilson 95% cc upper `< 2.30 × 10⁻⁵` |
| Replay Determinism Rate | 100% — hash‑chain links OK 284,807/284,807 |
| TOCTOU violations | 0 |
| Class‑Veto Effectiveness | 100% — all 492 fraud rows held in SAFE_STATE (0/492 failures) |
| **All six invariants hold** | **Yes** (0 violations each) |
| Negative control — **actual** dataset baseline | weighted‑sum admits **0** false permits vs LLC (adversarial rows fail multiple predicates) |
| Negative control — **Corollary 2 counterfactual** | an isolated single deficit (0.077) `< τ`=0.15 → weighted‑sum would false‑permit **492** rows LLC denies |
| Measured latency | mean **0.0347 ms**, p95 0.0417 ms, p99 0.0517 ms, max 1.25 ms |
| Throughput | **~28,821 decisions/s** (pure software, this host) |

> **Denominator hygiene (why UER ≠ FPR).** A *false permit* can only occur on a row ground truth
> says to deny, so FPR's denominator is the **should‑deny population (492)**, not all 284,807 rows.
> Reporting `0/492` gives a Wilson upper bound near **1.3 × 10⁻²** — far wider (and more honest)
> than the `2.3 × 10⁻⁵` you get by (incorrectly) spreading the same 0 events over all rows. That
> over‑total figure is really the **UER**, which the runner now reports separately.

## Real-Dataset Golden-Trace Validation

In addition to the generated LAB v1.0 benchmark suite, this repository includes
[gamma_test_runner.py](gamma_test_runner.py), a dataset‑level validator for mapped Gamma G‑0
golden traces.

This runner reads a Gamma G‑0 mapped CSV, independently re‑derives the authorization
decision using the L‑DREA externalization‑monitor rule set, computes the six LAB v1.0
metrics, verifies runtime invariants, emits a per‑decision ERTuple replay manifest,
and optionally verifies TLC attestation hashes.

Example:

```bash
python3 gamma_test_runner.py \
  --input GAMMA_G0_CREDITCARD_FULL_mapped.csv \
  --output gamma_validation_results.csv \
  --summary gamma_summary.json \
  --lab-report gamma_lab_v1_report.json \
  --replay-manifest gamma_replay_manifest.jsonl
```

The credit‑card mapped run reported:

- **N = 284,807** rows
- **284,315** derived PERMIT decisions
- **492** derived SAFE_STATE decisions
- **0** unauthorized executions
- **0** false permits
- **0** false denials
- **6/6** runtime invariants satisfied
- **284,807/284,807** replay‑manifest hash‑chain links valid
  (independently re‑verified by [gamma_replay_verify.py](gamma_replay_verify.py):
  0 adjacency failures, 0 ledger‑bind failures, 0 consistency failures)

This is a **mapped‑dataset authorization validation**. It does **not** replace the synthetic
LAB‑A1–A5 benchmark, hardware‑in‑the‑loop evaluation, or formal TLC source‑level reproduction.

### Metric Denominator Discipline

The following denominators are reported separately (a rate is taken over the population at risk
of that event, never blindly over all rows):

| Metric | Denominator |
|---|---|
| Unauthorized Execution Rate | all rows |
| False Permit Rate | should‑deny / adversarial rows |
| False Denial Rate | should‑permit / nominal rows |
| Replay Determinism | all replayed rows |
| Revocation Compliance | rows containing revocation/expiry tests |
| TOCTOU Violation Rate | rows containing stale/revalidation tests |
| Class‑Veto Effectiveness | class‑veto rows |

## 11. The webpage / dashboard

[gamma_report_page.py](gamma_report_page.py) reads **only** the JSON the runner produced and
emits a single self‑contained [gamma_report.html](gamma_report.html) — animated KPI cards,
Chart.js charts, the decision flowchart, a what/how/why narrative, and the **verbatim**
terminal output embedded from `gamma_terminal_full.txt`.

> No numbers are hand‑written in the page — every value is read from the runner's JSON, so the
> dashboard cannot display data the run did not produce. Open it with `open gamma_report.html`.

<img width="1470" height="744" alt="Screenshot 2026-06-30 at 2 00 00 PM" src="https://github.com/user-attachments/assets/92268f57-2b19-4b23-b953-aad05f842968" />


Hero + KPIs — Headline result: decision agreement, unauthorized executions, invariants satisfied, and replay determinism across 284,807 real card transactions.
What we are doing — Re-deriving each authorization decision from the Law of Concurrence (Γ = maxᵢ(1−gᵢ)) and scoring it against the LAB v1.0 metrics.



<img width="1470" height="720" alt="Screenshot 2026-06-30 at 2 00 33 PM" src="https://github.com/user-attachments/assets/14d6ad8b-6bfb-4b60-99cb-ced9e6a15637" />

<img width="1470" height="839" alt="Screenshot 2026-06-30 at 2 00 51 PM" src="https://github.com/user-attachments/assets/c47cd8ab-499b-4f3e-a46e-9ae56f1f7b11" />

How it works — The seven-step authorization pipeline: an action enters with zero authority and leaves only via a permit or a logged SAFE_STATE denial.
Rules & parameters — The exact decision rule, predicates, derived deficits, integrity rules, and run parameters that govern every result on the page.

<img width="1470" height="451" alt="Screenshot 2026-06-30 at 2 01 33 PM" src="https://github.com/user-attachments/assets/bdeaf7f5-8506-4ae3-90fd-76508e2613c7" />

Why it matters — Negative control showing a compensatory weighted-sum would false-permit fraud the non-compensatory gate denies, plus the six LAB metrics on a log scale.


<img width="1470" height="837" alt="Screenshot 2026-06-30 at 2 01 56 PM" src="https://github.com/user-attachments/assets/3953e759-a5d2-4143-811e-4644a727ab96" />

Results — measured this run — Decision distribution, measured per-decision latency vs the §6.0 limit, per-scenario class breakdown, and the six runtime invariants.
Primary metrics & Wilson bounds — The six LAB v1.0 metrics with events/N, observed rate, and cluster-corrected Wilson 95% upper bounds.

<img width="1470" height="254" alt="Screenshot 2026-06-30 at 2 03 04 PM" src="https://github.com/user-attachments/assets/18411014-faba-4590-8366-e6be357f501b" />

LAB v1.0 summary — Appendix-A-style plain-language summary of the run's headline numbers.

<img width="1470" height="793" alt="Screenshot 2026-06-30 at 2 03 23 PM" src="https://github.com/user-attachments/assets/eca641b0-c7d2-4bed-a169-cbd425856ca5" />
<img width="1470" height="793" alt="Screenshot 2026-06-30 at 2 03 36 PM" src="https://github.com/user-attachments/assets/c060a9f8-efbe-459f-a530-c7ba80000d7b" />
<img width="1470" height="274" alt="Screenshot 2026-06-30 at 2 03 53 PM" src="https://github.com/user-attachments/assets/306494ac-e18d-4df5-91b2-9bf1163c7363" />


Reader's questions — answered straight — Why the run scores 100% (tautological integrity proof), why enrichment reaches ~65–70%, why production reaches ~85–92%, plus the full field/predicate mapping and the bank data that would raise the bar.

<img width="1470" height="496" alt="Screenshot 2026-06-30 at 2 04 11 PM" src="https://github.com/user-attachments/assets/826d6eb1-fedd-4133-97e1-d7165133ab1f" />


Verbatim terminal output — The unedited console output from the runner for this exact run.

## 12. Independent verification: TLC, replay manifest, reproducibility bundle

Beyond the benchmark itself, the runner emits three artifacts that let a **third party**
re‑check the results without trusting us — each is genuinely computed, not decorative.

### 12.1 TLC model‑check verification (tiered, not just displayed)

Earlier the runner merely *printed* the trace's TLC state counts. It now **verifies** the
TLC attestation with [`verify_tlc()`](gamma_test_runner.py#L445) — nine checks surfaced in
`gamma_lab_v1_report.json → tlc_verification`, escalating through **verification tiers** as you
supply artifacts:

| Check | What it proves | Tier |
|---|---|---|
| V1 `spec_hash_consistent` | one `TLCSpecHash` across every row (no per‑row tampering) | 0 |
| V2 `cfg_hash_consistent` | one `TLCCfgHash` across every row | 0 |
| V3 `states_constant` | one `TLCTotalStates` across every row | 0 |
| V4 `nontrivial_state_space` | `TLCTotalStates > 0` (model checking actually ran) | 0 |
| V5 `zero_safety_violations` | `Σ TLCViolationCount == 0` (safety held during checking) | 0 |
| V6 `spec_source_binding` *(needs `--tla-spec`)* | `sha256(spec.tla) == TLCSpecHash` | 1 |
| V7 `cfg_source_binding` *(needs `--tla-cfg`)* | `sha256(spec.cfg) == TLCCfgHash` | 1 |
| V8 `log_states_match` *(needs `--tlc-log`)* | log's *distinct states found* == `TLCTotalStates` | 2 |
| V9 `log_no_violation` *(needs `--tlc-log`)* | log reports clean completion, no error | 2 |

| Tier | Meaning | Requires |
|---|---|---|
| `tier0_attestation_consistency_only` | attestation internally sound + zero violations | (default) |
| `tier1_source_bound` | + `.tla`/`.cfg` bytes hash‑match the attested hashes | `--tla-spec`, `--tla-cfg` |
| `tier2_log_cross_checked` | + TLC console log's state count & clean‑completion agree | `--tlc-log` |
| `tier3_fully_reproduced` | re‑run TLC from source | out of this harness's scope (`tla2tools.jar`) |

The checks collapse into one `attestation_digest`; the report also records the verbatim
`--tlc-run-command` and the parsed log (`distinct_states`, violation status). Every optional
check is **genuine** — a wrong `.tla` fails V6, a wrong state count in the log fails V8 (both
demonstrated). The report lists `artifacts_missing_for_full_closure` so you always know what
would raise the tier. Full re‑execution (tier 3) needs the sources + `tla2tools.jar`.

```bash
# Raise TLC to tier 2 by supplying the console log + run command:
python gamma_test_runner.py --input GAMMA_G0_CREDITCARD_FULL_mapped.csv \
  --tla-spec spec.tla --tla-cfg spec.cfg \
  --tlc-log tlc_console.log \
  --tlc-run-command "java -jar tla2tools.jar -config spec.cfg spec.tla"
```

### 12.2 Per‑item ERTuple replay manifest

[`write_replay_manifest()`](gamma_test_runner.py#L539) writes `gamma_replay_manifest.jsonl`:
a header line plus **one self‑describing evidence record per decision** — `proposal_id`,
`ertuple_id`, `policy_hash`, `hash_prev`/`hash_current`, `decision`, `gamma_g/gamma_class/pi`,
and the **Evidence Quad** `{decision, method_version, policy_hash, ledger_hash}`.

[gamma_replay_verify.py](gamma_replay_verify.py) re‑audits that file **with zero
dependencies** (stdlib only — no pandas, no dataset, no runner). Per record it re‑checks:
hash‑chain **adjacency** (`rec[i].hash_prev == rec[i-1].hash_current`, GENESIS‑anchored),
**evidence‑quad↔ledger** binding (`ledger_hash == hash_current`), and record
**self‑consistency** (`decision`, `pi`, `gamma` agree). It also recomputes the manifest's own
SHA‑256 so any post‑hoc edit is caught. Exit code is `0` iff everything passes:

```bash
python gamma_replay_verify.py gamma_replay_manifest.jsonl \
  --expect-sha256 <manifest_sha256_from_the_run>
```

Tested: **PASS** on a clean 1,000‑row manifest; a single flipped byte flips it to **FAIL**.

### 12.3 Full lab reproducibility bundle

`--bundle <dir>` invokes [`write_repro_bundle()`](gamma_test_runner.py#L618), producing a
tamper‑evident package:

- **`MANIFEST.json`** — SHA‑256 + size of every *input*, *source* and *output* file, the exact
  command line, the TLC verification block, the replay‑manifest summary, and a single
  `bundle_digest_sha256` sealing the whole thing;
- **`env.json`** — Python / pandas / platform / method version;
- **`command.txt`** — the literal command that produced the run;
- **`REPRODUCE.md`** — step‑by‑step: check input digests → re‑run → independently verify the
  replay manifest → bind TLC to source → diff outputs (deterministic fields reproduce exactly;
  MEASURED latency is host‑dependent and will differ).

### 12.4 Caveat — what "replay" verifies here

The bundled golden trace's hash chain is **linked but not re‑derivable** from
[gamma_map_raw.py](gamma_map_raw.py)'s canonical formula (its row‑1 SHA‑256 does not
reproduce), which means that trace was emitted by a *different* generator. Replay therefore
verifies **adjacency + genesis anchoring + evidence‑quad binding**, not full per‑row hash
re‑computation. Files produced by `gamma_map_raw.py` itself *are* fully re‑derivable; wiring
the trace generator's exact canonical‑record format into the verifier would upgrade this to
end‑to‑end hash re‑computation.

## 13. Honesty notes & scope

- **Ground truth is real.** Decisions are scored against the genuine ULB `Class` label, not a
  synthetic oracle. The hash chain is genuinely SHA‑256 computed and verified.
- **Latency is real but software‑only.** The measured `~0.02 ms/decision` is predicate eval +
  SHA‑256 hash‑chain advance + HMAC‑SHA256 sign (representative crypto) + optional WAL fsync on
  *this host*. It is **not** comparable to the paper's HSM/FPGA hardware‑in‑the‑loop figures
  (54.3 ms with hardware signing).
- **Signatures are structural.** `AuthoritySignatureValid` / `TOKEN_VALID` are treated as
  predicates in the trace, not live HSM verifications.
- **Scope of the zero‑event claim.** Results are stated **relative to this dataset and rule
  set**. They demonstrate the *non‑compensatory authorization logic behaves correctly on real
  labelled data*; they are not a universal absence‑of‑unauthorized‑execution guarantee, exactly
  as the paper bounds its own claim to its documented threat surface.
- **The mapper is a faithful reconstruction** of the synthetic golden‑trace construction that
  produced the bundled 1,000‑row sample (its first rows reproduce the sample), driven by the
  real fraud label.
- **TLC is verified in tiers, not re‑run.** [§12.1](#121-tlc-modelcheck-verification-tiered-not-just-displayed)
  checks the attestation's consistency + zero‑violation status (tier 0), its cryptographic
  binding to `.tla`/`.cfg` source (tier 1), and its agreement with a supplied TLC console log
  (tier 2). It does **not** re‑execute the model checker (tier 3 needs the sources +
  `tla2tools.jar`). The report always lists what artifacts would raise the tier.
- **Replay verifies adjacency, not full re‑derivation** for the bundled golden trace — see
  [§12.4](#124-caveat--what-replay-verifies-here). Traces produced by `gamma_map_raw.py` are
  fully re‑derivable.

---

## 14. ConcurBench conformance, stress test & FCR (one command)

Three layers were added on top of the base benchmark, all wired into a single entry point and
surfaced on the same dashboard. They run over the **real ULB corpus** (284,807 rows / 492 fraud
/ 13 predicates) — not the placeholder figures from the requirements doc.

### One command runs everything

```bash
# run EVERYTHING end-to-end — nothing skipped (this is the default)
# includes the heavy base benchmark: reads the 451 MB mapped CSV, rebuilds the manifest
python3 run_all.py

# fast path: skip the base benchmark and reuse existing artifacts, run layers 2-6
python3 run_all.py --reuse

# don't auto-open the browser
python3 run_all.py --no-open
```

By default nothing is skipped: a fresh clone runs the full base LAB v1.0 benchmark (with all
its console output) and then every layer, so anyone who runs it sees the complete pipeline.
Use `--reuse` only if you want the fast path on already-generated artifacts.

`run_all.py` chains: **(1)** base LAB v1.0 benchmark → **(2)** [concurbench_full.py](concurbench_full.py)
→ **(3)** [stress_test.py](stress_test.py) → **(4)** [fcr_test.py](fcr_test.py) →
**(5)** [full_spec_conformance.py](full_spec_conformance.py) → **(6)** unified `gamma_report.html`
(base sections **+** ConcurBench **+** stress **+** FCR **+** FULL_SPEC), then prints a
**full terminal results summary** of all five result groups. Each layer also runs standalone
(`python3 concurbench_full.py`, etc.).

### 14.1 ConcurBench full conformance packet — `concurbench_full.py`

Populates **every field** of the "Document 1 — Benchmark Verification Requirements" §18
top-level object and emits `concurbench_full_report.json`.

| Level | What is computed on the real corpus | Result |
|---|---|---|
| **L1 Authorization correctness** | confusion matrix, UER, FPR, FDR, **FCR**, DR + Wilson 95% | **PASS** — FP 0, UER 0, FPR 0 |
| **L2 Adversarial robustness** | 8 synthetic attack families + adaptive attacker + contamination/canary + ablation | **PASS** — 0 false permits, adaptive 0/11,808 |
| **L3 Distributed consistency** | simulated 5-node fleet: consistency, revocation-latency p50/p95/p99, partition, quorum, desync | **PASS** — fleet 1.0, partition fails closed |
| **L4 Replay + auditability** | explicit replay attempts/passes/failures/rate + Evidence Quad + independent verifier subprocess | **PASS** — rate 1.0, verifier PASS, hash-chain PASS |

Also fully populated: report envelope, dataset/repro, HITL governance, ASB (5 families, temporally
ordered event streams), assumptions/limitations, independent-validation status. **Overall verdict:
`COMPLIANT_PASS`** (scope: internal + *simulated*-fleet; third-party audit / hardware-in-the-loop
are honestly disclosed as `not_run` / `not_available`).

### 14.2 Financial-services stress test — `stress_test.py`

Executes the four scenarios from *Lakhowal Stress-Test Analysis (15 May 2026)* as real,
deterministic predicate evaluations against the non-compensatory Γ engine (a single deficit
denies), with per-condition tables and honest out-of-scope markers. Emits `stress_test_report.json`.

| Scenario | Confidence | Effectively tackled | Verdict | Fail-closed |
|---|---|---|---|---|
| P1 — Ghost Treasury Transfer ($28M deepfake CFO wire) | HIGH | 92–95% | STRONG FIT | ✓ (Γ=6) |
| P2 — Sanctions Drift Cascade (3 sub-cases + oracle gap) | MEDIUM | 60–70% | PARTIAL FIT | ✓ (A/C) |
| P3 — Multi-Agent Liquidity Panic (federated + class veto) | HIGH | 75–85% | STRONG FIT | ✓ |
| P4 — Sovereign Cascade (compound simultaneous failure) | MEDIUM-HIGH | 70–80% | DEFENSIBLE | ✓ |

Weighted effectively-tackled ≈ **78.4%**; all in-scope denials fail closed. The oracle problem
(stale truth behind a fresh feed) and upstream data poisoning are reported as **out of scope**, as
in the source document.

### 14.3 Fail-Closed Rate (FCR) test — `fcr_test.py`

Measures `FCR = P(SAFE_STATE | should-deny OR uncertain)` over the 492 real fraud rows plus five
injected uncertainty families (invalid token, stale telemetry, TOCTOU, missing predicate, ambiguous
signature). Adverse event = a **fail-open** (permit under uncertainty). Emits `fcr_test_report.json`.

| Population | n | Fail-open | FCR |
|---|---|---|---|
| should_deny_real | 492 | 0 | 1.0 |
| invalid_token / stale_telemetry / stale_context_toctou / missing_predicate / ambiguous_signature | 4,000 each | 0 | 1.0 |
| **Overall** | **20,492** | **0** | **1.0** (Wilson 95% fail-open bound reported) |

### 14.4 FULL_SPEC conformance — `full_spec_conformance.py`

The corrected, complete authorization flow that **enforces** (not just references) every
FULL_SPEC.md construct the base runner left implicit, over the real telemetry columns in the
corpus (ICS, ΔV, C_om, AIS, Latency_ms, risk scores). Emits `full_spec_conformance_report.json`.

| FULL_SPEC clause | Now enforced in code | Result |
|---|---|---|
| §7.1 acceptance bands (ICS≥0.90, PR_LCB≥0.80, CI_WIDTH≤0.03, ΔV≤0, C≥0.85, PTP≤1ms, latency≤100ms, ER_LOCAL=1.0) | evaluated per-row as predicates feeding Γ (non-compensatory) | all hold; 0 false denials |
| §6.12 Audit-as-Control (AIS) | **live composite** = min(chain integrity, storage availability, signature health, time sync, retention horizon); AIS<0.99 → Γ>0 → run-wide fail-closed | AIS = 1.0 (all sub-signals healthy) |
| §6.7 three-signal closure `P_phys = SIG_COMMIT ∧ SIG_GAMMA ∧ SIG_WATCHDOG` | per-row, watchdog = deadline monitor | 0 closure violations |
| §6.10 WID(T) = (boot nonce, monotonic counter) | emitted | present |
| §11.1 SVR + FFC (Γ-compliance `P(ŷ=0│Γ>0)`) | computed | SVR 0.0 · Γ-compliance 1.0 |
| §1.11 theorem family T0–T9 | **proved in Paper A, not here**; the six runtime invariants I1–I6 that instantiate them are verified | 6/6 invariants hold (0 violations) |
| §10 TLC | total 2,489,446 / distinct 40,192 / MaxClockSkew 1 / 0 violations | reported |
| §9 DET-5 + REVOC_P95 | bounded enforcement horizon + simulated revocation drill | ~16 ms P95 |
| §8 continuity (TVE/DFP/CDM/ASG/ASR/BER) + §0.10 SAFE_STATE absorption | structured | present |

The PR_LCB robustness band independently catches all 492 fraud rows without causing a single
false denial. **Verdict: `FULL_SPEC_CONFORMANT (Tier-S)`** — the software root-of-trust
realization; the Tier-H hardware interlock (HSM three-signal, WID silicon) remains §6/§15 future.

### 14.5 Dashboard

All four added layers render as sections at the bottom of `gamma_report.html`
(server-rendered by `build_extra_sections()` in [gamma_report_page.py](gamma_report_page.py)),
so the base benchmark, ConcurBench conformance, stress scenarios, FCR, and FULL_SPEC
conformance all live on one page.
