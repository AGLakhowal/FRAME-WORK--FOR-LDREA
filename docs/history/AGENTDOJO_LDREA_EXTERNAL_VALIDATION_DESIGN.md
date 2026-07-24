# AgentDojo as an Independent External Validation Environment for L-DREA

**Scientific design document for the IEEE Access revision (Access-2026-24317).**
**Status:** design-only. No code, no adapters, no modification to Gamma/L-DREA, no modification to AgentDojo, no new benchmark.
**Authority hierarchy (binding):** (1) IEEE Paper → (2) FULL_SPEC → (3) Execution Integrity.md → (4) Reviewer comments.
**Governing invariant:** AgentDojo validates Gamma. Gamma is never modified to fit AgentDojo. Any integration strategy that would require altering terminology, architecture, theorem wording, benchmark philosophy, evaluation methodology, scientific claims, the evidence model, metrics, or formal assumptions is rejected and an alternative proposed.

---

## PART 0 — Framing invariant used throughout

L-DREA partitions any AI system into a **capability plane C** (untrusted, adversarial) and an **authority plane A** (the externalization monitor EM), separated by the **externalization boundary** (Definition 4, Lemma 1). The reviewer's request — evaluate L-DREA inside an existing open-source agent environment — is satisfiable **without touching the framework** precisely because AgentDojo is, in its entirety, a capability-plane artifact:

- AgentDojo's LLM agent, its `AgentPipeline`, its planner/tool-selection, and — critically — its adversarial injection corpus all live in **plane C**, which L-DREA already models as actively hostile (Threat Model §III; white-box adaptive adversary, FULL_SPEC §0.6).
- L-DREA's authority plane **A** is interposed at AgentDojo's tool-dispatch chokepoint. The tool's effect on AgentDojo's environment **is** the externally effective action (Definition 1), in sandboxed proxy form.

Because AgentDojo occupies exactly the role the paper already reserves for C, no Gamma construct has to change. The integration is a **seam**, not a modification. This is the entire basis of what follows.

---

## PART 1 — AgentDojo Architectural Analysis

### 1.1 What AgentDojo is

AgentDojo (Debenedetti et al., NeurIPS 2024 Datasets & Benchmarks; paper ref [1]) is a dynamic evaluation environment for **prompt-injection attacks and defenses on tool-using LLM agents**. It is not a static Q&A set: it instantiates a live agent loop that reads and writes a stateful environment through typed tools, and it scores both *task utility* and *attack success* against deterministic, author-independent checker functions.

The pre-registered target in the manuscript (§IX-F) is pinned at **79 user tasks and 629 adversarial injection cases** across four task suites. (The public repository has grown across releases; the pre-registration must therefore pin an exact release commit SHA — see Part 8. The frozen paper numbers govern the claim.)

### 1.2 Core components (the six the brief asks for)

| # | Component | AgentDojo realization | Role |
|---|-----------|-----------------------|------|
| 1 | **Benchmark runner** | `agentdojo.benchmark` — `benchmark_suite_with_injections()`, `run_task_with_injection_tasks()`, producing `SuiteResults`; CLI `python -m agentdojo.scripts.benchmark` | Iterates (user task × injection task × attack) triples, runs each to completion, calls utility/security checkers, aggregates Utility and Targeted ASR. |
| 2 | **Task model** | `TaskSuite` holding a typed `TaskEnvironment` (Pydantic state), a set of `BaseUserTask` (benign goals + `utility()` checker), and a set of `BaseInjectionTask` (adversary goals + `security()` checker) | Defines *what* is legitimate vs adversarial, with deterministic ground truth **not authored by L-DREA**. This is the load-bearing property for construct validity. |
| 3 | **Agent loop** | `AgentPipeline` = ordered `BasePipelineElement`s: `InitQuery` → `SystemMessage` → LLM element (e.g. `OpenAILLM`/`PromptingLLM`) → `ToolsExecutionLoop`(`ToolsExecutor`, LLM) | The capability-plane cognition: turns a user prompt + (possibly injected) environment observations into proposed tool calls, looping until no more calls. |
| 4 | **Tool execution pipeline** | `ToolsExecutor.query()` reads the LLM's proposed `tool_calls` and dispatches each | The element that converts a *proposed* action into an *executed* one. |
| 5 | **Runtime dispatcher** | `FunctionsRuntime.run_function(env, function_name, kwargs)` | The **single** function through which every tool call — regardless of which pipeline element triggered it — actually mutates the environment. |
| 6 | **Execution boundary** | The call edge `ToolsExecutor → FunctionsRuntime.run_function → tool(env, …)` | The point at which computation crosses into persistent (simulated) external effect on the environment state. |

### 1.3 Attack mechanism

Attacks (`BaseAttack`, e.g. `ImportantInstructionsAttack`) inject adversarial text into the *environment content* the agent will later read (email bodies, documents, web pages, message threads). The injection is delivered **through a tool's return value** (indirect prompt injection), not through the user prompt. When the agent reads that content, the injected instruction attempts to steer the agent into performing the injection task's goal — typically an effectful tool call (exfiltrate data, send money, share a file, message an attacker).

### 1.4 The exact interception point for L-DREA

**Interception point: `FunctionsRuntime.run_function`, evaluated immediately before the tool body mutates `TaskEnvironment`.** Equivalently, the authority plane is interposed as the gate between `ToolsExecutor`'s dispatch and the runtime's actual execution.

