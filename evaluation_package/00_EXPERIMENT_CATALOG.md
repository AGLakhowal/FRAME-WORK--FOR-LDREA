# L-DREA Experimental Evaluation — Experiment Catalog

**Package owner:** Principal Research Scientist (experimental evaluation for IEEE Access submission)
**Execution date:** 2026-07-09
**Host:** Apple M5, 10 cores, 16 GB RAM, macOS (Darwin 25.5.0), Python 3.9.6 (`./.venv`)
**Repo HEAD at execution:** `763008a`
**Scope of this package:** validate the *architecture* (L-DREA) — correctness, determinism, safety,
reproducibility, scalability, domain-independence — against the paper's claims. Every number in this
package was produced by an experiment **executed in this session**, or is explicitly marked BLOCKED
with the exact missing dependency. No number is estimated, reused as a substitute, or fabricated.

> **Substrate scope (read first).** The paper's headline tables (Table 3/4/5, §IX latency) describe a
> **Tier-H hardware-in-the-loop** deployment (Xilinx Kintex-7 FPGA + SGX enclave + PCIe HSM, Xeon
> 8480+, N = 1.2×10⁶ LAB proposals, 360 k adversarial). **That hardware and the LAB v1.0 1.2 M
> scenario generator are not present in this repository.** This host is a **Tier-S software-only**
> stack. Everything below is therefore the *Tier-S architectural validation*: it validates the
> decision logic, invariants, determinism, fail-closed behaviour, and scaling of the same frozen
> engine the paper describes, on the evidence actually available (ULB corpus, AgentDojo, formal
> enumeration, concurrency/ablation microbenchmarks). Claims that *require* Tier-H hardware or the
> unreleased 1.2 M generator are marked BLOCKED and enumerated in `08_THREATS_TO_VALIDITY.md` and
> `10_REVIEWER_CLAIM_MATRIX.md`.

---

## Experiment index

| ID | Experiment | Category | Executes | LLM/HW req? | Primary artifact |
|----|------------|----------|----------|-------------|------------------|
| **A1** | LAB v1.0 base benchmark (ULB corpus) | A Runtime correctness | `gamma_test_runner.py` | none | `gamma_lab_v1_report.json` |
| **A2** | ConcurBench L1–L4 conformance | A | `concurbench_full.run()` | none | `concurbench_full_report.json` |
| **A3** | Financial stress scenarios | A | `stress_test.run()` | none | `stress_test_report.json` |
| **A4** | Fail-Closed Rate (FCR) | A | `fcr_test.run()` | none | `fcr_test_report.json` |
| **A5** | FULL_SPEC conformance (bands/AIS/SVR) | A | `full_spec_conformance.run()` | none | `full_spec_conformance_report.json` |
| **A6** | Independent replay-manifest verifier | A | `gamma_replay_verify.py` | none | log `E-D2_replay_verify.log` |
| **B1** | AgentDojo metric re-derivation (recorded traces) | B Agent governance | `stats_engine.write_reports()` | traces only | `evidence/agentdojo/statistics.json` |
| **B2** | AgentDojo FPR/FDR labeling (recorded traces) | B | `fpr_fdr_labeling.run()` | traces only | `evidence/agentdojo/fpr_fdr/fpr_fdr.json` |
| **B3** | AgentDojo **boundary FPR** (direct adjudication, no LLM) | B | `experiment_agentdojo_boundary_fpr.py` | **none** | `evidence/agentdojo_boundary/boundary_fpr.json` |
| **B4** | AgentDojo fresh episodes (permit/deny/entropy/overhead) | B | `run_audit.py` | **Ollama+llama3.1:8b** | BLOCKED |
| **C1** | Concurrency scaling 1→64 threads | C Performance | `concurrency_scaling.run()` | none | `evidence/concurrency/concurrency_scaling.json` |
| **C2** | Runtime profile (RCL + Replay planes) | C | `runtime_profile.run()` | none | `evidence/runtime_profile/runtime_profile.json` |
| **D1** | Exhaustive state-space verifier (2¹⁶) | D Formal | `independent_verifier.py` | none | `independent_verifier_report.json` |
| **D2** | TLA+/TLC model-check of Appendix D | D | `formal/ExternalizationMonitor.tla` | **Java+TLC** | see `06_FORMAL_VERIFICATION_REPORT.md` |
| **E1** | Component ablation (class-veto / Γ / auth-layer) | E Ablation | `experiment_ablation.py` | none | `fresh_evidence/ablation/ablation.json` |

---

## Per-experiment specification

Each experiment below follows the required IEEE structure: Purpose · Hypothesis · Setup · Input ·
Command · Sample size · Metrics · Result · Limitations · Output.

### A1 — LAB v1.0 base benchmark
- **Purpose.** Establish authorization correctness, fail-closed, class-veto, replay determinism and
  execution integrity on the real ULB credit-card corpus.
- **Hypothesis.** Every should-deny (adversarial) transaction transitions to SAFE_STATE (0 false
  permits); every decision is bitwise replay-deterministic; all 6 runtime invariants hold.
