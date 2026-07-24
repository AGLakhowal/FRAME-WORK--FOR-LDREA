# EQUATION_CONFORMANCE.md

**Phase 3 — Part C: branch-by-branch proof that `evaluate_decision()` implements exactly the
FULL_SPEC / paper equations, with no skipped logic.**

Two conformance obligations are discharged:
- **(C-A)** `evaluate_decision` (single-row) ≡ paper equations (README §7/§8, §IV-B, Eq. 7).
- **(C-B)** single-row `evaluate_decision` ≡ vectorized `run_benchmark` LLC (the batch twin), on the
  authorization decision Π/decision.

Both are backed by exhaustive enumeration (`independent_verifier.py`, 65,536 states, 0 mismatches).

Legend: **PAPER** = specification equation; **CODE** = exact source; **⊢** = proof.

---

## C1. Node deficit branch

- **PAPER:** dᵢ = 1 when node predicate gᵢ fails.
- **CODE** ([:142-145](gamma_test_runner.py#L142-L145)): `for g in NODE_GATE_COLS: if not row[g]: deficit=1; deficit_count+=1`.
- **⊢** The iteration domain is exactly `NODE_GATE_COLS` = the 10 paper node predicates (verified equal to `independent_verifier.REF_GATES` at runtime). Each falsy gate raises `deficit`. No gate is skipped; no extra gate is added. ∎ CONFORMS.

## C2. Threshold/environmental deficit branch

- **PAPER:** dᵢ = max(0, mᵢ − θᵢ); HARM admissible iff HARM_RISK ≤ θ; stale context and stale telemetry are deficits.
- **CODE** ([:146-154](gamma_test_runner.py#L146-L154)): `HARM_RISK > harm_threshold`, `StaleContext`, `not TelemetryFresh`.
- **⊢** For a scalar measure, `max(0, m−θ) > 0 ⇔ m > θ`; the strict `>` matches "admissible iff ≤ θ". θ is the *parameter* `harm_threshold` (default 0.5, README §8), not a magic constant. Two boolean deficits map directly. ∎ CONFORMS.

## C3. Γ_G aggregation branch (non-compensatory)

- **PAPER:** Γ_G = maxᵢ dᵢ; ANY deficit ⇒ Γ_G = 1; non-compensatory.
- **CODE:** `deficit` initialized 0 ([:140](gamma_test_runner.py#L140)); monotonically set to 1 by C1/C2; returned as `gamma_g` ([:171](gamma_test_runner.py#L171)).
- **⊢** `deficit` is the OR (=max on {0,1}) of all 13 binary deficits. **Crucially, no branch decrements `deficit`** — verified by inspection of lines 140-169: the only writes to `deficit` are `= 1`. Hence a clean predicate cannot compensate a dirty one. This is exactly non-compensatory max-aggregation. ∎ CONFORMS. (Also the code witness for Corollary 2.)

## C4. Γ_class veto branch

- **PAPER:** Γ_class = 1 iff ReasonCodes ∈ {CLASS_1, GOODHART}; forces SAFE_STATE even if all node predicates concur.
- **CODE** ([:156-157](gamma_test_runner.py#L156-L157)): `gamma_class = 1 if ("CLASS_1" in reason or "GOODHART" in reason) else 0` with `reason = str(...).upper()`.
- **⊢** Substring test on upper-cased ReasonCodes. Independent of `deficit`; enters Π as a separate conjunct (C5), so it can veto even when Γ_G=0. ∎ CONFORMS.

## C5. Π decision branch

- **PAPER:** `PERMIT iff Π = 1`, `Π = [max(Γ_G, Γ_class) == 0]`.
- **CODE** ([:159](gamma_test_runner.py#L159), [:176](gamma_test_runner.py#L176)): `pi = 1 if (deficit==0 and gamma_class==0) else 0`; `decision = "PERMIT" if pi==1 else "SAFE_STATE"`.
- **⊢** `(Γ_G=0 ∧ Γ_class=0) ⇔ max(Γ_G,Γ_class)=0` on {0,1}. Decision is a total function of Π with no third branch (proved exhaustively — only PERMIT / SAFE_STATE ever emitted; `STATE_SPACE_VERIFICATION.md`). ∎ CONFORMS.

## C6. ISB branch

- **PAPER (§V-B):** interpretive sufficiency = signatures ∧ freshness ∧ ¬stale.
- **CODE** ([:160-165](gamma_test_runner.py#L160-L165)): `TOKEN_VALID ∧ AuthoritySignatureValid ∧ TelemetryFresh ∧ ¬StaleContext`.
- **⊢** Direct 4-way conjunction; matches the paper term. ∎ CONFORMS.

## C7. Eq. 7 (unauthorized) branch — CONFORMS WITH ONE DOCUMENTED SCOPE DIFFERENCE

- **PAPER (Eq. 7):** `Unauth = Execute ∧ (¬Valid ∨ max(Γ_G,Γ_class)>0 ∨ ISB=0 ∨ hash-chain link broken)`.
- **CODE single-row** ([:166-169](gamma_test_runner.py#L166-L169)): `execute ∧ (¬TOKEN_VALID ∨ deficit≠0 ∨ gamma_class≠0 ∨ isb==0)` — **four** disjuncts.
- **CODE vectorized** ([:977-987](gamma_test_runner.py#L977-L987)): the same four **plus** `| (~DerivedChainLinked)` — **five** disjuncts (full Eq. 7).
- **⊢** The single-row form omits the *hash-chain link broken* disjunct. This is **structural**, not an error: `evaluate_decision(row, θ)` receives a single decision record with **no `HASH_prev`/`HASH_current`**, so chain linkage is undefined at that scope. On the domain the single-row API can represent (chain always trivially "linked"), the two forms are logically identical. The full Eq. 7 with the chain term is enforced on the corpus by the vectorized path, which reported `unauthorized_execution_count: 0` and `replay_divergence_count: 0` over 284,807 rows (`gamma_summary.json`).
- **Verdict:** **CONFORMS on decision (Π); Eq. 7 single-row is a proper scope-restriction of Eq. 7.** Logged as observation A6.

---

## C-B. Single-row ≡ vectorized equivalence (Π / decision)

| Quantity | single-row `evaluate_decision` | vectorized `run_benchmark` | Identical? |
|---|---|---|---|
| Γ_G | OR over 13 deficits ([:140-158](gamma_test_runner.py#L140-L158)) | `deficits.max(axis=1)` over the same 13 columns ([:914-922](gamma_test_runner.py#L914-L922)) | **Yes** |
| Γ_class | substring on upper(ReasonCodes) ([:157](gamma_test_runner.py#L157)) | `str.contains("CLASS_1")|str.contains("GOODHART")` on upper ([:929-932](gamma_test_runner.py#L929-L932)) | **Yes** |
| Π | `deficit==0 and gamma_class==0` | `(GammaG==0)&(GammaClass==0)` ([:935-937](gamma_test_runner.py#L935-L937)) | **Yes** |
| decision | `PERMIT if pi else SAFE_STATE` | `map({1:PERMIT,0:SAFE_STATE})` ([:938](gamma_test_runner.py#L938)) | **Yes** |
| ISB | 4-way ∧ | identical 4-way ∧ ([:942-947](gamma_test_runner.py#L942-L947)) | **Yes** |
| unauthorized | 4 disjuncts | 5 disjuncts (+chain) | Scope diff (C7) |

**⊢** Column-for-column the deficit set, aggregation, veto, and Π rule are the same. The independent verifier confirms the single-row engine matches the from-scratch equations on **all 65,536** states with **0** field mismatches; the vectorized twin uses the identical column formulas. Therefore Π/decision are equivalent across both engines. ∎

---

## C-Result

| Branch | Paper eq | Verdict |
|---|---|---|
| C1 node deficit | dᵢ=¬gᵢ | CONFORMS |
| C2 threshold deficit | max(0,m−θ) | CONFORMS |
| C3 Γ_G | max, non-compensatory | CONFORMS |
| C4 Γ_class | class veto | CONFORMS |
| C5 Π / decision | Π=[max=0] | CONFORMS |
| C6 ISB | sig∧fresh∧¬stale | CONFORMS |
| C7 Eq. 7 | 5-disjunct | CONFORMS on Π; single-row = documented scope-restriction |

**No branch of `evaluate_decision` was skipped in this proof. No logic outside the seven branches exists in the function (lines 140-178 fully covered).** Overall: **the decision (Π, PERMIT/SAFE_STATE) is proven identical to the specification; the only divergence is the single-row Eq. 7 diagnostic's absent cross-row chain term, which cannot affect any authorization decision.**
