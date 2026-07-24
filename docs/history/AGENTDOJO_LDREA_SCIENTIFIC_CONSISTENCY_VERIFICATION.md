# Scientific Consistency Verification — AgentDojo Integration vs the Gamma / L-DREA Contribution

**Role:** IEEE Access Senior Reviewer · AI Security Research Scientist · Formal Methods Researcher · Benchmark Methodology Expert · Research Integrity Reviewer.
**Purpose:** the implementation approval gate. Prove — honestly — whether integrating the **real AgentDojo** benchmark alters any existing scientific claim, theorem, architecture, benchmark philosophy, or formal contribution of Gamma / L-DREA.
**Inputs governing this verification (authority order):** IEEE Paper → FULL_SPEC → Execution Integrity.md → Reviewer comments. Supersedes nothing; certifies V1/V2 design.
**No code. No adapters. Scientific verification only.**

**Thesis of this document (stated up front, then proved):** The integration **modifies nothing**. It **additively extends** three things the frozen framework already anticipates — (i) the set of *domain instantiations* of Definition 1, (ii) the *empirical evaluation* with an external-validity surface, (iii) the *ground-truth provenance* of FPR/UER on that surface (author-defined → third-party). One frozen *methodological claim* — the §IX-F independence claim — is **conditional** on the anti-circularity preconditions actually holding at experiment time. That conditionality is the reason the verdict is **Option B**, not Option A.

---

## PART 1 — Scientific Consistency Matrix

Classification: **Modified** (definition/wording/logic changes — forbidden), **Extended** (additively, without altering the original), **Referenced** (used as-is), **Unchanged** (untouched). A component may be both *Referenced* and *Unchanged*; where an additive extension exists it is called out precisely.

| Core component | Modified? | Extended? | Referenced? | Unchanged? | Why AgentDojo does / does not affect it |
|---|---|---|---|---|---|
| **Gamma** (overall system) | No | No | Yes | Yes | Integration is interposition at a seam; the system is invoked, not altered. |
| **Gamma G-0** (standard) | No | No | Yes | Yes | The governance standard is applied to a new environment; its clauses are unchanged. |
| **L-DREA** (architecture) | No | No | Yes | Yes | The monitor is placed at AgentDojo's `run_function`; its two-plane architecture is used verbatim (Definition 4). |
| **LUIPM** | No | No | — | Yes | Not engaged by the integration. (Term not defined in the provided corpus; treated as a frozen construct the seam does not touch. Flagged for the authors to confirm no interaction.) |
| **Γ authorization** (`Γ = maxᵢ dᵢ`, `Π = 1[Γ=0]`) | No | No | Yes | Yes | Computed identically over the mapped predicate vector; the aggregation law is unchanged (§IV-B). |
| **SAFE_STATE** | No | No | Yes | Yes | The deny path is used as specified; denial on an AgentDojo EEA is a SAFE_STATE + ERTuple, per §2.3. |
| **Evidence Quad** | No | No | Yes | Yes | Emitted per decision with identical fields at the AgentDojo seam. |
| **Hydra Ledger** | No | No | Yes | Yes | Same append-only hash-chained ERTuple store; environment-independent. |
| **Execution Integrity** (construct) | No | No | Yes | Yes | AgentDojo *produces* EI evidence; it does not redefine the construct (Execution Integrity.md hierarchy intact). |
| **LAB v1.0** | No | No | Yes | Yes | Remains the native benchmark. AgentDojo results are *reported in LAB format*, but LAB's protocol, scenario classes, mutation library, and 10⁶ evaluation are untouched. |
| **ConcurBench** | No | No | — | Yes | Not modified and not replaced; AgentDojo maps only to its Corrupted/Adversarial cells and claims nothing about the other five classes. |
| **ASB** | No | No | — | Yes | Untouched; AgentDojo does not implement ASB's temporally-extended families. |
| **Runtime Sovereignty** (Invariant 6) | No | No | Yes | Yes (partial coverage) | Theorem unchanged. At Tier-S the *substrate-dependent* conjuncts (via A3) are not exercised; this **bounds coverage**, it does not alter the invariant or its proof. |
| **Execution Sovereignty** (Invariant 1) | No | No | Yes | Yes (partial coverage) | Theorem and its A1–A3 antecedents unchanged. A3 is not satisfied at Tier-S, so AgentDojo exercises the *authorization-logic* layer, not the substrate interlock. Scope statement, not modification. |
| **Formal assumptions A1–A4** | No | No | Yes | Yes | No new assumption introduced. A3 (substrate isolation) is not met at Tier-S — which *narrows what AgentDojo tests*, exactly as the paper already permits (Tier-S is a documented degraded fallback, §V-G). |
| **Threat model (§III)** | No | No | Yes | Yes | AgentDojo *realizes* existing adversary capability (iii) context corruption from plane C. The content-layer of prompt injection remains out of scope (Property v; §XII-A); the *resulting action* is in scope. Consistent, not contradictory. |
| **Formal properties (5 structural, Def. 2)** | No | No | Yes | Yes | Complete mediation, tamper-resistance, verifiability, non-compensatory aggregation, epistemic bounding all used as-is; the seam is chosen to satisfy complete mediation. |
| **Proof dependency graph (Table 5)** | No | No | Yes | Yes | No new theorem, corollary, or dependency is introduced; the DAG is unchanged. |
| **Replay verification** | No | No | Yes | Yes | Same ERTuple/adjacency/GENESIS mechanism; environment-agnostic. |
| **Independent verifier** | No | No | Yes | Yes | Reused unchanged (stdlib-only, zero dependency on adapter/dataset/runner). |
| **Metrics (UER/FPR/FDR/FCR/RDR/…)** | No | **Yes (provenance only)** | Yes | Yes (definitions) | **Definitions unchanged** (§VIII-G). The only extension: on the AgentDojo surface, the should-deny/should-permit *labels* come from AgentDojo's third-party `security()`/`utility()` checkers instead of author-defined ExpectedPermit. This is the intended de-circularization, not a redefinition. |

