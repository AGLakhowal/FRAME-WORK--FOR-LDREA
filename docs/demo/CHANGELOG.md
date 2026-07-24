# Gamma demo site — changelog

Two-page static site, updated from "decision engine" framing to a technically faithful
**execution-authority boundary**.

File names are unchanged so the Vercel deployment and all existing links keep working:

| Spec name          | Actual file                                        |
| ------------------ | -------------------------------------------------- |
| `how-it-works.html`| `docs/demo/gamma-overview.html`                     |
| `live-gate.html`   | `docs/demo/gamma-wire.html`                         |
| deployed copies    | `gamma-demo/gamma-overview.html`, `gamma-demo/index.html` |

---

## Architecture corrections

- **Capability vs authority.** The AI proposal now explicitly starts with *zero inherent
  execution authority*. Stage 1 of the pipeline is boundary interception, not evaluation.
- **Source evidence vs completed authorization proof.** Split into two distinct stages:
  `sourceEvidence` (bound *before* the decision) and `commit` (the ERTuple, Evidence Quad
  and ledger append, committed *after* the decision and *before* any action). Every claim
  that "all evidence is committed before authorization" was removed.
- **Evidence bundle vs Evidence Quad.** The complete record is now the
  **Authorization Evidence Bundle / ERTuple**. The **Evidence Quad** is only its four-part
  anchor: specification clause, evaluation ID, method version, ledger hash.
- **Permit-to-Act.** A PERMIT is now issued as a signed, scoped, TTL-bounded, single-use,
  revocable credential bound to one exact action hash — with a real lifecycle
  (`ISSUED → ACTIVE → CONSUMED | EXPIRED | REVOKED`).
- **Commit-before-actuate.** Added the three-signal interlock
  `P_phys = SIG_COMMIT ∧ SIG_GAMMA ∧ SIG_WATCHDOG`, computed independently of the decision.
- **Γ_class is now real.** Previously hardcoded to 0. It is now driven by a separate
  class-level control set and vetoes independently of Γ_G.
- **Authorization replay vs execution verification.** Separated: replay recomputes
  predicates/Γ/Π/decision/reason codes; execution verification checks permit validity,
  consumption and receipt binding. Replay never re-runs the payment network.
- **One-way architecture** expanded from 4 layers to 9 (capability plane → gateway →
  predicate plane → decision core → authority services → evidence services → enforcement
  substrate → external executor → governance operations).

## Copy corrections

- Hero: **"Deterministic execution authority for AI actions"** / "The last gate before an
  AI-proposed action becomes an external effect."
- The missing checkpoint is described as an **externalization boundary**, not another
  review layer.
- "Gamma **evaluates the approved predicate manifest**" replaces any phrasing implying
  Gamma authors policy.
- Added `Policy management`, `An AI judge` and `A semantic-truth engine` to the
  struck-through "what this is not" chips.
- Determinism claim tightened everywhere: *"Same canonical evidence + same policy epoch +
  same method version → same authorization decision"*, plus an explicit **authority-horizon**
  note (determinism ≠ truthful evidence, complete predicates, or semantic correctness).
- Risk classification is shown compiling into a concrete **Enforcement Profile**
  (complete mediation, 5 s permit TTL, dual authorization, class veto, commit-before-actuate,
  enhanced retention, no degraded execution) rather than existing as a label.
- Footers on both pages replaced with the canonical positioning statement.
- Honesty section now states results are **Tier-S**; Tier-H/T remain specification.

## Stage additions (live demo)

Pipeline grew from 9 to **28 stages**, numbered to the master operating model and grouped
into the three planes with inline band headers:

```
GOVERNANCE PLANE 1–5
  register → classify → mapping → generate → sign
GAMMA BOUNDARY · RUNTIME AUTHORIZATION PLANE 6–24
  intercept → context → sufficiency → identity → account → beneficiary → policy → risk
  → sourceEvidence → classControls → decision → binding → permit → commit
  → interlock → revalidate → execution → receipt → replay
GOVERNANCE OPERATIONS PLANE 25–28
  monitoring → incident → evolution → epoch
```

The demo previously covered only stages 6–24. It now runs the full lifecycle:

- **1–5 Governance plane.** Use-case registration; impact and risk classification (each
  dimension scored, Tier 4 / CRITICAL derived, and compiled into a concrete enforcement
  profile); policy-to-control mapping; control-to-predicate generation (counts computed
  live from the manifest — 49 action + 6 class + 9 revalidation = 64); manifest approval
  and signing.
- **Governance genuinely feeds runtime.** Stage 5 hashes the real manifest object with
  SHA-256; that `manifest_hash` is bound into the Context Translation Record as
  `policy_snapshot` and therefore into the ERTuple and every downstream hash. Governance is
  not decorative — change the manifest and every evidence hash changes.
