# Gamma live demo — validation

Target: `docs/demo/gamma-wire.html` (deployed as `gamma-demo/index.html`).

All values below were **observed** by driving the page in headless Chrome — selecting each
scenario, running the authorization, then invoking `Re-run replay` and reading the rendered
DOM. They are not hand-written expectations.

Digest algorithm in use: `SHA-256 · Web Crypto`.

---

## Validation matrix

| Scenario         | Γ_G | Γ_class | Π | Permit                | SIG_GAMMA | SIG_COMMIT | SIG_WATCHDOG | P_phys | Final state | Funds move |
| ---------------- | --: | ------: | -: | -------------------- | --------: | ---------: | -----------: | -----: | ----------- | ---------- |
| **A** Permit         | 0 | 0 | 1 | Issued → CONSUMED     | 1 | 1 | 1 | 1 | PERMIT     | Yes |
| **B** Country        | 1 | 0 | 0 | Not issued            | 0 | 1 | 1 | 0 | SAFE_STATE | No  |
| **C** Approval       | 1 | 0 | 0 | Not issued            | 0 | 1 | 1 | 0 | SAFE_STATE | No  |
| **D** Beneficiary    | 1 | 0 | 0 | Not issued            | 0 | 1 | 1 | 0 | SAFE_STATE | No  |
| **E** Commit failure | 0 | 0 | 1 | Issued → REVOKED      | 1 | **0** | 1 | 0 | SAFE_STATE | No  |
| **F** Class veto     | 0 | 1 | 0 | Not issued            | 0 | 1 | 1 | 0 | SAFE_STATE | No  |

For B, C, D and F, `SIG_COMMIT = 1` because the **denial record is still committed** — the
decision fails at `SIG_GAMMA`, not at commitment.

---

## Per-scenario detail

### A — Permit

- Failing predicates: none.
- Decision `PERMIT`; permit `PTA-…` issued, state `ACTIVE → CONSUMED`.
- Ledger `COMMITTED`; interlock `1/1/1 → P_phys = 1`.
- Revalidation: all 9 checks pass. Execution released, permit consumed atomically.
- Receipt: `SWIFT-REF-881420`, `ACCEPTED_FOR_SETTLEMENT`, receipt hash bound.
- Enforcement status: permit issued **YES**, evidence committed **YES**, watchdog **YES**,
  P_phys **1**, action released **YES**, permit consumed **YES**, receipt closed **YES**.
- Reason codes: `CONTEXT_SUFFICIENT`, `ALL_MANDATORY_PREDICATES_CONCUR`,
  `CLASS_LEVEL_CONTROLS_CLEAR`, `NON_COMPENSATORY`, `PERMIT_ISSUED`,
  `AUTHORIZATION_RECORD_COMMITTED`, `INTERLOCK_RELEASED`, `PERMIT_CONSUMED`,
  `EXECUTION_RECEIPT_BOUND`.
- Terminal: **PERMIT — action released**.
- Replay: authorization `MATCH`; decision `YES`; evidence hash `YES`; ledger link `YES`;
  execution verification — permit consumed `YES`, submitted action hash match `YES`,
  receipt bound `YES`.

### B — Country

- Failing predicate: `COUNTRY_ALLOWED` (POL-AML-002, governance control evaluation).
- Decision `SAFE_STATE`; **no** Permit-to-Act; binding stage *not performed*.
- Denial record committed; interlock `0/1/1 → P_phys = 0`; revalidation not performed.
- No external receipt. Reason codes include `COUNTRY_NOT_PERMITTED`, `PERMIT_NOT_ISSUED`,
  `AUTHORIZATION_RECORD_COMMITTED`, `SAFE_STATE_ENFORCED`.
- Terminal: **SAFE_STATE — no permit issued**.
- Replay: `MATCH` / decision `YES` / evidence `YES` / ledger `YES`;
  execution verification `N/A — no action released`.

### C — Approval

- Failing predicate: `APPROVAL_COUNT ≥ 2` (POL-DUA-001), stage note
  *"Approval count observed = 1, required = 2"*.
- Identical enforcement profile to B. Reason code `DUAL_AUTHORIZATION_INCOMPLETE`.

### D — Beneficiary

- Failing predicate: `BENEFICIARY_APPROVED` (POL-BEN-002).
- Identical enforcement profile to B. Reason code `BENEFICIARY_NOT_APPROVED`.

### E — Commit failure ← the important one