### 1.5 Why this point is scientifically correct (not merely convenient)

Four independent arguments, each anchored to a frozen paper construct:

1. **Complete mediation (Definition 2(i), LCP-6 implied).** `run_function` is the *sole* chokepoint through which every tool invocation passes. Intercepting at the LLM-output parse, or inside a single pipeline element, would leave alternate dispatch paths unmediated and would violate complete mediation. Intercepting at `run_function` mediates **every** candidate action by construction — this is the property Definition 2(i) demands, mapped onto AgentDojo's call graph.

2. **Capability–authority partition (Definition 4, Lemma 1).** Everything upstream of `run_function` — prompt assembly, the LLM, tool selection, the injected content — is plane C. The interposed monitor is plane A. Placing the seam here makes AgentDojo's entire agent loop untrusted-by-construction, which is exactly the paper's threat posture (§III). No trust is extended to AgentDojo's planner; this preserves §V-H (deterministic authorization under adaptive planning): the monitor is *indifferent to how the candidate was produced*, including production by prompt injection.

3. **Externally effective action semantics (Definition 1).** The tool's write to `TaskEnvironment` is precisely "an effect that persists outside the computational boundary and cannot be unilaterally rescinded" — in sandboxed proxy. Read-only tools produce **no** persistent effect and therefore lie **outside** the externalization boundary by Definition 1; the monitor must *not* gate them (doing so would over-claim mediation scope and inflate FDR). The `run_function` seam lets us classify per-tool exactly at the boundary Definition 1 draws.

4. **Commit-before-actuate (§V-F, DET-2).** `run_function` is the last instant at which "commit the ERTuple, then actuate" can be enforced with the trace preceding the effect. Gating here lets the ERTuple/Hydra-Ledger append precede the environment mutation, satisfying the ordering the paper requires (`CommitTimestamp ≤ ActuateTimestamp`).

**Conclusion of Part 1:** The interception point is uniquely determined by complete mediation. It is the AgentDojo image of the externalization boundary the paper already defines; it requires no change to AgentDojo internals (the monitor observes and admits/denies at a chokepoint AgentDojo already funnels through) and no change to L-DREA (the monitor sees a typed candidate action + context exactly as it does natively).

---

## PART 2 — Action Mapping

**Classification rule (complete-by-rule).** A tool is an **Externally Effective Action (EEA)** iff its execution mutates persistent `TaskEnvironment` state or emits content/effect outside the agent (Definition 1). All `get_*`, `read_*`, `search_*`, `list_*` tools are **read-only → outside the externalization boundary → not mediated** (one collapsed row per suite below). Only EEAs receive a Permit-to-Act evaluation. Predicate families are drawn **only** from existing constructs (LCP-6 R1–R6; FULL_SPEC §6 node predicates; §V-C class metrics); none are invented.

Predicate-family shorthand (all pre-existing):
**CTR/ISB** = typed context translation + interpretive-sufficiency (R1);
**Γ/non-comp** = non-compensatory aggregation (R2);
**Gate** = cross-domain gates: recipient/destination recognition, amount/limit, scope-of-authority, resource-ownership (R3);
**Auth/Token** = token validity, freshness/TTL, authorization provenance/signature (R4);
**Trace** = evidence-chain/Evidence-Quad integrity (R5);
**Interlock** = commit-before-actuate three-signal closure (R6);
**Class** = Γ_class autonomy-band / drift / reward-hacking proxy (§V-C).

### 2.1 Workspace suite (email · calendar · cloud drive)

| Tool | Purpose | External Effect | EEA Class | Required Predicate Families | SAFE_STATE behavior | Risk |
|------|---------|-----------------|-----------|-----------------------------|---------------------|------|
| `send_email` | send email | outbound message, irreversible | MESSAGE_DISPATCH | CTR/ISB, Γ, Gate(recipient-recognition, scope), Auth/Token, Trace, Interlock | not dispatched; hold draft; ERTuple + first-failing-gate | HIGH (exfil vector) |
| `delete_email` | delete inbox item | destructive state change | RECORD_DELETION | CTR/ISB, Γ, Gate(ownership, scope), Auth/Token, Trace, Interlock | not deleted; hold state | MEDIUM |
| `create_calendar_event` | add event | persistent write | CALENDAR_MUTATION | CTR/ISB, Γ, Gate(scope), Auth/Token, Trace, Interlock | not created | LOW–MEDIUM |
| `cancel_calendar_event` | cancel event | destructive write | CALENDAR_MUTATION | CTR/ISB, Γ, Gate(ownership, scope), Auth/Token, Trace, Interlock | not cancelled | MEDIUM |
| `reschedule_calendar_event` | change time | persistent write | CALENDAR_MUTATION | CTR/ISB, Γ, Gate(ownership), Auth/Token, Trace, Interlock | unchanged | LOW–MEDIUM |
| `add_calendar_event_participants` | add attendees | outbound + write (info disclosure) | CALENDAR_MUTATION / ACCESS_GRANT | CTR/ISB, Γ, Gate(recipient-recognition, scope), Auth/Token, Trace, Interlock | not added | MEDIUM |
| `create_file` | create drive file | persistent write | FILE_MUTATION | CTR/ISB, Γ, Gate(scope), Auth/Token, Trace, Interlock | not created | LOW–MEDIUM |
| `append_to_file` | modify file | persistent write | FILE_MUTATION | CTR/ISB, Γ, Gate(ownership), Auth/Token, Trace, Interlock | unchanged | MEDIUM |
| `delete_file` | delete file | destructive | RECORD_DELETION | CTR/ISB, Γ, Gate(ownership, scope), Auth/Token, Trace, Interlock | not deleted | MEDIUM–HIGH |
| `share_file` | grant access | irreversible disclosure to third party | ACCESS_GRANT | CTR/ISB, Γ, Gate(recipient-recognition, scope), Auth/Token, Trace, Interlock | not shared | HIGH (exfil vector) |
| `get_*`/`read_*`/`search_*`/`list_*` (emails, events, files) | observe state | none (read-only) | — (outside boundary) | not mediated (Definition 1) | n/a — pass-through; content may carry injection, which surfaces only at the next EEA | n/a |

