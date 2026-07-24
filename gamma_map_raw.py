#!/usr/bin/env python3
"""
Raw ULB credit-card  ->  Gamma G-0 golden-trace mapper
======================================================

Transforms the raw ULB / Kaggle credit-card dataset (creditcard.csv with
columns Time, V1..V28, Amount, Class) into the 112-column Gamma G-0
golden-trace schema consumed by gamma_test_runner.py.

This is a faithful reconstruction of the same synthetic golden-trace
construction that produced the bundled 1,000-row sample (its first three
rows match creditcard.csv exactly). Honesty notes:

  * GROUND TRUTH is the real `Class` column (0 = legitimate, 1 = fraud).
    The authorization outcome is driven by that real label, not invented.
  * The hash chain (HASH_prev -> HASH_current) is GENUINELY computed with
    SHA-256 over the canonical core record, GENESIS-anchored.
  * Per-row identifiers (token/ERTuple/profile ids) are deterministic
    hashes of the row; signatures are represented structurally (the runner
    treats AuthoritySignatureValid as a predicate, not a real HSM check).
  * Structural constants (PolicyHash, SpecVersion, NodeID, TLC* hashes,
    substrate ids) are copied from the sample template so the emitted file
    is schema-identical to a real golden trace.

The derivation rule (mirrors the sample):
    Class == 1  -> HARM_RISK high, Gate_A3 & Gate_A7 & Lambda_G fail,
                   Gamma = 1, SAFE_STATE (denied, not actuated)
    Class == 0  -> all gates pass, Gamma = 0, PERMIT (actuated)

Usage:
    python gamma_map_raw.py --raw creditcard.csv --out GAMMA_G0_FULL.csv
    python gamma_test_runner.py --input GAMMA_G0_FULL.csv
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

SAMPLE_TEMPLATE = "GAMMA_G0_CREDITCARD_GOLDEN_TRACE_20260629_001_sample_master112_1000.csv"
EPOCH_BASE = datetime(2013, 9, 1, tzinfo=timezone.utc)  # ULB 2013 reference base

# Columns that vary per transaction; everything else is copied from the template.
HARM_FRAUD = 0.8


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Map raw ULB credit-card CSV to Gamma G-0 schema.")
    p.add_argument("--raw", default="creditcard.csv", help="Raw ULB CSV (Time,V1..V28,Amount,Class).")
    p.add_argument(
        "--template",
        default=SAMPLE_TEMPLATE,
        help="Gamma G-0 golden-trace sample used as the schema/constants template.",
    )
    p.add_argument("--out", default="GAMMA_G0_CREDITCARD_FULL_mapped.csv", help="Output golden-trace CSV.")
    p.add_argument("--limit", type=int, default=0, help="Map only the first N raw rows (0 = all).")
    p.add_argument(
        "--run-id",
        default="GAMMA_G0_CREDITCARD_FULL_MAPPED_001",
        help="RunID / benchmark id stem for the mapped trace.",
    )
    return p.parse_args()


def h12(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:12]


def h16(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:16]


def iso_ms(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def derive_harm_risk(amount: float, v_anomaly: float) -> float:
    """Small deterministic legit-row risk proxy in [0, ~0.05] from amount + PCA spread.

    Only used for Class==0 rows; it must stay <= the runner's harm threshold so
    legitimate rows permit. The real fraud signal is the Class label, not this.
    """
    amt = min(max(amount, 0.0), 25000.0) / 25000.0
    base = 0.02 + 0.025 * amt + 0.005 * min(abs(v_anomaly) / 50.0, 1.0)
    return round(min(base, 0.049), 6)


def main() -> None:
    args = parse_args()
    raw_path, tmpl_path, out_path = Path(args.raw), Path(args.template), Path(args.out)

    raw = pd.read_csv(raw_path)
    if args.limit:
        raw = raw.head(args.limit)
    for col in ("Amount", "Class"):
        if col not in raw.columns:
            raise SystemExit(f"Raw file missing required column '{col}'. Found: {list(raw.columns)}")
    has_time = "Time" in raw.columns
    v_cols = [c for c in raw.columns if c.startswith("V")]

    tmpl = pd.read_csv(tmpl_path)
    columns = list(tmpl.columns)
    legit_tpl = tmpl.iloc[0].to_dict()
    fraud_rows = tmpl[tmpl["Status"].astype(str).str.upper() == "SAFE_STATE"]
    fraud_tpl = (fraud_rows.iloc[0] if len(fraud_rows) else tmpl.iloc[0]).to_dict()

    n = len(raw)
    print(f"[map] raw rows: {n} | fraud(Class=1): {int((raw['Class'] == 1).sum())} "
          f"| legit: {int((raw['Class'] == 0).sum())}")

    out_rows = []
    prev_hash = "GENESIS"
    amounts = raw["Amount"].tolist()
    classes = raw["Class"].astype(int).tolist()
    times = raw["Time"].tolist() if has_time else [0] * n
    v_anom = raw[v_cols].abs().sum(axis=1).tolist() if v_cols else [0.0] * n

    for i in range(n):
        is_fraud = classes[i] == 1
        row = dict(fraud_tpl if is_fraud else legit_tpl)  # copy structural constants
        idx = i + 1
        t_sec = float(times[i]) if times[i] == times[i] else 0.0  # NaN-safe
        base_ts = EPOCH_BASE + timedelta(seconds=t_sec)
        commit_ts = base_ts + timedelta(milliseconds=10)
        actuate_ts = base_ts + timedelta(milliseconds=25)

        amount = float(amounts[i]) if amounts[i] == amounts[i] else 0.0
        harm = HARM_FRAUD if is_fraud else derive_harm_risk(amount, v_anom[i])

        # ---- per-row overrides -------------------------------------------- #
        row["RunID"] = args.run_id
        row["BenchmarkRowID"] = f"{args.run_id}_ROW_{idx:06d}"
        row["ProposalID"] = f"TXN_{idx:06d}"
        row["Step"] = idx
        row["TimestampUTC"] = iso_ms(base_ts)
        row["DatasetID"] = "DS2_ULB_CREDITCARD_2013"
        row["SubjectProfileID"] = f"CARDPROFILE_SYN_{h12('profile', idx)}"
        row["EnvironmentContext"] = (
            f"ULB_2013_EU_CARD;source_time_sec={int(t_sec)};amount={amount:g};"
            f"class={classes[i]};source=anonymized_PCA"
        )
        row["HARM_RISK"] = harm
        row["DomainHazardScore"] = harm
        row["SeverityScore"] = round(harm + 0.0003, 6)

        if is_fraud:
            row["Gate_A3"] = False
            row["Gate_A7"] = False
            row["Lambda_G"] = False
            row["Gamma"] = 1
            row["GammaZero"] = False
            row["ACT_PERMIT"] = False
            row["ExecutionLegitimacy"] = False
            row["SAFE_STATE"] = True
            row["Actuated"] = False
            row["CommitBeforeActuate"] = True
            row["Status"] = "SAFE_STATE"
            row["DecisionOutcome"] = "DENIED_SAFE_STATE"
            row["ReasonCodes"] = "CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL;SAFE_STATE_DENIAL"
            row["FirstFailingGate"] = "Gate_A3"
            row["ActuateTimestamp"] = ""  # never actuated
        else:
            for g in ("Gate_A1", "Gate_A2", "Gate_A3", "Gate_A4", "Gate_A5", "Gate_A6", "Gate_A7"):
                row[g] = True
            row["Lambda_G"] = True
            row["Gamma"] = 0
            row["GammaZero"] = True
            row["ACT_PERMIT"] = True
            row["ExecutionLegitimacy"] = True
            row["SAFE_STATE"] = False
            row["Actuated"] = True
            row["CommitBeforeActuate"] = True
            row["Status"] = "PERMITTED"
            row["DecisionOutcome"] = "PERMITTED_ACTUATED"
            row["ReasonCodes"] = "CLASS_0_LEGITIMATE;ALL_GATES_PASS;PERMITTED_ACTUATED"
            row["FirstFailingGate"] = "NONE"
            row["ActuateTimestamp"] = iso_ms(actuate_ts)

        # tokens / evidence ids (deterministic per row)
        row["TOKEN_VALID"] = True
        row["AuthoritySignatureValid"] = True
        row["PermitTokenID"] = f"PERMIT_{h16('permit', idx)}"
        row["ERTuple_ID"] = f"ERT_{h16('ertuple', idx)}"
        row["ADAPT_PERMIT"] = False
        row["FalsePermitFlag"] = False
        row["SafeStateViolationFlag"] = False
        row["OrderingInversionFlag"] = False
        row["ReplayDivergenceFlag"] = False
        row["CommitTimestamp"] = iso_ms(commit_ts)

        # ---- genuine hash chain ------------------------------------------- #
        canon = (
            f"{row['ProposalID']}|{row['Status']}|{row['Gamma']}|{harm:.6f}|"
            f"{row['PermitTokenID']}|{row['TimestampUTC']}"
        )
        cur_hash = hashlib.sha256((prev_hash + "||" + canon).encode()).hexdigest()
        row["HASH_prev"] = prev_hash
        row["HASH_current"] = cur_hash
        prev_hash = cur_hash

        out_rows.append(row)
        if idx % 50000 == 0:
            print(f"[map] {idx}/{n} rows mapped...")

    out = pd.DataFrame(out_rows, columns=columns)
    out.to_csv(out_path, index=False)
    print(f"[map] wrote {len(out)} rows x {len(columns)} cols -> {out_path}")
    print(f"[map] PERMITTED: {int((out['Status'] == 'PERMITTED').sum())} | "
          f"SAFE_STATE: {int((out['Status'] == 'SAFE_STATE').sum())}")


if __name__ == "__main__":
    main()
