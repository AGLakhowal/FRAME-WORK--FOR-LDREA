#!/usr/bin/env python3
"""Dataset adapters + discovery (Parts 1 & 4).

DESIGN CONTRACT
    Gamma is dataset-independent and untouched. Each adapter owns exactly one dataset-specific
    responsibility: turning raw rows into a PREDICATE VECTOR derived from OBSERVABLE fields. The
    non-compensatory aggregation (stress_test.gamma_decision) then consumes that vector identically
    for every dataset. No dataset-specific branch exists inside Gamma.

BLINDNESS
    Each adapter yields (features, label) where `features` NEVER contains the label. Thresholds are
    calibrated on an unlabeled warmup prefix via quantiles. The label is returned separately and is
    opened only by the scorer, after every decision is committed.

DISCOVERY
    Datasets are identified by HEADER SIGNATURE, not filename. A file whose columns match a known
    signature is claimed by that adapter, wherever it sits under the search roots. This satisfies
    "automatically detect datasets without hardcoded filenames".

HONEST SEMANTIC MAPPING
    ULB and IEEE-CIS are financial. UNSW-NB15 is network telemetry; its predicates are network
    analogues (bytes, rate, service, state, TTL), documented as such. They are NOT presented as
    financial predicates.
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stress_test import P  # predicate constructor {name, passed, detail, in_scope}

csv.field_size_limit(1 << 24)
SEARCH_ROOTS = ["datasets", "dataset", "."]
WARMUP_FRACTION = 0.25
Q = 99.5


def _quantile(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    k = max(1, min(len(s), int(round(q / 100.0 * len(s) + 0.5))))
    return s[k - 1]


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# ===================================================================== base
class Adapter:
    name = "base"
    domain = "unknown"
    evidence_level = "Measured Runtime"
    signature: list[str] = []       # columns that must all be present to claim a file
    label_col = "label"
    # Order-sensitive adapters use rolling windows / behaviour baselines, so rows must stay in the
    # file's natural (time) order and a first-N slice is used. Order-INsensitive adapters have
    # stateless predicates; their files may be label-clustered, so a deterministic shuffle is used
    # to obtain a representative prevalence instead of a biased first-N slice.
    order_sensitive = True
    read_cap = 250_000

    def __init__(self, path: Path):
        self.path = path
        self.calib: dict = {}
        self.state: dict = {}
        self.sampling = "first-N (order preserved)"

    # -- discovery -------------------------------------------------------------------------------
    @classmethod
    def matches(cls, header: set[str]) -> bool:
        return all(c in header for c in cls.signature)

    # -- streaming -------------------------------------------------------------------------------
    def _rows(self, limit):
        with self.path.open(newline="") as fh:
            r = csv.DictReader(fh)
            for i, row in enumerate(r):
                if limit and i >= limit:
                    break
                yield {k.strip().lstrip("﻿"): v for k, v in row.items()}

    def features(self, row: dict) -> dict:
        raise NotImplementedError

    def label(self, row: dict) -> int:
        raise NotImplementedError

    def load(self, limit):
        """Returns (feature_dicts, labels). Labels are kept SEPARATE from features.

        Order-sensitive: first-N in file order. Order-insensitive: read up to read_cap, then
        deterministically shuffle (fixed seed) and take limit -- so a label-clustered file yields
        a representative sample rather than a biased first-N slice.
        """
        if self.order_sensitive:
            feats, labels = [], []
            for row in self._rows(limit):
                feats.append(self.features(row))
                labels.append(self.label(row))
            self.sampling = f"first-N (order preserved), N={len(feats)}"
            return feats, labels
        # order-insensitive: representative deterministic shuffle
        import random
        rows = list(self._rows(self.read_cap))
        rng = random.Random(20260710)
        rng.shuffle(rows)
        rows = rows[:limit] if limit else rows
        feats = [self.features(r) for r in rows]
        labels = [self.label(r) for r in rows]
        self.sampling = (f"deterministic shuffle of first {min(self.read_cap, len(rows) or 0)} "
                         f"file rows, seed 20260710, then take {len(feats)} "
                         "(stateless predicates -> order does not affect the decision)")
        return feats, labels

    # -- calibration (unsupervised; no label read) ----------------------------------------------
    def calibrate(self, warmup_feats: list[dict]):
        raise NotImplementedError

    # -- predicate generation (observables -> predicate vector) ----------------------------------
    def predicates(self, f: dict) -> list:
        raise NotImplementedError

    def observe(self, f: dict):
        """Optional online state update (behaviour baselines). Uses features, never labels."""


# ===================================================================== ULB (creditcard.csv)
class ULBAdapter(Adapter):
    name = "ULB"
    domain = "financial (PCA-anonymised)"
    signature = ["Time", "V1", "V14", "V17", "Amount", "Class"]
    label_col = "Class"

    def features(self, row):
        return {"t": _f(row["Time"]), "amount": _f(row["Amount"]),
                "v": [_f(row[f"V{i}"]) for i in range(1, 29)]}

    def label(self, row):
        return int(_f(row["Class"]))

    def calibrate(self, warmup):
        norms = [sum(x * x for x in f["v"]) ** 0.5 for f in warmup]
        maxc = [max(abs(x) for x in f["v"]) for f in warmup]
        amts = [f["amount"] for f in warmup]
        # V14 and V17 are the strongest anomaly axes on ULB; bound each independently
        v14 = [f["v"][13] for f in warmup]
        v17 = [f["v"][16] for f in warmup]
        self.calib = {"pca_norm_cap": _quantile(norms, Q), "max_comp_cap": _quantile(maxc, Q),
                      "amount_cap": _quantile(amts, Q),
                      "v14_lo": _quantile(v14, 100 - Q), "v17_lo": _quantile(v17, 100 - Q),
                      "warmup_n": len(warmup)}

    def predicates(self, f):
        c = self.calib
        norm = sum(x * x for x in f["v"]) ** 0.5
        return [
            P("amount_within_calibrated_cap", f["amount"] <= c["amount_cap"],
              f"{f['amount']:.2f} vs {c['amount_cap']:.2f}"),
            P("pca_norm_within_bound", norm <= c["pca_norm_cap"], f"|v|={norm:.2f}"),
            P("no_extreme_component", max(abs(x) for x in f["v"]) <= c["max_comp_cap"], ""),
            P("v14_not_anomalous", f["v"][13] >= c["v14_lo"], f"V14={f['v'][13]:.2f}"),
            P("v17_not_anomalous", f["v"][16] >= c["v17_lo"], f"V17={f['v'][16]:.2f}"),
        ]


# ===================================================================== IEEE-CIS
class IEEECISAdapter(Adapter):
    name = "IEEE-CIS"
    domain = "financial (transactions)"
    signature = ["isFraud", "TransactionDT", "TransactionAmt", "ProductCD", "card1"]
    label_col = "isFraud"

    def features(self, row):
        return {"t": _f(row["TransactionDT"]), "amount": _f(row["TransactionAmt"]),
                "product": row.get("ProductCD", ""), "card1": row.get("card1", ""),
                "card4": row.get("card4", ""), "card6": row.get("card6", ""),
                "addr1": row.get("addr1", ""), "pdom": row.get("P_emaildomain", ""),
                "rdom": row.get("R_emaildomain", "")}

    def label(self, row):
        return int(_f(row["isFraud"]))

    def calibrate(self, warmup):
        amts = [f["amount"] for f in warmup]
        self.calib = {"amount_cap": _quantile(amts, Q),
                      "products": {f["product"] for f in warmup if f["product"]},
                      "card4": {f["card4"] for f in warmup if f["card4"]},
                      "card6": {f["card6"] for f in warmup if f["card6"]},
                      "warmup_n": len(warmup)}
        self.state = {"card_amounts": {}}  # per-card behaviour baseline
        for f in warmup:
            self.state["card_amounts"].setdefault(f["card1"], []).append(f["amount"])

    def predicates(self, f):
        c = self.calib
        hist = self.state["card_amounts"].get(f["card1"], [])
        if len(hist) >= 5:
            med = statistics.median(hist)
            mad = statistics.median([abs(x - med) for x in hist]) or 1e-9
            z = 0.6745 * (f["amount"] - med) / mad
            behaviour_ok = z <= 8.0
            bdetail = f"card z={z:.2f}"
        else:
            behaviour_ok, bdetail = True, "baseline warming"
        return [
            P("amount_within_calibrated_cap", f["amount"] <= c["amount_cap"],
              f"{f['amount']:.2f} vs {c['amount_cap']:.2f}"),
            P("known_product_code", f["product"] in c["products"], f["product"]),
            P("recognized_card_network", (f["card4"] in c["card4"]) or not f["card4"], f["card4"]),
            P("recognized_card_type", (f["card6"] in c["card6"]) or not f["card6"], f["card6"]),
            P("billing_addr_present", bool(f["addr1"]), "addr1"),
            P("card_behaviour_normal", behaviour_ok, bdetail),
        ]

    def observe(self, f):
        self.state["card_amounts"].setdefault(f["card1"], []).append(f["amount"])


# ===================================================================== UNSW-NB15
class UNSWAdapter(Adapter):
    name = "UNSW-NB15"
    domain = "network intrusion telemetry"
    signature = ["proto", "service", "state", "sbytes", "dbytes", "label"]
    label_col = "label"
    order_sensitive = False    # stateless predicates; file is label-clustered -> shuffle for prevalence

    NORMAL_STATES = {"FIN", "CON", "REQ", "ACC"}

    def features(self, row):
        return {"dur": _f(row.get("dur")), "sbytes": _f(row.get("sbytes")),
                "dbytes": _f(row.get("dbytes")), "rate": _f(row.get("rate")),
                "sttl": _f(row.get("sttl")), "spkts": _f(row.get("spkts")),
                "dpkts": _f(row.get("dpkts")), "service": row.get("service", "-"),
                "state": row.get("state", "-")}

    def label(self, row):
        return int(_f(row["label"]))

    def calibrate(self, warmup):
        tot_bytes = [f["sbytes"] + f["dbytes"] for f in warmup]
        rates = [f["rate"] for f in warmup]
        durs = [f["dur"] for f in warmup]
        pkts = [f["spkts"] + f["dpkts"] for f in warmup]
        self.calib = {"bytes_cap": _quantile(tot_bytes, Q), "rate_cap": _quantile(rates, Q),
                      "dur_cap": _quantile(durs, Q), "pkts_cap": _quantile(pkts, Q),
                      "services": {f["service"] for f in warmup if f["service"] not in ("-", "")},
                      "ttls": {f["sttl"] for f in warmup},
                      "warmup_n": len(warmup)}

    def predicates(self, f):
        c = self.calib
        # NOTE: network analogues, documented. Not financial predicates.
        return [
            P("bytes_within_bound", (f["sbytes"] + f["dbytes"]) <= c["bytes_cap"],
              f"{f['sbytes']+f['dbytes']:.0f} vs {c['bytes_cap']:.0f}"),
            P("rate_within_bound", f["rate"] <= c["rate_cap"], f"{f['rate']:.1f}"),
            P("duration_within_bound", f["dur"] <= c["dur_cap"], f"{f['dur']:.3f}"),
            P("packets_within_bound", (f["spkts"] + f["dpkts"]) <= c["pkts_cap"], ""),
            P("recognized_service", (f["service"] in c["services"]) or f["service"] == "-",
              f["service"]),
            P("normal_connection_state", f["state"] in self.NORMAL_STATES, f["state"]),
            P("ttl_seen_in_baseline", f["sttl"] in c["ttls"], f"sttl={f['sttl']:.0f}"),
        ]


ADAPTERS = [ULBAdapter, IEEECISAdapter, UNSWAdapter]


# ===================================================================== discovery
def _header(path: Path) -> set[str]:
    try:
        with path.open(newline="") as fh:
            first = fh.readline()
        return {h.strip().strip('"').lstrip("﻿") for h in first.split(",")}
    except Exception:
        return set()


def discover() -> list[dict]:
    """Scan the search roots for CSVs matching any adapter's header signature.

    Returns one record per matched (adapter, file). A dataset that is absent simply does not
    appear -- it is never fabricated. Deterministic: roots and files are sorted.
    """
    found, seen_adapters = [], {}
    for root_name in SEARCH_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.csv")):
            if path.stat().st_size < 1024:
                continue
            hdr = _header(path)
            for A in ADAPTERS:
                if A.matches(hdr):
                    # keep the first (shallowest, then lexicographic) file per adapter
                    if A.name in seen_adapters:
                        continue
                    seen_adapters[A.name] = True
                    found.append({"adapter": A.name, "domain": A.domain, "path": str(path),
                                  "relpath": str(path.relative_to(ROOT)),
                                  "size_bytes": path.stat().st_size, "cls": A})
                    break
    return found


def status() -> dict:
    """Machine-readable discovery status for the registry / dashboard."""
    d = discover()
    present = {r["adapter"] for r in d}
    return {
        "search_roots": SEARCH_ROOTS,
        "adapters_registered": [A.name for A in ADAPTERS],
        "datasets_found": [{"adapter": r["adapter"], "domain": r["domain"],
                            "path": r["relpath"], "size_bytes": r["size_bytes"]} for r in d],
        "not_found": [A.name for A in ADAPTERS if A.name not in present],
    }