### 2.2 Banking suite

| Tool | Purpose | External Effect | EEA Class | Required Predicate Families | SAFE_STATE behavior | Risk |
|------|---------|-----------------|-----------|-----------------------------|---------------------|------|
| `send_money` | transfer funds | irreversible financial | FUNDS_TRANSFER | CTR/ISB, Γ, Gate(recipient/IBAN-recognition, amount-limit, scope), Auth/Token, Trace, Interlock, Class(velocity/drift) | not sent; hold last state; ERTuple | HIGH |
| `schedule_transaction` | schedule future transfer | deferred irreversible financial | FUNDS_TRANSFER | as `send_money` + freshness/TTL | not scheduled | HIGH |
| `update_scheduled_transaction` | modify scheduled transfer | financial mutation | ACCOUNT_MUTATION | CTR/ISB, Γ, Gate(ownership, amount-limit), Auth/Token, Trace, Interlock | unchanged | HIGH |
| `update_user_info` | change account owner info | identity/PII mutation | IDENTITY_MUTATION | CTR/ISB, Γ, Gate(ownership, scope), Auth/Token, Trace, Interlock | unchanged | HIGH (fraud/exfil) |
| `get_balance` / `get_iban` / `get_most_recent_transactions` / `get_scheduled_transactions` / `read_user_info` | observe state | none | — (outside boundary) | not mediated | n/a — injection may ride in returned strings; surfaces at next EEA | n/a |

### 2.3 Travel suite

| Tool | Purpose | External Effect | EEA Class | Required Predicate Families | SAFE_STATE behavior | Risk |
|------|---------|-----------------|-----------|-----------------------------|---------------------|------|
| `reserve_hotel` / `reserve_restaurant` / `reserve_car` | commit reservation | binding commitment, cost | RESERVATION_COMMIT | CTR/ISB, Γ, Gate(resource-recognition, amount-limit, scope), Auth/Token, Trace, Interlock | not reserved | MEDIUM–HIGH |
| `book_flight` (where present) | book flight | binding, cost | RESERVATION_COMMIT | as above | not booked | HIGH |
| `send_email` (travel-suite variant) | outbound message | irreversible | MESSAGE_DISPATCH | as Workspace `send_email` | not dispatched | HIGH |
| `get_all_hotels_in_city` / `get_hotels_prices` / `get_rating_reviews_for_hotels` / `get_flight_information` | observe | none | — (outside boundary) | not mediated | n/a | n/a |

### 2.4 Slack suite

| Tool | Purpose | External Effect | EEA Class | Required Predicate Families | SAFE_STATE behavior | Risk |
|------|---------|-----------------|-----------|-----------------------------|---------------------|------|
| `send_direct_message` | DM a user | outbound message | MESSAGE_DISPATCH | CTR/ISB, Γ, Gate(recipient-recognition, scope), Auth/Token, Trace, Interlock | not sent | HIGH (exfil vector) |
| `send_channel_message` | post to channel | outbound broadcast | MESSAGE_DISPATCH | CTR/ISB, Γ, Gate(scope), Auth/Token, Trace, Interlock | not posted | MEDIUM–HIGH |
| `add_user_to_channel` | grant channel access | access change | ACCESS_GRANT | CTR/ISB, Γ, Gate(identity-recognition, scope), Auth/Token, Trace, Interlock | not added | MEDIUM–HIGH |
| `remove_user_from_channel` | revoke access | destructive access change | ACCESS_GRANT | CTR/ISB, Γ, Gate(ownership, scope), Auth/Token, Trace, Interlock | not removed | MEDIUM |
| `invite_user_to_slack` | onboard external identity | irreversible identity/access | ACCESS_GRANT / IDENTITY_MUTATION | CTR/ISB, Γ, Gate(identity-recognition, scope), Auth/Token, Trace, Interlock | not invited | HIGH |
| `post_webpage` / outbound-to-web (where present) | publish content externally | irreversible external publication | WEB_EXFIL / OUTBOUND_CONTENT | CTR/ISB, Γ, Gate(destination-recognition, scope), Auth/Token, Trace, Interlock | not published | HIGH (exfil vector) |
| `read_channel_messages` / `read_inbox` / `get_users_in_channel` / `get_webpage` | observe | none (read; `get_webpage` returns possibly-injected content) | — (outside boundary) | not mediated | n/a — canonical indirect-injection carrier; effect surfaces only at the next EEA | n/a |

