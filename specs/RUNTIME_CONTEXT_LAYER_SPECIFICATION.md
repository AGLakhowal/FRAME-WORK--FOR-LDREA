# RUNTIME CONTEXT LAYER (RCL) — ARCHITECTURE SPECIFICATION

**A scientific architecture specification only. No code, no implementation, no redesign of Gamma / L-DREA / FULL_SPEC / paper / predicates / Γ aggregation / SAFE_STATE / LUIPM / LAB / ConcurBench / AgentDojo.**

**Reviewer roles adopted:** IEEE Access Senior Reviewer · Runtime-Systems Architect · Formal-Methods Researcher · AI-Governance Researcher · Distributed-Systems Researcher.

---

## 0. Purpose and the single invariant of this layer

The Runtime Evidence Architecture study established five evidence planes — **A** Transaction, **B** Runtime Context, **C** Authority Infrastructure, **D** External Governance, **E** Derived Runtime Output — and concluded that Gamma consumes evidence from *multiple* planes, of which the transaction dataset is only one.

This document specifies the **minimum Runtime Context Layer (RCL)**: the plane-**B** producer, plus the read-only ports through which the already-assumed A/C/D evidence reaches predicate evaluation. The RCL is an **adapter**, nothing more.

> **RCL Prime Invariant.** The RCL **exposes evidence**; it **never decides**. It owns no predicate, no threshold, no aggregation, no authority model, and no theorem. Every authorization semantic remains in the frozen Gamma engine. The RCL's entire contract is: *given observable execution evidence, surface it in the typed shape the frozen predicates already expect.*

A consequence used throughout: for each predicate the RCL is either its **owner** (plane-B state the RCL genuinely maintains) or a **mere exposer** (plane-A/C/D evidence the RCL passes through a read-only port without authoring). The RCL owns **only** plane-B objects, and only the minimal set below.

---

## 1. What the RCL is and is not

| RCL **is** | RCL **is not** |
|---|---|
| a read model over observable execution evidence (plane B) | an authorization engine |
| a set of typed **ports** exposing A/C/D evidence unchanged | a producer of authority, risk, or transaction facts |
| an assembler of a per-request **EvidenceBundle** for the Predicate Generator | a predicate, a threshold, or an aggregator |
| deterministic, replay-reproducible, Class-blind | a classifier, predictor, or Class consumer |MASTER PROMPT — Explain the Entire Project Like I'm New (No Coding)
You are NOT writing code.

You are acting as

Senior Software Architect

Technical Writer

University Professor

IEEE Research Mentor

Your job is to teach me this entire project.

Assume I wrote the paper but forgot how every file works.

Explain everything in simple English.

Do NOT assume I know the code.

OBJECTIVE
I want to completely understand

how this project starts

how it runs

what every major file does

how the experiments work

where every paper value comes from

what commands I run

what outputs are produced

how the reviewer evidence is generated

At the end I should be able to explain the project to another researcher.

PART 1 — High Level Overview
Explain in very simple language

What is L-DREA?

Why was it created?

What problem does it solve?

How is it different from normal AI safety?

What is Gamma?

What is LAB?

What is ConcurBench?

What is AgentDojo?

How do all of these fit together?

Give analogies whenever possible.

PART 2 — Complete Architecture
Create a beautiful Mermaid flowchart showing the entire repository.

Example:

User
      │
      ▼
Agent
      │
      ▼
Runtime Interceptor
      │
      ▼
Gamma Authorization
      │
      ├── Predicate Engine
      ├── Runtime Context
      ├── Evidence Quad
      ├── Hydra Ledger
      └── Replay
      │
      ▼
Decision
      │
      ▼
Execution
      │
      ▼
Evidence
      │
      ▼
Paper Tables
Include every major module.

PART 3 — Repository Map
Draw the folder structure.

For every important file explain

Purpose

Inputs

Outputs

When it is used

