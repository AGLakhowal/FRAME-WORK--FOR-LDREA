#!/usr/bin/env python3
"""Label-leakage audit of the mapped ULB corpus (Objective C, prerequisite).

READ-ONLY. Modifies no engine, no experiment, no existing artifact. It answers one question:

    Do the inputs that gamma_test_runner.evaluate_decision() reads depend on the ground-truth
    label `Class`, such that the reported authorization accuracy is a tautology rather than a
    detection result?

Method
    For every column the engine reads, partition the corpus by DecisionOutcome and test whether the
    observed value sets are DISJOINT. A disjoint input is, on this corpus, a perfect classifier: it
    alone determines the outcome. Disjointness is established empirically over all rows, not sampled.

    Additionally, each disjoint input is scored as a standalone single-feature classifier against
    the recoverable ground truth (ReasonCodes carries CLASS_0/CLASS_1 verbatim).

Output
    label_leakage_audit.json   (NEW artifact; nothing existing is read for writing or changed)

    python experiments/audit_label_leakage.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "GAMMA_G0_CREDITCARD_FULL_mapped.csv"
OUT = ROOT / "label_leakage_audit.json"

# Exactly the columns gamma_test_runner.evaluate_decision() consults.
NODE_GATES = ["Gate_A1", "Gate_A2", "Gate_A3", "Gate_A4", "Gate_A5", "Gate_A6", "Gate_A7", "Lambda_G"]
ENGINE_INPUTS = NODE_GATES + ["HARM_RISK", "StaleContext", "TelemetryFresh", "ReasonCodes"]

csv.field_size_limit(1 << 24)


def _truth(reason: str) -> int:
    """Ground truth recovered from the corpus itself: ReasonCodes embeds the label verbatim."""
    r = reason.upper()
    if "CLASS_1" in r:
        return 1
    if "CLASS_0" in r:
        return 0
    return -1


def run() -> dict:
    if not CORPUS.exists():
        raise SystemExit(f"corpus not found: {CORPUS}")

    values = defaultdict(lambda: defaultdict(set))   # col -> label -> {values}
    counts = defaultdict(lambda: defaultdict(Counter))
    labels = Counter()
    n = 0

    with CORPUS.open(newline="") as fh:
        rd = csv.DictReader(fh)
        for row in rd:
            y = _truth(row.get("ReasonCodes", ""))
            labels[y] += 1
            n += 1
            for c in ENGINE_INPUTS:
                v = row.get(c, "")
                values[c][y].add(v)
                # bound memory: HARM_RISK on legit rows is continuous
                if len(counts[c][y]) < 64:
                    counts[c][y][v] += 1

    n_fraud, n_legit = labels[1], labels[0]
    findings = []
    for c in ENGINE_INPUTS:
        s0, s1 = values[c].get(0, set()), values[c].get(1, set())
        overlap = s0 & s1
        disjoint = bool(s0) and bool(s1) and not overlap
        constant_on_fraud = len(s1) == 1
        # a disjoint input is a perfect single-feature classifier on this corpus
        acc = 1.0 if disjoint else None
        findings.append({
            "column": c,
            "distinct_values_on_legit": len(s0),
            "distinct_values_on_fraud": len(s1),
            "example_legit": sorted(s0)[0] if s0 else None,
            "example_fraud": sorted(s1)[0] if s1 else None,
            "value_sets_disjoint": disjoint,
            "constant_on_fraud_rows": constant_on_fraud,
            "overlapping_values": len(overlap),
            "standalone_classifier_accuracy": acc,
            "leaks_label": disjoint,
        })

    leaking = [f["column"] for f in findings if f["leaks_label"]]
    clean = [f["column"] for f in findings if not f["leaks_label"]]

    return {
        "audit": "label_leakage_of_engine_inputs",
        "evidence_level": "Benchmark Evidence (read-only audit of an existing corpus)",
        "corpus": CORPUS.name,
        "rows_examined": n,
        "ground_truth_source": "ReasonCodes (embeds CLASS_0 / CLASS_1 verbatim)",
        "class_balance": {"legit_class_0": n_legit, "fraud_class_1": n_fraud},
        "engine_entrypoint": "gamma_test_runner.evaluate_decision",
        "columns_examined": ENGINE_INPUTS,
        "findings": findings,
        "leaking_inputs": leaking,
        "non_leaking_inputs": clean,
        "verdict": {
            "label_leakage_present": bool(leaking),
            "n_leaking_inputs": len(leaking),
            "interpretation": (
                "Every listed leaking input has value sets that are perfectly disjoint across the "
                "two classes over all rows. Each is therefore, alone, a 100%-accurate classifier on "
                "this corpus. They were produced from the label: gamma_map_raw.py writes "
                "'Class == 1 -> HARM_RISK high, Gate_A3 & Gate_A7 & Lambda_G fail' and encodes the "
                "label verbatim into ReasonCodes."),
            "consequence": (
                "The reported authorization accuracy and the 0-false-permit result on this corpus "
                "are CONFORMANCE results: they establish that the reference monitor faithfully "
                "enforces the predicates it is given. They are NOT detection results, and must not "
                "be read as evidence that L-DREA can identify fraud from observable runtime "
                "features. No claim of runtime detection is supported by this corpus."),
            "what_would_be_required": (
                "Blind runtime detection requires the raw ULB features (Time, V1..V28, Amount) with "
                "Class withheld until after the decision. Those columns are not present anywhere in "
                "this repository; the mapping discarded them. Supply creditcard.csv and run "
                "experiments/experiment_runtime_detection.py."),
        },
        "does_not_invalidate": [
            "Replay integrity (E2) — independent of how predicates were produced.",
            "Formal verification (E3) — a property of the decision model, not the corpus.",
            "Predicate coverage (E9) — a synthetic suite over the frozen entry point.",
            "Non-compensatory soundness — a property of the aggregation rule.",
        ],
    }


def main() -> int:
    rep = run()
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    v = rep["verdict"]
    print(f"[leakage-audit] rows={rep['rows_examined']:,} "
          f"legit={rep['class_balance']['legit_class_0']:,} "
          f"fraud={rep['class_balance']['fraud_class_1']:,}")
    print(f"[leakage-audit] leaking engine inputs: {v['n_leaking_inputs']} -> {rep['leaking_inputs']}")
    print(f"[leakage-audit] non-leaking: {rep['non_leaking_inputs']}")
    print(f"[leakage-audit] label_leakage_present = {v['label_leakage_present']}")
    print(f"[leakage-audit] wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
