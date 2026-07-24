# Runtime Evidence Audit — L-DREA

Every figure below was produced by `python experiments/run_runtime_stack.py --n 8000`, which is
step **E11** of `python RUN_ALL_EXPERIMENTS.py`. Nothing is transcribed from a prior run and nothing
is hardcoded.

> **This audit distinguishes three evidence levels and never blurs them.**
> **Measured Runtime** — timed or counted during execution. **Derived From Measured** — a hash or
> tuple of measured values. **Synthetic Runtime** — computed over a synthetic stream; describes the
> generator and the pipeline, not the world.
> **Production Evidence: 0. External Validation: 0.**

---

## 1. Measured runtime metrics (this run)

| Area | Metric | Value | Level |
|---|---|---|---|
| Predicate generation | generators / decision | 10, all computed | Measured |
| | generation latency mean | 0.906 ms | Measured |
| Runtime risk detection | attack families | 12 | Measured |
| | attacks detected | **2394 / 2394** | Measured |
| | detection precision | **1.000** (control passes) | Measured |
| | suite has power | **true** | Measured |
| | response latency p99 | 0.884 ms | Measured |
| Fleet | worker processes / PIDs | 5 / 5 | Measured |
| | throughput | 2,281 decisions/s | Measured |
| | busy fraction mean | 0.037 | Measured |
| | load imbalance (CV) | 0.432 | Measured |
| Watchdog | injected stalls detected | **1 / 1** | Measured |
| | false triggers | **0** | Measured |
| | heartbeat latency mean | 3.46 ms | Measured |
| Revocation | acknowledgements | **600 / 600** | Measured |
| | compliance rate | **1.000** | Measured |
| | false permits after revocation | **0** | Measured |
| | revocations/sec | 19.4 | Measured |
| Clock consistency | timestamp resolution | 41 ns | Measured |
| | sampling jitter p95 | 292 ns | Measured |
| | monotonic consistency | true | Measured |
| | wall-vs-monotonic drift | 18.2 ppm | Measured |
| Blind detection (**synthetic**) | precision / recall | 0.203 / 0.414 | Synthetic |
| | AUROC / MCC | 0.692 / 0.270 | Synthetic |

---

## 2. Verification checklist

| Check | Status | How verified |
|---|---|---|
| Nothing simulated where measurement is possible | **✓** | fleet/watchdog/revocation moved to real OS processes + IPC; only clock skew and key custody remain simulated (§4) |
| No fabricated metrics | **✓** | audited my own code; five hardcoded invariants were found and replaced with real verification paths (see FINAL_PRODUCTION_COMPLETION_REPORT §6) |
| No hardcoded runtime values | **✓** | thresholds are unsupervised warmup quantiles; every table row resolves from an artifact pointer |
| Every dashboard value links to evidence | **✓** | §27 renderer reads only `production_evidence/*.json`; dashboard shows 11/11 experiments |
| Every paper number links to runtime output | **✓** | `runtime_tables.json`: 7 tables, 46 rows, **0 unresolved**; each row carries `evidence_source` = `artifact::pointer` |
| Every table links to an experiment | **✓** | all tables read E11 artifacts |
| Every experiment reproducible | **✓** | E11 wired into `RUN_ALL_EXPERIMENTS.py`; ran via `--only runtime_stack` |
| Blind pipeline is genuinely blind | **✓** | `Observation` has no `label` field; `Observation(..., label=1)` raises `TypeError` |
| Attack suite has discriminating power | **✓** | benign control accepted 400/400; a reject-everything verifier would fail it |
| Watchdog detection is real | **✓** | 1/1 injected stall across repeated runs, 0 false triggers |
| Entire project reproducible from one command | **✓** | `python RUN_ALL_EXPERIMENTS.py` → E1–E11, then generators |

---

## 3. Provenance chain (Objective 10)

Every runtime number traces:

```
execution → ERTuple (runtime_stack.build_ertuple) → ledger block (Merkle root)
          → production_evidence/*.json → paper_tables/table_runtime_*.{md,tex}
          → SCIENTIFIC_DASHBOARD.html §27 → runtime_tables.json (evidence_source pointer)
```

`runtime_tables.json` records, per metric: value, units, 95% CI (where the artifact carries one),
sample size, `evidence_source` (`artifact::json_pointer`), evidence level, and paper section.
**0 rows unresolved.**

---

## 4. What remains simulated, and why (unchanged, restated honestly)

| Component | Simulated part | Measured part |
|---|---|---|
| **Clock skew / PTP** | one host = one clock; renamed to *Runtime Clock Consistency* | resolution, jitter, monotonicity, wall-vs-monotonic drift |
| **Key custody** | seed is a published constant | the Ed25519 signatures themselves |
| **Packet loss / retries** | no network; queues are lossless | reported `0` with `not_applicable`, never as reliability evidence |
| **Detection ground truth (blind)** | synthetic stream | pipeline, latencies, monotone calibration curve |

**PTP was NOT invented.** `runtime_clock_consistency_report.json` carries a `why_not_ptp` field:
PTP synchronises clocks across separate physical hosts against a grandmaster; on one machine there
is nothing to synchronise. Distributed skew requires ≥ 2 hosts and a grandmaster.

**Fraud detection was NOT faked.** The attack suite (`runtime_risk_detection_report.json`) measures
*enforcement* against attacks we constructed — ground truth is exact by construction, so
precision/recall are deterministic, not statistical claims. The statistical blind pipeline is
labelled Synthetic, and the real-ULB result (`runtime_detection_report.json`, root) is
`status: BLOCKED`.

---

## 5. Naming-collision guard

`runtime_detection_report.json` (root) = real-ULB, **BLOCKED**.
`production_evidence/runtime_detection_report_synthetic.json` = synthetic blind pipeline.
`production_evidence/runtime_risk_detection_report.json` = attack-injection enforcement.
Three distinct files, three distinct experiments, each cross-referencing the others in its own body.

---

## 6. Reproducibility

* `python RUN_ALL_EXPERIMENTS.py` runs E1–E11 then regenerates figures, tables (including
  `generate_runtime_tables.py` and `generate_provenance_matrix.py`), dashboard, README, docs.
* E11 verified in isolation via `python RUN_ALL_EXPERIMENTS.py --only runtime_stack`.
* The blind decision path is deterministic under the fixed seed (identical confusion matrix on
  repeat). Fleet/watchdog latencies are wall-clock and vary between runs, as documented.
* No E1–E10 artifact was mutated by E11 (verified by hash diff; the only deltas are the
  timing-derived `stress_latency_report.json` and the run manifest `run_index.json`).

---

## 7. What is still NOT done

| Objective | Status |
|---|---|
| 9 — full figure suite (utilization, heartbeat timeline, ROC/PR plots) | **Not done** — tables and dashboard cards are in; SVG figures are not |
| 11 — README runtime section | **Not done** |
| Real-ULB blind detection (root report) | **BLOCKED** — needs `creditcard.csv` |
| Distributed clock skew, consensus under partition, HSM custody, third-party audit | **Unreachable** on one machine — see FINAL_GAP_ANALYSIS.md §3–4 |

Marking any of these green would be the failure mode this repository exists to prevent.