Who calls it

Who depends on it

Do NOT skip files.

PART 4 — Runtime Flow
Show exactly what happens when

I type one command.

For example

python run_all.py
Explain

what starts first

what runs second

what JSON is produced

what CSV is produced

what figures are produced

what reports are produced

what paper tables are produced

Show this as a flowchart.

PART 5 — Every Command
Create a table.

Command

Purpose

Expected runtime

Required software

Output files

Example

For example

python run_all.py
python gamma_test_runner.py
python reproduce_paper.py
python agentdojo_integration/run_audit.py
etc.

Include EVERY executable entry point.

PART 6 — Which Commands Do I Actually Need?
Suppose I'm a normal user.

Give me

Beginner workflow

Research workflow

Paper workflow

Reviewer workflow

Developer workflow

Explain exactly which commands I should run.

PART 7 — How Paper Values Are Produced
Create a flowchart.

Dataset

↓

Experiment

↓

Logs

↓

Statistics

↓

JSON

↓

Tables

↓

Figures

↓

Paper
Explain every step.

PART 8 — Every Experiment
Create a table.

Experiment

Purpose

Input

Output

Paper Table

Paper Figure

Reviewer Comment Addressed

Runtime

Can it be rerun?

PART 9 — Generated Files
After running everything,

show me exactly what new files appear.

Example

paper_tables/

paper_figures/

audit_run/

summary/

reports/

logs/

json/

csv/
Explain each folder.

PART 10 — Explain Like I'm 10 Years Old
Pretend this project is a bank se



| traceable to existing paper / FULL_SPEC constructs | a source of any new scientific construct |

---

## 2. Per-predicate evidence-exposure determination

For every predicate already defined by L-DREA: **(1) producing plane · (2) does RCL expose it? · (3) required observable evidence · (4) evidence nature · (5) RCL owns or merely exposes.**

Note on `Gate_A1…A7` and `Lambda_G`: the paper treats these as a **generic policy-bound node-predicate vector** `G = {g_i}`; the binding of a specific gate *index* to a specific evidence plane is a **deployment policy** already externalised (the AgentDojo `ExecutionBinding`, Layer 2). The RCL therefore does **not** fix a gate's plane; it exposes whatever plane the binding names. The rows below give each gate's plane *for a credit-card-style deployment binding* (representative, not a new semantic).

| Predicate | (1) Plane | (2) RCL exposes? | (3) Required observable evidence | (4) Nature | (5) Owns / Exposes |
|---|---|---|---|---|---|
| `Gate_Ak` bound to amount-limit | **A** | **YES** | transaction `Amount` vs policy limit | externally supplied (payload) | **exposes** (via TransactionPort) |
| `Gate_Ak` bound to velocity/ordering | **B** | **YES** | rolling execution-history window over prior requests | **derived / computed** | **OWNS** (ExecutionHistoryWindow) |
| `Gate_Ak` bound to authority/approval | **C** | **YES** | authority-service boolean (approval/delegation) | externally supplied | **exposes** (via AuthorityPort) |
| `Gate_Ak` bound to sanctions/AML | **D** | **YES** | governance-service boolean | externally supplied | **exposes** (via GovernancePort) |
| `Lambda_G` (node aggregate/authority) | **C** (policy-bound) | **YES** | authority-plane concurrence signal | externally supplied | **exposes** (AuthorityPort) |
| `TOKEN_VALID` | **C** | **YES** | token-store / session validity result | externally supplied | **exposes** (AuthorityPort) |
| `AuthoritySignatureValid` | **C** | **YES** | HSM/PKI signature-verification result | externally supplied | **exposes** (AuthorityPort) |
| `HARM_RISK` | **D** | **YES** | risk/AML service hazard score ∈ [0,1] | externally supplied | **exposes** (GovernancePort) |
| `StaleContext` *(deficit-vector input)* | **B** | **YES** | context-capture vs decision timestamp | **native / computed** | **OWNS** (FreshnessClock) |
| `TelemetryFresh` *(deficit-vector input)* | **B** | **YES** | telemetry heartbeat age vs bound | **native / computed** | **OWNS** (FreshnessClock) |
| commit-before-actuate *(I5 input)* | **B** | **YES** | commit-log & actuation-log events | **native** | **OWNS** (CommitActuateJournal) |
| hash-chain / ledger link *(replay input)* | **B/E** | partial | prior decision's ledger hash | **cached** (from Evidence Collector) | **exposes** (read-only handoff) |
| `ExecutionLegitimacy` | **E** | **NO** | — (Gamma output) | derived by engine | neither (engine owns) |
| `HARM_RISK > θ` deficit | **E-internal** | **NO** | θ is a **policy** constant, not RCL state | engine comparison | neither |
| `ACT_PERMIT` | **E** | **NO** | — (Gamma output `Π`) | derived by engine | neither |
| `SAFE_STATE` | **E** | **NO** | — (Gamma output `¬Π`) | derived by engine | neither |
| `ReasonCodes` | **E** | **NO** | — (Gamma output, from failing deficits) | derived by engine | neither |
| `FirstFailingGate` | **E** | **NO** | — (Gamma output) | derived by engine | neither |
| Γ (deficit aggregate) | **E** | **NO** | — (`max_i d_i`, frozen) | derived by engine | neither |

