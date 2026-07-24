# IMPLEMENTATION_EQUATIONS.md

**Phase 3 — Part B: Equations mechanically derived from the frozen implementation.**
Method: each equation below is read *out of* the source (no reference to the paper is used to
construct the left column); the paper equation is placed alongside only for the cross-check in
`EQUATION_CONFORMANCE.md`. Source of truth: [gamma_test_runner.py:133-178](gamma_test_runner.py#L133-L178).

---

## E1 — Node deficit

```
Source (lines 142-145):
    for g in NODE_GATE_COLS:
        if not row[g]:
            deficit = 1; deficit_count += 1
```

**Derived equation:** for each node gate gᵢ ∈ NODE_GATE_COLS,  `dᵢ = ¬gᵢ`  (i.e. `dᵢ = 1 ⇔ gᵢ = False`).

**Proof:** the loop sets `deficit=1` iff at least one `row[g]` is falsy. `deficit_count` counts how many. Binary domain ⇒ `dᵢ = 1 − 𝟙[gᵢ]`.

---

## E2 — Environmental / risk deficits

```
Source (lines 146-154):
    if row["HARM_RISK"] > harm_threshold: deficit=1; deficit_count+=1
    if row["StaleContext"]:               deficit=1; deficit_count+=1
    if not row["TelemetryFresh"]:         deficit=1; deficit_count+=1
```

**Derived:**
`d_harm = 𝟙[HARM_RISK > θ]`,  `d_stale = 𝟙[StaleContext]`,  `d_telem = 𝟙[¬TelemetryFresh]`.

This is the code realization of dᵢ = max(0, mᵢ − θᵢ) specialized to a boolean/threshold measure: for HARM the measure mᵢ=HARM_RISK, threshold θᵢ=θ; `max(0, m−θ) > 0 ⇔ m > θ`.

---

## E3 — Γ_G (non-compensatory aggregation)

```
Source: `deficit` starts at 0 (line 140) and is set to 1 by ANY branch in E1/E2.
Return (line 171): "gamma_g": deficit
```

**Derived equation:**
```
Γ_G = max( d₁,…,d₁₀, d_harm, d_stale, d_telem )      (13 binary deficit sources)
    = OR of all deficits
    = 1  iff  at least one deficit is present, else 0
```

`deficit` is a running logical-OR (`max` over binary values). **Non-compensatory:** there is no branch that *lowers* `deficit`; a surplus on clean predicates can never offset a single deficit. This is the code witness for **Corollary 2** (a weighted-sum would be compensatory; this is not).

---

## E4 — Γ_class (class-level veto)

```
Source (lines 156-157):
    reason = str(row["ReasonCodes"]).upper()
    gamma_class = 1 if ("CLASS_1" in reason or "GOODHART" in reason) else 0
```

**Derived:** `Γ_class = 𝟙[ "CLASS_1" ⊑ upper(ReasonCodes)  ∨  "GOODHART" ⊑ upper(ReasonCodes) ]`
(⊑ = substring). Case-insensitive by construction (`.upper()`).

---

## E5 — Π (authority predicate) and decision

```
Source (lines 159, 176):
    pi = 1 if (deficit == 0 and gamma_class == 0) else 0
    "decision": "PERMIT" if pi == 1 else "SAFE_STATE"
```

**Derived equations:**
```
Π        = 𝟙[ Γ_G = 0  ∧  Γ_class = 0 ]   ≡   𝟙[ max(Γ_G, Γ_class) = 0 ]
decision = PERMIT   if Π = 1
         = SAFE_STATE otherwise
```

Equivalence `(Γ_G=0 ∧ Γ_class=0) ⇔ max(Γ_G,Γ_class)=0` holds because both are in {0,1}.

---

## E6 — ISB (interpretive-sufficiency bit)

```
Source (lines 160-165):
    isb = 1 if (row["TOKEN_VALID"] and row["AuthoritySignatureValid"]
                and row["TelemetryFresh"] and not row["StaleContext"]) else 0
```

**Derived:** `ISB = TOKEN_VALID ∧ AuthoritySignatureValid ∧ TelemetryFresh ∧ ¬StaleContext`.

---

## E7 — Unauthorized execution (Eq. 7, single-row form)

```
Source (lines 166-169):
    execute = bool(row["Actuated"] or row["ACT_PERMIT"])
    unauthorized = execute and ((not row["TOKEN_VALID"])
                    or deficit != 0 or gamma_class != 0 or isb == 0)
```

**Derived:**
```
execute      = Actuated ∨ ACT_PERMIT
Unauthorized = execute ∧ ( ¬TOKEN_VALID ∨ Γ_G ≠ 0 ∨ Γ_class ≠ 0 ∨ ISB = 0 )
```

**Documented divergence from the paper's full Eq. 7 (an OBSERVATION, not a fix):**
The paper / README Eq. 7 has a fifth disjunct — *hash-chain link broken*:
`Unauth = Execute ∧ (¬Valid ∨ max(Γ_G,Γ_class)>0 ∨ ISB=0 ∨ chain broken)`.
The **single-row** `evaluate_decision` omits the `chain broken` term because a single decision row carries **no cross-row chain context**. The **vectorized** implementation includes it:
[gamma_test_runner.py:985](gamma_test_runner.py#L985) `| (~df["DerivedChainLinked"])`.
Consequence: `decision`/`Π` are identical in both forms (the chain term never enters Π); only the `unauthorized` diagnostic differs, and only when chain linkage is broken — a state the single-row API cannot represent. Fully analyzed in `EQUATION_CONFORMANCE.md` §C7 and `IMPLEMENTATION_ASSUMPTIONS.md` A6.

---

## E8 — Summary table (implementation ⇒ equation)

| # | Implementation (verbatim locus) | Derived equation |
|---|---|---|
| E1 | `if not row[g]: deficit=1` | dᵢ = ¬gᵢ |
| E2 | `HARM_RISK>θ`, `StaleContext`, `¬TelemetryFresh` | d_harm, d_stale, d_telem |
| E3 | running OR into `deficit`; `return gamma_g=deficit` | Γ_G = max dᵢ (non-compensatory) |
| E4 | `"CLASS_1"/"GOODHART" in upper(ReasonCodes)` | Γ_class = 𝟙[class token present] |
| E5 | `pi = (deficit==0 and gamma_class==0)` | Π = 𝟙[max(Γ_G,Γ_class)=0]; decision |
| E6 | `TOKEN_VALID ∧ Sig ∧ Fresh ∧ ¬Stale` | ISB |
| E7 | `execute ∧ (¬TOKEN_VALID ∨ Γ_G≠0 ∨ Γ_class≠0 ∨ ISB=0)` | Unauthorized (single-row; no chain term) |

All eight equations were additionally confirmed by exhaustive enumeration — see `STATE_SPACE_VERIFICATION.md` (65,536 states, 0 field mismatches).
