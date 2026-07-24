# RUNTIME EVIDENCE ARCHITECTURE

**An architectural research document (no code, no implementation, no redesign of Gamma / L-DREA / paper / predicates / runtime / benchmark).**

**Reviewer roles adopted:** IEEE Access Senior Reviewer · Runtime-Systems Architect · Formal-Methods Researcher · AI-Governance Researcher · Distributed-Systems Researcher.

**The question this document answers.** The previous redesign (`PREDICATE_GENERATION_REDESIGN.md`) asked *"which dataset field can approximate each predicate?"* — a **dataset-first** framing. This document steps back and asks the prior, more fundamental question: **according to the L-DREA architecture in the paper and FULL_SPEC, where should each authorization predicate naturally originate?** The inquiry is architectural, not computational. We do **not** ask "how do we compute this predicate"; we ask "what part of a real L-DREA deployment is the *native producer* of this evidence."

**Method.** For every predicate we assign exactly one **natural evidence source** from the five-category model (A–E), state whether the credit-card dataset *should* be its provider (YES / PARTIALLY / NO), and — when NO — name the runtime component that should, and check whether that component **already exists in this repository** (with `file:line`) or is an architectural slot yet to be occupied.

---

## 1. The five evidence sources (source-of-truth model)

| Code | Source | Native producer in a real L-DREA deployment | Examples |
|---|---|---|---|
| **A** | **Transaction Evidence** | the request payload itself | Amount, Time, merchant, action, observable request fields |
| **B** | **Runtime Context** | the execution substrate observing itself over time | execution history, current state, context freshness, prior authorizations, telemetry, execution ordering, session state |
| **C** | **Authority Infrastructure** | the identity/authority plane | authority token, approval chain, delegation, cryptographic signature, identity verification, policy-engine authority |
| **D** | **External Governance** | organisational governance services | compliance/AML engine, risk service, sanctions oracle, enterprise policy |
| **E** | **Derived Runtime Output** | Gamma itself (the frozen engine) | Γ, SAFE_STATE, ReasonCodes, ExecutionLegitimacy, ACT_PERMIT, FirstFailingGate, Status |

**Architectural axiom (from the paper / FULL_SPEC).** L-DREA is an *execution-governance* architecture: it *mediates* actions by evaluating evidence that the surrounding runtime, authority, and governance planes **already produce**. Predicates are **read from** those planes; they are not *manufactured from the request payload*. The transaction payload (A) is only one of five inputs — the *smallest* one. Any framing that treats the dataset as the default home for all predicates inverts the architecture.

---

## 2. Per-predicate evidence-origin determination

For each predicate: **scientific meaning → natural source (A–E) → should the credit-card dataset provide it? → if NO, which runtime component should → does that component already exist in Gamma?**

---

### 2.1 Amount-limit gate (a concrete `Gate_Ak`)
1. **Meaning.** Amount within authorised limit — bounded-authority admissibility.
2. **Natural source: A (Transaction Evidence).** The amount is intrinsic to the request.
3. **Dataset should provide? YES.** `Amount` is a genuine, semantic transaction field.
4/5. N/A — correctly dataset-sourced.

### 2.2 Velocity / temporal-ordering gate (a concrete `Gate_Ak`)
1. **Meaning.** Request rate / ordering within a safe envelope.
2. **Natural source: B (Runtime Context).** Velocity is a *property of execution history*, not of a single request. The raw timestamp is A; the *aggregate over prior executions* is B.
3. **Dataset should provide? PARTIALLY.** `Time` gives global ordering, but the *per-subject* history that makes velocity meaningful requires an account/session key the dataset lacks.
4. **Component that should provide it:** a **Runtime Context Layer** maintaining per-subject execution history.
5. **Exists in Gamma?** **Partially.** The AgentDojo interception reads live environment state to build recognised-sets ([predicate_evaluation.py](agentdojo_integration/interception/predicate_evaluation.py) — "reads env state to compute a NAMED recognized-set"); that is the *pattern* of a Runtime Context reader, but there is no persistent per-subject history store for the credit-card arm. Architectural slot: **Execution Context Layer / Runtime Context Generator** (not yet occupied for this arm; must not be faked from the dataset).