**Reading.** The RCL **owns exactly four** plane-B objects (velocity window, freshness clock, commit/actuate journal, and their assembled bundle). Everything **C/D** it merely *exposes* through read-only ports; everything **A** it passes through; everything **E** it does not touch at all (those are Gamma outputs). This is the minimum: remove any owned object and a specific already-assumed deficit-vector input (velocity, freshness, or ordering) would have no producer.

---

## 3. Runtime Context Model — object catalogue (minimal, plane-B owned)

Each object: **Name · Purpose · Origin · Producer · Lifetime · Mutability · Update trigger · Consumer · Scientific justification.** Only objects the RCL genuinely **owns** are listed; ports (§4) expose foreign planes and own no state.

### 3.1 `ExecutionContextRecord`
- **Purpose:** the immutable per-request snapshot of runtime context at decision time (request id, decision timestamp, references to the window/freshness/journal readings used).
- **Origin:** assembled at the moment of mediation.
- **Producer:** RCL.
- **Lifetime:** one request; then sealed into the Evidence Collector (Hydra Ledger) for replay.
- **Mutability:** **immutable** once sealed (append-only, consistent with DET4).
- **Update trigger:** a new mediated request arrives at the execution boundary.
- **Consumer:** Predicate Generator (reads), Evidence Collector (persists).
- **Justification:** the paper's replay-determinism / evidence model (Appendix A; DET1 identical-input→identical-decision) requires a reproducible per-decision context snapshot. This object *is* that snapshot; it introduces no new construct.

### 3.2 `ExecutionHistoryWindow`
- **Purpose:** a bounded rolling view of prior mediated requests, exposing **velocity** and **execution ordering** aggregates that a plane-B velocity/ordering gate reads.
- **Origin:** accumulated from prior `ExecutionContextRecord`s.
- **Producer:** RCL.
- **Lifetime:** bounded window `W` (time- or count-bounded); older entries evicted.
- **Mutability:** **append + bounded-eviction** (monotonic within the window).
- **Update trigger:** each sealed request appends; time/count advance evicts.
- **Consumer:** Predicate Generator (velocity/ordering gate evidence).
- **Justification:** velocity and execution-ordering are Runtime-Context signals the paper's deficit vector already references (velocity in the stress model; ordering in §V-F TOCTOU / Invariant I5). The window merely *observes* history; it computes no decision.
- **Note (honest bound):** per-subject windows require a subject key the transaction plane may not provide (see §5); absent a key, only a **global** window is exposable. The RCL exposes what the subject port provides and nothing more.

