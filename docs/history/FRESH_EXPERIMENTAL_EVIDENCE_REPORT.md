# FRESH_EXPERIMENTAL_EVIDENCE_REPORT.md

**Lead Research Engineer — fresh-execution evidence for IEEE Access submission.**
Every value below comes from an experiment **executed in this session** (2026-07-09), not copied from
a prior JSON. Where an experiment could not run, the exact missing dependency is named and **no value
is fabricated, estimated, or substituted from old artifacts.**

Host: Darwin arm64, 10 cores, 16 GB RAM, Python 3.9.6 (`./.venv`). No Java, no Ollama, no FPGA/SGX/HSM.

---

## 0. THE LOAD-BEARING FINDING (read first)

**The paper's headline empirical tables describe experiments that do not exist in this repository.**
The paper (all three PDFs) reports a **hardware-in-the-loop Tier-H deployment** — Xilinx Kintex-7
FPGA + SGX enclave + PCIe HSM secure element on a Xeon Platinum 8480+ — running **N = 1.2 × 10⁶**
action proposals with a **360,000-item LAB v1.0 adversarial-mutation subset**. This repository is a
**software-only (Tier-S)** stack: a 284,807-row credit-card corpus + an AgentDojo interposition.

Consequently the following paper tables/numbers **cannot be produced here from raw experiment**, and
per the "scientific honesty" rule they are reported as **BLOCKED with exact missing dependency** (§13–15),
not populated:

| Paper artifact | Blocking reason |
|---|---|
| Table 8/3 (FPR 0/360,000; RDR 99.9994%) | No LAB v1.0 1.2 M scenario generator in repo; no Tier-H hardware |
| Table 9/4 (substrate + component FPR ablation: Tier-T 0.0058%, Tier-S 0.63%, −Γ 1.72%, −class-veto 3.11%) | Same generator + hardware absent; FPR requires the 360 k labeled adversarial subset |
| §IX latency 54.3 ms (19.3 ms **HSM handshake**) | No HSM / secure element; software path is µs-scale, not comparable |
| §IX-J adaptive attacker (120,000 attempts) | No LAB adaptive generator |
| Table 12/5 (head-to-head per-category FPR vs baselines) | Same 360 k adversarial subset + baseline installs absent |
| Table 11 (AgentDojo fresh episodes) | Requires Ollama + llama3.1:8b (not installed) |
| Appendix D (TLC: 2,489,446 states) | No Java runtime; no `.tla`/`.cfg` file in repo |

What **can** be freshly measured on the Tier-S software stack was executed and is reported in §1.

---

## 1. EXPERIMENTS EXECUTED (fresh)

| # | Experiment | Command | Duration | Fresh outputs |
|---|---|---|---|---|
| E1 | Concurrency scaling (1–64 threads) | `python -c "concurrency_scaling.run('fresh_evidence/concurrency', 200000, [1,2,4,8,16,32,64])"` | 21 s | `fresh_evidence/concurrency/*.{json,csv,md,svg}` |
| E2 | Component ablation (Tier-S path) | `python experiment_ablation.py` | 3 s | `fresh_evidence/ablation/ablation.{json,csv}` + `ablation_log.jsonl` |
| E3 | Runtime-profile (RCL + Replay planes) | `python -c "runtime_profile.run('fresh_evidence/runtime_profile', 5000)"` | 1 s | `fresh_evidence/runtime_profile/runtime_profile.{json,md}` |
| E4 | Formal verifier (exhaustive 2¹⁶ state space) | `python independent_verifier.py` | ~2 s | `independent_verifier_report.json` |

---

## 2. E1 — CONCURRENCY SCALING (fresh, no LLM, no hardware)

Frozen decision path `GammaBridge.decide → evaluate_decision`; 200,000 decisions/level. Reference
ledger `3034e5e6…`. **Every level: authorization-correct, ledger-consistent, replay-consistent,
0 false permits, 0 false denials.**

| threads | throughput (dec/s) | p50 (ms) | p95 (ms) | p99 (ms) | queue-delay mean (ms) | auth correct | FP | FD |
|---:|---:|---:|---:|---:|---:|:--:|--:|--:|
| 1 | 234,087 | 0.00229 | 0.00254 | 0.00279 | (see json) | ✓ | 0 | 0 |
| 2 | 229,370 | 0.00233 | 0.00254 | 0.00308 | | ✓ | 0 | 0 |
| 4 | 215,529 | 0.00233 | 0.00275 | 0.00367 | | ✓ | 0 | 0 |
| 8 | 70,929 | 0.00262 | 0.00446 | 0.00512 | | ✓ | 0 | 0 |
| 16 | 53,768 | 0.00329 | 0.00467 | 0.00554 | | ✓ | 0 | 0 |
| 32 | 48,718 | 0.00350 | 0.00475 | 0.00567 | | ✓ | 0 | 0 |
| 64 | 50,053 | 0.00342 | 0.00492 | 0.00675 | | ✓ | 0 | 0 |

