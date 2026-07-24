# SCIENTIFIC_CORRECTNESS_CERTIFICATE.md

**Phase 3 — Part J: publication evidence certificate.**
Read-only verification. No implementation, benchmark, statistic, replay, or trace was modified.
Every answer below is backed by a cited artifact in this package.

**Subject:** L-DREA / Gamma G-0 runtime authorization core (`evaluate_decision`) and the AgentDojo
interposition chain.
**Verification date:** 2026-07-09.
**Primary evidence:** `independent_verifier_report.json` (65,536-state exhaustive check, 0 mismatch);
`gamma_summary.json` (284,807-row corpus run); `full_spec_conformance_report.json`.

---

## The eleven certificate questions

### Q1. Does the implementation exactly match the paper?
**On the authorization decision — YES, mechanically proven.** Γ_G, Γ_class, Π, and
PERMIT/SAFE_STATE were derived from source (`IMPLEMENTATION_EQUATIONS.md`), proven branch-by-branch
against the paper equations (`EQUATION_CONFORMANCE.md` C1–C6), and confirmed identical to an
independent re-derivation on all 65,536 states with **0** field mismatches.
**One documented scope difference:** the single-row Eq. 7 `unauthorized` diagnostic omits the
hash-chain disjunct present in the vectorized Eq. 7 (structural — no cross-row context at single-row
scope; decision Π is unaffected). See C7 / A6.

### Q2. Does the implementation exactly match FULL_SPEC?
**Qualified YES.** **There is no literal `FULL_SPEC.md` file** in the repo (Observation O1); the
"FULL_SPEC" is realized as README §7/§8 + the seven frozen manifests + `full_spec_conformance.py`.
Against that encoded spec, `full_spec_conformance_report.json` returns
**`FULL_SPEC_CONFORMANT (Tier-S)`** with all §7.1 acceptance bands holding, UER=0, SVR=0, 0 false
permits. Match on the encoded clauses: confirmed.

### Q3. Is every theorem / property implemented?
**Every claimed property is present in code and verified; two are fully mechanized, the rest hold
empirically on the full corpus, and two carry named limits** (`FORMAL_PROPERTY_VERIFICATION.md`):
- MECHANIZED (exhaustive, 0 counterexamples): Determinism (P1), Safety / Non-Compensatory
  Soundness (P6).
- EMPIRICAL (0 violations over 284,807 rows): Replay determinism (P2), Commit-before-actuate on
  traces (P3), Execution Integrity / Eq. 7 (P4).
- INSPECTION + EXECUTED: Complete mediation (P5), Non-bypassability (P7), Evidence completeness (P8).
- **NOT exhaustively proven:** runtime-layer *enforcement* of commit-before-actuate (P3 is a
  measured trace invariant, not a pre-actuate barrier in `run_function`); architectural
  *universality* of non-bypassability (P7 relies on assumption A1).

### Q4. Is every equation implemented?
**YES.** E1–E8 (`IMPLEMENTATION_EQUATIONS.md`) each map to a verbatim source locus and were
exhaustively confirmed. No specified equation is missing; no extra decision logic exists outside
lines 140–178 of `evaluate_decision`.

### Q5. Are there unreachable states?
**No unreachable states in the abstract decision space** — all 4 (Γ_G, Γ_class) cells are reachable
(`unreachable_abstract_cells: []`). The `decision` codomain is exactly {PERMIT, SAFE_STATE}; any
other output is unreachable (0 occurrences in 65,536 states). PERMIT is reachable in exactly 4
states (Γ=(0,0)); the internal state Π=1 ∧ Γ>0 is unreachable by construction (Invariant I3).

### Q6. Any hidden assumptions?
**Ten catalogued** (`IMPLEMENTATION_ASSUMPTIONS.md`). Correctness-relevant: **A1** (AgentDojo routes
every call through `run_function` — foundational, assumed), **A5** (PERMIT means "no *evaluated*
deficit"; excluded families default clean — Tier-S structural-only scope), **A10** (malformed
amount → PASS, a single local fail-open). The rest are checked integrity anchors or documented
parameters.

### Q7. Any undocumented behaviour?
**Minor.** (i) README paper→line citations (e.g. `gamma_test_runner.py:407-434`, `:469-484`) are
**stale** — those lines now hold unrelated functions; the real LLC logic is at :133-178 (single-row)
and :914-987 (vectorized). Observation O2. (ii) A10's local fail-open is present in code but
contrary to the stated global fail-closed posture. No undocumented behaviour affects the decision.

### Q8. Any ambiguity?
**Two naming/scope ambiguities.** (i) "FULL_SPEC" has no single file (O1). (ii) "PERMIT" /
"authorized" is Tier-S structural-only: it certifies no *evaluated env-derived* deficit, not
absence of every conceivable predicate failure (A5). Both are resolved explicitly here.

### Q9. Any contradiction?
**None in the authorization logic.** Single-row and vectorized engines agree on Π/decision (C-B);
independent verifier agrees on all fields; corpus outcomes are consistent with the exhaustive
decision table. The only cross-form difference (Eq. 7 chain term) is a scope restriction, not a
contradiction.

### Q10. Any reviewer concern remaining?
**Five, all disclosed, none affecting decision correctness:**
1. A1 — complete mediation rests on AgentDojo's routing contract (external).
2. A5 — authorization scope is exactly the env-derived families (Tier-S).
3. A10 — one local fail-open on malformed amount input (unobserved on corpus; **reported, not fixed** per Phase-3 rules).
4. O1 — no literal `FULL_SPEC.md`; spec is distributed.
5. O2 — README line-number citations are stale (documentation drift).

### Q11. Overall.
The **decision engine is exactly correct** against the specification (mechanized, exhaustive). The
**surrounding safety envelope holds on the full corpus** with zero violations, subject to the named,
disclosed assumptions.

---

## Certificate verdict

> **VERIFIED WITH MINOR OBSERVATIONS.**
>
> The Law-of-Concurrence authorization core (`evaluate_decision`: Γ ⇒ Π ⇒ PERMIT/SAFE_STATE) is
> proven identical to the paper equations across the entire 65,536-state input space with zero
> mismatches, and identical between its single-row and vectorized implementations. Determinism and
> non-compensatory safety are fully mechanized. Replay determinism, commit-before-actuate, and
> execution integrity hold with zero violations over the 284,807-row corpus. The observations (O1
> spec-file naming, O2 stale README citations) and assumptions (A1 routing, A5 Tier-S scope, A10 one
> local fail-open) are disclosed and do **not** alter any authorization decision. No theorem
> violation, no mismatch, and no contradiction was found.

*No discrepancy was fixed; per Phase-3 rules all findings are reported only. Certifier: automated
read-only verification harness (`independent_verifier.py`) + source audit.*
