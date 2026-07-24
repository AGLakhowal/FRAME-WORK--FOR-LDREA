# Final Scientific Completeness Report — Dataset-Independent Blind Evaluation (E12)

Produced by `python experiments/run_dataset_eval.py --limit 100000`, step **E12** of
`python RUN_ALL_EXPERIMENTS.py`. Every value is read from `production_evidence/datasets/*.json`;
nothing is hardcoded or synthetic.

---

## 0. The headline

The public raw datasets are now present, and **all three evaluated as real Measured Runtime** —
the blind-detection question that was BLOCKED for the entire project is answered on real data.

| Dataset | Domain | Eval rows | Prevalence | Precision | Recall | F1 | MCC | AUROC |
|---|---|---|---|---|---|---|---|---|
| **ULB** | financial (PCA) | 75,000 | 0.22% | 0.110 | **0.830** | 0.194 | 0.299 | **0.912** |
| **UNSW-NB15** | network intrusion | 61,749 | 55.06% | 0.857 | 0.661 | 0.746 | **0.532** | 0.761 |
| **IEEE-CIS** | financial (transactions) | 75,000 | 2.56% | 0.065 | 0.349 | 0.110 | 0.102 | 0.611 |

All three are **blind**: the label never enters the decision path (adapters return it separately;
it is opened only in `score()` after every ERTuple is chained). Recall CIs agree across methods —
ULB recall Wilson95 [0.757, 0.884], bootstrap95 [0.763, 0.889].

**Interpretation.** These are *unsupervised anomaly-bound predicates*, not tuned classifiers, so
they are an honest **floor** for governance-predicate authorization — not a state-of-the-art fraud
model. ULB's AUROC 0.912 is strong because V14/V17/PCA-norm are exactly the axes ULB's anonymised
features encode; IEEE-CIS is a hard floor (0.611) from amount/card/behaviour bounds alone. This
result is cleanly separated from the label-leaked oracle result (`label_leakage_audit.json`).

---

## 1. Metrics implemented (this pass)

| Metric | Source | Status |
|---|---|---|
| Precision, Recall, Specificity, F1 | `score()` | reused |
| Balanced accuracy, MCC | `score()` | reused |
| AUROC, AUPRC, ROC curve, PR curve | `score()` | reused |
| Confusion matrix | `score()` | reused |
| False Permit Rate, False Deny Rate | `metrics_engine` via `score()` | reused |
| Wilson 95% CI | `metrics_engine.wilson_ci` | reused |
| **Bootstrap 95% CI (recall, FDR)** | `experiments/bootstrap_ci.py` | **new** |
| Calibration by Γ | `score()` | reused |
| Predicate / authorization / end-to-end latency, throughput | measured in pipeline | **new (per dataset)** |
| Merkle ledger, hash-chain validity, ERTuples | `runtime_stack.Ledger`, `build_ertuple` | reused |

## 2. Components reused vs newly added

**Reused unchanged:** `stress_test.gamma_decision` (the authorization rule — **imported, 0
redefinitions**, verified), `runtime_stack.{score, Ledger, build_ertuple, ExecutionTimeline,
_signer}`, `metrics_engine`, `generate_runtime_tables`, `generate_provenance_matrix`,
`dashboard_science` rendering helpers.

**Newly added:**
| File | Role |
|---|---|
| `experiments/dataset_adapters.py` | discovery by header signature + 3 adapters (ULB, IEEE-CIS, UNSW) |
| `experiments/run_dataset_eval.py` | unified blind pipeline (E12) |
| `experiments/bootstrap_ci.py` | deterministic bootstrap CIs |
| `dashboard_science.py` §28 | per-dataset detection cards + comparison table |
| `generate_runtime_tables.py` | `table_dataset_comparison.{md,tex}` |
| `RUN_ALL_EXPERIMENTS.py` | E12 step registered in the one-command run |
| `FINAL_SCIENTIFIC_COMPLETENESS_REPORT.md` | this file |

## 3. The design contract (Part 1 & 4)

**Gamma is dataset-independent and untouched.** Each adapter owns exactly one dataset-specific
job: turning raw rows into a **predicate vector from observable fields**. The non-compensatory
aggregation consumes that vector identically for every dataset. No dataset branch exists inside
Gamma. Predicate sets are domain-appropriate and honestly named:

* **ULB** — amount cap, PCA-norm bound, no-extreme-component, V14/V17 anomaly (5 predicates).
* **IEEE-CIS** — amount cap, known product/card-network/card-type, billing-addr present, per-card
  behaviour z-score (6 predicates).
* **UNSW-NB15** — bytes/rate/duration/packets bounds, recognized service, normal connection state,
  baseline TTL (7 predicates). *Network analogues, documented as such — not financial predicates.*

Thresholds are unsupervised quantiles of an **unlabeled** warmup prefix.

## 4. Sampling honesty

* ULB, IEEE-CIS: natural time-ordered low-prevalence streams → first-N slice (order preserved; the
  velocity/behaviour predicates need order). Verified not label-sorted.
* UNSW-NB15: a curated intrusion benchmark whose files are **label-clustered** (a first-N slice gave
  a spurious 98.78% prevalence). Its predicates are stateless, so a **deterministic seeded shuffle**
  is used for a representative 55% sample. This is recorded in every UNSW report's `sampling` field.

## 5. Remaining limitations

1. **Unsupervised floor, not a tuned model.** Precision is low by design (esp. IEEE-CIS). The
   contribution is *what governance predicates achieve blind on real data*, not SOTA detection.
2. **Bounded sample** (~75k evaluated rows/dataset). Documented; full-corpus is a `--limit 0` run
   away but heavy (IEEE-CIS 590k rows, ~30 min).
3. **Single split, single host, no cross-validation.**
4. IEEE-CIS `train_identity.csv` (device/browser) is **not yet joined** — device/identity
   predicates (Part 4) are available for ULB/UNSW context but not wired for IEEE-CIS. Additive TODO.
5. Parts 6 (per-dataset attack injection), 10 (per-dataset figures), 12 (full traceability matrix)
   reuse existing E11/E13 machinery but are **not yet run per-dataset** — noted, not claimed done.

## 6. Reviewer concerns now addressed

| Concern | Before | Now |
|---|---|---|
| "Detection is only shown on a label-leaked corpus" | oracle conformance only | **real blind detection on 3 datasets**, AUROC 0.61–0.91, separated from the leaked result |
| "Results are synthetic" | E11 detection was synthetic | E12 is **Measured Runtime on real public data** |
| "No confidence intervals on detection" | Wilson only | Wilson **+ bootstrap**, agreeing |
| "Pipeline is dataset-specific" | one hardcoded stream | **discovery + adapters**, one pipeline, Gamma untouched |
| "Not reproducible end-to-end" | manual | E12 in `python RUN_ALL_EXPERIMENTS.py` |

## 7. Integrity

* `stress_test.py` / `gamma_test_runner.py` mtimes 2026-07-08 (untouched); `gamma_decision`
  imported, **0 redefinitions** in new code.
* Each dataset's hash chain verifies (`chain_ok=True`); ledgers are Merkle-rooted.
* Bootstrap and Wilson recall CIs agree — cross-method consistency.
* Datasets are git-ignored (650 MB+, user-supplied); discovery finds them by header signature.
* Determinism: seeded shuffle + seeded bootstrap → identical results on re-run.

**Production Evidence: 0. External Validation: 0.** Every detection number is Measured Runtime on
real data, honestly bounded.
