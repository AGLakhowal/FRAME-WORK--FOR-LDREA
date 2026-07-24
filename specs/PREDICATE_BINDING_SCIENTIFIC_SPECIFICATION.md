# RUNTIME PREDICATE BINDING — SCIENTIFIC SPECIFICATION

**A scientific specification only. No code, no algorithm, no feature engineering, no threshold fitting, no dataset fitting, no use of `Class`, no metric optimisation.** Every resolution below is derived from the authoritative L-DREA corpus (Runtime Evidence Architecture, EEB spec, RCL spec, Implementation Traceability, Engineering Migration Roadmap, and the predicate definitions already present); where the corpus does **not** determine an answer, the item is flagged as an owner ruling and **not** invented.

**Roles:** Principal Runtime-Governance Researcher · IEEE Methodology Reviewer · Formal-Systems Architect · Scientific-Specification Author.

**Scope note.** `FULL_SPEC.md` and the IEEE paper are cited by the in-repo specs but are **not present as files**; they are treated as frozen external references and cited only where the in-repo specs quote them (non-default-permit / fail-closed 2.3 / 0.10; Eq. 7; Invariant I5; DET1/DET4).

---

## 1. Purpose

Specify the **Runtime Predicate Binding** `B` — the missing bridge between the sealed Execution Evidence Bundle and the frozen authorization engine:

```
Execution Evidence Bundle  ──B──►  frozen engine decision schema  ──►  evaluate_decision (FROZEN)  ──►  Γ  ──►  Decision
```

`B` maps **observable evidence** (planes A/B/C/D, each with provenance) to the **predicate inputs** the frozen engine already reads (`NODE_GATE_COLS`, `HARM_RISK`, `StaleContext`, `TelemetryFresh`, the veto). `B` owns **shape and origin**, never **meaning**: it authors no predicate definition, no aggregation, and no decision — those remain frozen (RCL §0 Prime Invariant; EEB §5). This document formalizes `B`, resolves the specification gaps that the architecture already determines, and isolates the residual gaps that only a named owner may rule.

## 2. Scientific principles (all pre-existing in the corpus)

| P | Principle | Source |
|---|---|---|
| P1 | **Native-plane origin.** Every predicate input is read from its architecturally-correct plane; none is manufactured from the request payload or the label. | RUNTIME_EVIDENCE_ARCH §1 axiom, §3 |
| P2 | **Fail-closed default.** Absent/degraded evidence is a *fact of availability*; the frozen non-default-permit policy converts it to SAFE_STATE. The binding never decides what absence means. | EEB §2.3, §4, §6; FULL_SPEC 2.3/0.10 |
| P3 | **Class-blindness.** `Class` has no field, no port, no producer; it enters only at Ground-Truth Evaluation. | EEB §1 (Class-blind), §9; RCL §8 |
| P4 | **Evidence ≠ predicate ≠ decision.** The binding carries evidence into predicate-input shape; predicate definitions and Γ stay frozen. | RCL §0, §10; EEB §5 |
| P5 | **Replay determinism.** The binding is a pure function of persisted evidence (DET1); no live re-fetch, no wall-clock. | EEB §7; RCL §3.1 |
| P6 | **Slice evaluation.** Each arm is evaluated on the slice its evidence supports; predicates whose plane is unfilled in an arm are exercised on the arms that produce them. | RUNTIME_EVIDENCE_ARCH §6 |
| P7 | **Do not invent.** Unsupported predicates are declared unsupported, never synthesised. | RUNTIME_EVIDENCE_ARCH §6, §211 |

## 3. Formal definitions

- **Evidence bundle** `E` — a sealed EEB (EEB §2): a set of provenanced `EvidenceField`s `{(v_i, ρ_i)}`, `ρ_i = (plane, producer, quality, observed_at, verify, trust)`, `plane ∈ {A,B,C,D,E-cached}`, `quality ∈ {PRESENT, ABSENT, DEGRADED, EXPIRED}`.
- **Engine input schema** `S` — the fields the frozen engine reads (`gamma_test_runner.py:119-130, 866-892`): the `NODE_GATE_COLS` booleans, `HARM_RISK`, `StaleContext`, `TelemetryFresh`, the class-veto token, replay/ordering fields.
- **Predicate Binding** `B : E → S` — a **pure, provenance-preserving map** with three admissible per-field outcomes only:
  1. **Carry** — a plane-native `PRESENT` value is transported verbatim into its schema slot (no transform).
  2. **Absent → fail-closed** — an `ABSENT`/`DEGRADED` value maps to the schema value the frozen non-default-permit policy treats as a deficit (P2); `B` does not decide, it marks the availability fact and the frozen engine converts it.
  3. **Unsupported → out-of-slice** — a predicate whose plane is not produced in this arm is declared out-of-slice and evaluated on the arm that produces it (P6).
