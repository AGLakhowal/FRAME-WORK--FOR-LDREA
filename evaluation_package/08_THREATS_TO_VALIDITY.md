# Threats to Validity & BLOCKED Experiments

This document states, without softening, every gap between the paper's claims and the evidence
generatable on this host, and for each BLOCKED item names the **exact** missing dependency, the
install/provide step, the rerun command, and the expected output. **No BLOCKED item was worked around
with a fabricated or substituted number.**

## 1. Construct validity — does the Tier-S evidence measure what the paper claims?

- **Substrate mismatch (the load-bearing threat).** The paper's headline results (Tables 3–5, §IX
  latency) are for a **Tier-H hardware-in-the-loop** deployment: Xilinx Kintex-7 FPGA + SGX enclave +
  PCIe HSM on a Xeon Platinum 8480+, N = 1.2×10⁶ proposals, 360,000 adversarial. **This repository is a
  Tier-S software-only stack.** Consequently every experiment in this package validates the *decision
  logic, invariants, determinism, and fail-closed behaviour of the frozen engine* — not the Tier-H
  substrate, the HSM handshake latency, or the 1.2 M sample size. Treat the package as **architectural
  validation of the mechanism at Tier-S**, explicitly not a reproduction of the Tier-H tables.
- **Author-controlled ground truth.** LAB v1.0 ground truth, the deficit workloads (ablation, FCR,
  ConcurBench), and the stress scenarios are all author/repo-defined and deterministic. They test the
  engine's response to *specified* inputs, not an adversary the authors did not anticipate. The
  AgentDojo boundary probe (B3) is the one experiment using an **externally-authored** adversarial
  corpus.
- **Recognition-set gating limitation (surfaced by B3).** Recognized-set authorization cannot flag a
  *legitimate contact weaponized as an exfil sink*; it also does not gate the 8 `structural_only`
  mediated tools (`delete_file`, `update_password`, …). Both are documented in
  `04_AGENTDOJO_EVALUATION_REPORT.md` §B3, not hidden.

## 2. Internal validity

- **µs-scale timing is noise-dominated and host-dependent.** Latency/throughput numbers differ
  materially across fresh runs (e.g. concurrency @1 thread: 227,771 dec/s this session vs. 390,766 in a
  prior artifact — 0.58×). No timing figure is reported without its host. Correctness/safety figures
  (0 FP/0 FD, RDR 100%, 0 formal mismatches) reproduce **exactly**.
- **Concurrency model.** C1 uses Python threads on the GIL-bound path; it demonstrates *safety* under
  concurrency, and honestly reports that *throughput does not scale up* (P2, NEGATIVE). It is not a
  multi-process or Tier-H throughput claim.

## 3. External validity / generalization

- **Two domains, not many.** Domain-independence is evidenced on exactly two domains (ULB credit-card
  financial rows; AgentDojo agent tool-calls). This supports "substrate-neutral / domain-independent"
  as *demonstrated on two*, not as a universal claim.
- **33 recorded AgentDojo episodes** ≠ the pre-registered 79 tasks / 629 injections; B1/B2 metrics are
  bounded to those 33. B3 covers all 27 injection tasks at the boundary level.

## 4. Statistical-conclusion validity

- **Wide zero-event bounds.** With 492 should-deny rows the FPR Wilson95 upper bound is 1.31×10⁻² — far
  from the paper's 8.3×10⁻⁶, which requires the 360,000-item adversarial subset. The *rate* (0) matches;
  the *bound* is honestly weaker on this smaller denominator.
- **Cluster correction** uses DE = 1.7 (matching the paper); N_eff = N/DE.

---

## 5. BLOCKED experiments — exact dependency, install, rerun, expected output

### B1-blocked — LAB v1.0 primary + ablation at paper scale (Tables 3, 4, 5; §IX latency/adaptive)
- **Missing:** (i) the **LAB v1.0 scenario generator + 7-family adversarial-mutation library** that emit
  the 1.2 M proposals / 360,000 adversarial subset — **not present in this repo** (confirmed by full
  tree search; only a LAB-class *classifier* `derive_lab_class` exists, no generator). (ii) **Tier-H
  hardware** (Kintex-7 FPGA, SGX host, PCIe HSM) for the substrate-tier FPR rows and the 54.3 ms
  (19.3 ms HSM handshake) latency.
- **Provide:** the Appendix-C generator artifact (unreleased) + Tier-H hardware, **or** a documented
  Tier-S emulation of the 360 k adversarial subset.
