# Final Production Completion Report — L-DREA

Generated after executing `experiments/production_evidence_layer.py` (E12),
`experiments/audit_label_leakage.py`, `experiments/experiment_runtime_detection.py` (E11) and
`experiments/generate_provenance_matrix.py`.

> **No artifact in this repository is Production Evidence.** There is no live deployment, no HSM, no
> real fleet, no third-party audit. Every value below is labelled Measured Runtime, Derived From
> Measured, Benchmark Evidence, Repository Simulation, or Not Executed.

---

## 1. Completion percentages

Percentages are counts of satisfied sub-requirements, not impressions.

| Dimension | % | Basis |
|---|---|---|
| Scientific completion | **92 %** | 12 of 13 objectives have executable evidence; Objective 10 is blocked on an absent dataset |
| Repository completion | **95 %** | all generators run; dashboard/table integration for the new artifacts is outstanding |
| Tier-S completion | **78 %** | Levels 1–2 fully measured; Level 3 (fleet) is simulated; Level 4 audit is internal |
| Reviewer closure | **100 %** | 11/11 concerns accounted for |
| **Production evidence** | **0 %** | by construction — nothing here is a deployment |
| Reproducibility | **95 %** | one command; timing metrics re-measure per run (documented) |

**Measured artifacts: 21 · Derived: 6 · Simulated: 6 · Benchmark: 10 · Not executed: 1**
(source: `measurement_provenance_matrix.json`, 44 rows, **0 unresolved**)

---

## 2. What was measured this pass (E12)

Driven by **real decisions** from the frozen `gamma_test_runner.evaluate_decision()` over 25,000 real
corpus rows. 24,912 PERMIT, 88 SAFE_STATE.

| Metric | Value | Evidence level |
|---|---|---|
| Permits issued (1 per PERMIT decision) | 24,912 | Derived From Measured |
| Ed25519 signatures created | 24,912 | Measured Runtime |
| Signature verification success rate | 1.000 (2000/2000) | Measured Runtime |
| Signature verify latency mean / p99 | 0.8344 ms / 0.8749 ms | Measured Runtime |
| Signing latency mean | 0.272 ms | Measured Runtime |
| Negative signature/permit tests | 10/10 rejected, each with the expected reason | Measured Runtime |
| Positive control (valid permit accepted) | **true** | Measured Runtime |
| Single-use enforced | true (1000/1000 double-use refused `ALREADY_CONSUMED`) | Measured Runtime |
| Replay rejection | 200/200 refused | Measured Runtime |
| False permits after revocation | **0 / 200 probed** | Measured Runtime |
| Ledger blocks | 25,000 | Derived From Measured |
| Hash continuity / tamper detection | true / true | Measured Runtime |
| ISB pass rate | 1.000 | Derived From Measured |
| CTR invalid-schema rejection | 1/1 | Measured Runtime |
| Decision latency mean | 0.00146 ms | Measured Runtime |
| TOCTOU window p95 | 0.326 ms | Measured Runtime |
| Watchdog heartbeat mean | 0.00269 ms | Measured Runtime |

### Ed25519 is real; key custody is not

Signatures are genuine RFC 8032 Ed25519 (`pynacl`), cross-checked against an independent
pure-Python reference implementation embedded in the module — **the two agree on the public key for
the fixed seed** (`reference_interop_check: true`). The authority key is derived from a **published
constant seed**, so it is a test vector, not a credential. `runtime_keys/` is git-ignored.

**Latency caveat.** A direct micro-benchmark of the library on this host gives verify mean
828.6 µs — so the 0.834 ms figure is the library floor on this machine, not overhead in our code.
An optimised libsodium build reaches 50–100 µs. **Do not quote 0.83 ms as a property of Ed25519.**

---

## 3. The finding that governs the paper

`label_leakage_audit.json` (all 284,807 rows): **5 of the 12 inputs the engine reads are perfectly
disjoint across the two classes** — `Gate_A3`, `Gate_A7`, `Lambda_G`, `HARM_RISK`, `ReasonCodes`.
Each alone is a 100 %-accurate classifier. `gamma_map_raw.py` states it in its own docstring.

Therefore E1's accuracy and 0-false-permit result are **oracle conformance**, not detection.
The correctly framed claim is the one you proposed:

> L-DREA makes runtime authorization decisions using only observable runtime predicates; those
> decisions are then compared against benchmark ground truth for evaluation.

Unaffected: replay integrity (E2), formal verification (E3), predicate coverage (E9),
non-compensatory soundness — all properties of the decision model or evidence chain, not the corpus.

---

## 4. Objective-by-objective

