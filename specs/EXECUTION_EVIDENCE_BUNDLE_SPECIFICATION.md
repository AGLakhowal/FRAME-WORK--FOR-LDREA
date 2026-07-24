# EXECUTION EVIDENCE BUNDLE (EEB) — DATA-CONTRACT SPECIFICATION

**A software-architecture specification only. No code, no pseudocode, no implementation, no redesign, no optimization. No change to Gamma / L-DREA / IEEE paper / FULL_SPEC / LUIPM / Γ / SAFE_STATE / LAB / ConcurBench / AgentDojo / the RCL specification.**

**Reviewer roles adopted:** IEEE Access Systems Reviewer · Runtime-Systems Architect · Software Architect · Formal-Methods Researcher.

---

## 0. Scope and the one thing the EEB is

The Execution Evidence Bundle is the **immutable data contract** carried from the evidence planes — **A** Transaction, **B** Runtime Context, **C** Authority Infrastructure, **D** External Governance — into the **frozen** Predicate Evaluator / Gamma engine. It is **not** a new scientific construct. It transports evidence and records evidence *quality*; it never authorizes.

> **EEB Prime Invariant (inherited from the RCL Prime Invariant).** The bundle **carries evidence and its provenance**. It contains **zero** authorization semantics, **zero** decision logic, **zero** policy, **zero** thresholds. Every predicate, every threshold, every aggregation, and every decision remains in the frozen engine ([gamma_test_runner.py:133-178](gamma_test_runner.py#L133-L178) single-row; [:868-892](gamma_test_runner.py#L868-L892) vectorized).

**Consumer ground truth (what the contract must satisfy).** The frozen evaluator reads exactly this input set (verified at [gamma_test_runner.py:119-130](gamma_test_runner.py#L119-L130) and [:1114-1124](gamma_test_runner.py#L1114-L1124)): the ten `NODE_GATE_COLS` booleans, `HARM_RISK`, `StaleContext`, `TelemetryFresh`, `Actuated`, `ACT_PERMIT`, the `ReasonCodes` class token (for the class-level veto, [:883-886](gamma_test_runner.py#L883-L886)), and the replay linkage `HASH_prev`/`HASH_current` ([:908-911](gamma_test_runner.py#L908-L911)). The EEB's payload is the union of these inputs, each tagged with its origin plane and provenance — **and nothing more**.

---

## SECTION 1 — Architectural principles

| Principle | Meaning for the EEB |
|---|---|
| **Immutable** | Once created (sealed at decision time), no field ever changes. There is no setter, no post-hoc correction; a new observation produces a *new* bundle, never a mutation. |
| **Append-only** | Bundles are added to the evidence stream; the stream and each bundle are write-once. This is the transport-level counterpart of the append-only Hydra Ledger (DET4). |
| **Deterministic** | The bundle is a pure function of the observed evidence at decision time. Given identical evidence, an identical bundle is produced (structural determinism; supports DET1). |
| **Replay-safe** | The bundle carries everything the Predicate Evaluator needs to reproduce *identical* inputs on replay, without re-contacting live services (§7). |
| **Reproducible** | Independent re-serialization of the same evidence yields byte-identical canonical form (stable field order, canonical encoding), enabling hash verification. |
| **Class-blind** | No field is produced from, derived from, or correlated to the `Class` ground-truth label. `Class` has **no field, no port, and no producer** in the bundle. It exists only downstream at scoring. |
| **Versioned** | The bundle carries an explicit schema version and method version so long-term consumers can validate compatibility (§6 version mismatch). |
| **Serializable** | The bundle has a single canonical, self-describing serialization suitable for persistence, transport, and hashing. |
| **No authorization semantics** | The bundle encodes *what was observed*, never *what should be permitted*. It has no permit/deny field of its own. |
| **No derived decisions** | Γ, Π, SAFE_STATE, ACT_PERMIT-as-decision, ReasonCodes-as-verdict, FirstFailingGate are **engine outputs (plane E)** and are **not** inputs of the bundle. |
| **No policy ownership** | Thresholds (θ, limits, freshness bounds), directives, and enterprise rules are **not** in the bundle; they live in the frozen policy plane and are applied by the evaluator. |
| **Provenance-complete** | Every evidence field carries an origin plane, a producer identity, and an evidence-quality marker. No field may have unknown provenance (§4). |

**Why these and no others.** Each principle is a *transport* property (immutability, versioning, serialization, replay) or a *non-ownership* guarantee (no semantics/decisions/policy/thresholds, Class-blind). Together they make the EEB a stable interface: consumers can evolve, services can fail, arms can differ — the contract's meaning does not drift.

---

## SECTION 2 — Complete field catalogue

The bundle has three regions: **(2.1) Envelope** (structural transport metadata, plane = *envelope*, carries no evidence semantics), **(2.2) Evidence payload** (planes A/B/C/D — the Predicate Evaluator inputs), and **(2.3) Per-field provenance descriptor** (a sub-record attached to every payload field). Global rule: **every field is Immutable = YES**; stated once here, confirmed per row.

Column legend: Plane ∈ {Env, A, B, C, D, E-cached}; Req = Required/Optional; Persist = persisted to ledger; Replay = must be identical on replay (§7); Crypto = covered by the bundle integrity digest / chain; Recon = reconstructable from other evidence.

### 2.1 Envelope fields (structural; NOT predicate inputs)

| Field | Description | Type | Producer | Consumer | Plane | Req | Persist | Replay | Crypto | Recon | Justification |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `bundle_id` | unique id of this bundle/decision | opaque string | RCL | all | Env | Req | Yes | Yes | Yes | No | correlation key; replay addressing (Appendix A evidence model) |
| `schema_version` | EEB contract version | string | RCL | Evaluator, verifier | Env | Req | Yes | Yes | Yes | No | long-term compatibility (§6) |
| `method_version` | frozen method tag | string | RCL (reads `METHOD_VERSION`) | Evidence Quad | Env | Req | Yes | Yes | Yes | No | binds bundle to engine version; already in Evidence Quad ([:1102](gamma_test_runner.py#L1102)) |
| `created_at` | decision-time timestamp (context clock) | timestamp | RCL | Evaluator (freshness base), ledger | Env | Req | Yes | Yes | Yes | No | replay-determinism reference (DET1) |
| `subject_ref` | opaque correlation handle (NOT identity, NOT a predicate) | opaque string / null | RCL | ledger, windowing | Env | Opt | Yes | Yes | Yes | No | enables plane-B windowing where a key exists; **carries no authorization meaning** |
| `integrity_digest` | canonical hash over all fields | hash | RCL | verifier | Env | Req | Yes | Yes | Yes | Yes (recompute) | tamper-evidence; ties to ledger chain |

### 2.2 Evidence payload fields (Predicate Evaluator inputs)

| Field | Description | Type | Producer | Consumer | Plane | Req | Persist | Replay | Crypto | Recon | Justification |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `txn_amount` | transaction amount | number | Transaction Interpreter | Evaluator (amount-bound gate) | **A** | Req | Yes | Yes | Yes | No | native request fact (§V observable request) |
| `txn_time` | transaction time / arrival | number/timestamp | Transaction Interpreter | Evaluator, RCL window | **A** | Req | Yes | Yes | Yes | No | native request fact; ordering base |
| `txn_action_ref` | action / externalization target reference | opaque string | Transaction Interpreter | Evaluator (mediation scope) | **A** | Req | Yes | Yes | Yes | No | Definition 1 externalization boundary |
| `txn_feature_ref` | opaque feature embedding (e.g. `V1..V28`) **as governance-service input only; NOT a predicate** | opaque vector / ref | Transaction Interpreter | GovernancePort (D) input | **A** | Opt | Yes | Yes | Yes | No | may feed a risk service; **never** read as a predicate (anti-mixing, RCL §5) |
| `node_predicate_vector` | the `NODE_GATE_COLS` booleans (`Gate_A1..A7`, `Lambda_G`, `TOKEN_VALID`, `AuthoritySignatureValid`), each with its own provenance descriptor | list of provenanced booleans | RCL exposes; per-element producer varies by binding | Evaluator ([:119-130](gamma_test_runner.py#L119-L130)) | **A/B/C/D** per binding | Req | Yes | Yes | Yes | No | the frozen predicate vector `G`; EEB fixes no gate's plane — the binding does |
| `harm_risk_score` | hazard score ∈ [0,1] | number | Governance service | Evaluator (`HARM_RISK`, [:871](gamma_test_runner.py#L871)) | **D** | Req | Yes | Yes | Yes | No | §V HARM admissibility; a governance-service *output*, transported not computed |
| `class_veto_evidence` | class-level deficit signal; the non-Class origin of the `ReasonCodes` class token read at [:883-886](gamma_test_runner.py#L883-L886) | enum/string | Governance/Authority plane | Evaluator (class veto) | **D** (or C) | Opt | Yes | Yes | Yes | No | class-level veto input; **must be produced by governance, never by `Class`** |
| `stale_context` | context-staleness reading | boolean | RCL `FreshnessClock` | Evaluator (`StaleContext`, [:873](gamma_test_runner.py#L873)) | **B** | Req | Yes | Yes | Yes | Yes (from timestamps) | §V-F / I5 TOCTOU |
| `telemetry_fresh` | telemetry-freshness reading | boolean | RCL `FreshnessClock` | Evaluator (`TelemetryFresh`, [:874](gamma_test_runner.py#L874)) | **B** | Req | Yes | Yes | Yes | Yes (from timestamps) | §V-B ISB freshness |
| `commit_timestamp` | commit-log event time | timestamp/null | RCL `CommitActuateJournal` | Evaluator (ordering, [:918](gamma_test_runner.py#L918)) | **B** | Opt* | Yes | Yes | Yes | No | §V-F commit-before-actuate |
| `actuate_timestamp` | actuation-log event time | timestamp/null | RCL `CommitActuateJournal` | Evaluator (ordering, [:919](gamma_test_runner.py#L919)) | **B** | Opt* | Yes | Yes | Yes | No | §V-F / I5 |
| `commit_before_actuate` | ordering-asserted flag | boolean | RCL `CommitActuateJournal` | Evaluator ([:923](gamma_test_runner.py#L923)) | **B** | Opt* | Yes | Yes | Yes | Yes (from the two timestamps) | I5 |
| `actuation_observation` | whether externalization occurred/was intended (the Eq.7 `Actuated`/`ACT_PERMIT` execute term) | boolean | RCL (runtime fact) | Evaluator (Eq.7 execute, [:931](gamma_test_runner.py#L931)) | **B/E** | Opt | Yes | Yes | Yes | No | Eq.7 unauthorized-execution term; **naming-collision caveat in §10** |
| `prior_ledger_link` | previous decision's `HASH_current` (for adjacency) | hash | Evidence Collector (cached) | Evaluator (replay link, [:908-911](gamma_test_runner.py#L908-L911)) | **E-cached** | Req | Yes | Yes | Yes | Yes (from prior bundle) | Appendix A replay determinism |

\* `commit_*`/`actuate_*` are Required **iff** `actuation_observation` indicates an actuated op (they are meaningless for a non-actuated request); this conditional is a *shape* rule, not a policy.

**Fields deliberately ABSENT (plane E — engine outputs, never bundle inputs):** `DerivedGammaG`, `DerivedPi`, `DerivedDecision`/`Status`, `SAFE_STATE`, `ACT_PERMIT` (as a *decision*), `ReasonCodes` (as a *verdict*), `FirstFailingGate`, `ExecutionLegitimacy`, `DerivedISB`. These are produced by Gamma downstream ([:876-901](gamma_test_runner.py#L876-L901)) and must not be carried as inputs — carrying them would re-introduce the authoring inversion that caused the original leakage.

### 2.3 Per-field provenance descriptor (attached to every 2.2 field)

| Sub-field | Description | Type | Justification |
|---|---|---|---|
| `origin_plane` | A / B / C / D / E-cached | enum | provenance completeness (§4) |
| `producer_id` | identity of the producing component/service | string | auditability |
| `evidence_quality` | `PRESENT` / `ABSENT` / `DEGRADED` / `EXPIRED` | enum | records quality; **never decides** (§6) |
| `observed_at` | when the evidence was observed | timestamp | freshness/replay |
| `verification_method` | how the value's integrity is checked (e.g. signature-verified, timestamp-derived, service-attested) | enum | §4 verification |
| `trust_level` | attested / self-reported / derived | enum | §4 trust |

The descriptor **describes** evidence; it holds no threshold and makes no pass/fail judgement. `evidence_quality = ABSENT` is a *fact about availability*, not a decision — the frozen fail-closed policy (FULL_SPEC 2.3 / 0.10) decides what absence means.

---

## SECTION 3 — Field lifecycle

Applies uniformly (the immutability principle makes the lifecycle simple).

| Stage | Rule |
|---|---|
| **Creation** | All fields are populated **once**, at decision time, by their producer (Transaction Interpreter, RCL, or a port surfacing C/D). The bundle is then **sealed**. |
| **Validation** | At seal, structural validation only: required fields present, types correct, provenance descriptor complete, canonical form well-formed, `integrity_digest` computed. Validation checks **shape and provenance**, never evidence *content* against any threshold. |
| **Consumption** | The Predicate Evaluator reads fields **read-only**. Consumption never writes back. |
| **Persistence** | The sealed bundle is persisted into the Evidence Collector / Hydra Ledger, append-only, alongside the Evidence Quad the engine emits. |
| **Replay** | On replay, the persisted bundle is re-read to reproduce identical evaluator inputs (§7). No live re-fetch. |
| **Archival** | Bundles are archived as part of the append-only ledger; retention follows the ledger's policy (not defined here — out of contract scope). |
| **Deletion policy** | **No in-place deletion or edit.** The append-only ledger forbids mutation; correction is a new bundle, never an edit (consistent with DET4). |
| **Mutation policy** | **None.** Immutable after seal. There is no code path that mutates a sealed field. |
| **Ownership** | Envelope + plane-B fields owned by the **RCL**; plane-A owned by the **Transaction Interpreter**; plane-C/D fields **owned by their services**, merely *carried* by the bundle. The bundle owns **structure**, never the *meaning* of any field. |

**No field changes after bundle creation** — this is the load-bearing lifecycle guarantee and the precondition for replay determinism.

---

## SECTION 4 — Evidence provenance

For every payload field: **Producer · How produced · Observable source · Verification method · Trust level · Replay verification · Failure behaviour.** Grouped by plane (fields within a plane share the pattern).

| Plane / field group | Producer | How produced | Observable source | Verification method | Trust level | Replay verification | Failure behaviour |
|---|---|---|---|---|---|---|---|
| **A** `txn_amount`, `txn_time`, `txn_action_ref`, `txn_feature_ref` | Transaction Interpreter | direct read of the request payload | the transaction record | field-presence + type; digest coverage | self-reported (payload) | value must be byte-identical on replay | if malformed → `evidence_quality=DEGRADED`; engine applies frozen fail-closed |
| **B** `stale_context`, `telemetry_fresh`, `commit_*`, `actuate_*`, `commit_before_actuate`, `actuation_observation` | RCL (FreshnessClock, CommitActuateJournal) | pure derivation from observed substrate timestamps/events | context/telemetry/commit/actuation clocks & logs | timestamp-derived; recomputable from `observed_at` deltas | derived (deterministic) | derived fields recomputed from persisted timestamps must match | if source clock/event missing → `ABSENT`/`EXPIRED`; never fabricated |
| **C** `node_predicate_vector` (authority-bound elements), `TOKEN_VALID`, `AuthoritySignatureValid` | Authority Service (via AuthorityPort) | service lookup / signature verification | token store, HSM/PKI, approval workflow | signature-verified / service-attested | attested | recorded result replayed as-is (service NOT re-contacted) | if service unavailable → `ABSENT` (§6); engine fail-closes; **never** synthesized |
| **D** `harm_risk_score`, `class_veto_evidence`, governance-bound vector elements | Governance service (via GovernancePort) | risk/AML/sanctions evaluation | external governance service | service-attested (optionally signed) | attested / self-reported | recorded score replayed as-is | if service unavailable → `ABSENT`; engine fail-closes; **never** the `Class` label |
| **E-cached** `prior_ledger_link` | Evidence Collector | copied from prior bundle's `HASH_current` | the ledger | adjacency recompute against prior bundle | derived (cached) | adjacency re-checked on replay (`gamma_replay_verify.py`) | if link breaks → `ReplayDivergence` recorded by engine, not by bundle |
| **Envelope** | RCL | assigned/derived at seal | RCL state | digest recompute | derived | `integrity_digest` recomputed & compared | mismatch → bundle rejected as corrupted (§6) |

**No field has unknown provenance** — every row above names a producer, a source, and a verification method. The one honest caveat: trust levels differ (attested C/D vs. self-reported A vs. derived B/E); the descriptor records this so a reviewer can weight it. The bundle does not *upgrade* trust; it only reports it.

---

## SECTION 5 — Interface contract (responsibilities)

```
 Transaction Interpreter → EXECUTION EVIDENCE BUNDLE → Predicate Evaluator → Gamma → Evidence Quad → Hydra Ledger
```

| Interface | Responsibility | Must NOT |
|---|---|---|
| **Transaction Interpreter** | read the request; populate plane-A fields + their provenance | derive predicates; touch B/C/D; read `Class` |
| **RCL (bundle assembler)** | own plane-B fields; surface A via TransactionPort and C/D via Authority/Governance ports; assemble + seal + digest the bundle | decide; author thresholds; synthesize absent C/D evidence |
| **Execution Evidence Bundle** | be the immutable, provenance-complete, Class-blind carrier of evaluator inputs | contain any decision, policy, threshold, or plane-E output |
| **Predicate Evaluator** | read bundle fields; instantiate the frozen predicate families; read thresholds from the **policy plane** (not the bundle) | mutate the bundle; invent evidence |
| **Gamma** | compute `Γ = max_i d_i`, `Π`, SAFE_STATE/ACT_PERMIT, ReasonCodes, FirstFailingGate (plane E) | read `Class`; be modified |
| **Evidence Quad** | bind {decision, method_version, policy_hash, ledger_hash} per decision ([:1099-1107](gamma_test_runner.py#L1099-L1107)) | carry raw evidence back as authority |
| **Hydra Ledger** | append-only persistence + hash chain of {bundle, quad} | mutate or delete |

The bundle is a **passive carrier** between the Interpreter/RCL (producers) and the Evaluator (consumer); Gamma and downstream are strictly its consumers, never its editors.

---

## SECTION 6 — Error handling (records quality; never decides)

The bundle **never makes an authorization decision.** For each condition it records an `evidence_quality` (and, for structural faults, is rejected at the transport layer). What the *absence/fault means* for authorization is decided **only** by the frozen engine's fail-closed policy.

| Condition | Bundle behaviour (records, does not decide) | Who decides the consequence |
|---|---|---|
| **Missing evidence** (a payload field's producer returns nothing) | field marked `evidence_quality=ABSENT`; value carried as null | frozen fail-closed policy (FULL_SPEC 2.3/0.10) |
| **Unavailable Authority Service** | affected C fields → `ABSENT`; `producer_id` records the unreachable service | engine (deficit → SAFE_STATE) |
| **Unavailable Governance Service** | affected D fields (e.g. `harm_risk_score`) → `ABSENT` | engine (fail-closed) |
| **Unknown transaction fields** | unknown A fields dropped from the typed payload; noted in envelope; never passed as predicates | evaluator ignores; no decision by bundle |
| **Corrupted evidence** (fails integrity/type check at seal) | bundle **rejected at validation**; not sealed, not consumed | transport layer (reject); no partial bundle reaches the engine |
| **Replay mismatch** (recomputed digest ≠ recorded) | replay flagged; bundle marked non-reproducible | replay verifier (`gamma_replay_verify.py`); engine records `ReplayDivergence` |
| **Version mismatch** (`schema_version`/`method_version` incompatible with consumer) | bundle rejected/quarantined by the consumer's version gate | consumer version policy |
| **Malformed bundle** (structure invalid) | rejected at validation; never enters evaluation | transport layer |
| **Expired context** (`observed_at` older than the substrate's freshness window) | relevant B field → `evidence_quality=EXPIRED` | engine (freshness deficit) |
| **Missing runtime context** (RCL cannot produce a B object) | B field → `ABSENT` | engine (fail-closed) |

**Cardinal rule:** every branch above either (a) records a *quality marker* on the evidence or (b) *rejects the whole bundle* structurally. Neither branch is an authorization decision. The engine's frozen fail-closed default converts absent/degraded evidence into SAFE_STATE — the bundle merely tells the truth about what it observed.

---

## SECTION 7 — Replay contract

Replay must reproduce **identical Predicate Evaluator inputs** from the persisted bundle, without re-contacting any live service.

| Field class | Replay obligation |
|---|---|
| **Must remain identical (bitwise)** | all plane-A fields, all attested C/D results (`harm_risk_score`, `class_veto_evidence`, token/signature booleans), `created_at`, `bundle_id`, `method_version`, `schema_version`, and every recorded value the evaluator read. These are **frozen at seal** and replayed as-is. |
| **Environment-specific (excluded from the identity requirement)** | `producer_id` host details, transport metadata, and any wall-clock of the *replaying* host. These may differ; they are not evaluator inputs. |
| **Deterministic (pure functions of persisted inputs)** | `integrity_digest` (recomputed and compared), `stale_context`/`telemetry_fresh`/`commit_before_actuate` (recomputable from persisted timestamps), `prior_ledger_link` adjacency (re-checked against the prior bundle). |
| **Requires recomputation on replay** | the `integrity_digest` and the derived B flags above are recomputed and must **match** the recorded values; a mismatch is a replay failure (§6). |

**Guarantee.** Because attested C/D evidence is *recorded* (not re-fetched) and A/derived-B are frozen/deterministic, feeding the persisted bundle to the frozen evaluator yields the *same deficit vector* → the *same* Γ → the *same* decision. This is the transport-level basis of DET1 and the Appendix-A replay claim, and it is exactly what `gamma_replay_verify.py` re-checks for the ledger.

---

## SECTION 8 — Traceability

Every field → its anchor in the frozen specification. (Where an explicit FULL_SPEC subsection number is not enumerable from the repository, the named construct is cited rather than an invented number.)

| Field | Paper section | FULL_SPEC | Definition/Theorem | RCL object | Evaluator input | Gamma use | Evidence Quad / Ledger |
|---|---|---|---|---|---|---|---|
| `txn_amount`, `txn_time`, `txn_action_ref` | §V (observable request); Def. 1 | 2.3 | Definition 1 | TransactionPort | amount/ordering-bound gate | deficit `d_i` | persisted |
| `txn_feature_ref` | §V (risk input) | — | — (input to D, not a predicate) | TransactionPort→GovernancePort | (not a predicate) | none directly | persisted |
| `node_predicate_vector` | §V predicate vector `G` | §7.1 | node predicates | RCL bundle + ports | `NODE_GATE_COLS` ([:119-130](gamma_test_runner.py#L119-L130)) | `Γ_G = max d_i` | Quad |
| `harm_risk_score` | §V HARM admissibility | §7.1 | HARM deficit | GovernancePort | `HARM_RISK` ([:871](gamma_test_runner.py#L871)) | deficit | Quad |
| `class_veto_evidence` | §V class-level veto | — | class veto | Governance/Authority port | class token ([:883-886](gamma_test_runner.py#L883-L886)) | `Γ_class` | Quad |
| `stale_context`, `telemetry_fresh` | §V-B ISB; §V-F | §VI-B I5 | ISB; Invariant I5 | FreshnessClock | `StaleContext`,`TelemetryFresh` | deficit; ISB | Quad |
| `commit_*`, `actuate_*`, `commit_before_actuate` | §V-F | §VI-B I5 | Invariant I5 | CommitActuateJournal | ordering check ([:918-924](gamma_test_runner.py#L918-L924)) | I5 | Quad |
| `actuation_observation` | Eq. 7 | — | Eq. 7 unauthorized-exec | RCL (runtime fact) | execute term ([:931](gamma_test_runner.py#L931)) | Eq. 7 | Quad |
| `TOKEN_VALID`, `AuthoritySignatureValid` | Eq. 7; §V-B | 2.3 | Definition 2 | AuthorityPort | gate cols | deficit; ISB | Quad |
| `prior_ledger_link` | Appendix A | §Appendix A | DET1/DET4 | Evidence Collector | replay link ([:908-911](gamma_test_runner.py#L908-L911)) | replay determinism | Ledger chain |
| `bundle_id`,`created_at`,`method_version`,`schema_version`,`integrity_digest`,`subject_ref` | Appendix A (evidence) | — | DET1/DET4 | RCL envelope | (transport) | none | Ledger |

**Untraceable fields: none.** The single field with no *predicate* anchor — `txn_feature_ref` — is explicitly typed as a **governance-service input, not a predicate**, and is traceable as such (it feeds plane D, never the evaluator directly). It is identified here rather than invented into a predicate.

---

## SECTION 9 — Architecture diagram

Provenance legend: **[A]** Transaction · **[B]** Runtime Context · **[C]** Authority · **[D]** Governance · **[E]** Derived (Gamma) · **[Env]** envelope.

```
 Transaction (request)
   │  Amount, Time, action [, features]
   ▼
 Transaction Interpreter ───────────────► populates [A] fields (+provenance)      PRODUCER: Interpreter
   │
   ▼
┌─────────────────────────── EXECUTION EVIDENCE BUNDLE (immutable, Class-blind) ───────────────────────────┐
│  [Env] bundle_id, schema/method_version, created_at, subject_ref, integrity_digest                        │
│  [A]   txn_amount, txn_time, txn_action_ref, txn_feature_ref(→D input only)      ◄─ Transaction Interpreter│
│  [B]   stale_context, telemetry_fresh, commit_*/actuate_*, commit_before_actuate, actuation_observation    │
│                                                                                  ◄─ RCL (owns B)           │
│  [C]   node authority elements, TOKEN_VALID, AuthoritySignatureValid             ◄─ AuthorityPort (Service)│
│  [D]   harm_risk_score, class_veto_evidence, sanctions/aml elements              ◄─ GovernancePort (Service)│
│  [E-cached] prior_ledger_link                                                    ◄─ Evidence Collector     │
│  (each payload field carries: origin_plane, producer_id, evidence_quality, observed_at, verify, trust)     │
│  CONTAINS NO: decision · policy · threshold · Γ · SAFE_STATE · ReasonCodes-verdict · Class                 │
└───────────────────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                                 ▼                          CONSUMER: Predicate Evaluator
 Predicate Evaluator  (reads bundle; reads thresholds from POLICY plane, not the bundle)
   │  builds deficit vector G from [A]+[B]+[C]+[D]
   ▼
 Gamma (FROZEN)  Γ = max_i d_i ; Π = 1[Γ=0]                                        [E] outputs
   │
   ▼
 SAFE_STATE / ACT_PERMIT   [E]                                                     CONSUMER: execution boundary
   │
   ▼
 Evidence Quad  {decision, method_version, policy_hash, ledger_hash}  [E]          PRODUCER: Gamma
   │
   ▼
 Hydra Ledger  (append-only; persists {bundle, quad}; hash-chained)               CONSUMER: replay verifier
   │
   ▼
 Ground-Truth Evaluation ◄── Class enters HERE and ONLY here → FPR/FDR/UER
```

Everything above "Ground-Truth Evaluation" is Class-blind; the bundle sits wholly inside that region.

---

## SECTION 10 — Implementation readiness

**Sufficient to implement without further scientific decisions?** **Yes, with the caveats below flagged (not silently resolved).** The contract fixes: the exact field set (§2, pinned to the frozen evaluator's actual inputs), immutability/lifecycle (§3), provenance obligations (§4), interface responsibilities (§5), error→quality mapping (§6), the replay identity set (§7), and full traceability (§8). Remaining choices are **engineering** (serialization format, hash algorithm selection, container types) — not scientific.

**Remaining ambiguities — explicitly listed, deliberately unresolved (they require an owner's decision, not a silent default):**

1. **`actuation_observation` naming/temporal collision.** The frozen engine reads `Actuated`/`ACT_PERMIT` in the Eq.7 execute term ([:931](gamma_test_runner.py#L931)), yet `ACT_PERMIT` is *also* a plane-E decision name. Whether the bundle carries a *pre-decision intent* or a *post-actuation observation* (and how the counterfactual UER is timed) must be decided by the runtime owner. This spec carries it as a plane-B/E runtime fact and flags the collision; it does not pick a semantics.
2. **`class_veto_evidence` producer plane.** The class-level veto's non-Class origin could be a governance signal (D) or an authority signal (C) depending on deployment. The bundle supports either via provenance; the *binding* is a policy decision outside this contract.
3. **`subject_ref` availability.** Per-subject plane-B windowing depends on a correlation key the transaction source may or may not provide (the credit-card arm does **not**). The field is Optional by design; whether a given arm populates it is a data-source fact, not a contract choice.
4. **Canonical serialization + hash algorithm.** The contract requires *a* deterministic canonical form and *a* digest; the specific encoding and hash function are engineering selections (must be fixed once, then frozen for replay stability).
5. **Retention/archival window.** Ledger retention is referenced but intentionally out of contract scope; the owning system sets it.

None of these five affects Class-blindness, replay determinism, or the frozen semantics; each is a *binding/engineering* decision for the implementing team.

---

## FINAL VALIDATION

1. **New scientific construct?** **No.** Every field is transport of an input the frozen evaluator already reads (§2, §8); the bundle defines no predicate, threshold, or theorem.
2. **Changes Gamma?** **No.** Gamma consumes the same input schema unchanged ([:133-178](gamma_test_runner.py#L133-L178), [:868-892](gamma_test_runner.py#L868-L892)); the bundle is strictly upstream.
3. **Changes any theorem?** **No.** T0–T9 / I1–I6 are statements over the deficit vector and decision; transport of the vector's evidence alters neither.
4. **Changes authorization semantics?** **No.** `Γ=max d_i`, `Π=1[Γ=0]`, SAFE_STATE fail-closed, ISB, commit-before-actuate remain frozen; the bundle decides nothing (§6 cardinal rule).
5. **Owns any policy?** **No.** Thresholds/directives/enterprise rules live in the policy plane; the bundle reads none and carries none.
6. **Owns any predicates?** **No.** It carries predicate *inputs* with provenance; predicate *definitions* stay in the frozen evaluator.
7. **Owns any thresholds?** **No.** θ, limits, and freshness bounds are applied by the engine from the policy plane, never stored in the bundle.
8. **Remains Class-blind?** **Yes.** No field is produced from or correlated to `Class`; `Class` has no field, no port, no producer; it enters only at Ground-Truth Evaluation (§9). Absent C/D evidence is marked `ABSENT`, never backfilled with the label.
9. **Preserves replay determinism?** **Yes.** Attested evidence is recorded (not re-fetched), A/derived-B are frozen/deterministic, and the digest + adjacency are recomputed and compared on replay (§7) — identical bundle ⇒ identical evaluator inputs ⇒ identical decision (DET1).
10. **Can the RCL now be implemented directly from this specification?** **Yes**, subject to the five flagged engineering/binding decisions in §10. All *scientific* decisions are pinned; what remains are serialization, hashing, container, subject-key availability, and the actuation-timing binding — none of which touch Gamma, the predicates, the policy, or Class-blindness.

---

*Software-architecture data-contract specification only. No code, pseudocode, implementation, redesign, or optimization. No modification to Gamma, L-DREA, the IEEE paper, FULL_SPEC, LUIPM, Γ, SAFE_STATE, LAB, ConcurBench, AgentDojo, or the RCL specification. Existing components are cited by location solely to pin the bundle's transported fields to the frozen contribution.*