**Additive artifacts introduced (none are "modifications"):**
- **AgentDojo predicate/action instantiation** — a new *domain instantiation* at the same altitude as §X's treasury/clinical/grid worked examples. Classified **Extended** under §X (which already frames predicate sets as domain instantiations) and §XII-C (predicate/I_class extension as a *structural property* of the framework).
- **External-validity evaluation surface** — Classified **Extended** under §IX-F, which pre-registers exactly this.
- **Tables 11 / 11b / 11c and two figures** — additive reporting; no existing table/figure altered.

**Part 1 conclusion:** Zero components are **Modified**. All core constructs are **Referenced/Unchanged**. Exactly three items are **additively Extended**, each under a clause the frozen paper already contains.

---

## PART 2 — Theorem Preservation

For each formal result: does AgentDojo require new assumptions, theorem modification, proof modification, additional lemmas, or weakened claims? Proof of "no" follows each.

| Result | New assumption? | Theorem mod? | Proof mod? | New lemma? | Weakened? | Proof of preservation |
|---|---|---|---|---|---|---|
| **Prop. 1 (LLC equivalence)** | No | No | No | No | No | Proved from the definition of Γ alone (Table 5); AgentDojo supplies inputs to Γ, not a new Γ. Independent of environment. |
| **Cor. 1 (fail-closed on any deficit)** | No | No | No | No | No | Follows from Prop. 1; unaffected by where the deficit vector originates. |
| **Cor. 2 (compensatory aggregators unsafe)** | No | No | No | No | No | A statement about aggregator classes; AgentDojo does not introduce an aggregator. |
| **Prop. 2 (epistemic bounding)** | No | No | No | No | No | Declarative property; AgentDojo results are read strictly within the authority horizon H (content-layer harms excluded, Property v). AgentDojo *exercises* the bound, confirming it. |
| **Invariant 1 (Execution Sovereignty)** | No | No | No | No | No | Antecedents A1–A3 unchanged. At Tier-S, A3 is not satisfied, so the invariant is **not claimed to be tested** by AgentDojo — coverage is bounded, the theorem is not weakened. (The claim "no unauthorized externalization observed on AgentDojo" is an *empirical* observation over the logic layer, not a re-proof of Invariant 1.) |
| **Invariant 2 (Non-Bypassability)** | No | No | No | No | No | Rests on A3 substrate isolation; same Tier-S coverage bound. Theorem intact. |
| **Invariant 3 (Non-Compensatory Soundness)** | No | No | No | No | No | Exactly the property AgentDojo *does* exercise: an EEA with any deficit is denied. AgentDojo provides empirical corroboration at Tier-S; the proof (Cor. 1) is untouched. |
| **Invariant 4 (Class-Level Veto)** | No | No | No | No | No | Exercised where AgentDojo tasks trigger class metrics; proof (class-flag state machine) unchanged. Marginal in AgentDojo (short-horizon), which limits coverage, not validity. |
| **Invariant 5 (TOCTOU State-Consistency)** | No | No | No | No | No | Not exercised by AgentDojo's single-agent loop (no revalidation race). Not tested ≠ modified; A4 untouched. |
| **Invariant 6 (Runtime Sovereignty)** | No | No | No | No | No | Composes 1–5 under C1–C8; AgentDojo does not touch the composition. Partial coverage at Tier-S, theorem intact. |
| **TLA⁺ mechanization (Appendix D, Inv. 1)** | No | No | No | No | No | AgentDojo is empirical; it neither extends nor alters the bounded-model mechanization. |

