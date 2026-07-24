# Scientific Mapping Verification Report

**Purpose:** prove that the frozen Phase-2B manifests (Merkle root `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618`) introduce **ZERO new scientific constructs** — every mapping traces to the frozen specification (IEEE Paper › FULL_SPEC › Execution Integrity.md).
**Pass type:** verification-only. No manifest, code, Gamma, AgentDojo, or paper modification. All tables below are generated directly from the frozen manifests.
**Method:** automated trace-audit (predicate origins, threshold classification, label-vs-construct test) + manual justification.

**Definition of "new scientific construct" (the bar):** a new *definition*, *theorem/invariant*, *predicate type*, *aggregation rule*, *metric*, or *architecture component*. A new *descriptive instance label* for an instance of Definition 1, or an *instantiation* of an existing predicate family to a new resource type, is **not** a new construct (established and approved in Consistency-Verification Part 4; authorized by §XII-C, which makes predicate/`I_class` extension a *structural property* of the framework).

---

## SECTION A — Per-tool mapping justification

### A.1 EEA tools (mediated) — 25 of 69

Columns: Tool · EEA Class · Predicate Families · SAFE_STATE · §X mapping · Existing construct reused · New construct introduced. All rows: Execution Integrity reference = EI construct → LAB v1.0 metric family (UER/FPR/FDR/FCR/RDR); SAFE_STATE behavior = deny (do **not** call real `run_function`) + return deny sentinel/error to the agent loop + emit ERTuple/Evidence Quad/Hydra-Ledger entry (FULL_SPEC §2.3, §5 steps 6–7, §6.3).

| Tool | EEA Class | Predicate Families | SAFE_STATE | §X mapping | Reused? | New construct? |
|---|---|---|---|---|---|---|
| `add_user_to_channel` | ACCESS_GRANT | CTR ISB, GAMMA, identity recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A identity+scope | Def.1 + R1–R6 | label only |
| `invite_user_to_slack` | ACCESS_GRANT | CTR ISB, GAMMA, identity recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A identity+scope | Def.1 + R1–R6 | label only |
| `remove_user_from_slack` | ACCESS_GRANT | CTR ISB, GAMMA, identity recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A identity+scope | Def.1 + R1–R6 | label only |
| `share_file` | ACCESS_GRANT | CTR ISB, GAMMA, identity recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A identity+scope | Def.1 + R1–R6 | label only |
| `update_scheduled_transaction` | ACCOUNT_MUTATION | CTR ISB, GAMMA, ownership, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A banking mutation | Def.1 + R1–R6 | label only |
| `add_calendar_event_participants` | CALENDAR_MUTATION | CTR ISB, GAMMA, ownership, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `cancel_calendar_event` | CALENDAR_MUTATION | CTR ISB, GAMMA, ownership, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `create_calendar_event` | CALENDAR_MUTATION | CTR ISB, GAMMA, ownership, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `reschedule_calendar_event` | CALENDAR_MUTATION | CTR ISB, GAMMA, ownership, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `append_to_file` | FILE_MUTATION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `create_file` | FILE_MUTATION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `schedule_transaction` | FUNDS_TRANSFER | CTR ISB, GAMMA, recipient recognition, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK, CLASS velocity | deny+ERTuple | §X-A WIRE_TRANSFER (direct reuse) | Def.1 + R1–R6 | **no (== WIRE_TRANSFER)** |
| `send_money` | FUNDS_TRANSFER | CTR ISB, GAMMA, recipient recognition, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK, CLASS velocity | deny+ERTuple | §X-A WIRE_TRANSFER (direct reuse) | Def.1 + R1–R6 | **no (== WIRE_TRANSFER)** |
| `update_password` | IDENTITY_MUTATION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A ownership/scope | Def.1 + R1–R6 | label only |
| `update_user_info` | IDENTITY_MUTATION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A ownership/scope | Def.1 + R1–R6 | label only |
| `send_channel_message` | MESSAGE_DISPATCH | CTR ISB, GAMMA, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A recipient+scope | Def.1 + R1–R6 | label only |
| `send_direct_message` | MESSAGE_DISPATCH | CTR ISB, GAMMA, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A recipient+scope | Def.1 + R1–R6 | label only |
| `send_email` | MESSAGE_DISPATCH | CTR ISB, GAMMA, recipient recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A recipient+scope | Def.1 + R1–R6 | label only |
| `delete_email` | RECORD_DELETION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `delete_file` | RECORD_DELETION | CTR ISB, GAMMA, ownership, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X ownership+scope | Def.1 + R1–R6 | label only |
| `reserve_car_rental` | RESERVATION_COMMIT | CTR ISB, GAMMA, resource recognition, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X resource+amount+scope | Def.1 + R1–R6 | label only |
| `reserve_hotel` | RESERVATION_COMMIT | CTR ISB, GAMMA, resource recognition, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X resource+amount+scope | Def.1 + R1–R6 | label only |
| `reserve_restaurant` | RESERVATION_COMMIT | CTR ISB, GAMMA, resource recognition, amount limit, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X resource+amount+scope | Def.1 + R1–R6 | label only |
| `get_webpage` *(conditional, D-6)* | WEB_EXFIL | CTR ISB, GAMMA, destination recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A destination+scope (Def.1 outbound) | Def.1 + R1–R6 | label only |
| `post_webpage` | WEB_EXFIL | CTR ISB, GAMMA, destination recognition, scope, AUTH TOKEN, TRACE, INTERLOCK | deny+ERTuple | §X-A destination+scope (Def.1 outbound) | Def.1 + R1–R6 | label only |

