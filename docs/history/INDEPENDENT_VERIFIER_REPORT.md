# INDEPENDENT_VERIFIER_REPORT.md

**Phase 3 — Part I: independent implementation verification.**

A second, from-scratch verifier ([independent_verifier.py](independent_verifier.py)) re-implements
the paper equations directly and **never imports the reference decision logic to produce its own
answers**. It uses `gamma_test_runner.evaluate_decision` **only as an oracle to test against**, then
checks the chain: paper equations → independent verifier → implementation.

---

## I1. Independence guarantees (how this verifier is genuinely separate)

| Concern | Guarantee |
|---|---|
| Decision logic | `reference_decision()` re-derives Γ_G, Γ_class, Π, decision, ISB, Eq.7 from the paper text (verifier lines 60-95). It calls **no** function from `gamma_test_runner` to compute them. |
| Gate list | Gates are **hard-transcribed** as `REF_GATES` (verifier lines 44-47), then cross-checked equal to the frozen `NODE_GATE_COLS` at runtime (`independent_gate_list_matches_frozen: true`). A silent divergence in the gate set would fail this check. |
| Oracle isolation | `evaluate_decision` is imported once (verifier line ~148) and used solely for comparison, never inside `reference_decision`. |
| Input isolation | The oracle is passed a fresh `dict(row)` copy per call to prevent shared-state effects. |

## I2. Method

1. Enumerate the full input space (16 boolean dims, 2¹⁶ = 65,536 states) — verifier `DIMS`, `itertools.product`.
2. For each state: compute `reference_decision` (independent) and `evaluate_decision` (oracle).
3. Compare all seven output fields; tally per-field mismatches; record decision-space coverage.
4. Emit `independent_verifier_report.json`; exit 0 iff verdict `IDENTICAL`.

## I3. Result (executed 2026-07-09)

```json
{
  "independent_gate_list_matches_frozen": true,
  "input_dimensions": 16,
  "total_states_enumerated": 65536,
  "expected_states": 65536,
  "coverage_complete": true,
  "total_field_mismatches": 0,
  "per_field_mismatch_counts": {
    "gamma_g": 0, "gamma_class": 0, "deficit_count": 0,
    "pi": 0, "isb": 0, "decision": 0, "unauthorized": 0
  },
  "permit_states": 4,
  "safe_state_states": 65532,
  "unauthorized_true_states": 49149,
  "unreachable_abstract_cells": [],
  "verdict": "IDENTICAL"
}
```

**Chain verified:** paper equations ≡ independent verifier ≡ implementation, on all 65,536 states,
across all seven fields, with **zero** mismatch.

## I4. Replay leg (paper equations → implementation → replay)

The independent decision logic is the same function the runtime and replay consume. On the
production corpus the replay/summary path reports (`gamma_summary.json`, executed run):

| Replay/summary metric | Value |
|---|---|
| rows | 284,807 |
| derived_permit / derived_safe_state | 284,315 / 492 |
| match_status_rate | 1.0 |
| false_permit_count | 0 |
| false_denial_count | 0 |
| unauthorized_execution_count | 0 |
| replay_divergence_count | 0 |
| hash_chain_links_ok | 284,807 (all) |

The 4-cell decision table from the exhaustive verifier is consistent with the corpus outcome
(all 492 CLASS_1 fraud rows fall in Γ_class=1 and/or Γ_G=1 → SAFE_STATE; nominal rows in Γ=(0,0) →
PERMIT).

## I5. Mismatches found

**None.** `total_field_mismatches: 0`, `sample_mismatches: []`.

Had any mismatch existed, this report would list it and the offending bit-vector; **per the Phase-3
rules the implementation would NOT be modified** — only reported. No modification was needed and
none was made.

## I6. Scope note carried forward

The single-row Eq. 7 (`unauthorized`) has four disjuncts; the paper's full Eq. 7 has a fifth
(hash-chain broken) evaluated only in the vectorized path. The independent `reference_decision`
deliberately mirrors the **single-row** contract (no cross-row chain input exists at that scope),
so the 0-mismatch result is a faithful test of the single-row engine, not an artifact. The chain
disjunct is separately confirmed present in the vectorized code ([:985](gamma_test_runner.py#L985))
and yields `unauthorized_execution_count: 0` on the corpus. See `EQUATION_CONFORMANCE.md` §C7.

**PART I VERDICT: INDEPENDENT VERIFICATION PASSES — implementation is identical to an independent
re-derivation of the paper equations across the entire state space; 0 mismatches.**