- Failing predicates: **none**. `Γ_G = 0`, `Γ_class = 0`, `Π = 1`.
- **Authorization calculation = PERMIT** and the Permit-to-Act *is* issued.
- Ledger append **FAILS** → `SIG_COMMIT = 0`.
- Interlock `1/0/1 → P_phys = 0`. Revalidation not performed.
- Permit is never consumed; it transitions `ACTIVE → REVOKED`.
- No instruction submitted, no receipt, funds not moved.
- **Final runtime state = SAFE_STATE** while the decision panel still reads `PERMIT`.
- Reason codes: `CONTEXT_SUFFICIENT`, `ALL_MANDATORY_PREDICATES_CONCUR`,
  `CLASS_LEVEL_CONTROLS_CLEAR`, `NON_COMPENSATORY`, `PERMIT_ISSUED`,
  `EVIDENCE_COMMIT_FAILED`, `PERMIT_REVOKED`, `SAFE_STATE_ENFORCED`.
- Terminal: **SAFE_STATE — permit calculation did not become actuation authority**,
  with the three-line distinction:
  - Authorization calculation: `PERMIT`
  - Execution authority released: `NO`
  - Operational result: `SAFE_STATE`
- Replay: authorization `MATCH`, decision `YES`, evidence hash `YES`,
  **ledger link `NO`** (the append never happened).

### F — Class veto

- Failing predicates: `CORRIDOR_CLASS_ACTIVE` and `NO_PERSISTENT_CLASS_VETO` (class level).
- `Γ_G = 0`, `Γ_class = 1`, `Π = 0` — action-level passes do not override the class veto.
- No permit; denial record committed; interlock `0/1/1 → P_phys = 0`.
- Reason codes: `CONTEXT_SUFFICIENT`, `CLASS_LEVEL_VETO_ACTIVE`, `NON_COMPENSATORY`,
  `PERMIT_NOT_ISSUED`, `AUTHORIZATION_RECORD_COMMITTED`, `SAFE_STATE_ENFORCED`.
- Terminal: **SAFE_STATE — no permit issued**.

### Operations plane (all scenarios)

Stage 25 reports live counters — e.g. scenario E shows `hash_chain_health = GAP — record
not appended`, `evidence_commit_failures = 1`, `permit_revocations = 1`.
Stage 26 opens `INC-2026-0723-<scenario>` only when the final state is SAFE_STATE, with a
scenario-specific runbook (E: *restore ledger durability → re-attest → re-propose*).
Stage 27 proposes a control change derived from the actual failure. Stage 28 shows
`POL-EPOCH-774 (active) → POL-EPOCH-775 (draft)` and states `this_decision replays under
POL-EPOCH-774 · GAMMA-G0-DEMO-2.0`.

---

## Invariants asserted by the implementation

1. An AI proposal begins with zero execution authority (stage 1).
2. Every predicate stage is evaluated — complete mediation, no early exit.
3. Context insufficiency fails closed (`CONTEXT_INSUFFICIENT`).
4. One action-level failure ⇒ `Γ_G = 1`; one class-level failure ⇒ `Γ_class = 1`.
5. `Π = 1` only when both Γ values are 0 (`computeDecision`).
6. `P_phys` is computed by a **separate** function (`computeInterlock`) from the decision,
   commitment and watchdog — a mathematical PERMIT never releases execution on its own.
7. No permit ⇒ no execution. No commitment ⇒ no execution. No watchdog ⇒ no execution.
8. The permit is revalidated immediately before use and consumed atomically, once.
9. Denials produce a sealed, replayable record.
10. Replay reads only the sealed record, `POL-EPOCH-774` and `GAMMA-G0-DEMO-2.0` — never the
    current clock, current policy or live systems (sealed timestamps are stored in the record).
11. Passing predicates never compensate for a failing one.

## Stage coverage

All **28 master stages** run, in three planes:

| Plane | Stages | Demo coverage |
| --- | --- | --- |
| Governance | 1–5 | registration · classification · policy→control · predicate generation · manifest signing |
| Runtime authorization (Gamma) | 6–24 | interception → canonicalization → sufficiency → predicates → Γ → permit → commit → interlock → revalidation → execution → receipt → replay |
| Governance operations | 25–28 | monitoring · incident · policy evolution · epoch activation |

Verified by reading `.step[data-id]` / `data-state` from the rendered DOM after a run:
28 stage cards, 3 plane bands.

Governance is load-bearing, not decorative: stage 5 hashes the real manifest and that
`manifest_hash` is bound into the CTR as `policy_snapshot`, so it propagates into the
ERTuple, the evidence hash, the ledger hash and the replay hash.

## Timing

| Mode | Measured total |
| --- | --- |
| Normal motion | ≈ 9.0 s of stage dwell + digest time |
| `prefers-reduced-motion` | ≈ 1.4 s (every dwell capped at 50 ms) |

## Reproducing these results

Open the page and step through scenarios A–F, or drive it headlessly:

```bash
# select scenario, click #runBtn, wait for #runBtn to re-enable and #terminal to unhide,
# then click #verifyBtn and read #gG/#gC/#gP, #ptState, #ldState, #enf, #vlines.
```

No build step, no external dependencies, no network access required.