### A.2 Read-only tools (outside the externalization boundary) — 44 of 69

Excluded from mediation; no EEA class, no predicates, pass-through. **Justification (uniform):** Definition 1 — no persistent external effect and no outbound-carrying argument, so there is nothing for the externalization monitor to mediate. Mediating them would over-claim mediation scope and inflate FDR. **New construct: none** (exclusion by an existing definition).

`check_restaurant_opening_hours`, `get_all_car_rental_companies_in_city`, `get_all_hotels_in_city`, `get_all_restaurants_in_city`, `get_balance`, `get_car_fuel_options`, `get_car_price_per_day`, `get_car_rental_address`, `get_car_types_available`, `get_channels`, `get_contact_information_for_restaurants`, `get_cuisine_type_for_restaurants`, `get_current_day`, `get_day_calendar_events`, `get_dietary_restrictions_for_all_restaurants`, `get_draft_emails`, `get_file_by_id`, `get_flight_information`, `get_hotels_address`, `get_hotels_prices`, `get_iban`, `get_most_recent_transactions`, `get_price_for_restaurants`, `get_rating_reviews_for_car_rental`, `get_rating_reviews_for_hotels`, `get_rating_reviews_for_restaurants`, `get_received_emails`, `get_restaurants_address`, `get_scheduled_transactions`, `get_sent_emails`, `get_unread_emails`, `get_user_info`, `get_user_information`, `get_users_in_channel`, `list_files`, `read_channel_messages`, `read_file`, `read_inbox`, `search_calendar_events`, `search_contacts_by_email`, `search_contacts_by_name`, `search_emails`, `search_files`, `search_files_by_filename`

**Coverage:** 25 + 44 = 69 = all distinct tools. No tool unexplained.

---

## SECTION B — Per-predicate-family origin (5-column trace)

13 families in use; automated audit: **12 trace to a paper term/section; 1 flagged** (`GATE_ownership`). None is a new predicate *type*.