**Part 2 conclusion:** No theorem requires a new assumption, modification, additional lemma, or weakened claim. **What AgentDojo changes is *which invariants are empirically exercised*, not *what any invariant states or how it is proved*.** AgentDojo at Tier-S empirically corroborates the *authorization-logic* invariants (notably 3 and 4 and the decision layer); the substrate-dependent invariants (1, 2, and the substrate conjuncts of 6) remain carried by the LAB Tier-H results, unchanged. This coverage boundary must be stated in the revision (it already is, per V2 D-7) but it alters no formal result.

---

## PART 3 — Benchmark Independence Proof

**Claim to prove:** LAB v1.0, ConcurBench, and ASB remain the **native** evaluation framework; AgentDojo is **only** an independent external validation environment.

**Proof by four separations:**

1. **Ownership separation.** LAB/ConcurBench/ASB are owned by the framework (Execution Integrity.md §4–5; FULL_SPEC §11; Paper §VIII). AgentDojo is owned by a third party (Debenedetti et al. [1]). The integration adds a *consumer* of AgentDojo, not a component to it, and adds nothing to LAB/ConcurBench/ASB.

2. **Function separation.** The native framework answers the **internal-validity / rare-event conformance** question (10⁶ scale, seeded mutation library, full A1–A5 surface, Tier-H substrate ablation, six-invariant coverage). AgentDojo answers the **external-validity / independence** question (third-party oracle, realistic injection, foreign environment). Neither can perform the other's function: AgentDojo lacks scale, the A1/A2/A4/A5 surface, and the substrate layer; LAB lacks third-party ground truth. The functions are disjoint, so neither displaces the other.

3. **Metric-definition separation (the firewall).** All metric *definitions* remain LAB's (§VIII-G). AgentDojo's native metrics (Utility, TASR) are reported *alongside*, never fused into a Gamma definition. LAB defines the measurement; AgentDojo supplies an independent label source for FPR/UER on its own surface.

4. **Claim-scope separation.** The zero-event headline is scoped to LAB (§IX-L) and is *explicitly not expected to transfer* to AgentDojo (§IX-E.4). AgentDojo carries its own, wider-bounded, possibly non-zero results. The two claim surfaces do not overlap; therefore AgentDojo cannot contaminate or replace the LAB claim.

**Why this distinction is scientifically important.** If AgentDojo were treated as native, the framework would again be evaluating itself with an instrument it controls — the exact circularity §IX-F exists to remove. Keeping AgentDojo strictly external is what converts it into a *falsification surface*: it can only strengthen construct validity if it remains an oracle the authors did not build. Collapsing the distinction would forfeit the entire construct-validity gain. Hence the independence is not cosmetic — it is the load-bearing property of the whole integration.

**Part 3 conclusion:** LAB/ConcurBench/ASB remain native and unchanged; AgentDojo is provably confined to the external-validation role. ∎

---

## PART 4 — Generic Action Taxonomy Review

