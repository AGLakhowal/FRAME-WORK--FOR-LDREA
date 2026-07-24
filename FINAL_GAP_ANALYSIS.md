# Final Gap Analysis — L-DREA

All figures below were produced by a single execution of
`python experiments/run_runtime_stack.py --n 8000` (plus `experiments/production_evidence_layer.py`
and `experiments/audit_label_leakage.py`). Nothing is transcribed from a previous run.

Nothing is marked **PASS** unless a measurement collected during that execution supports it.

---

## 1. What is now FULLY MEASURED

### 1.1 Runtime predicate generation (was: replayed from dataset columns)

Ten predicates are now **computed from observable fields**, never read from a column that already
encodes the answer:

| Predicate | Computed from |
|---|---|
| `TOKEN_VALID` | Ed25519 verification + `exp` + subject binding on a JWT-like token |
| `AuthoritySignatureValid` | `kid` bound to the authority public key |
| `TelemetryFresh` | wall-clock delta against the observation timestamp |
| `StaleContext` | age of the subject's last context |
| `amount_within_daily_limit` | 24 h rolling sum per subject |
| `destination_account_recognized` | vendor-registry lookup |
| `velocity_check` | 60 s sliding-window counter |
| `behaviour_anomaly` | robust modified z-score vs an online learned baseline |
| `policy_consistency` | policy-hash comparison |
| `impossible_travel_absent` | haversine distance / Δt vs 900 km/h |

**Structural blindness.** `Observation` is a frozen dataclass with **no `label` field**;
`Observation(..., label=1)` raises `TypeError`. The label is opened once, in `score()`, after every
ERTuple is chained. Verified.

**Thresholds are not hand-chosen.** `daily_cap`, `velocity_cap` and `stale_context_ms` are 99.5th
percentiles of the *unlabeled* warmup prefix. `max_kmh` is a physical constant. The vendor registry
is an operational master file, not learned and not a label.

**Gamma is unmodified.** The non-compensatory rule is imported from `stress_test.gamma_decision()`.

| Measurement | Value | Level |
|---|---|---|
| Predicate generation latency (mean / p99) | 0.914 ms / 1.314 ms | Measured Runtime |
| Authorization latency (mean / p99) | 0.00166 ms / 0.00479 ms | Measured Runtime |
| Predicates per decision | 10 | Measured Runtime |

### 1.2 Blind detection — **SYNTHETIC stream only**

Evaluated on 6,000 post-warmup requests (2 % positive prevalence).

| Metric | Value |
|---|---|
| Confusion matrix | TP 48 · FN 68 · FP 189 · TN 5,695 |
| Precision / Recall | 0.2025 / 0.4138 |
| F1 / MCC | 0.2720 / 0.2698 |
| Balanced accuracy | ≈ 0.69 |
| AUROC | 0.6922 |
| False-deny rate | 0.0321 |
| Calibration by Γ | Γ=0 → 1.18 % · Γ=1 → 16.89 % · Γ=2 → 83.33 % |

The calibration curve is **monotone in Γ** — the strongest single piece of evidence that the
non-compensatory aggregation carries real signal.

**Recall is bounded above by ≈ 0.53 by construction**: 47 % of positives are *stealthy* (ordinary
amount, known vendor, valid token) and are observably identical to negatives. They must be false
negatives. The pipeline achieves 0.414 of an achievable 0.53. **A perfect score here would have
meant the generator leaked.**

> **Evidence level: `Synthetic Runtime`.** These numbers characterise the generator and the
> pipeline, **not the world**. They are written to
> `production_evidence/runtime_detection_report_synthetic.json` and must never be cited in place of
> the real-ULB report at `runtime_detection_report.json` (root), which is `status: BLOCKED`.

### 1.3 Execution lifecycle (was: evidence ended at commit)

All ten marks are `perf_counter_ns()` taken at the real point in the pipeline: `t_received`,
`t_validate`, `t_predicate`, `t_authorize`, `t_issue`, `t_execute_start`, `t_execute_finish`,
`t_commit`, `t_finalize`, `t_replay`. Execution performs real work and runs **only on PERMIT**.

| Measurement | Value | Level |
|---|---|---|
| End-to-end (mean / p95) | 1.518 ms / 1.865 ms | Measured Runtime |
| Permits issued / executions | 2,838 / 3,000 (this slice) | Measured Runtime |

### 1.4 Multi-process fleet (was: seeded RNG in one process)

**Five real OS processes** (`multiprocessing`, spawn). Cross-process timing uses `CLOCK_MONOTONIC`,
which is system-wide; `perf_counter()` is *not* used across processes because its epoch is
per-process.