- **25–28 Operations plane**, all populated from the actual run: monitoring counters
  (permit lifecycle, revocations, replay attempts, predicate-failure distribution, class
  vetoes, hash-chain health, evidence-commit failures, watchdog failures, SAFE_STATE
  events); incident operations (opens an incident only on SAFE_STATE, with a
  scenario-specific runbook and a re-attestation requirement); policy evolution (a proposed
  control change derived from what actually failed); and signed policy epoch activation
  (`POL-EPOCH-774 → 775`, explicitly noting that this decision still replays under 774).
- Stage 7 was split into **07 Action Envelope & CTR** and **08 Interpretive Sufficiency &
  Freshness** so the numbering matches the master figure exactly.

All predicate stages are now evaluated even after a failure — complete mediation over the
whole manifest — and every run reaches the decision stage so the sealed denial path is
visible.

## Predicate manifest

- Expanded from 25 to **61 predicates** across 8 stages plus 9 revalidation checks.
- Each predicate now carries: ID, plain question, machine token, policy source, evidence
  source, freshness requirement, owner, failure outcome, policy epoch — exposed per row via
  a keyboard-accessible ⓘ disclosure.
- **Fraud predicate corrected.** `FRAUD_SIGNAL_PRESENT` was removed and replaced with
  `FRAUD_ASSESSMENT_AVAILABLE`, `FRAUD_SIGNAL_FRESH`, `FRAUD_RISK_WITHIN_POLICY_BOUND` and
  `NO_ACCOUNT_TAKEOVER_INDICATOR` — a service returning a result no longer implies
  authorization.
- Added `CONTEXT_INSUFFICIENT` as the reason code for interpretive-sufficiency failure.

## Scenario changes

- Added **F — Class veto**: all action predicates pass, `CORRIDOR_CLASS_ACTIVE` and
  `NO_PERSISTENT_CLASS_VETO` fail → Γ_G = 0, Γ_class = 1, Π = 0.
- **E rewritten** from an ambiguous "evidence incomplete" to a post-decision
  **ledger-commit failure**: Γ_G = 0, Γ_class = 0, Π = 1, SIG_COMMIT = 0, P_phys = 0,
  final state SAFE_STATE. The mathematical decision values are *not* overwritten.
- B / C / D reason codes corrected to `COUNTRY_NOT_PERMITTED`,
  `DUAL_AUTHORIZATION_INCOMPLETE`, `BENEFICIARY_NOT_APPROVED`; C now shows
  `observed = 1, required = 2`.
- Segmented control extended to six options (`repeat(6,1fr)`, wrapping to 3×2 under 560 px).
- `NON_COMPENSATORY` is rendered neutral, not as a red error.

## Hashing changes

- Replaced the custom `xmur3`/`hash64` function with **Web Crypto `crypto.subtle.digest`
  (SHA-256)**; all hashing is async. If `crypto.subtle` is unavailable the page falls back
  to a deterministic demo digest **and relabels itself honestly** — the digest algorithm in
  use is printed in the replay panel.
- Added `canonicalize()`: recursive key sorting, stable arrays, money in minor units,
  policy epoch and method version included, **wall-clock time excluded** (sealed timestamps
  are stored in the record so replay is bit-stable).
- Hash panel relabelled to phase-accurate names: **Action hash, Evidence hash, Ledger hash,
  Replay hash, Receipt hash**. The pre-execution "Execution hash" label was removed.

## Replay changes

- `Re-run replay` now recomputes from the **sealed record only** — recomputing the
  predicate reduction, Γ_G, Γ_class, Π and decision, then comparing hashes and the ledger
  link.
- Reports `Authorization replay / Decision match / Evidence hash match / Ledger link valid`,
  and separately `Execution verification` (permit consumed, submitted action hash match,
  receipt bound) only when an action was actually released.
- Replay scope is pinned to `POL-EPOCH-774` and `GAMMA-G0-DEMO-2.0`.

## Accessibility changes

- Terminal result card is `role="status" aria-live="polite"`; added a visually-hidden
  `#announce` live region for decision and final-state changes.
- Scenario buttons keep `aria-pressed` and are disabled during a run; predicate metadata
  toggles are real `<button>`s with `aria-expanded`.
- Stage headers retain `role="button"`, `tabindex="0"` and Enter/Space activation;
  `:focus-visible` outlines added to new controls.
- **No layout shift during a run** — stages are not auto-expanded mid-animation; the
  decisive stage is expanded once, after the run completes.
- Sticky side panel scrolls internally rather than overflowing tall viewports; it becomes
  static under 940 px.
- All dynamic values are escaped (`esc()`); the predicate-token column and metadata
  collapse on narrow screens; no horizontal overflow at 360 px.
- `prefers-reduced-motion` caps every stage dwell at 70 ms (full run < 2 s) and disables
  hash scrambling.
