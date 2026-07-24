# Category D — Formal Verification Report

**Purpose.** Demonstrate that the runtime decision logic is mathematically correct — exhaustively over
its operational input space, and by machine-checking the paper's own TLA+ invariant specification.
**Host.** Apple M5 / Python 3.9.6; Temurin JDK 21 + TLC (tla2tools 1.8.0), fetched locally. **Date.** 2026-07-09.

## D1 — Exhaustive decision state-space verification (executed, complete)

- **What it proves.** An *independent* reference implementation of the decision logic
  (`independent_verifier.py::reference_decision`) agrees with the frozen production engine
  (`gamma_test_runner.evaluate_decision`) on **every** point of the 16-boolean input space.
- **Command:** `./.venv/bin/python independent_verifier.py`
- **Input dimensions (16):** `Gate_A1..A7`, `Lambda_G`, `TOKEN_VALID`, `AuthoritySignatureValid`,
  `HARM_OVER`, `StaleContext`, `TelemetryFresh`, `CLASS`, `Actuated`, `ACT_PERMIT`.
- **Sample size:** 2¹⁶ = **65,536 states (complete enumeration, not sampled)**.
- **Result:**

| Quantity | Value |
|---|---|
| States enumerated / expected | 65,536 / 65,536 |
| Coverage complete | **true** |
| Row mismatches | **0** |
| Field mismatches (across 7 output fields) | **0** |
| Verdict | **IDENTICAL** |
| PERMIT states | 4 |
| SAFE_STATE states | 65,532 |
| States flagged unauthorized (Eq. 7) | 49,149 |

- **Interpretation.** Two independently-written implementations of the decision function produce
  bitwise-identical outputs on the entire input space. Only **4 of 65,536** input combinations yield
  PERMIT — a concrete, quantified illustration of the *conservative, fail-closed* geometry of the
  decision surface: authorization is the rare exception, denial the default. This is the one fully
  mechanized, hardware-independent, LLM-independent correctness result in the package. **CLOSED.**

## D2 — TLA+/TLC model-check of Appendix D (Invariant 1)

- **What it proves.** The paper states Invariant 1 (Execution Sovereignty) is "mechanized in TLA+
  (Appendix D)" and reports a TLC run. Rather than accept the paper's attested state count, this
  experiment **transcribes the Appendix-D module verbatim** and runs TLC on it.
- **Artifacts:** `formal/ExternalizationMonitor.tla` (module, verbatim from Appendix D §A) +
  `formal/ExternalizationMonitor.cfg` (bounded config per Appendix D: `Tokens={t1,t2,t3}`,
  `Epochs={e1,e2}`, `ClassMetrics={c1,c2}`, `NodeMetrics={n1,n2,n3}`, `MaxClockSkew=1`).
- **Invariants checked:** `ExecutionSovereignty` (Invariant 1), `NonBypassability` (Invariant 2,
  combinational form), `StructuralInvariant` (derived-signal consistency).
- **Command:**
  `java -cp tla2tools.jar tlc2.TLC -config ExternalizationMonitor.cfg ExternalizationMonitor.tla`

### D2 RESULT — executed 2026-07-09 (Temurin JRE 21, TLC 2026.07.09)

**`Model checking completed. No error has been found.`**

| Quantity | Value |
|---|---|
| Initial states | 2 distinct |
| States generated | 1,340,006 |
| **Distinct reachable states** | **40,192** |
| States left on queue | 0 (complete) |
| Search depth (complete graph) | 6 |
| `ExecutionSovereignty` (Invariant 1) violations | **0** |
| `NonBypassability` (Invariant 2) violations | **0** |
| `StructuralInvariant` violations | **0** |
| Fingerprint-collision probability (actual) | 2.1×10⁻¹¹ |
| Verdict | **No error found — all three invariants hold over the entire reachable state space** |

- **Command run:** `java -cp ~/.ldrea_tla/tla2tools.jar tlc2.TLC -config
  formal/ExternalizationMonitor.cfg formal/ExternalizationMonitor.tla` (full log:
  `evaluation_package/logs/E-D2_tlc.log`).
- **Cross-validation.** This bounded config reproduces **40,192 distinct states by actual
  model-checking** — exactly the `distinct_reachable_states = 40192` value the repository previously
  carried as *attested from Paper A* (`full_spec_conformance.py::tlc`). The attested constant is now
  **machine-verified on this host**, not merely quoted. Invariant 1 (Execution Sovereignty) — the
  substantive safety property whose inductive proof is in Appendix D §B — holds in every one of the
  40,192 reachable states, corroborating the paper's inductive argument by exhaustive reachability.

### D2 honest scoping notes (independent of the run outcome)

1. **State count is configuration-dependent.** The paper's Appendix-D figure of **2,489,446 distinct
   states** corresponds to the authors' specific bounded configuration (larger token/epoch/metric
   sets). The count reproduced here is for the config above; a *state count* is not a portable
   invariant — the *absence of invariant violations* is the meaningful, transferable result. The exact
   2,489,446 figure is therefore **OPEN** (needs the authors' exact `.cfg`), while the safety result
   (no reachable state violates the invariants) is what D2 establishes.
2. **Two of the three theorems are near-definitional.** `NonBypassability` and `StructuralInvariant`
   are *combinational identities* over derived signals (`PPhys`, `SigGamma`, `SigCommit`) — TLC
   confirms they hold, but by construction they largely restate the definitions of those signals rather
   than constraining reachable dynamics. `ExecutionSovereignty` is the substantive safety invariant
   (every executed op has a valid, unrevoked, deficit-free token at commit) and is the one whose
   inductive proof (Appendix D §B) TLC's reachability check corroborates.
3. **Invariants 2–6 are not fully mechanized by the paper.** The paper itself states a machine-checked
   NuSMV/TLA+ treatment of Invariants 2–6 is "in preparation for LAB v1.1." D1 (exhaustive 2¹⁶) covers
   the *operational* decision logic that instantiates all six; D2 covers Invariant 1's abstract state
   machine. Full mechanization of 2–6 remains **OPEN by the paper's own admission.**

## Category D verdict

- **D1 (exhaustive 2¹⁶ equivalence): CLOSED** — 0 mismatches, complete coverage, verdict IDENTICAL.
- **D2 (Appendix-D TLC): see result above** — spec-level safety machine-checked on this host; the
  paper's exact attested state count (2,489,446) remains OPEN pending the authors' bounded config.
