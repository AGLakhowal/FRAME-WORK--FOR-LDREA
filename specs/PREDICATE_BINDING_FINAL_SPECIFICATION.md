# RUNTIME PREDICATE BINDING — FINAL SPECIFICATION (classification refinement)

**A scientific specification refinement only. No code, no repository modification, no invented thresholds/proxies/features/algorithms, no dataset fitting, no `Class`-dependent behaviour, no optimisation.** This document refines `PREDICATE_BINDING_SCIENTIFIC_SPECIFICATION.md` by classifying each remaining unresolved item as an **architectural invariant**, **scientific methodology**, or **deployment policy**, to determine whether any *new science* actually remains.

**Roles:** Principal Runtime-Governance Researcher · IEEE Methodology Reviewer · Formal-Systems Architect · Scientific-Specification Editor.

---

## 1. The classification test (explicit)

| Class | Definition | Test |
|---|---|---|
| **Architecture** | A frozen invariant fixed by the L-DREA architecture / FULL_SPEC / paper. Not a choice. | Does a frozen spec fix it with no free parameter? |
| **Science** | A methodology decision that determines a universal truth of the pipeline and, if unspecified, would require *inventing* a method. | Would proceeding require a new threshold/proxy/feature/algorithm/fit? |
| **Policy** | A deployment-specific parameter/binding an operator declares; varies by deployment; realized through an **existing** frozen mechanism; not fit to data, not `Class`-dependent. | Is it an operator input the corpus already externalises (ExecutionBinding / frozen policy)? |

**Key principle (from the corpus).** The paper treats the node-predicate vector `G` as a **"generic policy-bound"** vector; the *predicate definitions* and *aggregation* are science (frozen), while *which evidence each gate binds to* and *what limits apply* are **policy** (RCL §2; traceability Part 2). The science says *how* evidence becomes a decision; policy says *what* limits/bindings a given deployment uses.

---

## 2. Review — Gap 3 (Full-vector fail-closed vs Slice evaluation)

**Does the corpus define this as architecture, policy, or unresolved science?**

**Conclusion: it is ARCHITECTURE (posture + frozen fail-closed) realised by DEPLOYMENT POLICY (the gate-binding manifest). It is NOT unresolved science.** The apparent tension in the prior spec was a level confusion, now resolved by three citations:

1. **The bound set is deployment policy.** RCL §2: *"the binding of a specific gate index to a specific evidence plane is a **deployment policy** already externalised (the AgentDojo `ExecutionBinding`, Layer 2). The RCL therefore does **not** fix a gate's plane; it exposes whatever plane the binding names."* Traceability Part 2: the `ExecutionBinding` manifest loader is *"reused for gate→plane bindings if the credit-card arm adopts manifest-driven bindings."* §10.3: *"(Owner: **policy/binding**.)"*
2. **The evaluation posture is architecture.** RUNTIME_EVIDENCE_ARCH §6: *"evaluate each arm on the **slice its evidence supports** — the credit-card arm on the A/(B/D-proxy) slice"*; the C/B predicates are exercised on the arms that produce them.
3. **The fail-closed of a bound-but-absent gate is frozen.** EEB §4/§6: *"if service unavailable → ABSENT (§6); engine **fail-closes**"* — the frozen non-default-permit policy (FULL_SPEC 2.3/0.10).

These are **complementary, not contradictory**: (2) fixes *which slice* the arm reports (architecture), (1) *realises* that slice as a deployment ExecutionBinding manifest (policy), and (3) governs any bound-but-absent gate (frozen). "Full-vector all-deny" is simply the degenerate case of an ExecutionBinding that binds gates whose plane is unfilled — a *policy* choice, not a scientific one. **No new science; no architectural ambiguity.**

## 3. Review — Gap 4 (HARM proxy · θ · L_amt) — each treated INDEPENDENTLY

**(4a) HARM proxy admissibility.** Architecture §2.3: `HARM_RISK` is a governance-service **output** (plane D); a `V1..V28` proxy is *"defensible **only** as an explicitly-labelled proxy, never as the architecture's intended source."* §5: the credit-card arm has **no** risk service → HARM **absent**. Therefore the **architecturally-correct binding rejects the proxy** → HARM absent → frozen fail-closed. *Admitting* a proxy would require **inventing a hazard model** (feature engineering) — new science, and **forbidden here / not required to proceed**. → **Architecture (default reject); the admit path is optional out-of-scope Science we do not take.**

**(4b) θ (HARM threshold).** Traceability Part 2: the frozen `Policy Loader` *"source[s] **θ**/limits."* It is already an externalised engine parameter (`args.harm_threshold`, default 0.5). It is a value in the policy plane, and is **moot** in the credit-card arm (HARM absent under 4a). → **Deployment policy parameter.**