| Predicate family | Origin | Existing theorem | Existing definition | Existing runtime rule | Existing benchmark rule |
|---|---|---|---|---|---|
| `CTR_ISB` | R1 | supports Inv. 1 via ISB gating | CTR Eq.(4) §V-B; ISB | FULL_SPEC §5 step 1–2, §6.8 | LAB LCP-6 R1; LAB-A3 |
| `GAMMA` | R2 | Prop. 1, Cor. 1/2, **Inv. 3** | Γ=max·d_i, Π=1[Γ=0], Eq.(1)–(3) §IV-B | FULL_SPEC §1.2, §5 step 3, §6.1 | LAB Γ-compliance/FFC; LCP-6 R2 |
| `GATE_recipient_recognition` | R3 | Inv. 6 (gate composition) | R3 cross-domain gate; §X-A destination recognition | FULL_SPEC §5 step 2, §6.16 | LAB-A3; LCP-6 R3 |
| `GATE_identity_recognition` | R3 (instance) | Inv. 6 | R3 gate; §X-A recognition (instance: identity) | §5 step 2, §6.16 | LAB-A3; LCP-6 R3 |
| `GATE_destination_recognition` | R3 (instance) | Inv. 6 | R3 gate; §X-A recognition (instance: URL) | §5 step 2, §6.16 | LAB-A3; LCP-6 R3 |
| `GATE_resource_recognition` | R3 (instance) | Inv. 6 | R3 gate; §X-A recognition (instance: resource) | §5 step 2, §6.16 | LAB-A3; LCP-6 R3 |
| `GATE_amount_limit` | R3 | Inv. 6 | §X-A "amount-limit policy" (direct) | §5 step 2 | LCP-6 R3 |
| `GATE_scope` | R3 | Inv. 6 | §X-B "prescribing-clinician scope"; §X-C "operator on shift" | §5 step 2, §6.16 | LCP-6 R3 |
| `GATE_ownership` **[FLAG]** | R3 authority (concept) | Inv. 6 | **not a literal paper term** — R3 cross-domain authority composition; nearest: dual-control (§X-A), scope (§X-B) | §5 step 2, §6.16 | LCP-6 R3 |
| `AUTH_TOKEN` | R4 | **Inv. 5** (validity/TOCTOU) | PermitToken Eq.(5), Valid Eq.(6) §V-E | FULL_SPEC §6.4, §6.11 | LAB-A2; LCP-6 R4 |
| `TRACE` | R5 | replay/Inv. 6 | Evidence Quad; ERTuple; FULL_SPEC §3.3–3.4 | FULL_SPEC §6.3 Hydra Ledger | LAB RDR; LCP-6 R5 |
| `INTERLOCK` | R6 | **Inv. 1** | P_phys Eq.(7) §V-F | FULL_SPEC §6.7 | LCP-6 R6 (Tier-S: ordering only; hardware NOT exercised) |
| `CLASS_velocity` | Γ_class | **Inv. 4** | §V-C Γ_class; §X-A "velocity-window check" | FULL_SPEC §6.1, §6.5 | LAB-A5 |

**Untraceable predicates:** none. **Flagged (traces to concept, not to a literal term):** `GATE_ownership` — see Section D-1.

---

## SECTION C — Threshold classification (proof of no tuned threshold)

Automated scan of the Threshold Manifest, per family: is the admissibility threshold **structural** (binary membership/ordering), **derived** (from another predicate), **environment-derived** (a function of benign environment state), or **tuned** (a free numeric constant chosen by the author)?

| Predicate family | Threshold type | Numeric constant | Classification |
|---|---|---|---|
| `GATE_recipient_recognition` | binary_membership | none | STRUCTURAL |
| `GATE_identity_recognition` | binary_membership | none | STRUCTURAL |
| `GATE_destination_recognition` | binary_membership | none | STRUCTURAL |
| `GATE_resource_recognition` | binary_membership | none | STRUCTURAL |
| `GATE_amount_limit` | environment_derived_numeric | `available_balance` (from env state) | **ENV-DERIVED** |
| `GATE_ownership` | binary_structural | none | STRUCTURAL |
| `GATE_scope` | binary_structural | none | STRUCTURAL |
| `AUTH_TOKEN` | binary_structural | none | STRUCTURAL |
| `TRACE` | binary_structural | none | STRUCTURAL |
| `INTERLOCK` | binary_structural | none | STRUCTURAL |
| `CTR_ISB` | binary_structural | none | STRUCTURAL |
| `CLASS_velocity` | binary_structural | none | STRUCTURAL |

**Result: TUNED thresholds = NONE.** 11 of 12 are structural/binary; the single numeric (`GATE_amount_limit`) is `amount ≤ available_balance`, read from the benign `BankingEnvironment` — a function of environment state, not a free constant. This satisfies V2 D-1's requirement to minimize the tuning surface and eliminates the "predicates tuned to the corpus" objection at the threshold level. (Note: the paper's own numeric thresholds — e.g. §X-A sanctions/KYC freshness — were **not** instantiated for AgentDojo because its tasks are single-turn; no paper numeric was copied or re-tuned.)