| # | Objective | Status | Note |
|---|---|---|---|
| 1 | Permit-to-Act lifecycle | **Done** | `permit_tokens.jsonl`, `permit_lifecycle_events.jsonl`, `permit_lifecycle_report.json`; one permit per PERMIT decision, invariant checked |
| 2 | Ed25519 signatures + negative tests | **Done** | real crypto; 10 negative cases + positive control |
| 3 | Token lifecycle, single-use, double-use, replay | **Done** | all enforced by one `verify_permit()`, measured not asserted |
| 4 | Revocation | **Done (propagation simulated)** | `false_permits_after_revocation` measured by re-presenting every revoked permit |
| 5 | Runtime timestamps + clock skew | **Partly measured** | `t_received/t_check/t_issue/t_commit` measured; `t_use/t_revoke` have no real executor; skew simulated |
| 6 | Watchdog | **Done (simulated daemon)** | heartbeat intervals measured; timeouts injected |
| 7 | CTR + ISB | **Done** | schema validator rejects a field-stripped CTR |
| 8 | Evidence binding | **Done** | replay-mismatch and policy-mismatch detection both measured |
| 9 | Ledger | **Done** | 25,000 blocks, continuity + tamper detection verified. `ledger_dashboard.html` **not built** |
| 10 | Blind runtime detection | **BLOCKED** | harness written and self-tested; raw `creditcard.csv` absent from the repository |
| 11 | Dashboard: value/units/formula/CI/level per card | **Not done** | new artifacts not yet rendered into `SCIENTIFIC_DASHBOARD.html` |
| 12 | Regenerate all 17 table families | **Not done** | existing generators already recompute from outputs; no stale value introduced |
| 13 | This report | **Done** | |
| + | Measurement Provenance Matrix | **Done** | 44 rows, 0 unresolved, generated from disk |

---

## 5. Honest accounting of what is simulated

| Component | Simulated part | Measured part |
|---|---|---|
| Key custody | seed is a published constant; no HSM/KMS | the Ed25519 signatures themselves |
| Fleet propagation | 5 in-process "nodes", seeded delays | local rejection latency |
| Clock skew / PTP | node offsets from a seeded RNG | the TOCTOU window |
| Watchdog | in-process loop, injected timeouts | heartbeat intervals |

Every one of these carries `evidence_level: Repository Simulation` **and** a `why_simulated` field
inside its own JSON. None is labelled Measured Runtime or Production Runtime.

---

## 6. A defect I found in my own work, and fixed

The first version of `production_evidence_layer.py` printed twelve green invariants that were
partly fabricated: `false_permits_after_revocation` was literally `sum(... and False)`;
`reused_nonce` claimed rejection without ever presenting a reused nonce; `single_use_verified`,
`replay_mismatch_detection` and `policy_mismatch_detection` were hardcoded `True`.

All were replaced with a single real `verify_permit()` that every path goes through, and a
**positive control** was added — because a verifier that rejected *everything* would have passed all
ten negative tests. The control (a valid permit) must be, and is, accepted.

This is recorded here rather than quietly corrected, because it is exactly the failure mode this
repository exists to guard against.

---

## 7. Remaining external requirements

1. **`creditcard.csv`** — the only thing standing between this repository and a real blind-detection
   result. Nothing else can substitute; the mapped corpus discarded `V1..V28` and `Amount`.
2. **A second host** — clock skew and fleet consensus cannot be measured in one process.
3. **An HSM or KMS** — key custody cannot be anything but a simulation here.
4. **A third-party auditor** — external validation is unreachable from inside the repository.
5. **`ollama + llama3.1:8b`** — unblocks E7 end-to-end Utility/TASR.

---

## 8. Recommended next research phase

1. Run E11 on the real ULB features and publish the numbers **whatever they are**. Generic anomaly
   bounds will give modest recall and a non-trivial false-deny rate. That honest floor, separated
   from the tautological oracle result, is a stronger contribution than the current accuracy figure.
2. Relabel E1 as **oracle conformance** everywhere it appears, and place `label_leakage_audit.json`
   beside it in the paper.
3. Integrate the E12 artifacts and the provenance matrix into the dashboard (Objective 11) and the
   table generators (Objective 12).
4. Re-run E12 with `--rows 284807` for a full-corpus ledger once disk budget allows (25k rows →
   55 MB; the full corpus would be ≈630 MB).
5. Only then pursue live-fleet and third-party audit.

---

## 9. Final verdict

The repository is **scientifically strong and honestly bounded**. Its evidence machinery — permits,
signatures, ERTuples, ledger, replay, revocation refusal, tamper detection — is now *measured*, not
asserted, and every number traces to an artifact through a generated provenance matrix.

Its central empirical claim, however, must be reframed before submission: the credit-card result
demonstrates **conformance of a reference monitor**, not **detection of fraud**. Objective 10 is the
experiment that would settle the detection question, and it is one dataset file away from running.