| Measurement | Value | Level |
|---|---|---|
| Worker PIDs | 5 distinct | Measured Runtime |
| Throughput | 2,315 decisions/s | Measured Runtime |
| Queue delay p95 | 358.8 ms | Measured Runtime |

Queue delay is large because all 1,500 requests are dispatched before draining — it measures a
**burst admission**, not steady-state.

### 1.5 Real revocation propagation (was: `rng.uniform(2, 20)`)

Revocation is now broadcast over real IPC to real processes, which acknowledge with a
`CLOCK_MONOTONIC` timestamp.

| Measurement | Value | Level |
|---|---|---|
| Acknowledgements | **600 / 600** | Measured Runtime |
| Propagation p50 / p95 / p99 | 51.4 / 52.0 / 51.9 ms | Measured Runtime |
| Per-node ack p50 | 48.6 ms | Measured Runtime |
| False permits after revocation | **0 / 120 probed** | Measured Runtime |
| Control: un-revoked permit accepted | **true** (probe has power) | Measured Runtime |

> **Honest reading of the 51 ms.** It is *not* IPC cost. Workers poll the control queue between
> `req_q.get(timeout=0.05)` calls, so propagation is **bounded below by the 50 ms poll interval**.
> The number characterises this design's polling cadence, not the transport. Reducing the poll
> interval would reduce it almost linearly. Do not quote 51 ms as "fleet revocation latency".

### 1.6 Live watchdog (was: an in-process loop with injected timeouts)

A real `threading.Thread` supervisor sampling real CPU/RSS via `getrusage`, monitoring **per-worker
liveness** — necessary because a shared queue hides a single stalled worker from a global progress
monitor. One real 0.6 s stall was injected into worker 2.

| Measurement | Value | Level |
|---|---|---|
| Heartbeats | 298 | Measured Runtime |
| Heartbeat latency (mean overshoot) | 3.44 ms vs 20 ms target | Measured Runtime |
| Injected stalls detected | **1 / 1** | Measured Runtime |
| False triggers | **0** | Measured Runtime |
| Recovery latency p95 | 369.8 ms | Measured Runtime |

### 1.7 Enhanced ERTuples + Merkle ledger

ERTuple v2 carries: runtime predicates (+details), Γ, decision, failed predicates, permit id, policy
hash, replay hash, ledger hash, all ten execution timestamps, worker id, clock offset, evidence id,
nonce, ERTuple hash, Ed25519 signature.

| Measurement | Value | Level |
|---|---|---|
| Ledger blocks (batch 64) | 94 | Derived From Measured |
| Hash continuity | true | Measured Runtime |
| Tamper detection (mutated Merkle root) | **detected** | Measured Runtime |
| Fork detection (competing block) | **detected** | Measured Runtime |

### 1.8 Runtime signals

Twelve observable signals computed per request (weekend, outside-hours, large amount, unknown
destination, device mismatch, repeated failures, burst, token age, behaviour drift, cross-session
anomaly, impossible travel, velocity). **Signals are advisory context and do not enter the Γ
decision** — stated in the artifact, not merely here.

---

## 2. What is STILL SIMULATED

| Component | What is simulated | What is genuinely measured |
|---|---|---|
| **Key custody** | seed is a published constant; no HSM/KMS/key ceremony | the Ed25519 signatures themselves (RFC 8032, cross-checked against an independent reference implementation) |
| **Clock skew** | all processes read the same system clock | IPC round-trip and scheduling jitter |
| **Packet loss / retries** | there is no network; queues are lossless | reported as `0` with `not_applicable_reason`, never as evidence of reliability |
| **Detection ground truth** | the stream is synthetic | the pipeline, latencies and calibration curve |

**Clock synchronisation is NOT closed.** I moved the fleet from simulated to measured, but I did
**not** move clock skew. Five processes on one host share `CLOCK_MONOTONIC`, so any "offset" I
measure is scheduling jitter. Reporting it as distributed clock skew would be fabrication. It
remains `Repository Simulation`.

---

## 3. What CANNOT be measured in a single-machine research repository

1. **True clock skew and PTP synchronisation.** Requires ≥ 2 physical hosts and a grandmaster.
   Offsets between processes on one host are definitionally ~0.
2. **Network partition, packet loss, retries, consensus under partition.** No network exists.
   `multiprocessing.Queue` is lossless and ordered; a lossless channel cannot evidence loss handling.
3. **Byzantine or crash-fault consensus.** Five cooperating child processes on one kernel share fate
   with the parent. This is concurrency, not distribution.