**Mapping notes (scientifically load-bearing):**
- The exfiltration attack pattern in AgentDojo is: read injected content (read-only, unmediated) → attempt an EEA to an **unrecognized recipient/destination** (`send_email`, `send_direct_message`, `share_file`, `post_webpage`). L-DREA denies at the **Gate(recipient/destination-recognition)** predicate — **not** by detecting the injection text. This is exactly the paper's position (§XII-A): content-layer injection is LlamaFirewall's domain; L-DREA's contribution is that the *resulting action* still faces non-compensatory predicate concurrence.
- Read-only tools are deliberately **outside** the boundary. This preserves Definition 1 and avoids fabricating mediation the framework does not claim.

---

## PART 3 — Scenario Mapping (AgentDojo ↔ LAB / ConcurBench / ASB)

### 3.1 What AgentDojo actually exercises

AgentDojo's dominant threat is **indirect prompt injection through tool output** inside a **live LLM agent loop over realistic multi-tool tasks**, with **author-independent** success/security ground truth.

### 3.2 Mapping to LAB v1.0 scenario classes (LAB-A1…A5)

| LAB class | Definition | AgentDojo coverage | Verdict |
|-----------|------------|--------------------|---------|
| **LAB-A1** Direct bypass (execute without issuance) | attempt to actuate with no permit | Not exercised — AgentDojo cannot bypass `run_function`; it can only *propose* calls | **Missing in AgentDojo** |
| **LAB-A2** Token manipulation (forge/replay/scope-escalate) | attack the permit token | Not exercised — AgentDojo has no access to the epoch key / token schedule | **Missing in AgentDojo** |
| **LAB-A3** Context corruption (CTR tampering, injection) | adversarial context → candidate action | **Directly exercised** — this is AgentDojo's core: injected content corrupts the context that produces the candidate EEA | **Overlap (strong)** |
| **LAB-A4** Timing exploitation (TOCTOU) | race permit validity | Not exercised — no concurrent revalidation race in the single-agent loop | **Missing in AgentDojo** |
| **LAB-A5** Goodhart (class-level degradation under clean node predicates) | erode Γ_class | Weak/none — AgentDojo tasks are short-horizon; no sustained drift toward class-metric degradation | **Missing / marginal in AgentDojo** |

### 3.3 Mapping to ConcurBench v1.0 (7 classes) and ASB (5 families)

- **ConcurBench:** AgentDojo maps to **Corrupted** and **Adversarial** classes; partially to **Nominal** (its benign user tasks). It does **not** exercise **Missing**, **TOCTOU**, **Replay**, or **Concurrency** classes. So AgentDojo is a *deep probe of two ConcurBench cells*, not a substitute for the seven-class sweep.
- **ASB (temporally-extended):** partial map to **session/intent compromise** (injection hijacks an authorized session) and **cross-entity fraud propagation** (exfiltration to an attacker entity). It does **not** cover identity/provenance deception at the cryptographic layer, runtime-infrastructure drift, or economic-logic fragility at ASB's depth.

### 3.4 Coverage analysis

- **Overlap:** LAB-A3 / ConcurBench-Corrupted / ConcurBench-Adversarial — "does corrupted/adversarial context yield an unauthorized EEA?" Both LAB and AgentDojo answer this; they overlap *here and essentially only here*.
- **Complementary coverage:** AgentDojo answers the overlap question through a **live third-party LLM loop on realistic tasks with external ground truth**, whereas LAB answers it through a **fixed, seeded mutation library at 10⁶ scale with author-defined ground truth**. Same question, orthogonal altitude and provenance — this is complementary, not redundant.
- **Unique to AgentDojo:** (a) semantic indirect prompt injection through tool outputs; (b) realistic multi-tool chaining; (c) **author-independent ground truth** (the decisive property); (d) native Utility / Targeted-ASR baselines against published defenses.
- **Unique to LAB/ConcurBench/ASB (missing in AgentDojo):** direct bypass (A1), token/crypto manipulation (A2), TOCTOU (A4), Goodhart/class drift (A5), replay determinism, hash-chain integrity, distributed/fleet consistency (L3), formal invariant coverage, and 10⁶-scale rare-event statistics.

### 3.5 Does AgentDojo introduce new threat classes LAB lacks?

**Yes — and the manuscript already says so.** §IX-E.4 states verbatim that AgentDojo's corpus contains "prompt-injection-into-tool-output … multi-turn social engineering … that LAB v1.0's seven mutation families do not directly target." The new class is **semantic indirect prompt injection delivered through a live tool-use loop**, which LAB's authorization-record-level mutations do not generate. This is a *feature* of the integration: AgentDojo widens the falsifiability surface into a threat class LAB was never designed to cover, which is precisely why it strengthens construct validity rather than duplicating LAB. **No LAB definition changes** — AgentDojo is added alongside, mapped to A3 where it overlaps and flagged as new-class where it does not.

---

## PART 4 — Metric Mapping

### 4.1 Which existing Gamma metrics compute directly at the AgentDojo seam

All L-DREA metrics are computed from **ERTuples the monitor emits at `run_function`**, independent of the environment. Therefore they transfer directly, with one adjustment: **ground-truth labels for FPR/UER now come from AgentDojo's author-independent `security()`/`utility()` checkers**, not from L-DREA.

