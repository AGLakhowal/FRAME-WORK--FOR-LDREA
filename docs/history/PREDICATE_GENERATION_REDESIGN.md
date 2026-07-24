# PREDICATE-GENERATION REDESIGN

**A scientific design document (no code, no implementation).**

**Reviewer roles adopted:** IEEE Access Senior Reviewer · Runtime-Systems Researcher · AI-Governance Researcher · Security-Benchmark Researcher · Formal-Methods Researcher.

**Frozen (immutable) — not touched by this document:** Gamma, Gamma G-0, L-DREA, LUIPM, Γ aggregation, SAFE_STATE, Evidence Quad, Hydra Ledger, Runtime Sovereignty, Execution Sovereignty, LAB, ConcurBench, ASB, AgentDojo integration, the formal assumptions, definitions, theorems, proofs, and metrics.

**The single mutable object:** *the experimental methodology that produces authorization predicates from the public credit-card dataset* — i.e. the logic currently in `gamma_map_raw.py:122-181`. This document specifies its replacement **conceptually**; it writes no code and proposes no diff.

**Scientific contribution being protected:** runtime authorization / execution governance (L-DREA + Γ). **Not** fraud detection, ML, classification, or predictive modelling. The objective is **not** accuracy, zero false permits, or agreement — it is *scientific validity*: predicates must be a function of **observable runtime evidence**, never of the ground-truth `Class` label.

---

## 1. The leakage to be removed (one paragraph, for grounding)