### 2.3 HARM_RISK (and its `> θ` deficit)
1. **Meaning.** Domain hazard magnitude of the action.
2. **Natural source: D (External Governance — risk service).** In a real deployment the hazard number is emitted by an online risk/AML service; L-DREA *consumes* it. It is **not** a transaction field and **not** something the gate computes itself.
3. **Dataset should provide? PARTIALLY / NO.** The dataset can at most supply *input features* to a risk service (the anonymised `V1…V28`), but the **hazard score itself is a governance-service output**, not dataset content. Treating a statistical feature transform as "the hazard" (as the previous redesign proposed) quietly relocates a **D** signal into **A** — defensible only as an explicitly-labelled proxy, never as the architecture's intended source.
4. **Component that should provide it:** an **External Governance / Risk-Service interface** feeding a per-request hazard score to the predicate generator.
5. **Exists in Gamma?** **No** dedicated risk-service interface exists; `HARM_RISK` is currently consumed as a pre-supplied column ([gamma_test_runner.py:871](gamma_test_runner.py#L871)). Architectural slot: **Policy/Governance Service (risk sub-service)**. The θ ceiling is a **policy** constant (source D/policy engine), not a dataset artefact.

### 2.4 Node gates `Gate_A1…A7`, `Lambda_G` — the authority/approval slice (all beyond 2.1–2.2)
1. **Meaning.** The generic predicate vector `G = {g_1…g_n}` — distinct authorization conditions (dual-control, sanctions/entity clearance, KYC-token freshness, approval-chain completeness, deterministic-governance state; enumerated concretely in `stress_test.py`).
2. **Natural source: C (Authority Infrastructure)** primarily, with sanctions/AML members in **D**.
3. **Dataset should provide? NO.** These are properties of the *authority plane*, categorically absent from a `Time/Amount/V1…V28` record. Anonymised PCA axes cannot be assigned named authority semantics without fabrication.
4. **Component that should provide it:** the **Authority Service** (token/approval/delegation) and, for sanctions members, the **Policy/Governance Service**.
5. **Exists in Gamma?** **Conceptually yes, for environments that carry authority state.** The AgentDojo interception derives applicable predicate families from real environment state via the frozen policy manifests ([governed_runtime.py](agentdojo_integration/interception/governed_runtime.py); [frozen_policy.py](agentdojo_integration/interception/frozen_policy.py), 7 immutable manifests at Merkle root `ce8c8467…`). So the *Policy/Authority evaluation machinery already exists* — it simply has **no authority evidence to read in the bare credit-card arm**. Architectural home: **Authority Service + Policy Service** (present for AgentDojo; empty for credit-card).

### 2.5 TOKEN_VALID
1. **Meaning.** `Valid(Token)` — authority-token validity (Eq. 7, ISB).
2. **Natural source: C (Authority Infrastructure).**
3. **Dataset should provide? NO.** No token exists in a credit-card transaction.
4. **Component:** **Authority Service** (token store / session manager).
5. **Exists in Gamma?** The predicate is *consumed* (`NODE_GATE_COLS`, [gamma_test_runner.py:128](gamma_test_runner.py#L128)) and is genuinely exercised where token evidence exists — the FCR `invalid_token` family ([fcr_test.py:16](fcr_test.py#L16)) and AgentDojo env state. No standalone token store; architectural slot: **Authority Service**.

### 2.6 AuthoritySignatureValid
1. **Meaning.** Cryptographic authority-signature validity.
2. **Natural source: C (Authority Infrastructure).**
3. **Dataset should provide? NO.** No signature field exists.
4. **Component:** **Authority Service** (HSM / PKI verification).
5. **Exists in Gamma?** Consumed as a predicate ([gamma_test_runner.py:129](gamma_test_runner.py#L129)); exercised in the FCR `ambiguous_signature` family ([fcr_test.py:20](fcr_test.py#L20)). No HSM/PKI component. Slot: **Authority Service**.

### 2.7 StaleContext · TelemetryFresh
1. **Meaning.** TOCTOU freshness — context staleness and telemetry age (deficit vector, [gamma_test_runner.py:873-874](gamma_test_runner.py#L873-L874); ISB).
2. **Natural source: B (Runtime Context).** Freshness is a *substrate-observed* temporal property.
3. **Dataset should provide? NO** (StaleContext) / **weak PARTIAL** (TelemetryFresh, via `Time` gaps — but that conflates sampling cadence with telemetry age).
4. **Component:** **Execution Context Layer** (context-capture vs decision timestamps; telemetry heartbeat).
5. **Exists in Gamma?** Genuinely exercised in FCR `stale_telemetry` / `stale_context_toctou` families ([fcr_test.py:17-18](fcr_test.py#L17-L18)) and ConcurBench desync levels. No generic context-freshness collector for the credit-card arm. Slot: **Execution Context Layer**.

### 2.8 Commit-before-actuate ordering (I5 / TOCTOU)
1. **Meaning.** Actuated op must have `CommitTimestamp ≤ ActuateTimestamp` (paper §V-F; [gamma_test_runner.py:918-924](gamma_test_runner.py#L918-L924)).
2. **Natural source: B (Runtime Context — execution ordering).**
3. **Dataset should provide? NO.** There are no commit/actuate events in a transaction record; the current mapper *synthesises* both timestamps ([gamma_map_raw.py:128-129](gamma_map_raw.py#L128-L129)).
4. **Component:** **Execution Context Layer** (commit-log + actuation-log).
5. **Exists in Gamma?** The *check* exists ([:918-924](gamma_test_runner.py#L918-L924)); the *event evidence* is substrate-native. Slot: **Execution Context Layer / Evidence Collector**.

### 2.9 Hash chain / replay evidence (HASH_prev, HASH_current)
1. **Meaning.** Append-only Hydra Ledger continuity (DET4).
2. **Natural source: B/E** — produced by the **Evidence Collector** as decisions are recorded.
3. **Dataset should provide? NO.** A ledger is generated by the runtime at decision time, not carried by the request.
4. **Component:** **Evidence Collector (Hydra Ledger writer).**
5. **Exists in Gamma?** **Yes** — `write_replay_manifest` ([gamma_test_runner.py:635](gamma_test_runner.py#L635)) and the independent verifier `gamma_replay_verify.py`. This is correctly runtime-sourced already (the ledger is *emitted*, though note: today the mapper pre-writes the hashes — an artefact of the dataset-first pipeline, not the architecture).

### 2.10 Derived outputs — Γ, GammaZero, ACT_PERMIT, ExecutionLegitimacy, SAFE_STATE, ISB, ReasonCodes, FirstFailingGate, Status
1. **Meaning.** The decision and its explanation.
2. **Natural source: E (Derived Runtime Output).** These are **outputs of the frozen Γ engine**, functions of the A/B/C/D evidence — never inputs.
3. **Dataset should provide? NO — categorically.** The current mapper authoring these from `Class` ([gamma_map_raw.py:154-181](gamma_map_raw.py#L154-L181)) is the architectural inversion at the root of the leakage: it writes **E** (and its C/D/B inputs) from the *label*, then reads them back.
4. **Component:** **Gamma** itself.
5. **Exists in Gamma?** **Yes** — [gamma_test_runner.py:876-892](gamma_test_runner.py#L876-L892), reused unchanged by the AgentDojo bridge ([gamma_bridge.py](agentdojo_integration/interception/gamma_bridge.py)). Nothing to add; the duty is to **stop authoring these into the dataset**.

---

## 3. Consolidated evidence-origin table

| Predicate | Natural source | Dataset should provide? | Correct producing component | Already in Gamma? (where) |
|---|---|---|---|---|
| Amount-limit gate | **A** Transaction | **YES** | Transaction Interpreter | inherent (dataset) |
| Velocity / ordering gate | **B** Runtime Context | **PARTIALLY** (global only) | Runtime Context Layer | pattern only ([predicate_evaluation.py](agentdojo_integration/interception/predicate_evaluation.py)) |
| HARM_RISK / `>θ` | **D** External Governance (risk) | **PARTIALLY / NO** | Risk Service (+ policy θ) | consumed as column; no risk service |
| `Gate_A*`,`Lambda_G` authority slice | **C** Authority (+ D sanctions) | **NO** | Authority + Policy Service | eval machinery yes ([frozen_policy.py](agentdojo_integration/interception/frozen_policy.py), [governed_runtime.py](agentdojo_integration/interception/governed_runtime.py)); no authority evidence in this arm |
| TOKEN_VALID | **C** Authority | **NO** | Authority Service (token store) | consumed; FCR `invalid_token` ([fcr_test.py:16](fcr_test.py#L16)) |
| AuthoritySignatureValid | **C** Authority | **NO** | Authority Service (HSM/PKI) | consumed; FCR `ambiguous_signature` ([fcr_test.py:20](fcr_test.py#L20)) |
| TelemetryFresh | **B** Runtime Context | **weak PARTIAL** | Execution Context Layer | FCR `stale_telemetry` ([fcr_test.py:17](fcr_test.py#L17)) |
| StaleContext | **B** Runtime Context | **NO** | Execution Context Layer | FCR `stale_context_toctou` ([fcr_test.py:18](fcr_test.py#L18)) |
| Commit-before-actuate | **B** Runtime Context | **NO** | Execution Context Layer | check exists ([:918-924](gamma_test_runner.py#L918-L924)); events substrate-native |
| Hash chain / ledger | **B/E** Evidence Collector | **NO** | Evidence Collector | **yes** ([:635](gamma_test_runner.py#L635), `gamma_replay_verify.py`) |
| Γ/SAFE_STATE/ACT_PERMIT/ISB/ReasonCodes/FirstFailingGate/Status | **E** Derived | **NO (never)** | Gamma | **yes** ([:876-892](gamma_test_runner.py#L876-L892)) |

**Reading of the table.** Exactly **one** predicate (Amount) is natively **A** (dataset). One is **B-with-a-thin-A-shadow** (velocity, partial). One is **D** proxied weakly through **A** (HARM_RISK). **Seven** are **C / B** — authority and runtime-context evidence the dataset **cannot and should not** provide. Seven more are **E** — engine outputs that must never be authored at all. The dataset is the native home of roughly *one* predicate, not thirteen.

---

## 4. Final architecture

Legend of provenance: **[DATA]** dataset · **[RUN]** runtime/execution environment · **[AUTH]** authority infrastructure · **[POL]** policy/governance · **[ENGINE]** Gamma (frozen).

```
                          ┌───────────────────────── LABEL FIREWALL ─────────────────────────┐
                          │  Class is INADMISSIBLE everywhere left of the Evaluation node     │
 ┌──────────────────────┐ │
 │  Credit-Card Dataset │ │   Time, Amount, V1..V28            Class ─────────────────────────┼──► held aside
 │        [DATA]        │ │        │
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Transaction Interpreter  [DATA→request]      (source A)
 │ Transaction Evidence │ │  • Amount, Time as observable request fields
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Runtime Context Layer    [RUN]               (source B)
 │   Runtime Context    │ │  • execution history, velocity, context freshness,
 │        [RUN]         │ │    telemetry age, execution ordering, session state
 └──────────┬───────────┘ │    (native producer of B-class predicates; NOT the dataset)
            ▼             │        │
 ┌──────────────────────┐ │  Authority Infrastructure [AUTH]              (source C)
 │ Authority Service    │ │  • token validity, signatures, approval chain, delegation, identity
 │        [AUTH]        │ │    (native producer of TOKEN_VALID / AuthoritySignatureValid / authority gates)
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Policy / Governance Engine [POL]             (source D)
 │    Policy Engine     │ │  • risk/AML/sanctions score (HARM_RISK), thresholds θ, enterprise rules
 │        [POL]         │ │    (frozen manifests: frozen_policy.py root ce8c8467…)
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Predicate Generator      [assembles A+B+C+D → deficit vector G]
 │ Predicate Generator  │ │  • reads each g_i from its NATIVE source above; authors nothing from Class
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Gamma (FROZEN)           [ENGINE]            (source E outputs)
 │        Gamma         │ │  • Γ = max_i d_i ; Π = 1[Γ=0] ; SAFE_STATE ; ReasonCodes ; Evidence Quad ; Hydra Ledger
 └──────────┬───────────┘ │        │
            ▼             │        ▼
 ┌──────────────────────┐ │  Decision  PERMIT / SAFE_STATE
 │       Decision       │ │
 └──────────┬───────────┘ │        │
            ▼             └────────┼──────────────────────────────────────────────────────────┘
 ┌──────────────────────┐          ▼
 │ Ground-Truth Eval    │◄──────  Class enters HERE and ONLY here → FPR / FDR / UER (genuinely measurable)
 └──────────────────────┘
```

**Which plane owns which evidence:**
- **Dataset [DATA]** → Transaction Interpreter only: `Amount`, `Time` (source A), and *raw features* that a risk service may consume.
- **Runtime [RUN]** → Runtime Context Layer / Execution Context Layer: velocity, ordering, freshness, telemetry, commit/actuate events, ledger (source B).
- **Authority [AUTH]** → Authority Service: tokens, signatures, approval/delegation (source C).
- **Policy [POL]** → Policy/Governance Engine: HARM_RISK/risk/AML/sanctions, thresholds (source D).
- **Execution environment / engine [ENGINE]** → Gamma: all derived outputs (source E).

---

## 5. Component existence summary (does the architecture's producer already exist?)

| Architectural component | Exists in this repo? | Evidence |
|---|---|---|
| Transaction Interpreter (A) | trivially (dataset read) | `gamma_map_raw.py` reads `Amount`/`Time` |
| **Policy / Governance Engine (D)** | **YES** | frozen 7-manifest policy at Merkle root `ce8c8467…` ([frozen_policy.py](agentdojo_integration/interception/frozen_policy.py)), Layer-2 bindings ([execution_binding.py](agentdojo_integration/interception/execution_binding.py)) |
| **Execution boundary / interposition (RUN)** | **YES** | [governed_runtime.py](agentdojo_integration/interception/governed_runtime.py) — sole chokepoint, fail-closed to SAFE_STATE |
| **Runtime Context / env-state reader (B)** | **YES (as a pattern)** | [predicate_evaluation.py](agentdojo_integration/interception/predicate_evaluation.py) reads live env state into recognised-sets |
| **Evidence Collector / Hydra Ledger (B/E)** | **YES** | `write_replay_manifest` ([:635](gamma_test_runner.py#L635)) + independent `gamma_replay_verify.py` |
| **Gamma engine (E)** | **YES** | [:876-892](gamma_test_runner.py#L876-L892); reused via [gamma_bridge.py](agentdojo_integration/interception/gamma_bridge.py) |
| **Authority Service (C)** | **NO** (evidence is env-derived where present; no token/HSM store) | consumed as predicates; exercised only via FCR injections / AgentDojo env |
| **Risk-Service interface (D, HARM_RISK)** | **NO** | `HARM_RISK` consumed as a pre-supplied column |

**Key architectural finding.** The producers for **B, D, and E already exist in the repository** — they are exactly the `agentdojo_integration/` interception layer and the Gamma engine. The AgentDojo arm is *the* demonstration that L-DREA sources predicates from **runtime environment state + frozen policy**, never from a dataset label. The credit-card arm is anomalous precisely because it lacks those planes and therefore *simulated* them from `Class`. The missing pieces (Authority Service, Risk-Service interface) are **architectural slots**, and — per the standing constraint — this document only *locates* them; it proposes no implementation and changes no Gamma semantics.

---

## 6. CRITICAL QUESTION

> **Was the previous redesign fundamentally wrong in assuming that every predicate should originate from the dataset?**

**Answer: YES — the framing was architecturally wrong, though the previous redesign was directionally sound and already flinched toward the correct answer.**

**Why it was wrong.**
1. **It inverted the source-of-truth model.** L-DREA is an *execution-governance* architecture that **reads** evidence from the runtime (B), authority (C), and governance (D) planes and **derives** decisions (E). The transaction payload (A) is one of five sources and the *smallest*. Asking "which dataset field approximates each predicate" implicitly makes **A** the default home for all thirteen predicates — which the evidence-origin table (§3) refutes: only *one* predicate (Amount) is natively dataset-borne.
2. **It smuggled cross-plane relocations.** To keep predicates in the dataset, the previous redesign had to move a **D**-class risk-service output (HARM_RISK) into an **A**-class feature transform, and a **B**-class velocity signal into a global time aggregate. Each relocation is defensible *only* as a disclosed proxy; as architecture, each mislabels the evidence's native producer.
3. **The dataset cannot, even in principle, host C-plane evidence.** Tokens, signatures, and approval chains are properties of the *authority infrastructure*. No feature engineering over `V1…V28` can produce them without fabrication. The dataset-first framing therefore forces an impossible task for seven of the predicates and an author-it-away outcome for seven more (the E outputs).

**Why it was nonetheless directionally correct (not a wholesale error).**
- It correctly installed the **Label Firewall** (Class only at scoring) — which this architecture keeps verbatim.
- It correctly classified the C/B predicates as **UNSUPPORTED** and explicitly said "do not invent," and it correctly pointed to FCR / ConcurBench / AgentDojo as where those predicates are genuinely exercised. That pointer *is* the architectural answer stated in dataset-first language.

**The corrected principle.** Predicate origin is dictated by the **L-DREA architecture**, not by the dataset's schema. The credit-card dataset is the **Transaction Interpreter's input and nothing more** (source A, plus raw features a risk service may read). The authority (C), runtime-context (B), and governance (D) predicates must originate from their native planes — which, for B/D/E, **already exist in this repository** as the AgentDojo interception layer and the Gamma engine, and for C is a located-but-unfilled architectural slot. Consequently, the right experimental posture is not "regenerate all predicates from the dataset," but "**let each predicate come from its architecturally-correct plane, and evaluate each arm on the slice its evidence supports**" — the credit-card arm on the A/(B/D-proxy) slice, and the authority/context/ordering slice on the arms (FCR, ConcurBench, AgentDojo) whose runtimes actually produce that evidence.

---

*Architectural research document only. No code written, no implementation proposed, no modification to Gamma, L-DREA, FULL_SPEC, the paper, the predicates, the runtime, or the benchmark. Existing components are cited by location solely to determine the scientifically correct origin of each predicate.*
