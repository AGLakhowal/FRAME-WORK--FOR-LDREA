# STATE_SPACE_VERIFICATION.md

**Phase 3 — Part D: exhaustive Γ → Π → Decision verification over the entire legal state space.**

Generator/oracle: [independent_verifier.py](independent_verifier.py) → [independent_verifier_report.json](independent_verifier_report.json).
Executed 2026-07-09 with `./.venv/bin/python independent_verifier.py` (exit 0, verdict `IDENTICAL`).

---

## D1. State-space definition

`evaluate_decision` reads 16 **independent** boolean degrees of freedom (all other inputs are
functions of these). The HARM measure is collapsed to the only decision-relevant bit `HARM_RISK>θ`
(materialized as 0.0 / 0.8 against θ=0.5); ReasonCodes to the veto bit CLASS.

| # | Dimension | Feeds |
|---|---|---|
| 1–7 | `Gate_A1…Gate_A7` | node deficit → Γ_G |
| 8 | `Lambda_G` | node deficit → Γ_G |
| 9 | `TOKEN_VALID` | node deficit → Γ_G; ISB; Eq.7 |
| 10 | `AuthoritySignatureValid` | node deficit → Γ_G; ISB |
| 11 | `HARM_OVER` (HARM_RISK>θ) | deficit → Γ_G |
| 12 | `StaleContext` | deficit → Γ_G; ISB |
| 13 | `TelemetryFresh` | deficit → Γ_G; ISB |
| 14 | `CLASS` (ReasonCodes token) | Γ_class |
| 15 | `Actuated` | execute → Eq.7 |
| 16 | `ACT_PERMIT` | execute → Eq.7 |

**Total legal states = 2¹⁶ = 65,536.** All enumerated. **Coverage = 100%** (`coverage_complete: true`, `total_states_enumerated: 65536`).

---

## D2. Decision table (abstract Γ_G × Γ_class → Π → decision)

Counts are exact populations of the 65,536-state space (from the report's `decision_table`):

| Γ_G | Γ_class | Π | Decision | # concrete states |
|:---:|:---:|:---:|:---|---:|
| 0 | 0 | **1** | **PERMIT** | 4 |
| 0 | 1 | 0 | SAFE_STATE | 4 |
| 1 | 0 | 0 | SAFE_STATE | 32,764 |
| 1 | 1 | 0 | SAFE_STATE | 32,764 |
| | | | **PERMIT total** | **4** |
| | | | **SAFE_STATE total** | **65,532** |

Matches the verifier's headline: `permit_states: 4`, `safe_state_states: 65532`.

### Why exactly 4 PERMIT states (sanity derivation)
Π=1 requires Γ_G=0 **and** Γ_class=0. Γ_G=0 forces all 10 gates TRUE, HARM_OVER=False, StaleContext=False, TelemetryFresh=True (14 dimensions pinned). Γ_class=0 forces CLASS=False (15th pinned). The only free dimensions are `Actuated` and `ACT_PERMIT` ⇒ 2² = **4** PERMIT states. This is the arithmetic witness that PERMIT is maximally constrained ("zero-authority default; permit is the narrow exception") — the §0.10 non-default-permit posture.

---

## D3. Truth table — Π as a function of (Γ_G, Γ_class)

| Γ_G | Γ_class | Π = ¬Γ_G ∧ ¬Γ_class |
|:---:|:---:|:---:|
| 0 | 0 | 1 |
| 0 | 1 | 0 |
| 1 | 0 | 0 |
| 1 | 1 | 0 |

Π is the NOR of (Γ_G, Γ_class). Confirmed on every concrete state.

---

## D4. Reachable vs impossible states

- **Abstract (Γ_G, Γ_class) cells:** all 4 are **reachable** (`reachable_abstract_cells` lists all four; `unreachable_abstract_cells: []`).
- **Impossible decision outputs:** the codomain of `decision` is exactly `{PERMIT, SAFE_STATE}`. No state produced any third value — `decision` mismatch count = 0 over 65,536 states, and the only string constants in the return are these two ([:176](gamma_test_runner.py#L176)). Any output ∉ {PERMIT, SAFE_STATE} is **unreachable**.
- **Impossible internal states:** `Π=1 ∧ (Γ_G=1 ∨ Γ_class=1)` is unreachable by construction (D3) — this is exactly runtime invariant I3 (Non-Compensatory Soundness), confirmed with 0 counterexamples.

---

## D5. Field-level identity over the full space

`independent_verifier.py` compared **all seven** output fields per state against a from-scratch
reimplementation:

| Field | Mismatches / 65,536 |
|---|---|
| gamma_g | 0 |
| gamma_class | 0 |
| deficit_count | 0 |
| pi | 0 |
| isb | 0 |
| decision | 0 |
| unauthorized | 0 |
| **Total** | **0** |

`unauthorized_true_states = 49,149` (execute ∧ any-invalidity) — reproduced identically by both
implementations.

---

## D6. Result

- Coverage: **100 %** (65,536 / 65,536 legal states).
- Impossible states: none produced; `Π=1` restricted to the single Γ=(0,0) cell.
- Γ → Π → Decision verified against the derived equations with **zero** discrepancies on every field.

**PART D VERDICT: STATE SPACE FULLY VERIFIED — Γ⇒Π⇒Decision is exact on all 65,536 states.**