- **Admissibility constraints on `B`** (binding, from P1–P7): `B` must (a) read each field only from its native plane; (b) apply **no** threshold, comparison, or numeric transform (thresholds live in policy/engine); (c) never read `Class`; (d) be deterministic over persisted evidence. Any `B` violating (a)–(d) is rejected.

**Note.** Outcomes (1) and (2) are fully determined by the corpus (pure carry; frozen fail-closed). Outcome (3) — *which* predicates are out-of-slice vs fail-closed-in-vector — and the **parameter values** for any present-plane threshold predicate are the residual rulings (Gaps 3, 4).

## 4. Resolution of the five specification gaps

For each: **why the gap · constraints · options · consequences · recommendation · rationale · consistency**.

### Gap 1 — Actuation semantics (`actuation_observation` vs `ACT_PERMIT`, Eq. 7)
- **Why.** EEB §10.1 flags a naming/temporal collision: is the Eq. 7 execute term a *pre-decision intent* or a *post-actuation observation*? The EEB spec deliberately does not pick.
- **Constraints.** Eq. 7 unauthorized-execution term (`Actuated`/`ACT_PERMIT`); Invariant I5 commit-before-actuate (`gamma_test_runner.py:918-924`); DET4 append-only.
- **Options.** (a) pre-decision intent; (b) **post-actuation observation**.
- **Consequences.** (a) risks carrying a plane-E decision back as input (authoring inversion, EEB §32); (b) records a runtime fact consistent with I5 (commit precedes actuate ⇒ actuation observed after commit) and keeps UER counterfactual on actuated ops.
- **Recommendation.** **(b) post-actuation observation.**
- **Rationale.** Derivable from I5 + the EEB anti-inversion rule (never carry a plane-E decision as input); (b) is the only reading that keeps `actuation_observation` an *observation* (plane B/E-runtime fact), not a decision. **Low-stakes** for the credit-card arm (actuation does not enter `Γ_G`/`Π`).
- **Consistency.** Class-blind (no label); consistent with I5/Eq. 7, Evidence Quad (recorded as a runtime fact), replay (persisted observation), Gamma (not an input to `Γ_G`). **Recommended; owner-confirmable (runtime-semantics owner), non-material to the reported metrics.**