**(4c) `L_amt` (amount limit).** Traceability §10.4: *"**risk-budget SLA, not fit to `Class`**"*; Part 2: limits are sourced from the frozen Policy Loader. An SLA is an operator business input that varies by deployment (bank X vs bank Y), not a universal truth. Deriving/fitting one is forbidden; declaring one is policy. → **Deployment policy parameter.**

**Independent verdict:** only **4a** is science-flavoured, and its *architectural default (reject)* needs no invention; **4b** and **4c** are deployment policy parameters sourced from the existing frozen policy plane. **No new science is required to proceed.**

---

## 4. Per-item classification (OUTPUT MODEL)

### Item — Gate→plane binding *(Gap 3a)*
- **Current status:** previously "irreducible"; now recognised as deployment policy.
- **Can it be derived? NO** (a deployment choice) — but it is **defined** as policy with an existing mechanism, not missing science.
- **Classification: POLICY.**
- **Reasoning:** RCL §2 ("deployment policy already externalised, ExecutionBinding Layer 2"); traceability Part 2 (ExecutionBinding reused for gate→plane bindings); §10.3 ("Owner: policy/binding").
- **Impact on Gamma:** none (Γ = max dᵢ over the named vector; binding selects the evidence source, not aggregation).
- **Impact on Replay:** none (binding fixed per deployment; deterministic).
- **Impact on Predicate Semantics:** none (paper's `G` is "generic policy-bound"; this *is* the policy-bound part).
- **Impact on IEEE Claims:** none (the paper assumes an externalised binding; this realises it).
- **Recommendation:** declare a credit-card `ExecutionBinding` manifest realising the arch §6 A/(B/D) slice. No new science.

### Item — Absent-gate treatment / slice posture *(Gap 3b)*
- **Current status:** previously "unadjudicated tension"; now reconciled.
- **Can it be derived? YES** — posture from arch §6; fail-closed frozen (EEB §6); realisation via 3a policy.
- **Classification: ARCHITECTURE** (posture + frozen fail-closed), realised by **POLICY** (3a).
- **Reasoning:** the two authoritative readings operate at different levels (which gates are bound = policy; how a bound-absent gate behaves = frozen) and are complementary (§2 above).
- **Impact on Gamma / Replay / Predicate Semantics / IEEE Claims:** none (fail-closed is the existing non-default-permit; slice posture is arch §6).
- **Recommendation:** adopt the §6 slice posture; bound-but-absent gates fail-close (frozen).

### Item — HARM proxy admissibility *(Gap 4a)*
- **Current status:** partially resolvable.
- **Can it be derived? YES for the default (reject); NO for admit** (admit would require inventing a hazard model).
- **Classification: ARCHITECTURE** (default reject → native-plane-absent → fail-closed). The admit path is **Science**, optional and out-of-scope.
- **Reasoning:** arch §2.3 (HARM = D-service output; proxy non-architectural), §5 (no risk service → absent).
- **Impact on Gamma / Replay / Predicate Semantics / IEEE Claims:** none under reject (existing fail-closed on absent D). (Admitting a proxy *would* add a new derived D-signal — which we do not do.)
- **Recommendation:** **reject the proxy**; governance **confirms** (sign-off, not new science). If a real risk service is later bound, HARM comes from it (deployment), never a dataset proxy.

### Item — θ (HARM threshold) *(Gap 4b)*
- **Current status:** flagged SLA.
- **Can it be derived? NO** — but it is an existing externalised policy parameter.
- **Classification: POLICY** (deployment parameter).
- **Reasoning:** traceability Part 2 (θ sourced from frozen Policy Loader); existing `args.harm_threshold`; moot while HARM absent (4a).
- **Impact on Gamma / Replay / Predicate Semantics / IEEE Claims:** none (the `HARM_RISK > θ` predicate is defined; θ is its policy value).
- **Recommendation:** deployment policy parameter (frozen policy manifest); moot in this arm.

### Item — `L_amt` (amount limit) *(Gap 4c)*
- **Current status:** flagged external SLA.
- **Can it be derived? NO** — a risk-budget SLA; must not be fitted (forbidden).
- **Classification: POLICY** (deployment parameter).
- **Reasoning:** traceability §10.4 ("risk-budget SLA, not fit to `Class`"); Part 2 (limits sourced from frozen Policy Loader). Varies by deployment; not a universal truth.
- **Impact on Gamma / Replay / Predicate Semantics / IEEE Claims:** none (the `Amount ≤ L_amt` predicate is defined; `L_amt` is its policy value; different deployments set different limits, all valid).
- **Recommendation:** deployment policy parameter (operator SLA via the frozen policy manifest); if undeclared, the amount gate is out-of-slice (policy). Do **not** fit.

### Previously resolved (carried forward, re-classified)
- **Gap 1 (actuation):** **Architecture** — Eq. 7 + I5 ⇒ post-actuation observation; owner-confirmable, non-material to Γ.
- **Gap 2 (class-veto plane):** **Policy** — C or D (traceability §10.2 "Owner: policy"); **value ABSENT either way** in this arm ⇒ no material effect; recommend D per arch §2.3.
- **Gap 5 (velocity window):** **Architecture/data-fact** — global-only (no subject key, RCL §5); per-subject must not be faked.

---

## 5. Final classification

| Resolved Architectural Rules (frozen; no choice) | Resolved Scientific Rules (the methodology; fixed) | Deployment Policy Parameters (operator-declared; existing mechanisms) | Owner Decisions (policy/confirmation — NOT new science) |
|---|---|---|---|
| Fail-closed on absent/degraded evidence (EEB §6; FULL_SPEC 2.3/0.10) | Binding contract `B` = pure carry / absent→fail-closed / out-of-slice (RCL §0, EEB §5) | Gate→plane binding manifest — Gap 3a (ExecutionBinding) | Declare the credit-card `ExecutionBinding` gate-set (policy) |
| Native-plane origin (arch §1, §3) | Predicate definitions (frozen) | θ HARM threshold — Gap 4b (frozen policy loader) | Declare/omit θ, `L_amt` via the frozen policy manifest (policy) |
| Class-blindness (EEB §9; RCL §8) | Γ = maxᵢ dᵢ ; Π = 1[Γ=0] (frozen) | `L_amt` amount limit — Gap 4c (risk-budget SLA) | Governance sign-off **confirming** reject-proxy (4a) + slice posture (3b) |
| Slice-evaluation posture (arch §6) | SAFE_STATE fail-closed semantics (frozen) | Velocity window envelope — if velocity in-slice (Gap 5) | (Optional, out-of-scope) admit a HARM proxy — the only *new-science* path, explicitly **not taken** |
| Actuation = post-observation (Gap 1; Eq. 7 / I5) | Replay determinism DET1/DET4 (EEB §7) | Class-veto plane tag C/D — Gap 2 (absent-valued) | |
| HARM proxy default = reject → absent (Gap 4a; arch §2.3) | Class enters only at Ground-Truth Evaluation | | |
| Bound-but-absent gate → fail-closed (Gap 3b) | | | |

**Reading:** every previously-open item now lands in **Architecture** or **Policy**. The **Science** column is *complete and frozen* — no cell in it is unresolved. The single item with a *science* flavour (admit a HARM proxy) is an **optional, out-of-scope** path whose architectural default (reject) requires no invention. All Owner Decisions are **policy declarations or confirmations**, realizable through the **existing** frozen `ExecutionBinding` and `frozen_policy` mechanisms (traceability Part 2, REUSE-FROZEN).

---

## 6. Certification

The distinction the review sought is now explicit: the remaining unresolved items are **deployment policy** (gate-binding manifest, θ, `L_amt`, velocity envelope, veto plane-tag) and **architectural defaults** (reject-proxy, fail-closed, slice posture) — **not missing scientific methodology**. No item requires a new threshold, proxy, feature, algorithm, dataset fit, or `Class`-dependent behaviour to proceed; where invention *would* be required (admitting a HARM proxy), it is explicitly declared **out-of-scope deployment/governance policy, not taken**. No architectural ambiguity remains.

# READY FOR SCIENTIFIC IMPLEMENTATION

**What this means (and does not mean).** The scientific methodology is **complete and frozen**: the binding contract, predicate definitions, Γ aggregation, fail-closed, Class-blindness, replay determinism, and the slice-evaluation posture are all fixed by the corpus. Commit 5.1-B (the predicate binding) can be implemented as **pure engineering, parameterised by declared policy** — reading the gate→plane binding from an `ExecutionBinding` manifest and any θ/`L_amt` from the `frozen_policy` plane (both existing, REUSE-FROZEN). Commit 5.2's reported FPR/FDR/UER are **policy-conditional** (as any governance engine's are) and must be published together with the declared policy.

**It does *not* mean "run with zero inputs."** Activation still requires an operator to **declare the deployment policy** (the credit-card `ExecutionBinding` gate-set and any limits, or accept the fail-closed defaults) and governance to **confirm** the reject-proxy + slice posture. These are **policy acts, not scientific inventions** — which is precisely why the certification is *ready for implementation* rather than *blocked on new science*.

---

*Scientific specification refinement only. No code, no repository modification, no invented methodology. Every remaining item classified against the authoritative corpus with citations; the science is complete and frozen, and the residual owner decisions are deployment policy realizable through existing frozen mechanisms. Awaiting independent review before any implementation.*