Throughput **degrades** with threads — the pure-Python path is GIL-bound, consistent with the repo's
own honest framing. Safety (correctness / ledger / replay / 0 FP / 0 FD) holds at **every** level.

## 3. E2 — COMPONENT ABLATION (fresh; Tier-S software analogue of Table 9/10)

Workload: 60,000 deterministic decisions, controlled deficit mix (clean / single-node / class-veto-only
/ multi). Metric: **leaked permits** = denials the removed control converts to permits vs the full
baseline (the causal, measurable safety-regression signal on this stack).

| Config (removed control) | permits | leaked permits | leaked rate (Wilson95↑) | throughput (dec/s) | mean latency (ms) | p99 (ms) | replay |
|---|---:|---:|---|---:|---:|---:|:--:|
| baseline (full L-DREA) | 15,000 | 0 | — | 669,437 | 0.00134 | 0.00150 | ✓ |
| − class-level veto | 30,000 | **15,000** | 0.250 (≈0.253) | 661,098 | 0.00137 | 0.00150 | ✓ |
| − non-compensatory Γ (→ weighted-sum τ=0.15) | 30,000 | **15,000** | 0.250 | 796,455 | 0.00111 | 0.00125 | ✓ |
| − authorization layer (permit all) | 60,000 | **45,000** | 0.750 | 4,094,352 | 0.00011 | 0.00017 | ✓ |

**Interpretation (honest):** on this stack the class veto and the non-compensatory Γ each *causally*
account for 15,000/60,000 denials that a compensatory or veto-free rule would leak; removing
authorization leaks everything. This is the **software** analogue of the paper's Table-9 FPR deltas —
it is a leak-count on a synthetic deficit workload, **not** the paper's hardware-measured FPR on the
360 k LAB adversarial subset (that experiment is BLOCKED, §13). Full per-config latency distributions
(n, mean, median, std, min, max, p50/p90/p95/p99, bootstrap 95% CI) are in `ablation.json`.

## 4. E3 — RUNTIME PROFILE (fresh; the actual paper Table-10 RCL/Replay planes)

5,000 rows; 35,000 RCL calls; timers wrap the frozen `FreshnessClock`+`CommitActuateJournal` (Runtime
Context) and `write_replay_manifest` (Replay). **Fresh values:**

| Stage | ms/row (fresh) | % of end-to-end |
|---|---:|---:|
| Runtime Context (RCL) | 0.01609 | 6.74 % |
| Replay (ERTuple manifest) | 0.01101 | 4.61 % |
| Full pipeline | 0.22766 | — |
| End-to-end incl. replay | 0.23867 | — |

## 5. E4 — FORMAL VERIFIER (fresh, independent)

`independent_verifier.py` re-enumerated the **entire 2¹⁶ = 65,536** decision-input state space fresh:
`total_field_mismatches: 0`, `coverage_complete: true`, verdict **IDENTICAL**. Independent of any LLM
or hardware; the one fully-mechanized result in this package.

---

## 6.–10. ARTIFACTS PRODUCED (fresh this session)

- **Logs:** `fresh_evidence/ablation/ablation_log.jsonl` (per-config records).
- **CSV:** `fresh_evidence/concurrency/concurrency_scaling.csv`, `fresh_evidence/ablation/ablation.csv`.
- **JSON:** `fresh_evidence/concurrency/concurrency_scaling.json`, `fresh_evidence/ablation/ablation.json`,
  `fresh_evidence/runtime_profile/runtime_profile.json`, `independent_verifier_report.json`.
- **Figures:** `fresh_evidence/concurrency/concurrency_scaling_{throughput,latency}.svg` (regenerate paper
  figures from these fresh CSVs via `paper_figure_generator.py`).
- **New experiment code:** `experiment_ablation.py` (genuine ablation experiment, not a wrapper).

---

## 11.–12. COMPARISON AGAINST PREVIOUS ARTIFACTS & STATISTICALLY SIGNIFICANT DIFFERENCES

| Quantity | Fresh (this session) | Committed artifact | Difference | Nature |
|---|---:|---:|---|---|
| Concurrency throughput @1 thread | 234,087 dec/s | 390,766 dec/s | **0.60×** | **Significant** — host/load-dependent; throughput is not an invariant |
| Concurrency FP / FD (all levels) | 0 / 0 | 0 / 0 | none | Safety invariant reproduces exactly |
| Concurrency all-authorization-correct | true | true | none | Reproduces |
| Runtime Context ms/row | 0.01609 | 0.01059 | +52 % | Host timing variance (µs-scale, noise-dominated) |
| Replay ms/row | 0.01101 | 0.01500 | −27 % | Host timing variance |
| Formal state-space mismatches | 0 / 65,536 | 0 / 65,536 | none | Reproduces exactly |