- **Rerun (once generator exists):** `python <lab_generator> --n 1200000 --adv 360000 --seeds <file>` →
  feed to `evaluate_decision` → `metrics_engine` (FPR/RDR with cluster-corrected Wilson bounds).
- **Expected output:** `lab_v1_primary.json` (Table 3), `lab_v1_ablation.json` (Table 4/5).
- **Tier-S analogues that DID run:** A1 (FPR 0/492), E1 (leak-count ablation), A2 adaptive-attacker
  (0/11,808). These validate the mechanism and effect-ranking, not the paper's absolute FPR%.

### B2-blocked — AgentDojo fresh episodes (Utility / TASR, paper §IX-E) — *optional, agent-side only*
- **Scope:** This blocks **agent-side** Utility / TASR only. It does **not** block E7. Every L-DREA
  governance metric (FPR, FDR, replay determinism, predicate pass rate, evidence-quad completeness,
  hash-chain and ledger integrity, latency) is measured offline with no model in the loop — see
  `experiments/agentdojo/e7_metrics.json` (verdict `PASS`). External validation is **COMPLETE**.
- **Missing:** a running local `ollama` server + `llama3.1:8b` (host: `ollama not found`; port 11434
  refuses connection). **No hosted-provider credential is required, or accepted, for this arm.**
- **Install:** `brew install ollama && ollama serve & ollama pull llama3.1:8b`
- **Rerun:** `export LOCAL_LLM_PORT=11434; agentdojo_integration/.venv/bin/python
  agentdojo_integration/run_audit.py --suites workspace banking slack travel
  --outdir agentdojo_integration/audit_run`
- **Expected output:** fresh `execution_trace.jsonl` per episode (full 79/629) → `statistics.json`
  (Utility, TASR, permit/deny/entropy/stability/overhead/replay); then re-run B1/B2/B3 for episode-level
  FPR/FDR. **Tier-S analogue that DID run:** B3 boundary FPR 0/62 (no LLM).
- **Provenance note:** the 33 episodes already on disk were themselves generated locally with Ollama
  (`llama3.1:8b` via AgentDojo's `vllm_parsed` provider), so this arm has been executed historically —
  just not on this host.

### B4-future — AgentHarm second oracle (§IX-F pre-registration) — *never implemented*
- **Status:** pre-registered in the design document but **never implemented or executed**. There is no
  AgentHarm code in this repository.
- **Disposition:** reclassified as **optional future work**, not a blocked experiment. It is disclosed
  here rather than dropped silently, because removing a pre-registered arm without disclosure would be
  selective reporting.
- **Rationale for de-scoping:** this project evaluates runtime governance, authorization, execution
  integrity and runtime evidence. AgentDojo is the appropriate independent oracle for that. AgentHarm
  targets harmful-behaviour elicitation, a property of the *agent* rather than of the reference
  monitor. No claim in this repository depends on it.

### B3-blocked — Appendix-D TLC exact R4-text state count (2,489,446 states)
- **Executed part (NOT blocked):** this host fetched Temurin JRE 21 + TLC and **model-checked the
  transcribed Appendix-D module** — result `No error has been found`, **40,192 distinct states**, all
  three invariants (Execution Sovereignty / Non-Bypassability / Structural) with **0 violations** (see
  `06_FORMAL_VERIFICATION_REPORT.md` D2; log `logs/E-D2_tlc.log`). This reproduces the repository's
  attested Paper-A count of 40,192 **by actual model-checking**.
- **Still OPEN:** the R4 *manuscript text* cites 2,489,446 distinct states, corresponding to a **larger
  bounded config** than the one documented here. Only that specific count depends on the authors' exact
  token/epoch/metric-set sizes.
- **Provide:** the authors' larger `ExternalizationMonitor.cfg` from the LAB v1.0 artifact.
- **Rerun:** `java -cp ~/.ldrea_tla/tla2tools.jar tlc2.TLC -config <authors.cfg> ExternalizationMonitor.tla`
- **Expected output:** TLC console reporting `2,489,446` distinct states and `No error has been found`.

---

## Stop condition — status

**Met, in the sense the task defines it:** every scientific claim is backed **either** by an executed
experiment with a fresh generated artifact (Categories A, D1, E; boundary-FPR in B; concurrency/profile
in C), **or** by an explicitly documented, reproducible reason — exact missing dependency + install +
rerun command + expected output — why the evidence cannot be generated on *this* host (B1/B2/B3-blocked
above). No claim is left both unsupported and undocumented; no number is fabricated or substituted.