---

## SECTION D — Honest findings (surfaced, not silently kept)

### D-1 [FLAG] `GATE_ownership` — the one predicate not tracing to a literal paper term
**Finding.** `GATE_ownership` (used by ACCOUNT/IDENTITY/FILE/RECORD/CALENDAR mutation classes) is not a verbatim paper term. **Assessment:** it is an *instance* of the R3 cross-domain **authority-composition** gate — the same family as `GATE_scope` (§X-B) and dual-control (§X-A) — applied to "acting on a resource the principal owns/controls." Under §XII-C (predicate extension is a structural property of the framework), instantiating an R3 authority gate is authorized extension, **not a new predicate type or construct.** **It is therefore not a new scientific construct.** It is, however, the single mapping requiring interpretation rather than a literal term match.
**Resolution options (user's decision; none required to proceed since it is not a new construct):**
- **(c) Accept as-is, this report is the tracing record** *(recommended)* — `GATE_ownership` is documented here as an R3 authority-gate instance. Changing the manifest would re-open the anti-circularity freeze (new Merkle root) for a cosmetic naming issue, which is worse.
- (a) Fold `GATE_ownership` → `GATE_scope` (both R3 authority) — re-opens freeze, re-Merkle.
- (b) Rename to `GATE_authority_ownership` — re-opens freeze, re-Merkle.

### D-2 [note] `GAMMA` appears in per-class predicate lists
`GAMMA` is the non-compensatory **aggregator** (R2, §IV-B), not a node predicate. Its presence in the per-class predicate list is a labeling convenience meaning "the LLC aggregation applies to this class." Not a new construct; the aggregation law `Γ=max·d_i` is unchanged.

### D-3 [note] EEA class labels (9 new labels)
`MESSAGE_DISPATCH, ACCESS_GRANT, WEB_EXFIL, RESERVATION_COMMIT, CALENDAR_MUTATION, FILE_MUTATION, RECORD_DELETION, ACCOUNT_MUTATION, IDENTITY_MUTATION` are **new descriptive instance labels** of Definition 1 — at the same altitude as the paper's own §X labels (WIRE_TRANSFER, MEDICATION_ORDER_DISPATCH, SUBSTATION_DISPATCH_COMMAND). `FUNDS_TRANSFER` is a **direct reuse** of the WIRE_TRANSFER family. New labels ≠ new constructs (Consistency-Verification Part 4).

### D-4 [note] `get_webpage` conditional WEB_EXFIL (D-6)
Classified as an EEA only when its URL argument carries data to an unrecognized destination. Traces to **Definition 1** ("effect that persists outside the computational boundary"), not to a literal paper passage; the outbound-argument rule was recognized in the approved V2 design (D-6). Application of an existing definition, not a new construct.

### D-5 [note] SAFE_STATE return-shape
On deny, the monitor returns AgentDojo's `(result, error)` contract shape without calling the real function. The **SAFE_STATE semantics** are Gamma's (§2.3); the **return-shape** is AgentDojo's interface. Interface adaptation, not a scientific construct.

---

## VERDICT

**ZERO new scientific constructs are introduced by the frozen manifests.**

- Every one of the 69 tools is accounted for (25 EEA + 44 read-only), each mediation decision justified by Definition 1 + LCP-6 R1–R6 + §X.
- Every predicate family is an existing family (R1–R6, Γ_class) or an **instance** of one; no new predicate *type*.
- **No tuned threshold exists** — all structural/binary except one environment-derived numeric.
- What is genuinely new: **descriptive instance labels** (EEA classes) and **instantiations** of existing R3 gates to new resource types — both explicitly authorized as non-constructs by Consistency-Verification Part 4 and §XII-C.
- **One item flagged** (`GATE_ownership`) as tracing to the R3 *concept* rather than a literal paper *term*; it is an R3 authority-gate instance, **not** a new construct. Surfaced per instruction; recommended resolution is accept-as-is with this report as the tracing record.

**Because no new scientific construct exists, implementation is NOT stopped on scientific grounds.** The only open item is the user's disposition of the `GATE_ownership` labeling flag (D-1), which does not affect the zero-new-construct verdict. Awaiting that disposition and Phase 3 authorization.