### Gap 2 — Class-veto producing plane (C vs D)
- **Why.** The non-`Class` origin of the class-level veto (§10.2): governance (D) or authority (C)?
- **Constraints.** RUNTIME_EVIDENCE_ARCH §2.3/§3: hazard/AML/sanctions are **D** (governance) outputs; the veto is a harm/fraud-class concern. The credit-card arm has **no** governance service (D absent) and **no** authority service (C absent).
- **Options.** (a) plane **D** (governance); (b) plane C (authority).
- **Consequences.** Both resolve to `ABSENT` in this arm (no service on either plane), so the *value* is identical; only the provenance tag differs.
- **Recommendation.** **(a) plane D**, `evidence_quality = ABSENT`.
- **Rationale.** The class-level veto is semantically a harm/AML/fraud governance signal (§2.3), so D is its native plane (P1). Choosing D correctly records *where the missing producer lives*.
- **Consistency.** Class-blind (the veto's non-`Class` origin is a governance service, never the label — EEB §124); consistent with architecture plane assignment, fail-closed (absent D → deficit per P2), replay (absent is stable), Gamma/SAFE_STATE unchanged. **Derivable; recommended.**

### Gap 5 — Velocity/ordering window scope (per-subject vs global)
- **Why.** Velocity is a per-subject runtime-history signal, but the transaction source has **no** subject/account key (RCL §5 honest gap).
- **Constraints.** RCL §3.2 note + §5: absent a subject key, only a **global** window is exposable; per-subject velocity must not be faked (P7).
- **Options.** (a) **global-only** velocity/ordering; (b) declare velocity **out-of-scope** for this arm (P6).
- **Consequences.** (a) exposes a real but coarse global aggregate (no per-subject meaning); (b) evaluates velocity only on arms with a subject key (ConcurBench/AgentDojo).
- **Recommendation.** **(a) global-only**, explicitly labelled as global (with (b) as the honest fallback if the owner deems global velocity non-meaningful).
- **Rationale.** RCL §3.2 authorises exactly the global window and forbids faking per-subject; global-only carries what the substrate provides and nothing more (P1/P7).
- **Consistency.** Class-blind; consistent with RCL §3.2/§5, replay (deterministic over persisted history), Gamma (feeds a plane-B gate input only). **Derivable; recommended, with the honest global-only limitation disclosed.**

### Gap 3 — Gate-index → evidence-plane binding **and absent-gate treatment** ⚠️ IRREDUCIBLE
- **Why.** Two questions: (i) which `Gate_Ak` binds to which plane (amount→A, velocity→B, authority→C, sanctions→D); (ii) **how the frozen engine treats the credit-card arm's absent-plane gates** — as **fail-closed deficits inside the full vector** (complete mediation) or as **out-of-slice** predicates evaluated elsewhere (P6).
- **Constraints (both authoritative, in tension).**
  - **EEB §4/§6 + FULL_SPEC non-default-permit:** "if service unavailable → ABSENT (§6); engine **fail-closes**." The engine reads the full `NODE_GATE_COLS` and any absent authority gate ⇒ deficit (`gamma_test_runner.py:915-916`). ⇒ credit-card arm (C/D absent) **denies every row** (FPR=0, UER=0, FDR high).
  - **RUNTIME_EVIDENCE_ARCH §6:** "evaluate each arm on the **slice its evidence supports** — the credit-card arm on the A/(B/D-proxy) slice"; the C/B predicates are "**UNSUPPORTED** … do not invent," exercised on FCR/ConcurBench/AgentDojo.
- **Options.**
  - **(a) Full-vector fail-closed** (complete mediation): all `NODE_GATE_COLS` present; absent C/D ⇒ deficits ⇒ arm all-denies. *Zero parameters, fully derivable.*
  - **(b) A-slice reduced vector** (slice evaluation): the credit-card arm's reported vector is restricted to the present-plane predicates (amount A, optional global velocity B); absent authority/sanctions gates are out-of-slice. *Requires defining the slice membership and (Gap 4) the amount-gate parameter.*
- **Consequences.** (a) yields a genuine but **degenerate all-deny** measurement (removes the tautology; demonstrates fail-closed safety) — but does **not** exercise the amount predicate the architecture says to evaluate. (b) yields a **non-degenerate** A-slice measurement — but requires selecting slice membership and an external SLA (Gap 4), which the architecture reserves.
- **Recommendation.** **Cannot be recommended by derivation.** Both (a) and (b) are directly grounded in authoritative, frozen sources that **the corpus does not adjudicate between**: (a) is the literal frozen engine + fail-closed reading; (b) is the architecture's stated evaluation posture (§6). They produce **materially different reported science** (all-deny vs an A-slice trade-off). Selecting one is a **methodology decision reserved to an owner** (traceability §10.3, policy/binding owner). Choosing here would be inventing methodology (violates P7 / the ABSOLUTE RULE).
- **Consistency.** *Both* options are Class-blind and preserve Gamma/SAFE_STATE/replay/Evidence-Quad; the un-derivable part is *which authoritative reading governs the arm's reported slice*. **IRREDUCIBLE — owner ruling required.**

### Gap 4 — HARM_RISK proxy admissibility + Class-blind θ and amount limit `L_amt` ⚠️ IRREDUCIBLE (value)
- **Why.** `HARM_RISK` is a governance-service **output** (plane D); the credit-card arm has no risk service. §10.4 asks whether a label-free statistical proxy over `V1..V28` is an admissible D stand-in, and reserves θ / `L_amt` as a "**risk-budget SLA, not fit to `Class`**."
- **Constraints.** RUNTIME_EVIDENCE_ARCH §2.3: treating `V1..V28` as HARM "quietly relocates a **D** signal into **A** … defensible **only** as an explicitly-labelled proxy, never as the architecture's intended source." P2 (absent D → fail-closed). P8 (no threshold fitting, no `Class`).
- **Options.**
  - **Proxy:** (a) **reject** the proxy ⇒ `HARM_RISK` = ABSENT (plane D) ⇒ fail-closed; (b) admit a disclosed proxy (owner-accepted, plane-D-labelled).
  - **`L_amt` (amount gate) and θ_fresh (freshness):** external **risk-budget SLA** values; the architecture states they are **not derivable from data or architecture** ("SLA, not fit to `Class`").
- **Consequences.** (a) is architecturally clean (no plane inversion) but removes the only candidate D-signal, reinforcing all-deny under Gap-3(a); (b) enables a D-slice proxy but is a **governance admissibility** decision. Any concrete `L_amt`/θ is an SLA: no principled non-empirical value exists except the degenerate extremes (∞ = fail-open, forbidden; 0 = fail-closed).
- **Recommendation (partial).** **Reject the HARM proxy** (recommend (a)) — this *is* derivable from §2.3 (HARM is a D-service output; absent here) and needs only governance **confirmation**. **The θ/`L_amt` SLA values are NOT recommendable** — the architecture defines them as external policy; deriving or fitting one violates the ABSOLUTE RULE.
- **Consistency.** Rejecting the proxy is Class-blind, plane-correct (P1), fail-closed-consistent (P2), replay-stable. The SLA values, once supplied by policy, must preserve Class-blindness (not fit to `Class`) and determinism — which the spec constrains — but their **existence and magnitude are owner inputs**. **Proxy rejection: derivable/recommended. SLA values: IRREDUCIBLE — owner ruling required.**

## 5. Complete predicate-binding model

`B` for the credit-card arm, with every field's outcome and its governing rule:

| Engine schema field | Plane | Producer (built) | Binding outcome under `B` | Rule |
|---|---|---|---|---|
| `txn_amount`, `txn_time` | A | Transaction Interpreter (2.4) | **carry** (verbatim) | P1, carry |
| `txn_feature_ref` (`V1..V28`) | A | Interpreter | **carry as opaque** — governance-service *input only*, never a predicate | RCL §5 anti-mixing |
| amount-limit gate | A | derived from `txn_amount` vs `L_amt` | **present-plane predicate**; needs external SLA `L_amt` | **Gap 4 (SLA)** |
| velocity/ordering gate | B | ExecutionHistoryWindow (2.3) | **global-only** aggregate; boolean needs window envelope (SLA) | **Gap 5 (global) + Gap 4 (SLA)** |
| `StaleContext`, `TelemetryFresh` | B | FreshnessClock (2.3) — raw deltas | delta **carried**; boolean needs θ_fresh (SLA) or ABSENT→fail-closed | Gap 4 (θ) / P2 |
| `commit_*`, `actuate_*`, `commit_before_actuate`, `actuation_observation` | B | CommitActuateJournal (2.3) | **carry** ordering facts; actuation = post-observation | Gap 1 |
| `TOKEN_VALID`, `AuthoritySignatureValid`, `Lambda_G`, authority `Gate_A*` | C | AuthorityPort (2.2) — ABSENT | **absent → fail-closed** *or* **out-of-slice** | **Gap 3** |
| `harm_risk_score` | D | GovernancePort (2.2) — ABSENT | **absent → fail-closed** (proxy rejected) | **Gap 4 (proxy)** / P2 |
| class-veto token | D | Governance (absent) | **absent** (plane D) | Gap 2 |
| `prior_ledger_link` | E-cached | Evidence Collector | carry / absent | EEB §2.2 |

**The model is fully specified except at two decision points:** the **slice/absent-gate treatment** (Gap 3) and the **proxy admissibility + external SLA values** (Gap 4). Gaps 1, 2, 5 are resolved above. Every other field is a pure carry or a frozen fail-closed mapping.

## 6. Consistency proof (for the derived methodology)

The binding `B` as constrained in §3 and resolved for Gaps 1/2/5 satisfies:

- **Class-blind** — every outcome is a plane-native carry or an availability fact; no field reads/derives from `Class`; the veto's non-`Class` origin is governance-D (Gap 2). ✔ (EEB §9)
- **Runtime Evidence Architecture** — each field originates from its native plane (P1); unsupported predicates are declared, not synthesised (P7). ✔ (§1, §3, §6)
- **Execution Sovereignty (complete mediation)** — `B` feeds the single frozen mediator; it adds no bypass and no second decision path. ✔ (EEB §5)
- **Runtime Sovereignty** — plane-B evidence is owned/produced by the runtime substrate (RCL), carried verbatim, never fabricated. ✔ (RCL §0)
- **Evidence Quad** — `B` alters no `{decision, method_version, policy_hash, ledger_hash}`; it only supplies provenanced inputs the engine already binds into the Quad. ✔ (EEB §5, §8)
- **Gamma** — `B` produces the *inputs* to `Γ = max_i d_i`; it computes no deficit and no aggregation. ✔ (`:876-892` frozen)
- **SAFE_STATE** — absence maps to the frozen fail-closed deficit (P2); `B` never emits PERMIT/SAFE_STATE. ✔ (FULL_SPEC 2.3/0.10)
- **Replay determinism** — `B` is a pure function of persisted evidence, no wall-clock, no re-fetch (P5). ✔ (EEB §7; DET1)
- **IEEE paper** — Eq. 7 actuation reading (Gap 1), I5 ordering, and the non-default-permit policy are honoured; no theorem/invariant input is redefined. ✔

**The un-derived points (Gaps 3, 4) are consistency-neutral by construction:** whichever owner ruling is chosen, it must instantiate one of the admissible `B`-outcomes in §3, all of which preserve the nine properties above. The rulings decide *which reported slice*, not whether the invariants hold.

## 7. Assumptions

1. The frozen engine, `evaluate_decision`, Γ, SAFE_STATE, predicate definitions, replay, and metrics are unchanged (given).
2. The four planes' producers (2.2–2.5) and the EEB→engine adapter (4.1) are correct and frozen (verified in prior commits).
3. `FULL_SPEC.md`/IEEE paper content is as quoted by the in-repo specs (non-default-permit, Eq. 7, I5, DET1/DET4).
4. The credit-card arm has **no** authority service (C) and **no** governance/risk service (D) — a data-source fact (RCL §5, RUNTIME_EVIDENCE_ARCH §5).

## 8. Limitations

1. **Two irreducible owner rulings remain** (Gaps 3, 4); they are policy/governance/science decisions the corpus explicitly reserves, not derivable and not inventable here.
2. Under Gap-3(a) the arm is **degenerate all-deny**; under Gap-3(b)+Gap-4 it needs an external SLA. The choice materially changes reported FPR/FDR/UER and therefore must be signed.
3. Velocity is **global-only** (no subject key) — a data-source limitation, disclosed, not a binding defect.
4. This document specifies **methodology and provenance**, not values, algorithms, or features (by mandate).

## 9. Readiness certification

- **Derivable and resolved:** the binding contract `B` (§3, §5), and Gaps **1** (actuation = post-observation), **2** (class-veto = D-absent), **5** (velocity = global-only). These require only owner **confirmation**, not new science.
- **Irreducible (owner ruling required):** Gap **3** (full-vector fail-closed vs A-slice) — two authoritative readings the corpus does not adjudicate; and Gap **4** (HARM-proxy admissibility [recommend reject] and the external risk-budget SLA `L_amt`/θ, which the architecture defines as non-derivable policy).

Because the reported science of the credit-card arm is **determined by** Gaps 3 and 4, and both are owner-reserved (traceability §10.3–§10.4) and cannot be derived or invented without violating the ABSOLUTE RULE, the binding cannot be finalised for implementation on the existing corpus alone.

# ADDITIONAL SCIENTIFIC DECISION REQUIRED

**Two signed rulings** complete the binding: **(Gap 3)** whether the credit-card arm reports the **full-vector fail-closed** result or the **A-slice** result (policy/binding owner, reconciling EEB §6 fail-closed with RUNTIME_EVIDENCE_ARCH §6 slice-evaluation); and **(Gap 4)** governance confirmation to **reject the HARM proxy** and, if an A-slice is chosen, the **external risk-budget SLA** value(s) `L_amt`/θ (governance/science owner, disclosed and not fit to `Class`). Gaps 1, 2, 5 are resolved and need only confirmation. Once these are signed, Commit 5.1-B becomes pure engineering to the ruled spec, and Commit 5.2 (activation) can follow with scientific review of the deliberate metric change.

---

*Scientific specification only. No code, algorithm, feature engineering, threshold fitting, dataset fitting, `Class` use, or metric optimisation. Derived strictly from the authoritative L-DREA corpus; the two residual decisions are identified, not invented. Awaiting the two signed owner rulings before any scientific implementation.*