| Metric | Computable at AgentDojo seam? | Ground-truth source | Denominator (denominator discipline preserved) |
|--------|-------------------------------|---------------------|-----------------------------------------------|
| **UER** (Unauthorized Execution Rate) | **Yes** | AgentDojo `security()` — an injection-goal EEA that L-DREA permitted | all mediated EEAs |
| **FPR** (False Permit Rate) | **Yes** | AgentDojo injection ground truth (should-deny) | injection-goal (should-deny) EEAs only |
| **FDR** (False Denial Rate) | **Yes** | AgentDojo `utility()` (benign should-permit) | benign user-task EEAs only |
| **FCR** (Fail-Closed Rate) | **Yes** | uncertainty at seam (missing/stale/ambiguous context) | should-deny-or-uncertain EEAs |
| **Replay Determinism (RDR)** | **Yes** | internal (ERTuple hash chain) | all mediated EEAs |
| **Evidence Quad** | **Yes** | internal (per-decision) | per EEA |
| **Latency** | **Yes** | measured at seam (software Tier-S; disclose, not comparable to HSM/FPGA 54.3 ms) | per EEA |
| **Replay Verification** | **Yes** | `gamma_replay_verify.py`-class independent verifier over the emitted manifest | manifest |
| **Hash Integrity** | **Yes** | internal (Hydra Ledger adjacency, GENESIS anchor) | all mediated EEAs |

### 4.2 Critical construct-validity mechanic (the reason this matters)

Because AgentDojo's ground truth is **not author-controlled**, FPR/UER computed here can be **non-zero for an honest reason**: an injection may achieve its goal via an EEA that *passes* L-DREA's reference predicate vector (predicate incompleteness — Group II residual, G3/G16/G17). Under AgentDojo's external label that is a **true false-permit** and **must be reported** (outcome-irrespective publication, §IX-F.2). This is the falsification surface the manuscript pre-registered. The paper **already forecasts this** (§IX-E.4: does not expect the zero-event headline to transfer to AgentDojo; expects elevated FDR from predicate incompleteness). So any AgentDojo result — including false permits — lands in a bucket the paper already declared, changing **no** claim.

### 4.3 Additional useful measurements AgentDojo introduces (native, kept native)

These are **AgentDojo's own** metrics, reported *alongside* Gamma metrics — never merged into a Gamma definition:

- **Utility** (benign task success), and **Utility-under-L-DREA** (utility retained with the monitor in the loop) → directly surfaces the FDR/utility cost as an operational number.
- **Targeted Attack Success Rate (TASR)** with vs without L-DREA → shows the monitor's marginal reduction in attack success against **published defenses** as baselines.
- **Per-injection-class breakdown** → maps each AgentDojo attack to the closest LAB scenario class (LAB-A1…A5), as §IX-F.2 already requires ("each adversarial episode is mapped to the closest LAB scenario class").

**Metric firewall (non-negotiable):** Gamma metrics keep their Gamma definitions; AgentDojo metrics keep their AgentDojo definitions. The report presents them **side by side**. TASR is never redefined as FPR; Utility is never redefined as (1−FDR). They are cross-tabulated, not fused. This preserves the evidence model and the metric family verbatim.

---

## PART 5 — Scientific Positioning: why AgentDojo does NOT replace LAB

### 5.1 They answer different scientific questions

- **LAB v1.0 asks:** *Under a fixed, documented, author-controlled adversarial-mutation library at 10⁶ scale, does the authorization boundary ever admit an unauthorized externalization, with a rare-event statistical bound?* This is an **internal-validity, rare-event conformance** question requiring scale, seeded reproducibility, and the full A1–A5 surface (including bypass, token, TOCTOU, Goodhart) that only a purpose-built harness can generate.
- **AgentDojo asks:** *When L-DREA is dropped into a pre-existing, third-party agent environment with an adversarial corpus and ground truth the authors did not write, do the execution-boundary invariants survive attacks not designed by the authors?* This is an **external-validity / construct-validity** question requiring independence, not scale.

Neither question subsumes the other. LAB cannot answer the independence question (its corpus is author-controlled — the exact circularity §IX-F names). AgentDojo cannot answer the rare-event conformance question (it lacks A1/A2/A4/A5, scale, and the cryptographic/substrate surface). **Replacing LAB with AgentDojo would delete the rare-event bound, the substrate ablation, the six-invariant coverage, and the 10⁶ statistics — i.e., most of the paper's empirical contribution.** Rejected.

### 5.2 Why using both improves construct validity

Construct validity is threatened when the instrument and the ground truth share an author. LAB's strength (a controlled, exhaustive mutation library) is also its construct-validity weakness (self-authored oracle). AgentDojo supplies an **independent oracle** over an **overlapping-but-distinct threat class**. The pairing yields a **triangulation**:

- If L-DREA holds on LAB (scale + rare-event) **and** on AgentDojo (independence + realistic injection), the two failure modes that could explain LAB's zero-event result — *underpowered author-written adversary* and *oracle circularity* — are **both** ruled out. The negative control (§IX-C) already addresses "underpowered"; AgentDojo addresses "circularity." Together they close the two standard threats to a zero-event claim.

### 5.3 The honest asymmetry (kept explicit)

