# THREATS TO VALIDITY (auto-generated)

Each threat references actual experiments and their live-resolved status. Generated from the executed artifacts; not generic boilerplate.

## Construct validity
- **Threat.** Do the experiments measure runtime authorization correctness rather than fraud detection?
- **Mitigation (evidence).** The ULB dataset is used only as a transaction stream; the measured quantity is the authorization decision vs the golden-trace expected outcome (E1 confusion matrix), not a fraud label. The independent 2^16 verifier (E3) confirms the measured decision equals the specified decision function.
- **Residual risk.** Residual: ground truth for E1/E5 is repo-defined. Mitigated by the externally-authored AgentDojo adversarial corpus (E7, boundary FPR status Partially Supported).
- **Evidence experiments.** E1, E3, E7

## Internal validity
- **Threat.** Could the observed safety be an artifact of a trivial harness (e.g. deny-everything)?
- **Mitigation (evidence).** E8 includes a positive control (a clean actuated proposal PERMITs: True), and E1 shows 0 false denials on 284,315 should-permit rows — the engine is not trivially denying. Faults are injected only into the harness input; the engine and verifier are unchanged.
- **Residual risk.** Residual: deterministic constructed workloads (E5/E8) exercise specified distributions, not arbitrary ones. Mitigated by exhaustive E3 coverage of the whole input space.
- **Evidence experiments.** E1, E3, E8

## External validity
- **Threat.** Do results generalize beyond one dataset / host?
- **Mitigation (evidence).** Two domains are covered — financial transactions (E1) and autonomous-agent tool calls (E7). The one-command harness makes cross-host re-execution trivial; correctness results are host-invariant.
- **Residual risk.** Residual: generality rests on two domains. E7 executes offline (no LLM, no API credential); only the optional agent-side Utility/TASR arm is unmeasured, and no L-DREA claim depends on it. Boundary soundness status Partially Supported.
- **Evidence experiments.** E1, E7

## Statistical-conclusion validity
- **Threat.** Are zero-event claims statistically justified given the sample sizes?
- **Mitigation (evidence).** The statistics report gives Wilson 95% upper bounds and rule-of-three bounds for every zero-event proportion (E1 FPR/UER, E7 boundary FPR, E8 robustness). Because the engine is deterministic, intervals are interpreted as input-space coverage, and p-values are not invented for deterministic equalities.
- **Residual risk.** Residual: the ULB should-deny denominator (492) yields a wide FPR bound (~1e-2); the unauthorized-execution bound over 284,807 rows is ~1e-5. Reported as bounds, not points.
- **Evidence experiments.** E1, E7, E8

## Ecological validity
- **Threat.** Do the fault scenarios reflect realistic runtime failures?
- **Mitigation (evidence).** E8 injects 16 fault families spanning missing/delayed/corrupted/conflicting predicates, stale context, missing auth context, clock skew, replay/ledger corruption, partial loss, reordering, duplication, timeout, network delay, partial failure, and predicate races — all resolved fail-closed (0 false permits; every integrity corruption detected).
- **Residual risk.** Residual: faults are modeled at the decision/integrity boundary, not via a live distributed deployment; throughput under real load is GIL-bound (C9, disclosed).
- **Evidence experiments.** E8, E4