Today `gamma_map_raw.py:123` computes the sole branch variable `is_fraud = (Class == 1)` and then writes every authorization-bearing column from it: gates (`:151-153`), `HARM_RISK` (`:132`), `Status`/`ReasonCodes` (`:161-179`). The runtime ([gamma_test_runner.py:868-892](gamma_test_runner.py#L868-L892)) faithfully re-derives Γ from those columns, and the evaluation ([:954-959](gamma_test_runner.py#L954-L959)) then compares the result back to the same `Status` (itself `Class`). Both sides of the metric are `f(Class)`; FPR/UER are 0 **by construction**. The redesign's entire job is to break the top edge of that graph: **`Class` must not enter predicate generation at all.**

---

## 2. Core design principle — the *Label Firewall*

> **Definition (Label Firewall).** The `Class` column is admissible input to **exactly one** stage of the pipeline — the *final scoring* stage — and to **no** earlier stage. Every predicate `g_i`, the harm score, Γ, and the decision must be measurable functions of the observable feature set `X = {Time, Amount, V1…V28}` and of *policy/substrate constants that are fixed independently of `Class`*.

Two corollaries make the firewall auditable:

- **C-1 (Static provenance).** For every predicate there must exist a written rule `g_i = φ_i(X, Θ)` where `Θ` is a policy constant vector whose values are justified by an operational rationale, **not** fit to `Class` (no threshold chosen because it "separates fraud"). Choosing `Θ` from `Class` is *hyperparameter leakage* and is forbidden.
- **C-2 (Measurable error).** Because `φ_i` no longer sees `Class`, the derived decision *can now disagree* with `Class`. FPR, FDR, and UER become genuinely observable quantities that may be non-zero — which is the whole point. **We must not optimise them toward zero.**

This principle is *fully compatible* with the frozen science: L-DREA never required predicates to come from a label; it requires them to be *observable execution evidence evaluated non-compensatorily*. The firewall restores exactly that reading.

---

## 3. Predicate taxonomy — three evidence classes

Every predicate Gamma consumes belongs to one of three classes, distinguished by **where the evidence originates in a real deployment**. This taxonomy drives the entire suitability analysis.

| Class | Evidence origin in real deployment | Present in a bare transaction record? | Credit-card dataset can supply it? |
|---|---|---|---|
| **E1 — Transaction-intrinsic** | the request payload itself (amount, time, feature vector) | **Yes** | **Yes** — this is what the dataset *is* |
| **E2 — Risk-service / statistical** | an online risk/anomaly service scoring the request | Yes, if such a service is deployed | **Partially** — a label-free statistical score is computable from `V1…V28` |
| **E3 — Substrate / authority** | auth service, HSM, token store, approval workflow, commit-log — *the runtime governance substrate*, not the transaction | **No** — these are properties of the *governing system*, not the request | **No** — the dataset contains no such fields |

The current mapper hides this distinction by synthesising **all three** classes from `Class`. The redesign keeps E1/E2 as genuine label-free evidence and **honestly declares E3 predicates as substrate-provided constants that this dataset cannot exercise** (see §6, §7). Inventing E3 values from `Class` is precisely the leakage; inventing them from noise would be fabrication. Neither is acceptable — so E3 is *disclosed*, not faked.

---

## 4. Per-predicate construction specification

Each predicate below is specified with: **Scientific meaning · Real-deployment evidence · Observable inputs · Dataset mapping · Transformation pipeline · Deterministic construction rule · Rationale · Runtime interpretation · Limitations · Support class.** The construction rules are complete enough to implement without further scientific choices; the *values* of policy constants `Θ` are specified as "policy-fixed, label-free," with the mandated selection procedure stated so no implementer needs to consult `Class`.

Notation: `X = {Time, Amount, V1…V28}`. All standardisation uses **global** feature statistics (mean/variance over **all** rows, `Class`-blind). "Policy constant" = a value fixed by operational rationale and frozen before any row is scored.

---

### 4.1 HARM_RISK — (E2, the load-bearing redesign)

- **Scientific meaning (L-DREA).** The domain hazard magnitude of the proposed action; feeds the admissibility deficit `HARM_RISK > θ` in Γ. It is the *only* predicate whose job is to quantify "how dangerous is executing this?"
- **Real-deployment evidence.** An online risk service emits a bounded hazard score per request from request features + context. It does **not** consult a fraud label (the label does not exist at decision time).
- **Observable inputs.** `V1…V28` (anonymised PCA behavioural components), `Amount`. No `Class`.
- **Dataset mapping.** Treat `V1…V28` as the risk service's feature embedding (they are, by construction of the ULB set, zero-mean uncorrelated PCA components). Compute a **label-free statistical outlyingness score** and squash it to `[0,1]`.
- **Transformation pipeline.**
  1. Standardise each `Vi` by its **global** mean/std (Class-blind): `zi = (Vi − μi)/σi`.
  2. Anomaly energy `s = Σ_i zi²` (equivalently squared Mahalanobis distance under the PCA's diagonal covariance — no covariance estimation needed because components are uncorrelated).
  3. Amount contribution `a = clip(Amount / A_ref, 0, 1)` with `A_ref` a policy constant (a monetary reference, e.g. an institution's extraordinary-transaction reference), fixed **without** reference to `Class`.
  4. Bounded squash `HARM_RISK = 1 − exp(−(w_s·s/S_ref + w_a·a))`, with `S_ref`, `w_s`, `w_a` policy constants. This is monotone, deterministic, and ∈ [0,1).
- **Deterministic construction rule.** `HARM_RISK(row) = 1 − exp( −( w_s · (Σ zi²)/S_ref + w_a · clip(Amount/A_ref,0,1) ) )`. Fully determined by `X` and frozen constants; identical inputs → identical output (satisfies DET1).
- **Rationale.** A statistical-outlyingness → hazard map is the *standard* faithful stand-in for a runtime risk service: it scores "how far from normal execution context is this request," which is exactly what a hazard estimator observes. Crucially it is computed **before** and **independently of** any label.
- **Runtime interpretation.** The value a Tier-S risk service would hand the gate; `θ` is the governance admissibility ceiling.
- **Limitations.** (i) The squash constants and `θ` are policy choices; they must be fixed by rationale (e.g. "authorize at most the p-th percentile of the *score* distribution," where p is a risk-budget SLA), **never** tuned to maximise separation of `Class` — doing so re-imports leakage. (ii) Because `V1…V28` are anonymised, the score's semantic content is opaque; it is a *defensible proxy*, not a validated hazard model. This limitation must be stated in the paper's threats-to-validity.
- **Support class.** **PARTIALLY SUPPORTED** — a genuine, label-free, deterministic hazard proxy exists; its *hazard semantics* are proxied, not measured.

---

### 4.2 HARM_RISK-threshold deficit `HARM_RISK > θ` (E1/E2 boundary)

- **Meaning.** The admissibility gate: hazard beyond the governance ceiling is a deficit.
- **Construction rule.** `deficit = 1[ HARM_RISK(row) > θ ]`, `θ` a policy constant fixed by a *risk-budget rationale* (an SLA on the fraction of traffic routed to SAFE_STATE), documented and frozen before scoring, **Class-blind**.
- **Rationale / runtime interpretation.** Identical to the frozen runtime (`gamma_test_runner.py:871`); only the *upstream* `HARM_RISK` provenance changes. The Γ machinery is untouched.
- **Limitation.** θ selection discipline is the single most important anti-leakage control (see C-1).
- **Support class.** **SUPPORTED** (given 4.1), because the comparison is a fixed rule over a label-free score.

---

### 4.3 Amount-limit gate (assign to one concrete `Gate_Ak`, e.g. Gate_A3) (E1)

- **Scientific meaning.** "Amount within authorised limit" — the canonical bounded-authority predicate (a permit authorises up to a cap; beyond it, authority is absent). This is the cleanest real authorization predicate in the whole dataset.
- **Real-deployment evidence.** Every payment authorization system carries per-authority monetary limits; the amount is on the request.
- **Observable inputs.** `Amount`.
- **Dataset mapping.** Direct: `Amount` is a genuine, semantically meaningful observable.
- **Transformation pipeline.** Compare `Amount` to a policy cap `L_amt` (an authorised-limit constant, fixed by rationale — e.g. an extraordinary-transaction ceiling — not from `Class`).
- **Deterministic construction rule.** `Gate_Amount = 1[ Amount ≤ L_amt ]` (TRUE = pass).
- **Rationale.** Bounded authority is a first-class L-DREA concept (Bounded Execution Radius / limit predicates in the stress harness, `stress_test.py:62`). `Amount ≤ limit` is the faithful, observable, label-free realisation.
- **Runtime interpretation.** The limit check an authorization gateway performs before granting a permit.
- **Limitation.** A single global cap is coarse; real systems use per-account caps, and the dataset has **no account identifier** (see §6). So this is a *global* limit, not a per-subject one.
- **Support class.** **SUPPORTED.**

---

### 4.4 Velocity / temporal-context gate (assign to another `Gate_Ak`) (E1, partial)

- **Scientific meaning.** "Request rate within safe envelope" — a temporal-behaviour predicate (velocity spikes indicate compromised or runaway execution).
- **Real-deployment evidence.** Rate limiters / velocity monitors observe request timestamps.
- **Observable inputs.** `Time` (seconds since dataset start; the rows are time-ordered).
- **Dataset mapping.** Sliding-window count/sum over `Time`: within a `W`-second window ending at the row, compute global transaction count and Amount-sum.
- **Transformation pipeline.** For row *i*: `vel_i = #{j : 0 ≤ Time_i − Time_j < W}` (and/or Σ Amount in-window). Compare to a policy envelope `V_max`, `Σ_max`.
- **Deterministic construction rule.** `Gate_Velocity = 1[ vel_i ≤ V_max ∧ windowed_amount_i ≤ Σ_max ]`. Deterministic given the fixed row order and window constants.
- **Rationale.** Velocity gating is a standard runtime-authorization control and appears verbatim in the stress harness (`velocity_check`, `emergency_velocity_aggregate`, `stress_test.py:69,151`). `Time` supports it directly and label-free.
- **Runtime interpretation.** The rate-limit decision a gateway applies pre-authorization.
- **Limitation.** **Global** velocity only — no card/account key exists, so *per-subject* velocity (the operationally meaningful one) is not computable (see §6). This is the honest boundary of `Time`'s usefulness.
- **Support class.** **PARTIALLY SUPPORTED** (global velocity yes; per-subject velocity no).

---

### 4.5 Remaining node gates `Gate_A1, A2, A4, A5, A6, A7`, `Lambda_G` beyond §4.3-4.4 (E3)

- **Scientific meaning.** The generic node-predicate vector `G = {g_1…g_n}` — each is a *distinct authorization condition* that must concur for Γ_G = 0 (paper §V; `NODE_GATE_COLS`, `gamma_test_runner.py:119-130`). Concretely in the runtime substrate these are checks such as dual-control satisfaction, sanctions/entity clearance, KYC-token freshness, approval-chain completeness, deterministic-governance state, etc. (the taxonomy is enumerated in `stress_test.py`).
- **Real-deployment evidence.** Outputs of the governance substrate: an approvals service, a sanctions oracle, a KYC token store, a policy engine — each emitting a boolean per request.
- **Observable inputs.** **None present in the dataset.** These are properties of the *governing system*, not of a `Time/Amount/V1…V28` transaction record.
- **Dataset mapping.** **No defensible mapping exists.** Any attempt to synthesise them from `V1…V28` would be assigning invented authorization semantics to anonymised PCA axes — scientifically indefensible (we cannot claim "V17 = sanctions clearance"). Mapping them from `Class` is the original leakage.
- **Deterministic construction rule.** Hold at a **disclosed substrate constant** `TRUE` (evidence-present, effect = inert deficit) for the credit-card arm, explicitly labelled "substrate-provided, not exercised by this dataset." This is *not* a result; it is an honest declaration that this dataset cannot test these gates.
- **Rationale.** Faithfulness forbids inventing evidence. The paper's contribution does not require this dataset to exercise *every* gate — it requires that whatever gates *are* exercised be driven by observable evidence. Under-determined gates must be inert-and-disclosed, not fabricated.
- **Runtime interpretation.** In a real L-DREA deployment these fire from the substrate; the ConcurBench/ASB/AgentDojo arms (which *do* have substrate state) are where they are genuinely exercised.
- **Limitation.** The credit-card arm therefore tests the **harm/limit/velocity** slice of Γ, not the **authority/approval** slice.
- **Support class.** **UNSUPPORTED** (by this dataset).

---

### 4.6 TOKEN_VALID · AuthoritySignatureValid (E3)

- **Scientific meaning.** `Valid(Token)` and authority-signature validity — the cryptographic authority predicates in Eq. 7 and ISB (`gamma_test_runner.py:896-901`).
- **Real-deployment evidence.** Token store / HSM / PKI verification results.
- **Observable inputs.** **None** — there is no token or signature field in a credit-card transaction.
- **Dataset mapping.** **None defensible.** (The current mapper sets both `TRUE` for all rows, `gamma_map_raw.py:184-185` — inert already, so no leakage here today, but also no test.)
- **Deterministic construction rule.** Disclosed substrate constant `TRUE` (as today), labelled "not exercised on this dataset."
- **Runtime interpretation.** Exercised in AgentDojo integration and the FCR injected families (`fcr_test.py:16-20`), which *do* model invalid-token / ambiguous-signature evidence.
- **Support class.** **UNSUPPORTED** (by this dataset); **SUPPORTED elsewhere** (FCR injections, AgentDojo).

---

### 4.7 StaleContext · TelemetryFresh (E3, partial via Time)

- **Scientific meaning.** TOCTOU freshness signals — context staleness / telemetry age feeding the deficit vector (`gamma_test_runner.py:873-874`) and ISB.
- **Real-deployment evidence.** Timestamp deltas between context capture and decision; telemetry heartbeat age.
- **Observable inputs.** `Time` (a proxy for arrival ordering only).
- **Dataset mapping.** *Weak.* One could define `TelemetryFresh = 1[ inter-arrival gap < Δ_max ]` from consecutive `Time` deltas — but this conflates dataset sampling cadence with telemetry freshness, which is a stretch. `StaleContext` has no honest source.
- **Deterministic construction rule.** Either (a) disclosed substrate constant (fresh / not-stale), or (b) an explicitly-labelled *proxy* from `Time` gaps with a stated caveat. Recommend (a) for the credit-card arm; (b) only if the caveat is prominent.
- **Runtime interpretation.** Genuinely exercised in the `stale_telemetry` / `stale_context_toctou` FCR families (`fcr_test.py:17-18`) and ConcurBench desync levels.
- **Support class.** **PARTIALLY SUPPORTED** (weak `Time` proxy) / effectively **UNSUPPORTED** for `StaleContext`.

---

### 4.8 Derived predicates — Γ, GammaZero, ACT_PERMIT, ExecutionLegitimacy, SAFE_STATE, ReasonCodes, FirstFailingGate, Status (all E-derived, **must not be authored**)

- **Scientific meaning.** These are **outputs** of the frozen Γ machinery, *not* inputs. `Γ = max_i d_i`; `Π = 1[Γ=0]`; `SAFE_STATE = ¬Π`; `ACT_PERMIT = Π`; `ReasonCodes`/`FirstFailingGate` name the failing deficits; `Status` is the decision.
- **Redesign requirement.** In the current mapper these are **written from `Class`** (`gamma_map_raw.py:154-181`) — that is the leakage's second half. Under the redesign they must **not appear in the generated dataset at all as authored columns**; they are produced *by the runtime* ([gamma_test_runner.py:876-892](gamma_test_runner.py#L876-L892)) from the E1/E2 predicates above. The dataset carries only observable predicates + `Class` (held behind the firewall); the runtime derives Γ/decision; scoring compares to `Class`.
- **Deterministic construction rule.** None authored — these are computed downstream by frozen code. `ReasonCodes` must be *generated from the actually-failing deficits*, not a hardcoded `"CLASS_1_FRAUD…"` string.
- **Support class.** **N/A (derived)** — correctness is inherited from the frozen engine; the redesign's duty is to *stop authoring them*.

---

## 5. Dataset suitability analysis (summary)

| Predicate | Evidence class | Observable source in dataset | Support |
|---|---|---|---|
| HARM_RISK | E2 | `V1…V28` + `Amount` (label-free anomaly energy) | **PARTIALLY SUPPORTED** |
| `HARM_RISK > θ` deficit | E1/E2 | policy θ over label-free score | **SUPPORTED** |
| Amount-limit gate | E1 | `Amount` | **SUPPORTED** |
| Velocity/temporal gate | E1 | `Time` (global window) | **PARTIALLY SUPPORTED** (global only) |
| `Gate_A*` / `Lambda_G` (authority/approval slice) | E3 | none | **UNSUPPORTED** |
| TOKEN_VALID | E3 | none | **UNSUPPORTED** |
| AuthoritySignatureValid | E3 | none | **UNSUPPORTED** |
| TelemetryFresh | E3 | weak `Time` proxy | **PARTIALLY SUPPORTED** |
| StaleContext | E3 | none | **UNSUPPORTED** |
| Γ / SAFE_STATE / ACT_PERMIT / Status / ReasonCodes / FirstFailingGate | derived | computed by frozen engine | **N/A (must not be authored)** |

**What is genuinely missing (do not invent):** any *subject/account identifier* (kills per-account velocity, history, behavioural baselines); any *authority artefact* (token, signature, approval chain); any *substrate/session state* (context freshness, commit/actuate events, revocation); any *merchant/external-policy metadata*. `V1…V28` are anonymised PCA axes with no recoverable semantics, so they can support a *statistical* risk proxy but **cannot** support any *named* authorization predicate.

---

## 6. Alternative observable evidence for UNSUPPORTED predicates (real deployment)

Stated as *required evidence*, not invented values:

| Unsupported predicate | Observable evidence that exists in a real L-DREA deployment |
|---|---|
| `Gate_A*` authority/approval slice | approvals-service booleans, dual-control workflow state, sanctions/entity-oracle responses, KYC token-store lookups |
| TOKEN_VALID | token-store / session-manager validity result |
| AuthoritySignatureValid | HSM/PKI signature-verification result |
| StaleContext / TelemetryFresh | context-capture vs decision timestamps; telemetry heartbeat age; revocation-feed freshness |
| (commit-before-actuate ordering) | commit-log and actuation-log event timestamps from the execution substrate |
| per-subject velocity/history | account/card identifier + transaction history store |

These are exactly the fields the **ConcurBench desync levels, FCR injected families (`fcr_test.py:16-20`), and AgentDojo integration already carry** — which is why those arms *can* exercise the authority/freshness/ordering slice that the bare credit-card dataset cannot.

---

## 7. Recommended predicate-generation pipeline (label firewall)

```
             ┌──────────────────────── LABEL FIREWALL ────────────────────────┐
             │  Class is INADMISSIBLE anywhere left of this line               │
raw creditcard.csv                                                             │
   │  X = {Time, Amount, V1..V28}          Class ──────────────────────────────┼──► (held aside)
   ▼                                                                           │
Observable runtime features                                                    │
   • global-standardised V-anomaly energy   (E2, §4.1)                         │
   • Amount                                  (E1, §4.3)                         │
   • Time-windowed velocity                  (E1, §4.4)                         │
   • [substrate constants, disclosed]        (E3, §4.5-4.7)                     │
   ▼                                                                           │
Predicate construction  g_i = φ_i(X, Θ)   Θ = policy constants (Class-blind)   │
   ▼                                                                           │
Γ authorization  (FROZEN: gamma_test_runner.py:868-892)                        │
   ▼                                                                           │
Decision  PERMIT / SAFE_STATE  + Evidence Quad + Hydra Ledger (FROZEN)         │
   ▼                                                                           │
─────────────────────────────────────────────────────────────────────────────┘
   ▼
Ground-truth comparison  ← Class enters HERE and ONLY here
   FPR / FDR / UER / agreement  (now genuinely measurable, may be non-zero)
```

The only structural change vs. today: the top edge `Class → predicates` is **cut**, and `Class` re-enters solely at the scoring node. Everything below "Γ authorization" is frozen and unchanged.

---

## 8. Compatibility analysis — the frozen contribution is preserved

| Frozen component | Why it is unchanged |
|---|---|
| **Gamma / Γ aggregation** | Consumes a predicate vector; redesign only changes *how the vector is populated* (observable evidence vs. label). `max_i d_i` untouched. |
| **SAFE_STATE / ACT_PERMIT** | Still the frozen `Π = 1[Γ=0]` outputs; now driven by observable deficits. |
| **LUIPM / Interpretive-sufficiency ISB** | Formula unchanged (`:896-901`); its inputs (token/freshness) are E3-disclosed for this arm, exercised in others. |
| **Runtime & Execution Sovereignty** | Invariants I1–I6 (`:982-1001`) evaluate the same expressions over honestly-derived predicates; they can now *genuinely* hold or fail. |
| **Evidence Quad / Hydra Ledger** | Emission and hash-chain logic unchanged; `ReasonCodes` now names *actual* failing deficits instead of a hardcoded label string. |
| **LAB / ConcurBench / ASB** | Same runners, same metrics; only the credit-card *input generation* changes. ConcurBench/ASB substrate arms already carry E3 evidence and are untouched. |
| **AgentDojo integration** | Independent; derives predicates from live `TaskEnvironment`, never from `Class`. Explicitly out of scope. |
| **Theorems / definitions / assumptions / metrics** | All are statements about Γ and the invariants, not about predicate provenance. Removing label leakage makes the *evaluation* of these statements honest without altering the statements. |

**Why the scientific contribution is unchanged.** The paper claims *runtime authorization / execution governance*: given predicate evidence, Γ authorizes non-compensatorily and fails closed. That claim is a property of the mechanism, independent of where predicates originate. The redesign changes only the *experimental instrument* that feeds evidence in — from a label-echo to observable evidence — which strengthens, not alters, the contribution: the invariants and FPR/UER become *earned measurements* rather than tautologies.

---

## 9. FINAL ASSESSMENT

**Recommendation: OPTION C — the public credit-card dataset is fundamentally insufficient for some authorization predicates.**

This is chosen over A and B on direct technical grounds:

- **Not Option A.** The dataset as *currently used* is invalid (label leakage, verified separately). It is not "sufficient as-is."
- **Not Option B (fully).** Redesigning the methodology *does* rescue a genuine, defensible, label-free slice of Γ — the **harm/limit/velocity** predicates (§4.1–4.4) become real measurements against `Class`, which is a legitimate and worthwhile experiment. But redesign **cannot** manufacture evidence the dataset does not contain.
- **Therefore Option C, precisely bounded:**

**Predicates the credit-card dataset CAN support (label-free, after redesign):**
- `HARM_RISK` (statistical anomaly-energy proxy, semantics disclosed) and its θ-deficit — §4.1–4.2.
- Amount-limit gate — §4.3.
- Global velocity/temporal gate — §4.4.

**Predicates the credit-card dataset CANNOT support, and why (missing evidence, must not be invented):**
- **The authority/approval node-gate slice** (`Gate_A*`, `Lambda_G` beyond amount/velocity), **TOKEN_VALID**, **AuthoritySignatureValid** — these are **E3 substrate/authority** signals (tokens, HSM signatures, approval chains, sanctions oracles). A `Time/Amount/V1…V28` record contains **none** of them, and `V1…V28` being anonymised PCA axes cannot be assigned named authorization semantics without fabrication.
- **StaleContext**, and rigorously **TelemetryFresh**, and any **commit-before-actuate ordering** — **E3 session/substrate** evidence (context-capture timestamps, telemetry age, commit/actuation logs). The dataset's `Time` supports at most a weak, caveated freshness proxy and no ordering evidence at all.
- **Per-subject** velocity, history, and behavioural baselines — the dataset has **no account/card identifier**, so only *global* temporal aggregates are computable.

**Consequent scientific position for the paper.** Present the credit-card arm honestly as an experiment on the **harm/limit/velocity slice** of runtime authorization, with predicates derived label-free from observable transaction evidence and `Class` used *only* as post-hoc ground truth (§7). Exercise the **authority/token/freshness/ordering slice** where its evidence genuinely exists — the FCR injected families (`fcr_test.py:16-20`), ConcurBench desync levels, and the AgentDojo integration — which already carry E3 state. This partition removes label leakage entirely while preserving every frozen definition, theorem, metric, and the complete scientific contribution.

---

*Scientific design document only. No code written, no implementation proposed, no modification to Gamma, L-DREA, FULL_SPEC, LAB, ConcurBench, AgentDojo, or the paper. `gamma_map_raw.py` and all frozen components left untouched.*
