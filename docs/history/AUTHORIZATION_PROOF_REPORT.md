# AUTHORIZATION_PROOF_REPORT.md

**Phase 3 — Part H: exhaustive unit proofs — Expected decision ≡ Implementation decision for every
authorization state. Coverage target: 100 %.**

Evidence: [independent_verifier.py](independent_verifier.py) enumerated all 2¹⁶ = 65,536 legal
input states and asserted, per state, that the **independent expected** result (from the paper
equations) equals the **frozen implementation** result (`gamma_test_runner.evaluate_decision`).
Report: [independent_verifier_report.json](independent_verifier_report.json), verdict `IDENTICAL`.

---

## H1. Proof obligation

For every legal state s in the input space S,
`ExpectedDecision(s) = ImplementationDecision(s)` for `decision`, and additionally for the six
other output fields `{gamma_g, gamma_class, deficit_count, pi, isb, unauthorized}`.

`|S| = 65,536`. Enumerated exhaustively; **no combination skipped** (`coverage_complete: true`).

## H2. Result — global

| Metric | Value |
|---|---|
| States proven | 65,536 / 65,536 (**100 %**) |
| `decision` mismatches | **0** |
| All-field mismatches | **0** |
| Verdict | **ALL UNIT PROOFS PASS** |

## H3. Representative enumerated proof classes

Because the 65,536 rows are exhaustive, the table below is a *classification* of the same proofs,
not a sample subset — each class is closed and fully covered.

| Class | Defining condition | Expected decision | # states | Proven |
|---|---|---|---:|:---:|
| PERMIT | all 10 gates ∧ ¬HARM_OVER ∧ ¬Stale ∧ Fresh ∧ ¬CLASS | PERMIT | 4 | ✓ |
| Node-deficit denial | ≥1 gate False (Γ_G=1), ¬CLASS | SAFE_STATE | 32,764 | ✓ |
| Class-veto denial (nodes clean) | Γ_G=0 ∧ CLASS | SAFE_STATE | 4 | ✓ |
| Compound denial | Γ_G=1 ∧ CLASS | SAFE_STATE | 32,764 | ✓ |
| **Total** | | | **65,536** | **✓** |

### H3.1 Boundary/critical proofs (all within the enumeration)
- **Single-deficit denial (Corollary 2 witness):** exactly one gate False, all else clean → SAFE_STATE. Present and proven (subset of the 32,764 node-deficit states). Confirms a lone deficit denies regardless of predicate surplus.
- **Goodhart resistance:** every node predicate concurs (Γ_G=0) but ReasonCodes carries CLASS_1/GOODHART → SAFE_STATE. The 4 "class-veto denial" states prove the veto overrides full node concurrence.
- **HARM threshold boundary:** HARM_RISK=0.8 > θ=0.5 → deficit; HARM_RISK=0.0 → no deficit. Both polarities enumerated.
- **Token-invalid execution → unauthorized:** Actuated/ACT_PERMIT with ¬TOKEN_VALID → `unauthorized=True`; matches expected. (49,149 unauthorized-true states, all proven.)

## H4. Field-by-field unit-proof ledger

| Output field | Proven equal on all 65,536 states |
|---|:---:|
| gamma_g | ✓ (0 mismatch) |
| gamma_class | ✓ (0 mismatch) |
| deficit_count | ✓ (0 mismatch) |
| pi | ✓ (0 mismatch) |
| isb | ✓ (0 mismatch) |
| decision | ✓ (0 mismatch) |
| unauthorized | ✓ (0 mismatch) |

## H5. Reproduction

```
./.venv/bin/python independent_verifier.py
# -> coverage_complete: true, total_field_mismatches: 0, verdict: IDENTICAL, exit 0
```

## H6. Coverage statement

**100 % of the legal authorization state space is proven.** There are no skipped combinations,
no sampled shortcuts, and no unverified branches. Expected ≡ Implementation on the decision and on
all seven output fields.

**PART H VERDICT: AUTHORIZATION LOGIC EXHAUSTIVELY PROVEN (100 % coverage, 0 mismatches).**