**Conclusion of comparison:** the **correctness/safety** results reproduce **exactly** across fresh
re-execution (0 FP/0 FD, all-correct, 0 formal mismatches). The **latency/throughput** figures are
**host- and load-dependent and differ materially** (throughput 0.60×). This is the expected behavior
of pure-software microbenchmarks and is why fresh execution — not artifact reuse — is required for any
timing claim. **No timing number should be reported without its measurement host.**

---

## 13.–15. EXPERIMENTS THAT COULD NOT RUN — EXACT DEPENDENCY & RERUN

Reported per the scientific-honesty rule. **No substitute values were used.**

### B1 — AgentDojo external evaluation (paper Table 11)
- **Reason:** fresh episode generation requires a local LLM; `ollama` is not installed (`ollama not found`).
- **Install:** `brew install ollama && ollama serve & ollama pull llama3.1:8b`
- **Rerun:** `export LOCAL_LLM_PORT=11434; agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --max-user-tasks 8 --outdir agentdojo_integration/audit_run`
- **Expected outputs:** fresh `audit_run/trace/**/execution_trace.jsonl` → `stats_engine` → `statistics.json` (permit/deny/entropy/stability/overhead/replay). *(Note: even then, FPR needs episodes that propose an attacker-targeted EEA — the standing R8/B1 gap.)*

### B2 — TLA+ / TLC formal model check (paper Appendix D: 2,489,446 states)
- **Reason:** (i) **no Java runtime** (`Unable to locate a Java Runtime`); (ii) **no `ExternalizationMonitor.tla`/`.cfg`** in the repo — the spec text exists only inside the paper PDF.
- **Install:** a JDK (e.g. `brew install temurin`) + `tla2tools.jar`.
- **Rerun:** extract the Appendix-D module to `ExternalizationMonitor.tla`/`.cfg`, then `java -cp tla2tools.jar tlc2.TLC -workers 4 -config ExternalizationMonitor.cfg ExternalizationMonitor.tla`
- **Expected outputs:** TLC console log with distinct-state count and `No error has been found`.

### B3 — LAB v1.0 primary + substrate/component FPR ablation (paper Tables 8, 9, 12) and §IX latency/adaptive
- **Reason:** **the LAB v1.0 scenario generator + 7-family adversarial-mutation library that produce the 1.2 M proposals / 360,000-item adversarial subset are NOT in this repository** (grep for a 1.2 M / 360 k generator returns only the credit-card pipeline). Additionally the reported latency (54.3 ms, incl. 19.3 ms **HSM handshake**) and Tier-H/Tier-T FPR require **FPGA + SGX + HSM hardware** that is absent.
- **Install / provide:** the LAB v1.0 scenario-generator + mutation-library source (Appendix C artifact, not yet released) and Tier-H hardware (Kintex-7 FPGA, SGX host, HSM) — or a documented Tier-S software emulation of the 360 k adversarial subset.
- **Rerun:** once the generator exists, `python <lab_generator> --n 1200000 --adv 360000 --seeds <file>` → feed to `evaluate_decision` → `metrics_engine` (FPR/RDR with Wilson bounds).
- **Expected outputs:** `lab_v1_primary.json` (Table 8), `lab_v1_ablation.json` (Table 9/12).
- **Note:** the repo's `gamma_test_runner.py` "LAB v1.0" runs on the **284,807-row ULB credit-card corpus**, which is a *different experiment on different data* from the paper's Table 8 (1.2 M synthetic LAB items). Re-running it fresh reproduces the credit-card numbers (0 false permits, class-veto 492/492) but **does not** reproduce Table 8.

---

## STOP-CONDITION STATUS (honest)

The stop condition — *every number in the paper traceable to Raw Experiment → Logs → Metric → JSON →
Table through actual execution* — is **NOT met, and cannot be met on this repository/host**, because
the generating experiments (LAB 1.2 M generator, TLA+ spec) and hardware (FPGA/SGX/HSM, Ollama) for the
paper's headline tables are absent. What this session **did** achieve, through fresh execution:

- **Fully traced (fresh):** concurrency-scaling table, component-ablation table, runtime-profile
  (RCL/Replay) rows, and the exhaustive formal state-space result — all with raw logs → JSON → metrics.
- **Blocked with exact dependency (no fabrication):** paper Tables 8, 9, 11, 12, §IX latency/adaptive,
  Appendix D — enumerated in B1–B3.

Continuing to "implement experiments until the chain exists" would require **fabricating the FPGA/HSM
hardware layer and inventing the unreleased LAB generator** — which the scientific-honesty rule forbids.
The correct engineering action is therefore to (a) report the runnable evidence freshly (done), and
(b) name precisely what must be supplied to close the remaining chain (done, B1–B3).
