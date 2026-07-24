# Datasets — placement for reproduction

The blind runtime evaluation (experiment **E12**, `experiments/run_dataset_eval.py`) discovers
datasets **by CSV header signature**, not by filename, under `datasets/` or `dataset/`. Place the
raw public files anywhere beneath either directory and they are found automatically.

| Dataset | Expected file(s) | Signature columns | Source |
|---|---|---|---|
| **ULB Credit Card Fraud** | `creditcard.csv` | `Time, V1..V28, Amount, Class` | Kaggle: mlg-ulb/creditcardfraud |
| **IEEE-CIS Fraud** | `train_transaction.csv` (+ `train_identity.csv`) | `isFraud, TransactionDT, TransactionAmt, ProductCD, card1` | Kaggle: ieee-fraud-detection |
| **UNSW-NB15** | `UNSW_NB15_training-set.csv` / `..._testing-set.csv` | `proto, service, state, sbytes, dbytes, label` | UNSW: unsw-nb15 |

These files are large (650 MB+) and are **git-ignored**; they are never committed. If a dataset is
absent, E12 reports it under `not_found` with no metrics — nothing is fabricated.

Run just this experiment:

```bash
python experiments/run_dataset_eval.py --limit 100000     # bounded sample per dataset
python experiments/run_dataset_eval.py --limit 0          # full corpus (heavy)
```

Or the whole suite (E1–E12) in one command:

```bash
python RUN_ALL_EXPERIMENTS.py
```

**Scientific note.** E12 predicates are unsupervised anomaly bounds calibrated on an unlabeled
warmup prefix — an honest *floor* for governance-predicate authorization, not a tuned classifier.
Labels never enter the decision path. See `FINAL_SCIENTIFIC_COMPLETENESS_REPORT.md`.