4. **Hardware key custody, attestation, secure boot.** No HSM, TPM or enclave.
5. **Real-world detection.** The mapped ULB corpus derives 5 of 12 engine inputs from the label
   (`label_leakage_audit.json`) and discarded `V1..V28` / `Amount`. Blind detection on real data is
   **BLOCKED** pending `creditcard.csv`.
6. **Third-party audit / external replication.** Unreachable from inside the repository.

---

## 4. Infrastructure required for production-grade evidence

| Claim to be supported | Minimum infrastructure |
|---|---|
| Distributed clock skew, PTP bound | ≥ 2 physical hosts, PTP grandmaster (or GPS-disciplined clock), `ptp4l`/`phc2sys` |
| Fleet consensus, partition tolerance | Kubernetes (or ≥ 3 physical nodes), a real consensus layer (Raft/etcd), network fault injection (`tc netem`, Toxiproxy) |
| Revocation propagation at scale | real message bus (NATS/Kafka), measured under loss + partition |
| Key custody, signing attestation | HSM (PKCS#11) or cloud KMS; documented key ceremony; rotation logs |
| Production detection evidence | live transaction stream with delayed, adjudicated labels; prospective evaluation |
| Independent verification | third-party auditor with read-only ledger access |
| Real-world unsafe-action detection | deployed reference monitor in front of a real effector, with an incident ground truth |

---

## 5. Status against the seven stated gaps

| # | Gap | Status | Evidence |
|---|---|---|---|
| 1 | Predicates replayed from dataset columns | **CLOSED** | 10 generators; `Observation` has no label field |
| 2 | Engine validated, not shown detecting | **PARTLY CLOSED** | blind pipeline + monotone Γ calibration, on a **synthetic** stream; real-data detection remains BLOCKED |
| 3 | Fleet simulated | **CLOSED** | 5 real OS processes, 5 PIDs, measured throughput/queue delay |
| 4 | Watchdog simulated | **CLOSED** | real thread, real `getrusage`, 1/1 injected stall detected, 0 false triggers |
| 5 | Clock synchronisation simulated | **NOT CLOSED** | one host, one clock — see §2 |
| 6 | Evidence ends at commit | **CLOSED** | 10-mark lifecycle through `t_replay` |
| 7 | Runtime signals limited | **CLOSED** | 12 observable signals, advisory-only |

**Five of seven closed. One partly. One honestly not closed.**

---

## 6. Objectives not delivered in this pass

| # | Objective | Status | Why |
|---|---|---|---|
| 10 | Dashboard integration | **Not done** | the new artifacts are not yet rendered into `SCIENTIFIC_DASHBOARD.html` |
| 11 | Automatic paper outputs (tables/figures/LaTeX) | **Not done** | existing generators already recompute from outputs; the new artifacts are not yet wired in |

Marking these green would be the failure mode this repository exists to prevent.

---

## 7. Defects found and corrected during this pass

1. **`StaleContext` false-deny storm.** A hardcoded 10-minute threshold, shorter than the ~20-minute
   mean inter-arrival, denied 3,612 legitimate requests. Fixed by calibrating the threshold from
   warmup quantiles. This was a threshold artifact, never a finding.
2. **Watchdog could not observe a worker stall.** A global progress monitor never fires when four of
   five workers keep draining a shared queue. Replaced with per-worker liveness plus an
   `outstanding > 0` guard (without it, idle workers at drain time register as false triggers).
3. **Name collision.** The synthetic detection report was initially written to
   `runtime_detection_report.json`, colliding with the BLOCKED real-ULB report. Renamed to
   `..._synthetic.json` and cross-referenced in both directions.
4. **Mixed-run artifacts.** Determinism re-runs at `--n 4000` left `production_evidence/` holding
   values from two different executions. Re-run once, cleanly, so every artifact shares one run.
5. **Revocation latency misattribution.** The 51 ms is the worker's 50 ms control-poll interval, not
   IPC cost. Disclosed rather than quoted as a fleet property.

---

## 8. Integrity

* Gamma engine untouched: `stress_test.py` and `gamma_test_runner.py` mtimes are 2026-07-08, two
  days before this session; `gamma_decision()` is imported, never redefined.
* No pre-existing artifact was mutated (verified by hash diff before/after).
* The blind decision path is deterministic under a fixed seed (identical confusion matrix across
  repeated runs).
* Every artifact carries an `evidence_level`, and every simulated artifact carries a
  `why_simulated` / `why_not_measured` field.

**Production Evidence: 0 artifacts. External Validation: 0 artifacts.**