- **Setup / Input.** `GAMMA_G0_CREDITCARD_FULL_mapped.csv` (284,807 rows; 492 adversarial). Frozen
  engine `evaluate_decision`, θ = 0.5, design-effect 1.7 for cluster-corrected Wilson bounds.
- **Command.** `./.venv/bin/python gamma_test_runner.py --no-html --no-open`
- **Sample size.** N = 284,807 (nominal 284,315 · adversarial 492).
- **Metrics.** UER, FPR, FDR, RDR, class-veto effectiveness, TOCTOU violations, 6 invariants, latency.
- **Result (fresh).** UER 0/284,807; **FPR 0/492** (cluster-corr. Wilson95↑ 1.31×10⁻²);
  FDR 0/284,315; **RDR 100.0000%** (hash-chain links all OK); class-veto 492/492; TOCTOU 0;
  **6/6 invariants hold**; latency mean 0.0378 ms / p95 0.0434 / p99 0.0563; ~26,453 dec/s.
- **Limitations.** The corpus is 284,807 credit-card rows — a *different* experiment from the paper's
  Table 3 (1.2 M synthetic LAB items). The 492-row denominator gives a wide FPR bound (1.3×10⁻²), far
  from the paper's 8.3×10⁻⁶ (which needs the 360 k adversarial subset). This validates the *mechanism*,
  not the paper's sample size.
- **Output.** `gamma_lab_v1_report.json`, `gamma_summary.json`, `gamma_replay_manifest.jsonl`.

### A2–A5 — ConcurBench, stress, FCR, FULL_SPEC
- **Purpose.** Cross-check the same engine under ConcurBench's L1–L4 conformance model, adversarial
  financial scenarios, fail-closed-rate accounting, and the FULL_SPEC acceptance bands / AIS / SVR.
- **Commands.** `python -c "import concurbench_full as m; m.run(write=True)"` (and `stress_test`,
  `fcr_test`, `full_spec_conformance`).
- **Result (fresh).** ConcurBench `INTERNAL_PASS`; FCR overall 1.0 (0 fail-open events);
  FULL_SPEC `FULL_SPEC_CONFORMANT (Tier-S)`; stress weighted-effectively-tackled 78.4%.
- **Limitations.** ConcurBench L3 fleet-consistency and stress scenarios are **synthetic, in-script,
  deterministic** generators — they exercise the engine's response, not an external adversary. Verdict
  name `INTERNAL_PASS` is deliberately honest about this.
- **Output.** the four `*_report.json`.

### A6 — Independent replay-manifest verifier
- **Purpose.** Prove a third party can re-audit every decision from the manifest alone (hash-chain
  adjacency, evidence-quad ledger binding, self-consistency), independent of pandas/dataset/runner.
- **Command.** `./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl`
- **Result (fresh).** 284,807 records; adjacency failures 0; ledger-bind failures 0; consistency
  failures 0; manifest SHA-256 `1ce2a9e8…931da`. **RESULT: PASS.**

### B1/B2 — AgentDojo metric re-derivation (no LLM)
- **Purpose.** Re-derive permit/deny/stability/overhead and independent FPR/FDR from the 33 **recorded**
  AgentDojo episodes (workspace/banking/slack/travel) without regenerating episodes.
- **Commands.** `stats_engine.write_reports('…/audit_run/trace', outdir)`;
  `fpr_fdr_labeling.run('…/audit_run/trace', outdir)`.
- **Result (fresh).** 33 episodes → 14 adjudicated EEA decisions: permit rate 11/14 = 0.786
  (Wilson95 [0.524, 0.924]); denials 3/14; class-veto fired 0×; authorization stability 0.967;
  Γ-decision overhead mean 0.0216 ms. FPR/FDR: **malicious_actions = 0** in the executed corpus → FPR
  **undefined (n=0)**; FDR 0/5 (near-tautological, recognized-set defined).
- **Limitations (load-bearing).** 33 episodes ≠ the paper's pre-registered 79 tasks / 629 injections.
  Because the recorded agent never *proposed* an attacker-targeted EEA, FPR is undefined from traces —
  this is exactly why B3 exists.
- **Output.** `evidence/agentdojo/statistics.json`, `.../fpr_fdr/fpr_fdr.json`.

### B3 — AgentDojo boundary FPR (direct adjudication, no LLM) — **new experiment**
- **Purpose.** Close the B1/B2 FPR gap: the paper's soundness claim is a property of the *boundary*, so
  test the boundary directly against the **full real adversarial corpus** without an LLM.
- **Hypothesis.** No genuinely-foreign attacker target (an identifier absent from the environment's
  recognized set) is ever PERMITTED by the frozen boundary.
- **Setup.** For every injection task in all 4 AgentDojo v1 suites (27 injections, 97 user tasks →
  629 pairs), load the suite's default env **with the injection applied**, extract attacker target
  identifiers from the injection GOAL (IBAN/email/URL/@user), construct the mediated tool call that
  externalizes to each target, and adjudicate through the **exact frozen components**
  `GammaGovernedRuntime.run_function` uses (`classify → tool_binding → PredicateEvaluator.evaluate →
  GammaBridge.decide`) — only side-effect execution is skipped.