### 3.3 `FreshnessClock`
- **Purpose:** expose `TelemetryFresh` and `StaleContext` as timestamp-delta readings against policy bounds.
- **Origin:** timestamps of context capture, telemetry heartbeat, and decision.
- **Producer:** RCL (readings); **the bound values are policy constants, not RCL-owned**.
- **Lifetime:** evaluated per request; not retained beyond the record.
- **Mutability:** **read-only derivation** (pure function of timestamps).
- **Update trigger:** per request, at mediation.
- **Consumer:** Predicate Generator (freshness/stale-context deficit inputs), ISB (§V-B).
- **Justification:** §V-F / §VI-B Invariant I5 (TOCTOU) and the ISB freshness term (§V-B) already assume a freshness signal. The clock exposes it; the *threshold* to judge freshness lives in policy, not here.

### 3.4 `CommitActuateJournal`
- **Purpose:** expose the commit-before-actuate ordering evidence (commit-log and actuation-log event references) that Invariant I5 checks.
- **Origin:** substrate commit/actuation events.
- **Producer:** RCL (records event references as reported by the execution substrate).
- **Lifetime:** per actuated request; sealed into the ledger.
- **Mutability:** **append-only**.
- **Update trigger:** a commit event and/or an actuation event is reported for a request.
- **Consumer:** Predicate Generator / the frozen ordering check ([gamma_test_runner.py:918-924](gamma_test_runner.py#L918-L924)).
- **Justification:** §V-F commit-before-actuate; Invariant I5. The journal exposes ordering facts; it does not define the ordering rule (which is frozen).

### 3.5 `EvidenceBundle`
- **Purpose:** the single per-request, read-only aggregate handed to the Predicate Generator — the union of (TransactionPort facts, the three plane-B readings above, AuthorityPort booleans, GovernancePort scores), in the exact typed shape the frozen predicates expect.
- **Origin:** assembled at mediation from ports + owned objects.
- **Producer:** RCL.
- **Lifetime:** one request.
- **Mutability:** **immutable** once assembled.
- **Update trigger:** per request.
- **Consumer:** Predicate Generator → GammaBridge → frozen `evaluate_decision`.
- **Justification:** this is the "adapter" surface itself. It maps observable evidence into the predicate input schema **without** adding semantics — the same role the AgentDojo `PredicateEvaluator` input already plays ([predicate_evaluation.py](agentdojo_integration/interception/predicate_evaluation.py)). It owns *shape*, never *meaning*.

**Minimality claim.** Four owned state objects (3.2–3.4 produce the three plane-B deficit inputs; 3.1/3.5 are the snapshot and the assembled view). No fifth object is required by any already-assumed predicate; adding one would risk inventing a construct.

---

## 4. Read-only ports (exposure of foreign planes — RCL owns no state here)

| Port | Exposes plane | Surfaces | Owns state? | Foreign producer |
|---|---|---|---|---|
| **TransactionPort** | **A** | native + derived transaction facts (§6) | **No** | the transaction source / dataset interpreter |
| **AuthorityPort** | **C** | `TOKEN_VALID`, `AuthoritySignatureValid`, authority/approval booleans, `Lambda_G` concurrence | **No** | Authority Service (token store, HSM/PKI, approval workflow) |
| **GovernancePort** | **D** | `HARM_RISK` hazard score, sanctions/AML/compliance booleans | **No** | External Governance services |
| **PolicyPort** | policy | threshold directives, θ, limit constants (read for *shape/routing* only; values frozen in policy) | **No** | frozen policy manifests ([frozen_policy.py](agentdojo_integration/interception/frozen_policy.py)) |

Ports are typed read interfaces. They guarantee the RCL cannot *fabricate* C/D/A evidence: if a port has no backing producer in a given deployment arm (e.g. no Authority Service in the bare credit-card arm), it returns an explicit **evidence-absent** signal — never a synthesised value, never `Class`.

---

## 5. Transaction Evidence — precise contribution (never mixed)

What the transaction dataset legitimately contributes, strictly separated:

- **Native transaction facts (A, real):** `Amount`, `Time` — semantically meaningful observable request fields. These flow through TransactionPort unchanged.
- **Derived transaction evidence (A→, deterministic, Class-blind):** *feature inputs* a governance risk service may consume (e.g. the anonymised `V1…V28` as an opaque embedding). **These are inputs to plane D, not predicates themselves.** The RCL never converts them into a predicate; it only carries them to the GovernancePort's backing service if one exists.
- **Runtime evidence (B):** **NOT from the dataset.** Produced by RCL objects 3.2–3.4. A transaction record does not contain execution history, freshness, or commit/actuate events.
- **Authority evidence (C):** **NOT from the dataset.** Exposed only via AuthorityPort from an Authority Service.
- **Governance evidence (D):** **NOT from the dataset.** The hazard/sanctions outputs are service results exposed via GovernancePort; the dataset may supply *features* to that service but not the *score*.

**Anti-mixing rule.** The RCL must keep these five categories in disjoint typed channels. Collapsing a D-score or a B-window into an A-fact (as the previous dataset-first redesign implicitly did for HARM_RISK/velocity) is prohibited: it re-creates the plane inversion the architecture study identified.

**Honest gap.** The dataset provides **no subject/account identifier**, so plane-B windows (3.2) can be **global only**; per-subject velocity/history is unexposable here and must not be faked. This is a property of the transaction source, not a limit of the RCL.

---

## 6. Authority Infrastructure — assumed evidence (identified, not implemented)

The paper assumes these authority-plane values (Eq. 7 `Valid(Token)`; ISB §V-B; node-predicate concurrence §V):

| Assumed value | Native origin | Exposed via | Present in credit-card arm? |
|---|---|---|---|
| Authority token validity (`TOKEN_VALID`) | token store / session manager | AuthorityPort | No (evidence-absent) |
| Cryptographic signature (`AuthoritySignatureValid`) | HSM / PKI | AuthoritySignaturePort→AuthorityPort | No |
| Delegation / approval chain | approval workflow service | AuthorityPort | No |
| Identity verification | identity provider | AuthorityPort | No |
| Policy binding (`PolicyHash`) | frozen policy manifests | PolicyPort | Yes (already emitted) |
| Execution authority (node concurrence `Lambda_G`) | authority plane | AuthorityPort | No |

The RCL **only names the required evidence and its port**; it invents no token format, no signature scheme, no approval model. Where a producer is absent, the port returns evidence-absent and the frozen fail-closed policy (FULL_SPEC 2.3 / 0.10 non-default-permit) governs — unchanged.

---

## 7. Governance Services — assumed outputs (external vs runtime)

| Assumed output | External service or runtime state? | Exposed via |
|---|---|---|
| Risk / hazard score (`HARM_RISK`) | **external service** (online risk/AML) | GovernancePort |
| AML screening result | **external service** | GovernancePort |
| Sanctions oracle result | **external service** | GovernancePort |
| Compliance / enterprise policy | **external policy** (frozen manifests) | PolicyPort |
| Organisational rules / θ, limits | **policy state** (frozen) | PolicyPort |

Governance **scores** (risk/AML/sanctions) are *external service outputs* — the RCL exposes, never computes them. Governance **policy** (thresholds, limits, enterprise rules) is *frozen policy state* read through PolicyPort for routing/shape only. Neither category is RCL-owned.

---

## 8. Runtime execution flow — producers and consumers

```
 Transaction (request)                              PRODUCER → CONSUMER
   │  Amount, Time [, V1..V28 features]
   ▼
 Transaction Evidence           produced by: Transaction source   → consumed by: TransactionPort (RCL, read-only)
   │
   ▼
 Runtime Context Layer (RCL)    produced by: RCL (owns B)         → consumed by: Predicate Generator
   ├─ ExecutionHistoryWindow    (velocity, ordering)              [OWNED]
   ├─ FreshnessClock            (TelemetryFresh, StaleContext)    [OWNED]
   ├─ CommitActuateJournal      (commit-before-actuate)           [OWNED]
   ├─ ExecutionContextRecord    (per-request snapshot)            [OWNED]
   └─ EvidenceBundle            (assembled read-only view)        [OWNED]
   │        ▲ read-only ports (RCL owns no state):
   │        ├─ AuthorityPort  ← Authority Infrastructure  produced by: Authority Service (C)   [EXPOSED]
   │        ├─ GovernancePort ← Governance Services       produced by: Risk/AML/Sanctions (D)  [EXPOSED]
   │        └─ PolicyPort     ← frozen policy manifests   produced by: ScientificPolicy         [EXPOSED]
   ▼
 Predicate Evaluation           produced by: Predicate Generator  → consumed by: GammaBridge
   │  (reads EvidenceBundle; authors no threshold — reads directives from PolicyPort)
   ▼
 Γ  (FROZEN)                     produced by: evaluate_decision    → consumed by: decision path
   │  Γ = max_i d_i ; Π = 1[Γ=0]
   ▼
 SAFE_STATE / ACT_PERMIT (E)     produced by: Gamma                → consumed by: execution boundary
   │
   ▼
 Evidence Quad (E)               produced by: Gamma                → consumed by: Evidence Collector
   │
   ▼
 Hydra Ledger                    produced by: Evidence Collector   → consumed by: replay verifier (gamma_replay_verify.py)
   │
   ▼
 Ground-Truth Evaluation         Class enters HERE and ONLY here   → FPR / FDR / UER
```

Every node left of "Ground-Truth Evaluation" is **Class-blind**. The RCL sits entirely inside that Class-blind region and produces only plane-B evidence + exposure of A/C/D.

---

## 9. Traceability — every RCL object back to the frozen specification

| RCL object | Paper section | FULL_SPEC section | Definition / Theorem / Invariant | Predicate it feeds | Consumer |
|---|---|---|---|---|---|
| `ExecutionContextRecord` | Appendix A (replay/evidence) | §Appendix A format | DET1 (decision determinism) | all (snapshot) | Predicate Generator, Evidence Collector |
| `ExecutionHistoryWindow` | §V (predicate vector); velocity in stress model | §7.1 band inputs | node-predicate `g_i` (velocity/ordering) | velocity/ordering `Gate_Ak` | Predicate Generator |
| `FreshnessClock` | §V-B (ISB freshness); §V-F | §VI-B I5 | Invariant I5 (TOCTOU); ISB | `TelemetryFresh`, `StaleContext` | Predicate Generator, ISB |
| `CommitActuateJournal` | §V-F (commit-before-actuate) | §VI-B I5 | Invariant I5 | commit-before-actuate | frozen ordering check ([:918-924](gamma_test_runner.py#L918-L924)) |
| `EvidenceBundle` | §IV-B (LLC input) | 2.3 / 0.10 | Definition 1/2 (mediation) | assembled deficit vector | GammaBridge → `evaluate_decision` |
| TransactionPort | §V (observable request) | — | Definition 1 (externalisation boundary) | amount-limit `Gate_Ak` | Predicate Generator |
| AuthorityPort | Eq. 7 `Valid(Token)`; §V-B | 2.3 / 0.10 | Definition 2 (complete mediation) | `TOKEN_VALID`, `AuthoritySignatureValid`, authority gates, `Lambda_G` | Predicate Generator |
| GovernancePort | §V (HARM admissibility) | §7.1 | HARM threshold deficit | `HARM_RISK` | Predicate Generator |
| PolicyPort | §VI (policy); manifests | 2.3 / 0.10; §7.1 | Definition 4; non-default-permit | θ, limits, directives (shape only) | Predicate Generator |

**Untraceable objects: none.** Every object above corresponds to an evidence input the paper/FULL_SPEC already assumes; each is an *exposure* of that assumption, not a new construct. (Where a FULL_SPEC subsection number is not explicitly enumerable from the repository, the row cites the named construct — ISB §V-B, commit-before-actuate §V-F, Invariant I5 §VI-B, Definitions 1/2/4, FULL_SPEC 2.3/0.10 — rather than inventing a number.)

---

## 10. Implementation readiness (architecture-complete, no implementation)

The specification fixes, without further scientific decisions: the **owned object set** (§3, exactly five), their **lifetime/mutability/triggers** (§3), the **port set** (§4, exactly four read-only ports), the **strict category separation** of transaction/runtime/authority/governance evidence (§5–§7), the **producer→consumer flow** (§8), and full **traceability** (§9). An engineer implementing this makes only *engineering* choices (data structures, window representation); every *scientific* choice (what each object means, what predicate it feeds, where thresholds live) is already pinned to the frozen spec. The RCL owns shape and observation; it never owns meaning.

---

## 11. FINAL VALIDATION

**1. Does the RCL introduce any new scientific construct?**
**No.** Every RCL object is an *exposure* of an evidence input the paper/FULL_SPEC already assumes (§9 traceability, zero untraceable objects). It defines no predicate, threshold, theorem, or semantic.

**2. Does it change Gamma?**
**No.** Gamma's `evaluate_decision` / vectorised path ([gamma_test_runner.py:876-892](gamma_test_runner.py#L876-L892)) is consumed unchanged via the existing GammaBridge. The RCL sits strictly upstream, producing the same input schema.

**3. Does it change L-DREA?**
**No.** It occupies an evidence-producer role the architecture already presumes (plane B) and adds read-only ports for planes A/C/D that are also already presumed. No architectural semantic is altered.

**4. Does it change any theorem?**
**No.** Theorems T0–T9 (proved in Paper A) and invariants I1–I6 are statements over the decision and deficit vector; the RCL changes *where the vector's evidence is read from*, not the vector's meaning or any proof.

**5. Does it change any predicate?**
**No.** The predicate set and each predicate's definition are untouched; the RCL supplies each predicate's already-defined input from its architecturally-correct plane.

**6. Does it change authorization semantics?**
**No.** `Γ = max_i d_i`, `Π = 1[Γ=0]`, SAFE_STATE fail-closed, ISB, commit-before-actuate — all frozen. The RCL decides nothing; the Prime Invariant (§0) forbids it.

**7. Does it remove the label leakage?**
**Yes — structurally.** Leakage arose because predicate evidence was authored from `Class` ([gamma_map_raw.py:150-181](gamma_map_raw.py#L150-L181)) and read back. Under this specification, every deficit-vector input has a **non-Class producer**: plane-B inputs come from RCL-owned observation (history/freshness/ordering), plane-A from the TransactionPort (`Amount`/`Time`), plane-C/D from Authority/Governance ports (or an explicit *evidence-absent* signal, never a synthesised value, never `Class`). `Class` has no port and no producer inside the Class-blind region; it can enter **only** at Ground-Truth Evaluation (§8). Because no predicate can be a function of `Class`, the derived decision can now genuinely agree *or disagree* with `Class`, making FPR/FDR/UER real measurements. The leakage is removed by *construction of the evidence boundary*, not by tuning.

---

*Architecture specification only. No code written, no implementation proposed, no modification to Gamma, L-DREA, FULL_SPEC, the paper, the predicates, Γ aggregation, SAFE_STATE, LUIPM, LAB, ConcurBench, or AgentDojo. Existing components are cited by location solely to anchor the RCL's exposure role in the frozen scientific contribution.*