**Question:** are the existing action classes (WIRE_TRANSFER, MEDICATION_ORDER, GRID_DISPATCH) generic enough for AgentDojo? If not, what is the *minimal* extension?

**Finding:** The generic action class **already exists** — it is **Definition 1 (Externally Effective Action)**. WIRE_TRANSFER, MEDICATION_ORDER_DISPATCH, and SUBSTATION_DISPATCH_COMMAND are **not a taxonomy**; the paper explicitly calls them **worked examples / instantiations** (§X: "Each instantiation is a worked example"). They are *instances* of Definition 1, each with a domain predicate family.

**Therefore no new abstraction layer is required, and introducing one would be an unnecessary redesign.** AgentDojo's action classes are simply **additional instances of Definition 1**, at the same altitude as the three sector examples:

| Existing frozen instance (§X) | AgentDojo instance (new, same altitude) | Relationship |
|---|---|---|
| WIRE_TRANSFER (§X-A, banking/treasury) | **FUNDS_TRANSFER** (`send_money`, `schedule_transaction`) | **Direct reuse** — AgentDojo banking maps onto the existing §X-A predicate family (recipient/IBAN recognition, amount-limit, scope, freshness). Not even a new instance in substance. |
| — (generic messaging not in §X) | **MESSAGE_DISPATCH** (`send_email`, `send_*_message`) | New instance of Definition 1; predicate family = recipient-recognition + scope (a subset of the §X-A gate family). |
| — | **ACCESS_GRANT** (`share_file`, `add_user_to_channel`, `invite_user_to_slack`) | New instance; predicate family = identity/recipient-recognition + scope. |
| — | **RESERVATION_COMMIT** (`reserve_*`, `book_flight`) | New instance; predicate family = resource-recognition + amount-limit + scope (structurally identical to WIRE_TRANSFER's gate shape). |
| — | **WEB_EXFIL / OUTBOUND_CONTENT** (`get_webpage`→external, `post_webpage`) | New instance; predicate family = destination-recognition + scope. |
| MEDICATION_ORDER_DISPATCH (§X-B) | *(no AgentDojo analogue)* | Unchanged; remains a frozen worked example. |
| SUBSTATION_DISPATCH_COMMAND (§X-C) | *(no AgentDojo analogue)* | Unchanged; remains a frozen worked example. |

**Minimal-extension statement (satisfying every preservation constraint):**
- **Terminology preserved:** Definition 1 is the class; the three §X examples are untouched and remain exactly as written.
- **Proofs preserved:** the invariants are proved over Γ and the predicate vector, agnostic to which instance supplies it; adding instances adds no proof obligation.
- **Predicates preserved:** AgentDojo instances *reuse existing predicate families* (recognition / limit / scope / freshness / evidence / interlock) — no new predicate *type* is invented; only new instantiations of existing families.
- **Benchmark philosophy preserved:** instances feed the same LAB metric machinery; EI/ConcurBench/ASB unchanged.

**Recommendation:** Do **not** introduce a higher-level taxonomy. State in the revision that AgentDojo action classes are **additional instantiations of Definition 1**, exactly parallel to §X's three sector instantiations, with FUNDS_TRANSFER reusing WIRE_TRANSFER's family. This is the minimal, proof-preserving, terminology-preserving extension. WIRE_TRANSFER / MEDICATION_ORDER / GRID_DISPATCH remain unchanged and are already, by Definition 1, instances of the general class — no rewrite needed to make them so.

**Part 4 conclusion:** The framework is already generic at the correct level (Definition 1). AgentDojo requires **zero new abstraction** — only additional instances, reusing existing predicate families. ∎

---

## PART 5 — Predicate Authoring Integrity

**Question:** is the V2 anti-circularity mechanism sufficient? Evaluate blind authoring, predicate/threshold/mapping/recipient derivation; recommend which artifacts must be hash-committed before experimentation.

**Assessment of the V2 mechanism:** necessary and nearly sufficient, but V2 committed the components under **one** aggregate hash. A Research-Integrity reviewer requires **component-level tamper-evidence**: if one component (say the threshold vector) is quietly altered post-hoc, a single aggregate hash makes the change detectable only in bulk, not attributable. The fix is a **Merkle-style commitment**: five independently-hashed leaf manifests under one signed root, all committed before any run, root hash in the camera-ready.

| Manifest (leaf) | Contents | Hash-committed before experiment? | Why it must be separate |
|---|---|---|---|
| **1. Predicate Manifest** | the predicate families instantiated per AgentDojo action class, with their semantic derivation traced to §X | **Yes (BLOCKER)** | The core anti-circularity artifact (V2 D-1). Separate so predicate additions are independently detectable. |
| **2. Threshold Manifest** | the θ vector (admissibility thresholds) per predicate | **Yes (BLOCKER)** | Thresholds are the tuning surface most vulnerable to post-hoc fitting; must be independently frozen. |
| **3. Tool-Mapping Manifest** | per-tool EEA classification (incl. the D-6 outbound-argument rule) and read-only exclusions | **Yes (BLOCKER)** | Complete-mediation depends on this; changing a classification after seeing results would be undetectable under a bulk hash. |
| **4. Recipient/Destination-Derivation Manifest** | the deterministic function computing recognized recipients/IBANs/URLs/users from benign `TaskEnvironment` state | **Yes (BLOCKER)** | This gate does most of the anti-exfil work (V2 D-2); its derivation rule must be frozen and shown to be attack-independent. |
| **5. Evaluation Manifest** | metrics + denominators, models (≥2) + temperature 0 + seed, paired with/without arms, baseline-TASR power gate, attack set, N reconciliation | **Yes (BLOCKER)** | Freezes the *protocol* (extends §IX-F.2) so the experimental procedure cannot be reshaped after outcomes. |
| **6. Version Manifest** | AgentDojo repo/tag/commit-SHA, tool-registry SHA, dependency lock, OS, Python | **Yes (BLOCKER)** | Reproducibility anchor (V2 Part 2); pins the environment the other five are defined against. |
| **Root commitment** | SHA-256 Merkle root over manifests 1–6 + blind-authoring statement | **Yes — the single value in the camera-ready** | One published root; each leaf independently verifiable; any post-hoc edit to any component changes the root and is attributable to the leaf. |

**Blind authoring:** sufficient **only if** accompanied by (a) a signed statement that the injection corpus was unopened during authoring, and (b) derivation traceability of every predicate to §X action-class semantics (not to any attack). Both are required, both go under the root.

**Additional recommendation (integrity strengthener, low cost):** publish, alongside results, the **per-case predicate-gap analysis** for every honest false permit (F1). This is the strongest possible integrity signal — it demonstrates the predicate set was frozen *before* it was known to be incomplete on those cases.

**Part 5 conclusion:** The V2 mechanism is upgraded from one aggregate hash to **six leaf manifests under one Merkle root, all pre-committed**. With that upgrade, predicate-authoring integrity is sufficient to preserve the §IX-F independence claim. Without it, the independence claim is not defensible — which is precisely why the verdict is conditional.

---

## PART 6 — Reviewer Stress Test (harshest IEEE reviewer, post-integration)

Each criticism answered with **evidence that will exist after implementation**; future work invoked only where the frozen paper already discloses it.

**S1. "Adding an AgentDojo predicate set *is* modifying the framework — you changed the contribution."**
*Answer:* No new abstraction is introduced. Definition 1 is the generic class; §X already frames predicate sets as domain instantiations and §XII-C makes predicate/I_class extension a *structural property*. AgentDojo classes are additional instances reusing existing predicate families (Part 4), with FUNDS_TRANSFER reusing WIRE_TRANSFER. *Evidence:* the Consistency Matrix (Part 1), the instance-mapping table (Part 4), and the pre-committed Predicate Manifest tracing every predicate to §X. **Answered.**

**S2. "Tier-S only — your hardware sovereignty claims are untested here."**
*Answer:* Correct and scoped. AgentDojo empirically exercises the authorization-logic invariants (3, 4, decision layer) at Tier-S; the substrate-dependent invariants (1, 2, and the interlock conjuncts of 6) are carried by the unchanged LAB Tier-H evaluation. *Evidence:* the Tier-S scope disclosure (V2 D-7) and the theorem-coverage table (Part 2). **Answered (disclosed scope, not future work).**

**S3. "Swapping FPR ground truth to AgentDojo's checker is a metric redefinition."**
*Answer:* The metric *definition* (false permit over should-deny population) is unchanged (§VIII-G); only the *label provenance* becomes third-party — which is the intended de-circularization. *Evidence:* metric definitions identical to §VIII-G; the metric firewall keeps Utility/TASR separate. **Answered.**

**S4. "Prompt injection is out of your threat model, so you excuse the failures that matter."**
*Answer:* The **content-layer** of injection is out of scope (Property v; §XII-A); the **resulting action** is fully in scope (§III capability iii). L-DREA is scored on whether an unauthorized *action* externalizes. Honest false permits (Γ=0 predicate incompleteness, F1) are **reported**, not excused; content-layer-only harms (F9) are reported as delimiters. *Evidence:* the failure taxonomy (V2 Part 5) with the Γ=0-vs-Γ>0 diagnostic, plus per-case predicate-gap analysis. **Answered.**

**S5. "You tuned predicates to pass AgentDojo."**
*Answer:* Six leaf manifests under one Merkle root, committed before any run (Part 5), blind-authoring statement, predicates derived from §X semantics, and honest false-permit reporting. *Evidence:* the published root hash predating the run; F1 per-case analysis showing where the frozen set fails. **Answered.**

**S6. "The recipient allowlist is the whole trick, not a reference monitor."**
*Answer:* It is a **cross-domain gate (R3)** derived mechanically from benign environment state (Recipient-Derivation Manifest), identical in kind to §X-A's destination-bank gate. In-environment-recipient injections pass it and are reported as false permits — proving it is not an oracle. *Evidence:* the derivation manifest + reported in-environment false permits. **Answered.**

**S7. "Small N, one benchmark, weak bounds."**
*Answer:* AgentDojo's role is *independence*, not scale (Part 3, function separation); bounds reported at true N, never compared to LAB's 10⁻⁵. The pre-registered **AgentHarm** arm (§IX-F) adds a second independent oracle. *Evidence:* two-benchmark pre-registration already in the frozen paper. **Answered.**

**S8. "Nondeterministic LLM breaks your replay-determinism claim."**
*Answer:* DET-1 is scoped to the authorization decision over a fixed candidate+CTR (§IV-E), not the LLM; temperature 0 + seed + archived transcripts make the ERTuple stream replayable without the model. *Evidence:* the Evaluation Manifest + archived transcripts + independent verifier PASS. **Answered.**

**S9. "You still built the adapter; how do I know it mediates everything?"**
*Answer:* Complete mediation is enforced at the sole chokepoint `run_function`; the coverage audit proves every EEA emitted an ERTuple and every read-only tool did not; the independent verifier re-checks the ledger with zero dependency on the adapter. *Evidence:* the Tool-Mapping Manifest + coverage audit table + verifier exit-0. **Answered.**

**Criticisms requiring genuinely-future work (already disclosed in the frozen paper, so not new debt):**
- **S10.** "Invariants 2–6 aren't machine-checked." → LAB v1.1 (NuSMV/TLA⁺), already scheduled (§VI-D, Table 6). Not answerable by any agent benchmark.
- **S11.** "No independent *hardware*-substrate evaluation." → Tier-H independent evaluation is future work (§XII-F); AgentDojo is Tier-S by nature.

**Part 6 conclusion:** Every criticism that AgentDojo integration *could* create is answerable with post-implementation evidence. The only unanswerable ones (S10, S11) are pre-existing, already-disclosed future work that AgentDojo was never expected to close.

---

## PART 7 — Implementation Authorization

**Determination:** Implementation should proceed **subject to mandatory preconditions**. The scientific design is consistent; nothing in the contribution is modified; but the §IX-F independence claim is only preserved if the pre-registration preconditions are executed *before* experimentation. Approving unconditionally would ignore that dependency.

### Formal approval statement
> The integration of the real AgentDojo benchmark as an independent external validation environment for L-DREA is **scientifically consistent** with the Gamma / L-DREA contribution: it modifies no definition, theorem, proof, assumption, metric definition, benchmark, or claim. It additively extends (i) the set of Definition-1 instantiations, (ii) the empirical evaluation, and (iii) the ground-truth provenance of FPR/UER on the external surface — each under a clause the frozen paper already contains (§X, §IX-F, §XII-C). Implementation is **authorized** on the mandatory preconditions below.

### Prerequisites that MUST already exist before any code is written
1. All six leaf manifests (Predicate, Threshold, Tool-Mapping, Recipient-Derivation, Evaluation, Version) **hash-committed under one published Merkle root**, with the blind-authoring statement (Part 5).
2. The pinned AgentDojo release (repo · tag · 40-char SHA · tool-registry SHA) with N reconciled against the paper's 79/629 (V2 D-9).
3. The final EEA classification rule including the outbound-argument case, and the confirmed single interception point `FunctionsRuntime.run_function` (V2 D-6, Part 1).
4. The recognized-recipient derivation rule, published as a deterministic function of benign environment state (V2 D-2).
5. The paired with/without-L-DREA design across ≥2 frontier models with temperature 0 and the baseline-TASR>0 power gate (V2 D-4).
6. The failure taxonomy (V2 Part 5) adopted as the pre-committed interpretation framework, including the Γ=0-vs-Γ>0 diagnostic.
7. The Tier-S scope statement and the theorem-coverage boundary (Part 2 / V2 D-7).
8. (For reviewer certification, not for code) the verbatim Reviewer 2 text.

### Documents that MUST remain authoritative during implementation
- IEEE Paper (primary), FULL_SPEC (runtime semantics), Execution Integrity.md (benchmark hierarchy) — in that order.
- This verification document + V2 design as the implementation gate; V1 as historical rationale.
- The six committed manifests as the frozen experimental contract.

### What developers are explicitly NOT allowed to change
- Any Gamma / L-DREA construct: Γ authorization, LLC, SAFE_STATE, Evidence Quad, Hydra Ledger, ERTuple, the six invariants, the five structural properties, Definition 1/2/4, authority horizon H, assumptions A1–A4, LCP-6, the metric definitions, LAB/ConcurBench/ASB.
- AgentDojo internals (integration is interposition-only; no edits to AgentDojo source).
- The committed manifests (any change re-opens the anti-circularity gate and voids independence).
- The metric firewall (no fusing Utility/TASR into Gamma metric definitions).
- The claim scope (no asserting zero-event transfer to AgentDojo; no comparing AgentDojo N-bounds to LAB's 10⁻⁵).

---

## FINAL VERDICT

# OPTION B — Implementation Approved with Mandatory Preconditions

### Reasoning

**Why not Option C (not scientifically safe):** The verification is affirmative on every substantive axis. Part 1 shows zero components Modified. Part 2 shows no theorem needs a new assumption, modification, lemma, or weakened claim. Part 3 proves LAB/ConcurBench/ASB remain native and AgentDojo is confined to external validation. Part 4 shows the framework is already generic at Definition 1, requiring zero new abstraction. The design is scientifically sound; there is no unresolved inconsistency. Option C would be inaccurate.

**Why not Option A (unconditional approval):** One frozen *methodological* claim — the §IX-F independence claim — is **not self-executing**. It holds only if the predicate/threshold/mapping/recipient artifacts are authored blind and hash-committed *before* experimentation (Part 5). If a developer authored predicates after inspecting the injection corpus, no theorem would change, but the independence claim in the published paper would be **false** — a research-integrity failure worse than the original circularity. Because that outcome is *possible* absent the preconditions, unconditional approval would be irresponsible.

**Why Option B is exactly right:** The science is consistent and the contribution is fully preserved **conditional on** the six pre-registration manifests, the Tier-S scope statement, the paired multi-model power gate, and the failure-taxonomy interpretation framework being in place before code. These preconditions are enumerated, bounded, and achievable; none requires touching Gamma or AgentDojo. Once they exist and are committed, implementation is scientifically safe and the reviewer's request is satisfiable with honest, outcome-irrespective evidence.

**Certification:** Integrating the real AgentDojo benchmark **does not alter the scientific contribution of Gamma / L-DREA**. It preserves terminology, architecture, theorem wording, benchmark philosophy, evaluation methodology, scientific claims, the evidence model, metrics, and formal assumptions. Implementation is approved the moment the Part 7 preconditions are satisfied and their Merkle root is published — not before.