- **Command.** `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py`
- **Sample size.** 70 attacker-target adjudications (62 genuinely-foreign · 8 to already-recognized
  identifiers).
- **Result (fresh).** **FPR = 0/62 on genuinely-foreign targets** (Wilson95↑ 5.83×10⁻²), 0 across all
  4 suites. The 8 permits all target identifiers already in the env recognized set (legitimate contacts
  / pre-seeded URLs the GOAL merely *names*, e.g. `lily.white@gmail.com`, `security@facebook.com`) —
  correct-by-policy, not false permits.
- **Limitations (honest).** (i) Recognition-based gating cannot distinguish a *known contact
  weaponized as an exfil sink* — a documented limitation of recognized-set authorization, surfaced by
  the 8 recognized-identifier permits. (ii) 8 mediated tools are `structural_only` (no recognition
  predicate: `delete_file`, `update_password`, …); attacker GOALs targeting those are not identifier-
  gated. (iii) This measures the *boundary* (FPR), not agent susceptibility (TASR) — B4 is still needed
  for the end-to-end pre-registered numbers.
- **Output.** `evidence/agentdojo_boundary/boundary_fpr.json`, `.md`, `rows.jsonl`.

### B4 — AgentDojo fresh episodes — **BLOCKED**
- **Missing dependency.** `ollama` + `llama3.1:8b` (not installed; `ollama not found`).
- **Rerun.** `brew install ollama && ollama serve & ollama pull llama3.1:8b` then
  `agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking
  slack travel --outdir agentdojo_integration/audit_run`.
- **Expected outputs.** fresh `execution_trace.jsonl` per episode → `statistics.json` with
  Utility/TASR-augmented permit/deny/entropy/stability/overhead/replay over the full 79/629 corpus.

### C1 — Concurrency scaling 1→64 threads
- **Purpose.** Show safety invariants hold under concurrency and characterize throughput/latency/RSS.
- **Command.** `python -c "from agentdojo_integration.audit import concurrency_scaling as c;
  c.run('evaluation_package/evidence/concurrency', 200000, [1,2,4,8,16,32,64])"`
- **Sample size.** 200,000 decisions per thread level × 7 levels.
- **Result (fresh).** At every level: **all-authorization-correct, ledger-consistent, replay-consistent,
  0 false permits, 0 false denials.** Throughput **degrades** with threads (227,771 dec/s @1 →
  48,867 @64; speedup 0.215× @64) — pure-Python decision path is GIL-bound (honestly reported).
- **Limitations.** Python-threads model; not a multi-process or Tier-H throughput claim. Correctness is
  the invariant; throughput is host/GIL-dependent.
- **Output.** `evidence/concurrency/concurrency_scaling.{json,csv,md,svg}`.

### C2 — Runtime profile (RCL + Replay planes)
- **Command.** `python -c "from agentdojo_integration.audit import runtime_profile as r;
  r.run('evaluation_package/evidence/runtime_profile', 5000)"`
- **Result (fresh).** Full pipeline 0.2379 ms/row; end-to-end incl. replay 0.2481 ms/row (5,000 rows).
- **Limitations.** µs-scale timers are noise-dominated and host-dependent; report with host always.

### D1 — Exhaustive state-space verifier (2¹⁶)
- **Purpose.** Prove an independent reference implementation of the decision logic agrees with the
  frozen engine on **every** input state.
- **Command.** `./.venv/bin/python independent_verifier.py`
- **Sample size.** 2¹⁶ = 65,536 states (complete enumeration).
- **Result (fresh).** `total_field_mismatches: 0`, `coverage_complete: true`, verdict **IDENTICAL**.

### D2 — TLA+/TLC model-check of Appendix D
- **Purpose.** Machine-check the paper's own Invariant-1 spec (Execution Sovereignty), plus
  Non-Bypassability and the Structural invariant, rather than accepting the attested TLC counts.
- **Artifact.** `formal/ExternalizationMonitor.tla` + `.cfg` — transcribed **verbatim** from Appendix D.
- **Status.** See `06_FORMAL_VERIFICATION_REPORT.md` for the executed TLC result and configuration.

### E1 — Component ablation
- **Purpose.** Show each structural control (class-veto, non-compensatory Γ, authorization layer)
  causally accounts for denials that its removal converts to permits.
- **Command.** `./.venv/bin/python experiment_ablation.py`
- **Sample size.** 60,000 deterministic decisions per config.
- **Result (fresh).** baseline 0 leaked permits; **−class-veto → 15,000 leaked**; **−non-compensatory Γ
  → 15,000 leaked**; **−authorization-layer → 45,000 leaked**. Replay consistent in every config.
- **Limitations.** Leak-count on a synthetic deficit workload (Tier-S analogue of paper Table 4) — **not**
  the paper's hardware-measured FPR on the 360 k LAB adversarial subset.
- **Output.** `fresh_evidence/ablation/ablation.{json,csv}`, `ablation_log.jsonl`.