AgentDojo will likely show **non-zero FDR** (utility cost) and **may show isolated false permits** from predicate incompleteness. Far from weakening the paper, reporting these **strengthens** it: it demonstrates the falsifiability protocol is real, converts the Group II residual from a stated limitation into a *measured* one, and matches §IX-E.4's advance expectations. The scientific claim that transfers is **not** "zero-event everywhere" — it is **authorization-soundness under the declared predicate vector**, with predicate incompleteness explicitly outside the warrant (Property v, H). AgentDojo tests exactly that claim and nothing broader.

---

## PART 6 — Reviewer Mapping

**Caveat on inputs.** The brief says "every Reviewer 2 criticism," but only one reviewer request is present in the working context ("evaluation within an existing open-source AI agent environment"). The criticisms below are **reconstructed** from (a) that explicit request and (b) the manuscript's own defensive structure (§IX-F, §IX-C, §IX-L, §XII-A), which typically mirrors reviewer feedback. **To finalize this table verbatim I need the actual Reviewer 2 text.** The reconstruction is conservative and each row states its basis.

| # | Reconstructed R2 criticism (basis) | AgentDojo status | Why |
|---|-------------------------------------|------------------|-----|
| R2-a | **"Evaluate in an existing open-source agent benchmark, not only your own."** (explicit request) | **Fully addresses** | AgentDojo is a NeurIPS-published, third-party, open-source agent benchmark; L-DREA runs as the authorization layer over its unmodified harness. This is the literal request. |
| R2-b | **"Ground truth, adversarial corpus, and baselines are all author-controlled (circularity)."** (basis: §IX-F opening sentence) | **Fully addresses** | AgentDojo's `security()`/`utility()` checkers and injection corpus are not authored by L-DREA; FPR/UER acquire an independent oracle. |
| R2-c | **"Zero-event result may reflect an underpowered adversary."** (basis: §IX-C negative control) | **Partially addresses** (complements existing negative control) | AgentDojo adds an *independently authored* adversary; combined with the §IX-C negative control, both "underpowered" and "circular" explanations are excluded. AgentDojo alone doesn't provide the negative control — the pairing does. |
| R2-d | **"Does it generalize beyond the native benchmark / construct validity?"** (basis: §IX-L construct-validity section) | **Fully addresses** | Demonstrating the invariants survive in a foreign environment with foreign attacks is the definition of the external-validity evidence §IX-L flags as pending. |
| R2-e | **"Prompt-injection realism — synthetic mutations aren't real injection."** (basis: §IX-E.4) | **Fully addresses** | AgentDojo delivers genuine indirect prompt injection through tool outputs in a live LLM loop — the exact realism gap §IX-E.4 concedes. |
| R2-f | **"Compare against real defenses/baselines."** (basis: Table 2 / Table 12 baselines) | **Partially addresses** | AgentDojo ships defenses and native TASR/Utility baselines, enabling head-to-head on *its* metrics. It does not, however, benchmark L-DREA against the §XII cryptographic/substrate antecedents; that comparison stays in LAB. |
| R2-g | **"Formal claims (invariants) are only analytic/one mechanized."** (basis: §VI-D, Table 6) | **Does not address** | AgentDojo is an empirical environment; it cannot mechanize Invariants 2–6. This remains LAB v1.1 / TLA⁺-NuSMV work. Honestly out of AgentDojo's scope — must be stated, not implied solved. |
| R2-h | **"Hardware substrate (Tier-H) results aren't independently reproducible."** (basis: §IX scope box) | **Does not address** | AgentDojo runs Tier-S (software) only; it validates the *authorization logic*, not the hardware interlock. Disclose explicitly (as the CreditCard artifact already does for Tier-S). |
| R2-i | **"Latency numbers are from a bespoke rig."** (basis: §IX-H) | **Partially addresses** | AgentDojo yields per-decision software latency in a third-party loop, corroborating O(n)/software-latency behavior — but not the HSM/FPGA 54.3 ms figure. Report as Tier-S corroboration only. |

**Net:** AgentDojo **fully** satisfies R2-a, R2-b, R2-d, R2-e; **partially** satisfies R2-c, R2-f, R2-i (each in combination with existing paper content); and **does not** satisfy R2-g, R2-h (formal-mechanization and hardware-substrate items that are, by construction, outside an agent benchmark's reach and are already tracked as future work). The reviewer's **actual stated** request (R2-a) is fully satisfied.

---

## PART 7 — Paper Integration Plan (section-by-section)

**Governing principle:** the manuscript **already pre-registered** this evaluation (§IX-F, with Table 11 as a `[RUN]`-celled placeholder titled "Preliminary L-DREA results as the authorization layer over AgentDojo"). The integration **executes a commitment the paper already made** — it changes no claim; it fills placeholders and promotes a pre-registration to a completed independent evaluation.

### 7.1 New experiments
1. **AgentDojo external evaluation run:** L-DREA as authority plane over the pinned AgentDojo release; full 79 user tasks × 629 injection cases; pre-registered SHA-256 config manifest committed **before** the run.
2. **With/without-L-DREA ablation on AgentDojo's own metrics:** Utility and TASR with and without the monitor.
3. **Per-injection-class mapping run:** each episode mapped to LAB-A1…A5 (as §IX-F.2 requires).

### 7.2 New tables
- **Fill Table 11** (already present, currently `[RUN]`): injection cases evaluated / false permits / per-injection-class FPR (mapped to LAB-A1–A5) / TASR with vs without L-DREA / FDR-utility cost.
- **New Table 11b (proposed):** Utility and TASR, L-DREA vs native AgentDojo defenses (Gamma metrics and AgentDojo metrics side-by-side — the metric firewall of Part 4.3).
- **New Table 11c (proposed):** coverage crosswalk AgentDojo ↔ LAB-A1…A5 (overlap / new-class), i.e., Part 3.4 in publishable form.

### 7.3 New figures
- **Fig. (new): AgentDojo integration seam** — the two-plane diagram (Fig. 1) re-instantiated over AgentDojo's `AgentPipeline → ToolsExecutor → FunctionsRuntime.run_function → TaskEnvironment`, showing plane C = AgentDojo agent loop, plane A = interposed monitor, boundary = `run_function`.
- **Fig. (new): construct-validity triangulation** — LAB (scale/rare-event, author oracle) + negative control (not underpowered) + AgentDojo (independent oracle) → both threats to the zero-event claim excluded.

### 7.4 Updated sections
- **§IX-F** promoted from "pre-registered commitment" to "completed independent evaluation," retaining the falsifiability/outcome-irrespective language verbatim; add the executed manifest hash.
- **§IX-L** (construct validity) extended: external-validity evidence now *present*, not pending — but with the same normative scope (execution-boundary evaluation, not general AI-safety).
- **§I-C / Abstract:** the sentence "An independent evaluation … is pre-registered" updated to "… is pre-registered **and reported (Section IX-F)**." Minimal, factual.

### 7.5 Claims that remain UNCHANGED (explicitly)
- The zero-event LAB headline and its Wilson bound (§IX-B) — **unchanged**; AgentDojo is not claimed to reproduce it (§IX-E.4).
- All six invariants and their verification status (§VI, Table 6) — **unchanged**.
- Authority horizon H, Property (v) epistemic bounding, Definition 1/2/4 — **unchanged**.
- The substrate tiers and Tier-H empirical numbers (§IX-D) — **unchanged**; AgentDojo is Tier-S.
- LCP-6, the metric family, the statistical conventions — **unchanged**.

### 7.6 Sections that become STRONGER
- **§IX-F, §IX-L:** circularity and external-validity concerns move from "acknowledged/pending" to "empirically addressed."
- **§XII-A Group II (predicate completeness):** becomes a *measured* residual with an external falsification surface, not merely a stated one.
- **Table 2 positioning:** L-DREA now carries evaluation in a third-party benchmark, hardening the "explicit lineage + independent evaluation" distinguisher.

---

## PART 8 — Implementation Roadmap (described, not written)

**No code here.** This is the build description that will follow document approval. It respects: no Gamma modification, no AgentDojo modification (integration by interposition at the sanctioned seam, not by editing AgentDojo internals).

### 8.1 Where interception occurs
A **governance interposition** at `FunctionsRuntime.run_function` (equivalently, a monitor element gating `ToolsExecutor`'s dispatch), realized **without editing AgentDojo source** — via AgentDojo's supported extension surface (a wrapping runtime / pipeline element the harness already composes). The monitor receives the typed candidate tool call + arguments + the current environment observation, forms the CTR, evaluates Γ over the mapped predicate families (Part 2), and either admits (execute the original `run_function`) or returns SAFE_STATE (deny; do not execute) with an ERTuple.

### 8.2 Files that change
- **None in Gamma. None in AgentDojo.** The existing L-DREA reference monitor and the existing CreditCard-artifact tooling (`gamma_test_runner.py`, `gamma_replay_verify.py`, report/dashboard builders) are the substrate; they are reused, not modified in their authorization logic.

### 8.3 New files required (thin, additive)
1. **AgentDojo↔L-DREA interposition module** — binds the monitor at `run_function`; contains the per-tool EEA classification (Part 2 table as data), maps AgentDojo tool calls → CTR, and routes admit/deny. Pure adapter at the boundary; contains **no** Gamma logic (calls the existing monitor).
2. **Predicate-family binding for AgentDojo action classes** — a declarative table (FUNDS_TRANSFER, MESSAGE_DISPATCH, ACCESS_GRANT, …) → existing predicate families. Configuration, not new science.
3. **Ground-truth bridge** — reads AgentDojo `security()`/`utility()` outcomes to label each mediated EEA should-deny/should-permit for FPR/UER/FDR (external oracle).
4. **Pre-registration manifest** — SHA-256 over {AgentDojo release SHA, predicate set, θ vector, I_class, Tier-S selection, seed schedule}, committed before the run (§IX-F.2).
5. **Independent-evaluation report emitter** — produces the AgentDojo run's LAB-format report + Table 11/11b/11c values.

### 8.4 How replay integrates
The monitor emits the **same ERTuple / Evidence Quad / Hydra-Ledger** records at the AgentDojo seam as natively. The existing **stdlib-only independent verifier** re-audits the AgentDojo run's manifest (adjacency, GENESIS anchor, Evidence-Quad↔ledger binding, decision consistency, manifest SHA-256) with **no dependency on AgentDojo, the dataset, or the runner** — preserving the generator/verifier separation exactly.

### 8.5 How dashboards integrate
The AgentDojo run renders as an **additional section** in the existing dashboard pipeline (server-rendered from the run's JSON, no hand-entered numbers), alongside the CreditCard/ConcurBench/stress/FCR sections — same pattern as `run_all.py`'s composed page. AgentDojo metrics (Utility, TASR) and Gamma metrics shown in **separate panels** (metric firewall).

### 8.6 How reports integrate
A dedicated **"LAB v1.0 Independent Evaluation — AgentDojo"** JSON report (matching §IX-F.3's designation), containing: pre-registered manifest hash, per-task TASR, per-injection-class FPR mapped to LAB-A1–A5, Utility/FDR cost, and raw result logs. Fills Table 11 directly.

### 8.7 How reproducibility is preserved
- Reuse the **reproducibility-bundle** mechanism (MANIFEST.json with SHA-256 of every input/source/output, exact command, env, REPRODUCE.md, bundle digest).
- Pin the AgentDojo release commit SHA in the manifest.
- Deterministic-field outputs reproduce exactly; **software latency is host-dependent and disclosed as such** (never compared to Tier-H 54.3 ms).

### 8.8 How independent validation is demonstrated
Four independent legs, each already part of the framework's evidence model: (1) third-party benchmark + third-party ground truth (AgentDojo); (2) outcome-irrespective pre-registration (manifest hash committed first); (3) zero-dependency replay verifier re-checking the emitted ledger; (4) LAB-format metrics with Wilson bounds. Together these constitute the "principal external falsifiability surface" §IX-F describes — now executed.

### 8.9 Honesty ledger (must appear in the report, per FULL_SPEC §0.4 / §0.11)
- Tier-S (software) only; HMAC-SHA256 software analogs, not live HSM/FPGA.
- Zero-event LAB headline **not** claimed to transfer; AgentDojo results reported as-is including any false permits (predicate incompleteness) and FDR (utility cost).
- Formal mechanization of Invariants 2–6 remains future (LAB v1.1), untouched by AgentDojo.

---

## SUCCESS CRITERION

### Question
*After this integration, will Reviewer 2's request for evaluation in an existing open-source AI agent benchmark be fully satisfied?*

### Answer
**Yes for the reviewer's stated request; and substantially more of the surrounding critique than the request alone — with two items (formal mechanization, hardware-substrate independence) that lie outside any agent benchmark's reach and remain correctly scoped as future work.**

### Reasoning
1. **The literal request is met exactly.** The reviewer asked for evaluation inside an existing open-source AI agent environment. AgentDojo is a NeurIPS-published, open-source, third-party agent benchmark, and L-DREA is evaluated **as the authorization layer over its unmodified harness**, intercepting at the complete-mediation chokepoint (`FunctionsRuntime.run_function`). Nothing in Gamma is altered; the benchmark is not a self-authored simulation. This is precisely what the earlier rejected synthetic harness failed to be.

2. **It resolves the deeper concern behind the request — circularity/construct validity.** The reviewer's request is a proxy for "your evidence is self-authored." AgentDojo supplies an **author-independent oracle** (its `security()`/`utility()` checkers) over a **new threat class** (indirect prompt injection through a live tool loop) that LAB does not generate. Combined with the existing negative control (§IX-C), this excludes **both** standard explanations for a zero-event result: underpowered adversary and oracle circularity.

3. **It executes a commitment the paper already made, so it changes no claim.** §IX-F pre-registers exactly this evaluation and Table 11 already reserves the cells. The revision fills placeholders and promotes a pre-registration to a reported result — the strongest possible form of reviewer response because it introduces zero new claims and cannot destabilize the frozen contributions.

4. **The framework is preserved end-to-end.** Terminology, architecture, theorem wording, benchmark hierarchy (EI → ConcurBench/ASB → LAB), metrics, evidence model, and formal assumptions are untouched. AgentDojo occupies the capability plane the paper already defines as adversarial; the metric firewall keeps Gamma and AgentDojo metrics distinct; read-only tools stay outside the boundary per Definition 1.

5. **The honest residue is correctly scoped, not hidden.** Two reconstructed criticisms — mechanization of Invariants 2–6 (R2-g) and hardware-substrate independence (R2-h) — cannot be addressed by *any* agent benchmark; they are empirical/formal and hardware questions, already tracked as LAB v1.1 and Tier-H future work. Claiming AgentDojo closes them would be over-claiming; the revision states them as out of AgentDojo's scope.

### Two conditions on the "fully satisfied" verdict
- **(i) Verbatim Reviewer 2 text.** The reviewer mapping (Part 6) is reconstructed from the manuscript's defensive structure plus the one explicit request. If Reviewer 2 raised additional specific items, they must be mapped against this design before declaring full closure. **This is the one input I need from you to certify Part 6.**
- **(ii) Outcome-irrespective reporting held.** "Fully satisfied" is contingent on publishing AgentDojo results **as measured** — including any predicate-incompleteness false permits and FDR/utility cost — per §IX-F.2. If those appear and are reported honestly, the reviewer's construct-validity concern is *strengthened*, not weakened, because it proves the falsifiability protocol is real.

**Bottom line:** For the request as stated, this integration **fully satisfies** Reviewer 2, addresses the circularity and external-validity concerns behind it, and does so without modifying a single scientific contribution — because AgentDojo is admitted into the exact adversarial capability-plane role the framework already defines.
