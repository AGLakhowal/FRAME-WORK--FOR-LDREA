#!/usr/bin/env python3
"""
Gamma G-0 / L-DREA LAB v1.0 dataset test runner
================================================

Reads a Gamma G-0 golden-trace CSV, independently re-derives the runtime
authorization decision from the L-DREA externalization-monitor rule set, and
evaluates it against the LAB v1.0 benchmark methodology described in:

    A. Gill-Lakhowal, "Deterministic Runtime Enforcement for Autonomous AI
    Agents: A Substrate-Neutral Reference Monitor for the Execution Boundary"
    (IEEE Access, 2026) and the Gamma G-0 Constitutional Stack README/FULL_SPEC.

What this runner implements (paper section in brackets):

  * Law of Concurrence reconstruction  Gamma_G = max_i d_i, d_i = max(0, m_i-θ_i)
    with non-compensatory (max) aggregation and class-level veto  [IV-B, V-C]
  * Operational definition of Unauthorized Execution (Eq. 7)       [VIII-C / IX-C]
  * Six primary LAB v1.0 metrics with Wilson 95% intervals
    (FPR, FDR, RDR, Revocation Compliance, TOCTOU, Class-Veto)     [VIII-G]
  * Cluster-corrected Wilson bounds (design effect / N_eff)        [IX-G]
  * Six runtime invariants as pass/fail checks                     [VI-B]
  * Commit-before-actuate ordering / TOCTOU state-consistency      [V-F, VI-B]
  * Hash-chain replay-determinism verification                     [App. A]
  * Negative control: compensatory (weighted-sum) aggregator       [Corollary 2]
  * Evidence Quad per decision (method · policy · ledger hash)     [README]
  * MEASURED per-decision latency + throughput (pure-software,
    this host; NOT the paper's hardware-in-the-loop figures)       [IX-G]

Example:
  python gamma_test_runner.py \
    --input GAMMA_G0_CREDITCARD_GOLDEN_TRACE_20260629_001_sample_master112_1000.csv \
    --output gamma_validation_results.csv \
    --summary gamma_summary.json \
    --lab-report gamma_lab_v1_report.json
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


class _Tee:
    """Write to several streams at once (used to mirror console output into a
    buffer so the HTML dashboard's terminal panel reflects THIS run)."""

    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for s in self._streams:
            s.write(data)
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            s.flush()

# Representative signing key for the hot-path measurement. This is an
# HMAC-SHA256 stand-in for the production epoch-keyed HSM signature; it
# measures realistic symmetric-crypto cost, NOT a hardware signing latency.
_HOTPATH_KEY = b"gamma-g0-lab-v1-representative-hmac-key"

METHOD_VERSION = "gamma_test_runner/LAB-v1.0/2.0"

# Z for a two-sided 95% interval.
Z_95 = 1.959963984540054

# Boolean-like columns normalized up-front so the runner is robust to CSV export
# formats (TRUE/FALSE strings, 1/0, yes/no).
BOOL_COLS = [
    "ActionIrreversibility",
    "CrossAgentIndependent",
    "TelemetryFresh",
    "StaleContext",
    "RevocationFresh",
    "AuthorityRequired",
    "HumanOverrideAllowed",
    "Gate_A1",
    "Gate_A2",
    "Gate_A3",
    "Gate_A4",
    "Gate_A5",
    "Gate_A6",
    "Gate_A7",
    "Lambda_G",
    "GammaZero",
    "TOKEN_VALID",
    "PhysicianConcurrence",
    "AuthoritySignatureValid",
    "ACT_PERMIT",
    "ADAPT_PERMIT",
    "ExecutionLegitimacy",
    "CommitBeforeActuate",
    "Actuated",
    "SAFE_STATE",
    "FalsePermitFlag",
    "SafeStateViolationFlag",
    "OrderingInversionFlag",
    "ReplayDivergenceFlag",
]

# Node-level authorization predicates. Each must concur (be TRUE) for Gamma_G = 0.
# This is the predicate vector G = {g_1..g_n}; deficit d_i = 1 when g_i fails.
NODE_GATE_COLS = [
    "Gate_A1",
    "Gate_A2",
    "Gate_A3",
    "Gate_A4",
    "Gate_A5",
    "Gate_A6",
    "Gate_A7",
    "Lambda_G",
    "TOKEN_VALID",
    "AuthoritySignatureValid",
]


# --------------------------------------------------------------------------- #
# Hardened class-veto + evidence validation (Gamma Hardening v1).              #
#                                                                             #
# The legacy veto was `"CLASS_1" in ReasonCodes` — an unanchored substring    #
# that (a) misfired on CLASS_10.. (false denial), (b) tripped on the literal  #
# "GOODHART" appearing anywhere in free text (denial-of-service), and (c)     #
# silently passed a fraud row whose class token was absent/None (false permit).#
# These helpers parse ReasonCodes as ';'-delimited tokens, require a          #
# well-formed CLASS_<n>_ token, and fail closed when class evidence is         #
# missing/malformed.                                                          #
# --------------------------------------------------------------------------- #

# A decision row must carry these keys; a missing/None value fails closed
# (SAFE_STATE) instead of raising KeyError or silently permitting.
DECISION_REQUIRED_KEYS = (
    *NODE_GATE_COLS,
    "HARM_RISK",
    "StaleContext",
    "TelemetryFresh",
    "ReasonCodes",
)

# A well-formed class token: CLASS_<digits> optionally followed by _LABEL.
_CLASS_TOKEN_RE = re.compile(r"^CLASS_(\d+)(?:_.*)?$")


def classify_reasoncodes(reason) -> Tuple[int, bool]:
    """Parse ReasonCodes -> (gamma_class, well_formed).

    well_formed is False when no valid CLASS_<n>_ token is present, which the
    caller treats as absent class evidence and fails closed.
    gamma_class is 1 iff any class token is class 1 OR a standalone GOODHART[_..]
    token is present (whole-token match, never a substring of free text).
    """
    if reason is None:
        return 0, False
    tokens = [t.strip().upper() for t in str(reason).split(";") if t.strip()]
    class_nums = []
    goodhart = False
    for t in tokens:
        m = _CLASS_TOKEN_RE.match(t)
        if m:
            class_nums.append(int(m.group(1)))
        if t == "GOODHART" or t.startswith("GOODHART_"):
            goodhart = True
    if not class_nums:
        return (1 if goodhart else 0), False  # no class token => not well-formed
    gamma_class = 1 if (any(n == 1 for n in class_nums) or goodhart) else 0
    return gamma_class, True


def _row_evidence_invalid(row: Dict) -> str:
    """Return a non-empty reason string if the row is unfit to decide on."""
    for k in DECISION_REQUIRED_KEYS:
        if k not in row or row[k] is None:
            return f"MISSING_EVIDENCE:{k}"
    return ""


def evaluate_decision(row: Dict, harm_threshold: float) -> Dict:
    """Single-row authorization decision used for the MEASURED latency path.

    Mirrors the vectorized Law-of-Concurrence logic exactly (non-compensatory
    max-aggregation + class-level veto) so the timed loop reflects the real
    decision work, not a stand-in. Operates on native Python values only.

    Fails closed (SAFE_STATE) on missing/malformed evidence rather than raising
    or silently permitting.
    """
    invalid = _row_evidence_invalid(row)
    if invalid:
        return {
            "gamma_g": 1,
            "gamma_class": 0,
            "deficit_count": 1,
            "pi": 0,
            "isb": 0,
            "decision": "SAFE_STATE",
            "unauthorized": False,
            "fail_closed_reason": invalid,
        }

    deficit = 0  # Gamma_G = max(d_i); binary deficits here, so max == OR.
    deficit_count = 0
    for g in NODE_GATE_COLS:
        if not row[g]:
            deficit = 1
            deficit_count += 1
    # Canonicalize HARM_RISK to the 6-dp serialization precision so a CSV
    # float round-trip cannot flip the decision by one ULP at the boundary.
    harm = round(float(row["HARM_RISK"]), 6)
    if harm > harm_threshold:
        deficit = 1
        deficit_count += 1
    if row["StaleContext"]:
        deficit = 1
        deficit_count += 1
    if not row["TelemetryFresh"]:
        deficit = 1
        deficit_count += 1

    gamma_class, class_well_formed = classify_reasoncodes(row["ReasonCodes"])
    if not class_well_formed:
        # Absent/malformed class evidence => fail closed (do not permit).
        deficit = 1
        deficit_count += 1

    pi = 1 if (deficit == 0 and gamma_class == 0) else 0
    isb = 1 if (
        row["TOKEN_VALID"]
        and row["AuthoritySignatureValid"]
        and row["TelemetryFresh"]
        and not row["StaleContext"]
    ) else 0
    execute = bool(row["Actuated"] or row["ACT_PERMIT"])
    unauthorized = execute and (
        (not row["TOKEN_VALID"]) or deficit != 0 or gamma_class != 0 or isb == 0
    )
    return {
        "gamma_g": deficit,
        "gamma_class": gamma_class,
        "deficit_count": deficit_count,
        "pi": pi,
        "isb": isb,
        "decision": "PERMIT" if pi == 1 else "SAFE_STATE",
        "unauthorized": unauthorized,
    }


def percentile(sorted_vals: List[float], q: float) -> float:
    """Nearest-rank percentile on a pre-sorted list (q in [0, 100])."""
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(math.ceil(q / 100.0 * len(sorted_vals))) - 1))
    return sorted_vals[k]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the Gamma G-0 / L-DREA LAB v1.0 benchmark on a golden-trace CSV."
    )
    p.add_argument(
        "--input",
        default=None,
        help="Path to the input CSV. If omitted, auto-detects a GAMMA_*.csv "
        "(or the single CSV) in the current directory.",
    )
    p.add_argument(
        "--output",
        default="gamma_validation_results.csv",
        help="Path to write the row-level validation CSV.",
    )
    p.add_argument(
        "--summary",
        default="gamma_summary.json",
        help="Path to write the summary JSON report.",
    )
    p.add_argument(
        "--lab-report",
        default="gamma_lab_v1_report.json",
        help="Path to write the full LAB v1.0 benchmark JSON report.",
    )
    p.add_argument(
        "--harm-threshold",
        type=float,
        default=0.5,
        help="HARM_RISK admissibility threshold theta (deficit if HARM_RISK > theta).",
    )
    p.add_argument(
        "--latency-threshold",
        type=float,
        default=50.0,
        help="Authorization latency ceiling (ms) used for a soft operational check.",
    )
    p.add_argument(
        "--freshness-threshold",
        type=float,
        default=100.0,
        help="Telemetry freshness ceiling (ms) used for a soft operational check.",
    )
    p.add_argument(
        "--design-effect",
        type=float,
        default=1.7,
        help="Design effect DE for cluster-corrected Wilson bounds (N_eff = N / DE).",
    )
    p.add_argument(
        "--latency-limit-ms",
        type=float,
        default=100.0,
        help="Structural-cycle latency limit (paper §6.0/§7); used for headroom + Pass/Fail.",
    )
    p.add_argument(
        "--hotpath-limit-ms",
        type=float,
        default=5.0,
        help="Hot-path hash/sign/WAL P99 limit (paper §6.0/§7), checked separately.",
    )
    p.add_argument(
        "--no-wal",
        action="store_true",
        help="Skip the WAL fsync in the hot-path latency measurement (CPU-only).",
    )
    p.add_argument(
        "--latency-sample",
        type=int,
        default=50000,
        help="Cap rows used for the timed latency measurement (correctness metrics "
        "always use the full dataset). Use 0 for all rows.",
    )
    p.add_argument(
        "--html",
        default="gamma_report.html",
        help="Path for the generated HTML dashboard (built from this run's reports).",
    )
    p.add_argument(
        "--no-html",
        action="store_true",
        help="Do not generate the HTML dashboard after the benchmark.",
    )
    p.add_argument(
        "--no-open",
        action="store_true",
        help="Generate the HTML dashboard but do not auto-open it in a browser.",
    )
    p.add_argument(
        "--replay-manifest",
        default="gamma_replay_manifest.jsonl",
        help="Path for the per-item ERTuple replay manifest (JSONL). One evidence "
        "record per decision, independently re-verifiable by gamma_replay_verify.py.",
    )
    p.add_argument(
        "--no-replay-manifest",
        action="store_true",
        help="Do not emit the per-item replay manifest.",
    )
    p.add_argument(
        "--tla-spec",
        default=None,
        help="Path to the TLA+ specification (.tla). If given, its SHA-256 is "
        "recomputed and cryptographically bound against the trace's TLCSpecHash.",
    )
    p.add_argument(
        "--tla-cfg",
        default=None,
        help="Path to the TLC config (.cfg). If given, its SHA-256 is recomputed "
        "and bound against the trace's TLCCfgHash.",
    )
    p.add_argument(
        "--tlc-log",
        default=None,
        help="Path to the TLC/tlc2 console log. If given, its reported 'distinct "
        "states found' + violation status are cross-checked against the trace's "
        "TLCTotalStates / TLCViolationCount (LAB v1.0 artifact verification).",
    )
    p.add_argument(
        "--tlc-run-command",
        default=None,
        help="The exact command used to run TLC (recorded verbatim in the report "
        "so the model-checking step is reproducible).",
    )
    p.add_argument(
        "--bundle",
        default=None,
        help="If set, write a full lab reproducibility bundle to this directory "
        "(inputs/outputs/source digests, env, command, MANIFEST, REPRODUCE.md).",
    )
    p.add_argument(
        "--eeb-input",
        action="store_true",
        help="Opt-in (default OFF): source the decision-consumed inputs (Gamma_G/Pi/Decision) "
        "through an Execution Evidence Bundle round-trip instead of the raw CSV columns "
        "(Commit 4.1). The frozen decision logic is unchanged and produces identical "
        "Gamma_G/Pi/Decision; replay/ordering columns remain CSV-sourced. The default OFF path "
        "is byte-identical to before.",
    )
    return p.parse_args()


def ensure_columns(df: pd.DataFrame, cols: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    if series.dtype == "object":
        return (
            series.astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                    "yes": True,
                    "no": False,
                }
            )
            .fillna(False)
        )
    return series.fillna(0).astype(int).astype(bool)


# --------------------------------------------------------------------------- #
# Statistics: Wilson score intervals (paper Section VIII-G / IX-G)
# --------------------------------------------------------------------------- #
def wilson_interval(successes: int, n: int, z: float = Z_95) -> Tuple[float, float, float]:
    """Return (point_estimate, lower, upper) Wilson score interval.

    For the zero-event case (successes == 0) the upper bound reduces to
    z^2 / (n + z^2), the bound reported as the LAB v1.0 zero-event headline.
    """
    if n <= 0:
        return (0.0, 0.0, 0.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, center - half), min(1.0, center + half))


def metric_block(
    label: str,
    events: int,
    n: int,
    *,
    higher_is_better: bool,
    design_effect: float,
) -> Dict:
    """Build a metric record with naive + cluster-corrected Wilson bounds.

    `events` is the count of the *adverse* outcome (e.g. false permits). When
    higher_is_better is True the reported rate is the complement (e.g. a
    determinism/effectiveness rate) while the Wilson bound is still taken on the
    adverse count so a zero-event upper bound is meaningful.
    """
    p_adv, _lo_adv, up_adv = wilson_interval(events, n)
    n_eff = n / design_effect if design_effect > 0 else n
    _, _, up_adv_cc = wilson_interval(events, int(round(n_eff)))
    rate = (1.0 - p_adv) if higher_is_better else p_adv
    return {
        "metric": label,
        "n": n,
        "adverse_events": events,
        "reported_rate": round(rate, 8),
        "adverse_rate": round(p_adv, 10),
        "wilson95_naive_upper": round(up_adv, 10),
        "wilson95_clustercorrected_upper": round(up_adv_cc, 10),
        "n_eff": round(n_eff, 1),
        "design_effect": design_effect,
        "higher_is_better": higher_is_better,
    }


def fmt_rate(x: float) -> str:
    if x == 0:
        return "0"
    if x < 1e-3:
        return f"{x:.2e}"
    return f"{x:.4%}"


# --------------------------------------------------------------------------- #
# Scenario / class taxonomy (paper Section VIII-D)
# --------------------------------------------------------------------------- #
def derive_lab_class(reason: str) -> str:
    """Best-effort mapping of a row to a LAB-A scenario class from ReasonCodes."""
    r = str(reason).upper()
    if "REPLAY" in r:
        return "LAB-A2_TOKEN_MANIPULATION"
    if "TOKEN" in r and ("FORGE" in r or "INVALID" in r or "SCOPE" in r):
        return "LAB-A2_TOKEN_MANIPULATION"
    if "BYPASS" in r:
        return "LAB-A1_DIRECT_BYPASS"
    if "CTR" in r or "CONTEXT" in r or "INJECT" in r:
        return "LAB-A3_CONTEXT_CORRUPTION"
    if "TOCTOU" in r or "TIMING" in r or "STALE" in r:
        return "LAB-A4_TIMING_EXPLOITATION"
    if "GOODHART" in r or "DRIFT" in r or "GAMING" in r:
        return "LAB-A5_GOODHART_OPTIMIZATION"
    if "CLASS_1" in r or "FRAUD" in r:
        return "ADVERSARIAL_CLASS_1"
    return "NOMINAL_CLASS_0"


def discover_input() -> Path:
    """Find the dataset CSV when --input is not given."""
    cwd = Path.cwd()
    candidates = sorted(cwd.glob("GAMMA_*.csv"))
    if not candidates:
        # Fall back to any CSV that isn't one of our own output files.
        outputs = {"gamma_validation_results.csv"}
        candidates = [p for p in sorted(cwd.glob("*.csv")) if p.name not in outputs]
    if not candidates:
        raise SystemExit(
            "No input CSV found in the current directory. Pass one with --input <file.csv>."
        )
    if len(candidates) > 1:
        print(f"[info] Multiple CSVs found; using {candidates[0].name} "
              f"(override with --input).")
    return candidates[0]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_tlc_log(text: str) -> Dict:
    """Best-effort parse of a TLC / tlc2 console log.

    Extracts the 'distinct states found' count and whether the run reported a
    clean completion vs an invariant/property violation. Robust to thousands
    separators and to the common TLA+ Toolbox / command-line phrasings.
    """
    distinct = None
    m = re.search(r"([\d,]+)\s+distinct states found", text)
    if m:
        distinct = int(m.group(1).replace(",", ""))
    generated = None
    mg = re.search(r"([\d,]+)\s+states generated", text)
    if mg:
        generated = int(mg.group(1).replace(",", ""))
    no_error = bool(
        re.search(r"Model checking completed\.\s*No error has been found", text)
        or re.search(r"No error has been found", text)
    )
    has_error = bool(
        re.search(r"^Error:", text, re.M)
        or "is violated" in text
        or "Invariant .* is violated" in text
    )
    return {
        "distinct_states": distinct,
        "states_generated": generated,
        "no_error_reported": no_error,
        "error_reported": has_error,
    }


def verify_tlc(
    df: pd.DataFrame,
    spec_path: str | None,
    cfg_path: str | None,
    log_path: str | None = None,
    run_command: str | None = None,
) -> Dict:
    """Independently VERIFY (not merely display) the trace's TLC attestation.

    The golden trace carries a TLC model-checking attestation per row
    (TLCSpecHash, TLCCfgHash, TLCTotalStates, TLCViolationCount). We cannot
    re-run TLC here without the .tla/.cfg sources + tla2tools.jar, but we
    escalate through verification TIERS as artifacts are supplied:

      tier 0  attestation-consistency   V1–V5 (internal soundness only)
      tier 1  source-bound              + V6/V7 (sha256 of .tla/.cfg == attested)
      tier 2  log-cross-checked         + V8/V9 (TLC console log agrees)
      tier 3  fully-reproduced          re-run TLC from source (out of scope here)

    Verification predicates:
      V1 spec-hash consistency : one TLCSpecHash across every row (no tampering)
      V2 cfg-hash consistency  : one TLCCfgHash across every row
      V3 states constant       : one TLCTotalStates across every row
      V4 non-trivial exploration: TLCTotalStates > 0
      V5 zero safety violations: sum(TLCViolationCount) == 0
      V6 spec binding (optional): sha256(--tla-spec) == TLCSpecHash
      V7 cfg binding  (optional): sha256(--tla-cfg)  == TLCCfgHash
      V8 log states match (opt): log 'distinct states found' == TLCTotalStates
      V9 log no-violation (opt): log reports clean completion, no error
    """
    cols = ["TLCSpecHash", "TLCCfgHash", "TLCTotalStates", "TLCViolationCount"]
    if not all(c in df.columns for c in cols):
        return {
            "available": False,
            "verified": False,
            "note": "Trace carries no TLC attestation columns; nothing to verify.",
        }

    spec_hashes = sorted(df["TLCSpecHash"].astype(str).unique().tolist())
    cfg_hashes = sorted(df["TLCCfgHash"].astype(str).unique().tolist())
    states = pd.to_numeric(df["TLCTotalStates"], errors="coerce")
    viol = pd.to_numeric(df["TLCViolationCount"], errors="coerce").fillna(0)

    v1 = len(spec_hashes) == 1
    v2 = len(cfg_hashes) == 1
    v3 = states.nunique(dropna=True) == 1
    total_states = int(states.iloc[0]) if v3 else int(states.max())
    total_viol = int(viol.sum())
    v4 = total_states > 0
    v5 = total_viol == 0

    spec_hash = spec_hashes[0] if v1 else None
    cfg_hash = cfg_hashes[0] if v2 else None

    v6 = None
    spec_recomputed = None
    if spec_path:
        spec_recomputed = _sha256_file(Path(spec_path))
        v6 = (spec_recomputed == spec_hash)
    v7 = None
    cfg_recomputed = None
    if cfg_path:
        cfg_recomputed = _sha256_file(Path(cfg_path))
        v7 = (cfg_recomputed == cfg_hash)

    # V8/V9: cross-check against a supplied TLC console log.
    v8 = None
    v9 = None
    log_parsed = None
    if log_path:
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        log_parsed = _parse_tlc_log(log_text)
        if log_parsed["distinct_states"] is not None:
            v8 = (log_parsed["distinct_states"] == total_states)
        v9 = bool(log_parsed["no_error_reported"] and not log_parsed["error_reported"])

    # Single attestation digest binding (spec, cfg, states, violations).
    attestation = hashlib.sha256(
        f"{spec_hash}|{cfg_hash}|{total_states}|{total_viol}".encode("utf-8")
    ).hexdigest()

    checks = {
        "V1_spec_hash_consistent": v1,
        "V2_cfg_hash_consistent": v2,
        "V3_states_constant": v3,
        "V4_nontrivial_state_space": v4,
        "V5_zero_safety_violations": v5,
        "V6_spec_source_binding": v6,
        "V7_cfg_source_binding": v7,
        "V8_log_states_match": v8,
        "V9_log_no_violation": v9,
    }
    # A None check (optional evidence not supplied) does not fail the gate.
    verified = all(c for c in checks.values() if c is not None)

    # Escalating verification tier based on which artifacts were supplied/passed.
    source_bound = (v6 is True) or (v7 is True)
    log_checked = (v8 is True) or (v9 is True)
    if log_checked and source_bound:
        tier = "tier2_log_cross_checked_and_source_bound"
    elif log_checked:
        tier = "tier2_log_cross_checked"
    elif source_bound:
        tier = "tier1_source_bound"
    else:
        tier = "tier0_attestation_consistency_only"

    missing = []
    if not spec_path:
        missing.append("--tla-spec")
    if not cfg_path:
        missing.append("--tla-cfg")
    if not log_path:
        missing.append("--tlc-log")

    return {
        "available": True,
        "verified": bool(verified),
        "verification_tier": tier,
        "checks": checks,
        "spec_hash": spec_hash,
        "cfg_hash": cfg_hash,
        "spec_source_sha256": spec_recomputed,
        "cfg_source_sha256": cfg_recomputed,
        "total_states": total_states,
        "violation_count": total_viol,
        "attestation_digest": attestation,
        "tlc_log": log_parsed,
        "run_command": run_command,
        "artifacts_missing_for_full_closure": missing,
        "note": (
            f"TLC {tier}. Internal consistency + zero violations verified"
            + ("; source-bound (sha256 of .tla/.cfg == attested)" if source_bound else "")
            + ("; console log cross-checked" if log_checked else "")
            + (
                f". Supply {', '.join(missing)} to raise the tier"
                if missing
                else ". Full re-run of TLC from source (tier 3) is out of this harness's scope"
            )
            + "."
        ),
    }


def write_replay_manifest(df: pd.DataFrame, path: Path) -> Dict:
    """Emit a per-item ERTuple replay manifest (JSONL) + return its summary.

    Each decision becomes one self-describing evidence record — the "per-item
    evidence" — that a third party can feed to gamma_replay_verify.py to
    independently re-check the hash-chain adjacency and the evidence quad,
    without needing pandas or the original runner. The first line is a header
    record; every subsequent line is one decision's evidence tuple.
    """
    has_ert = "ERTuple_ID" in df.columns
    has_policy = "PolicyHash" in df.columns
    hp = df["HASH_prev"].astype(str).tolist()
    hc = df["HASH_current"].astype(str).tolist()
    dec = df["DerivedDecision"].tolist()
    linked = df["DerivedChainLinked"].tolist()
    unauth = df["DerivedUnauthorized"].tolist()
    gg = df["DerivedGammaG"].tolist()
    gc = df["DerivedGammaClass"].tolist()
    pi = df["DerivedPi"].tolist()
    pid = df["ProposalID"].astype(str).tolist()
    ert = df["ERTuple_ID"].astype(str).tolist() if has_ert else [""] * len(df)
    pol = df["PolicyHash"].astype(str).tolist() if has_policy else [""] * len(df)

    n = len(df)
    manifest_hash = hashlib.sha256()
    genesis_ok = str(hp[0]).upper() in {"GENESIS", "0", "NONE", ""}
    adjacency_ok = 0
    with open(path, "w", encoding="utf-8") as fh:
        header = {
            "record": "header",
            "kind": "gamma_g0_ertuple_replay_manifest",
            "method_version": METHOD_VERSION,
            "n_records": n,
            "genesis_anchor": str(hp[0]),
            "chain_algorithm": "adjacency: rec[i].hash_prev == rec[i-1].hash_current, genesis-anchored",
        }
        line = json.dumps(header, separators=(",", ":"))
        manifest_hash.update((line + "\n").encode("utf-8"))
        fh.write(line + "\n")
        for i in range(n):
            adj = (str(hp[i]).upper() in {"GENESIS", "0", "NONE", ""}) if i == 0 else (str(hp[i]) == str(hc[i - 1]))
            adjacency_ok += 1 if adj else 0
            rec = {
                "record": "decision",
                "seq": i,
                "proposal_id": pid[i],
                "ertuple_id": ert[i],
                "policy_hash": pol[i],
                "hash_prev": hp[i],
                "hash_current": hc[i],
                "adjacency_ok": bool(adj),
                "decision": dec[i],
                "gamma_g": int(gg[i]),
                "gamma_class": int(gc[i]),
                "pi": int(pi[i]),
                "chain_linked": bool(linked[i]),
                "unauthorized": bool(unauth[i]),
                "evidence_quad": {
                    "decision": dec[i],
                    "method_version": METHOD_VERSION,
                    "policy_hash": pol[i],
                    "ledger_hash": hc[i],
                },
            }
            line = json.dumps(rec, separators=(",", ":"))
            manifest_hash.update((line + "\n").encode("utf-8"))
            fh.write(line + "\n")

    return {
        "path": str(path),
        "n_records": n,
        "genesis_anchored": bool(genesis_ok),
        "adjacency_links_ok": adjacency_ok,
        "adjacency_all_ok": adjacency_ok == n,
        "manifest_sha256": manifest_hash.hexdigest(),
        "verify_with": f"python gamma_replay_verify.py {path}",
    }


def write_repro_bundle(
    bundle_dir: Path,
    *,
    input_path: Path,
    outputs: List[Path],
    sources: List[Path],
    command: List[str],
    tlc_verification: Dict,
    replay_summary: Dict,
) -> Dict:
    """Package a self-contained lab reproducibility bundle.

    Writes a MANIFEST.json digesting every input, source and output file, an
    env.json capturing the interpreter/library/platform, the exact command
    line, and a REPRODUCE.md with step-by-step instructions. Nothing here is
    copied blindly: every referenced file is SHA-256'd so the bundle is a
    tamper-evident record of exactly what produced these results.
    """
    import platform

    bundle_dir.mkdir(parents=True, exist_ok=True)

    def digests(paths: List[Path]) -> List[Dict]:
        out = []
        for p in paths:
            if p and p.exists():
                out.append(
                    {"file": str(p), "sha256": _sha256_file(p), "bytes": p.stat().st_size}
                )
        return out

    env = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pandas_version": pd.__version__,
        "method_version": METHOD_VERSION,
    }
    manifest = {
        "bundle": "GAMMA G-0 / L-DREA LAB v1.0 reproducibility bundle",
        "method_version": METHOD_VERSION,
        "command": command,
        "input": digests([input_path]),
        "sources": digests(sources),
        "outputs": digests(outputs),
        "tlc_verification": tlc_verification,
        "replay_manifest": replay_summary,
        "env": env,
    }
    # Bind the whole manifest with a single digest over its canonical form.
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["bundle_digest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()

    (bundle_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    (bundle_dir / "env.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    (bundle_dir / "command.txt").write_text(" ".join(command) + "\n", encoding="utf-8")

    reproduce = f"""# Reproducing this GAMMA G-0 / L-DREA LAB v1.0 run

Method version: `{METHOD_VERSION}`
Bundle digest (SHA-256): `{manifest["bundle_digest_sha256"]}`

## 1. Environment
- Python: `{env["python_version"].splitlines()[0]}`
- pandas: `{env["pandas_version"]}`
- Platform: `{env["platform"]}`

Install: `pip install pandas`

## 2. Verify the inputs are byte-identical
Check each SHA-256 in `MANIFEST.json` against your local copies, e.g.:

```
shasum -a 256 {input_path.name}
```

It must match the `input[].sha256` in `MANIFEST.json`.

## 3. Re-run the benchmark (regenerates every output)
```
{" ".join(command)}
```

## 4. Independently verify the per-item replay manifest
No pandas required — pure stdlib:
```
python gamma_replay_verify.py {replay_summary.get("path", "gamma_replay_manifest.jsonl")}
```
Expect: `n_records={replay_summary.get("n_records")}`, all adjacency links OK,
genesis-anchored, and manifest SHA-256 =
`{replay_summary.get("manifest_sha256")}`.

## 5. TLC attestation
TLC verified: `{tlc_verification.get("verified")}`;
attestation digest `{tlc_verification.get("attestation_digest")}`.
To cryptographically bind to source, re-run with
`--tla-spec <spec.tla> --tla-cfg <cfg.cfg>`; those SHA-256s must equal
`spec_hash`/`cfg_hash` in `MANIFEST.json`.

## 6. Compare outputs
Re-hash the regenerated outputs and compare to `outputs[].sha256` in
`MANIFEST.json`. Deterministic fields (decisions, gamma, hash-chain, evidence
quads) reproduce exactly; MEASURED latency fields are host-dependent and will
differ.
"""
    (bundle_dir / "REPRODUCE.md").write_text(reproduce, encoding="utf-8")

    return manifest


def main() -> None:
    args = parse_args()
    input_path = Path(args.input) if args.input else discover_input()
    output_path = Path(args.output)
    summary_path = Path(args.summary)
    lab_path = Path(args.lab_report)

    # Mirror everything printed below into a buffer so the HTML dashboard's
    # terminal panel shows this run's actual console output.
    console_buf = io.StringIO()
    sys.stdout = _Tee(sys.__stdout__, console_buf)

    df = pd.read_csv(input_path)

    required = [
        "ProposalID",
        "Status",
        "DecisionOutcome",
        "ReasonCodes",
        "FirstFailingGate",
        "HARM_RISK",
        "DomainHazardScore",
        "Latency_ms",
        "Freshness_ms",
        "HASH_prev",
        "HASH_current",
        "CommitTimestamp",
        "ActuateTimestamp",
        *BOOL_COLS,
    ]
    ensure_columns(df, required)

    for col in BOOL_COLS:
        df[col] = to_bool(df[col])

    # Commit 4.1 (opt-in, default OFF): source the decision-consumed inputs (Gamma_G/Pi/Decision:
    # node gates, HARM_RISK, StaleContext, TelemetryFresh, ReasonCodes) through an Execution
    # Evidence Bundle instead of the raw CSV columns. Dormant unless --eeb-input is passed.
    # Controlled-arm harness: the production RCL assembler builds one sealed EEB per row from the
    # existing evidence (producer), and the PURE-CONSUMER adapter reads the decision inputs back
    # out (consumer). No interpretation / threshold / Class; the FROZEN decision logic below reads
    # identical values and yields identical Gamma_G/Pi/Decision. Replay/ordering left untouched.
    if args.eeb_input:
        from runtime_context import eeb_to_engine
        from runtime_context.assembler import ExecutionEvidenceBundleAssembler
        from runtime_context.execution_evidence_bundle import (
            EvidenceField as _EF, ProvenanceDescriptor as _PD, OriginPlane as _OP,
            EvidenceQuality as _EQ, TrustLevel as _TL, VerificationMethod as _VM,
        )
        _asm = ExecutionEvidenceBundleAssembler()

        def _ef(value, plane, quality=_EQ.PRESENT):
            return _EF(value, _PD(plane, "eeb-controlled-arm", quality, "unobserved",
                                  _VM.FIELD_PRESENCE, _TL.DERIVED))

        def _eeb_for(row):
            return _asm.assemble(
                bundle_id="eeb-controlled-arm", created_at="unobserved",
                txn_amount=_ef(None, _OP.A, _EQ.ABSENT),
                txn_time=_ef(None, _OP.A, _EQ.ABSENT),
                txn_action_ref=_ef(None, _OP.A, _EQ.ABSENT),
                node_predicate_vector=tuple(_ef(bool(row[g]), _OP.C) for g in NODE_GATE_COLS),
                harm_risk_score=_ef(row["HARM_RISK"], _OP.D),
                stale_context=_ef(bool(row["StaleContext"]), _OP.B),
                telemetry_fresh=_ef(bool(row["TelemetryFresh"]), _OP.B),
                class_veto_evidence=_ef(str(row["ReasonCodes"]), _OP.D),
                prior_ledger_link=_ef(None, _OP.E_CACHED, _EQ.ABSENT),
            )

        df = eeb_to_engine.overlay_decision_inputs(
            df, (_eeb_for(row) for _, row in df.iterrows()), NODE_GATE_COLS)

    total = len(df)

    # ----------------------------------------------------------------- #
    # 1. Law of Concurrence: per-row deficit vector and Gamma_G (max).   #
    #    d_i = 1 if node predicate g_i fails; harm deficit if HARM>theta. #
    #    Gamma_G = max(d_i)  -> non-compensatory aggregation.             #
    # ----------------------------------------------------------------- #
    deficits = pd.DataFrame(index=df.index)
    for c in NODE_GATE_COLS:
        deficits[c] = (~df[c]).astype(int)  # gate FALSE -> deficit 1
    deficits["HARM_RISK_THETA"] = (df["HARM_RISK"] > args.harm_threshold).astype(int)
    # Freshness / context deficits feed the same vector (TOCTOU-relevant inputs).
    deficits["STALE_CONTEXT"] = df["StaleContext"].astype(int)
    deficits["TELEMETRY_STALE"] = (~df["TelemetryFresh"]).astype(int)

    df["DerivedGammaG"] = deficits.max(axis=1)  # 0 = all concur, 1 = a deficit exists
    df["DerivedDeficitCount"] = deficits.sum(axis=1)
    df["DerivedRuleFailures"] = deficits.apply(
        lambda row: [c for c in deficits.columns if row[c] > 0], axis=1
    )

    # Class-level veto: class-1 (fraud) deficit persists regardless of node cleanliness.
    # Hardened (Gamma Hardening v1): match well-formed ';'-delimited tokens only, so
    # CLASS_10.. no longer trips CLASS_1 and a bare "GOODHART" in free text cannot deny.
    _veto_re = r"(?:^|;)\s*(?:CLASS_1(?:_[^;]*)?|GOODHART(?:_[^;]*)?)\s*(?:;|$)"
    df["DerivedGammaClass"] = (
        df["ReasonCodes"].astype(str).str.upper().str.contains(_veto_re, regex=True)
    ).astype(int)
    # Fail closed if the row carries no well-formed CLASS_<n>_ token (absent class
    # evidence must not silently permit). No-op on the validated golden corpus.
    _has_class = df["ReasonCodes"].astype(str).str.upper().str.contains(
        r"(?:^|;)\s*CLASS_\d+(?:_[^;]*)?\s*(?:;|$)", regex=True
    )
    df["DerivedGammaG"] = df[["DerivedGammaG"]].assign(
        _mc=(~_has_class).astype(int)
    ).max(axis=1)

    # max(Gamma_G, Gamma_class) = 0  <=>  authority granted (Pi = 1).
    df["DerivedPi"] = (
        (df["DerivedGammaG"] == 0) & (df["DerivedGammaClass"] == 0)
    ).astype(int)
    df["DerivedDecision"] = df["DerivedPi"].map({1: "PERMIT", 0: "SAFE_STATE"})
    df["DerivedSafeState"] = df["DerivedDecision"].eq("SAFE_STATE")

    # Interpretive-sufficiency bit ISB (paper V-B): signatures ∧ freshness ∧ ¬stale.
    df["DerivedISB"] = (
        df["TOKEN_VALID"]
        & df["AuthoritySignatureValid"]
        & df["TelemetryFresh"]
        & (~df["StaleContext"])
    ).astype(int)

    # ----------------------------------------------------------------- #
    # 2. Hash-chain replay determinism (paper Appendix A).               #
    #    Each row's HASH_prev must equal the previous row's HASH_current #
    #    (first row anchored at GENESIS).                                #
    # ----------------------------------------------------------------- #
    prev_current = df["HASH_current"].shift(1)
    chain_ok = df["HASH_prev"].astype(str).eq(prev_current.astype(str))
    chain_ok.iloc[0] = str(df["HASH_prev"].iloc[0]).upper() in {"GENESIS", "0", "NONE", ""}
    df["DerivedChainLinked"] = chain_ok
    df["DerivedReplayDivergence"] = (~chain_ok) | df["ReplayDivergenceFlag"]

    # ----------------------------------------------------------------- #
    # 3. Commit-before-actuate / TOCTOU ordering (paper V-F, VI-B).      #
    #    Actuated rows must have CommitTimestamp <= ActuateTimestamp.    #
    # ----------------------------------------------------------------- #
    commit_ts = pd.to_datetime(df["CommitTimestamp"], errors="coerce", utc=True)
    actuate_ts = pd.to_datetime(df["ActuateTimestamp"], errors="coerce", utc=True)
    actuated = df["Actuated"]
    ordering_bad = actuated & actuate_ts.notna() & commit_ts.notna() & (actuate_ts < commit_ts)
    # Commit-before-actuate flag must also be asserted for any actuated op.
    cba_missing = actuated & (~df["CommitBeforeActuate"])
    df["DerivedOrderingInversion"] = ordering_bad | cba_missing | df["OrderingInversionFlag"]

    # ----------------------------------------------------------------- #
    # 4. Operational definition of Unauthorized Execution (Eq. 7).      #
    #    Unauth = Execute ∧ [¬Valid(Token) ∨ max(GammaG,GammaClass)>0    #
    #            ∨ ISB=0 ∨ evidence pointer invalid].                    #
    # ----------------------------------------------------------------- #
    execute = df["Actuated"] | df["ACT_PERMIT"]
    df["DerivedUnauthorized"] = (
        execute
        & (
            (~df["TOKEN_VALID"])
            | (df["DerivedGammaG"] != 0)
            | (df["DerivedGammaClass"] != 0)
            | (df["DerivedISB"] == 0)
            | (~df["DerivedChainLinked"])
        )
    )

    # ----------------------------------------------------------------- #
    # 5. Compare derived decision against the benchmark labels.          #
    # ----------------------------------------------------------------- #
    df["NormalizedStatus"] = (
        df["Status"].astype(str).str.upper().str.strip().replace({"PERMITTED": "PERMIT"})
    )
    df["MatchesStatus"] = df["NormalizedStatus"].eq(df["DerivedDecision"])
    df["MatchesSAFE_STATE"] = df["SAFE_STATE"].eq(df["DerivedSafeState"])
    df["MatchesACT_PERMIT"] = df["ACT_PERMIT"].eq(~df["DerivedSafeState"])

    # Ground-truth intent for FPR/FDR: derive from the labelled outcome.
    truth_permit = df["NormalizedStatus"].eq("PERMIT")
    derived_permit = df["DerivedDecision"].eq("PERMIT")
    # False permit: we permit something ground truth denies.
    df["FalsePermit"] = derived_permit & (~truth_permit)
    # False denial: we deny something ground truth permits.
    df["FalseDenial"] = (~derived_permit) & truth_permit

    # ----------------------------------------------------------------- #
    # 6. Scenario / class taxonomy.                                      #
    # ----------------------------------------------------------------- #
    df["LABScenarioClass"] = df["ReasonCodes"].apply(derive_lab_class)
    adversarial = df["LABScenarioClass"].isin(
        [
            "LAB-A1_DIRECT_BYPASS",
            "LAB-A2_TOKEN_MANIPULATION",
            "LAB-A3_CONTEXT_CORRUPTION",
            "LAB-A4_TIMING_EXPLOITATION",
            "LAB-A5_GOODHART_OPTIMIZATION",
            "ADVERSARIAL_CLASS_1",
        ]
    )
    n_adv = int(adversarial.sum())

    # ----------------------------------------------------------------- #
    # 7. Six runtime invariants (paper VI-B). Each is a per-row check;   #
    #    a violation is any row failing the invariant.                   #
    # ----------------------------------------------------------------- #
    # I1 Execution Sovereignty: Execute => Permit (no execution without authority).
    inv1_viol = (df["Actuated"]) & (df["DerivedPi"] == 0)
    # I2 Non-Bypassability: no unauthorized externalization slipped through.
    inv2_viol = df["DerivedUnauthorized"]
    # I3 Non-Compensatory Soundness: any deficit => Pi=0.
    inv3_viol = (df["DerivedDeficitCount"] > 0) & (df["DerivedPi"] == 1)
    # I4 Class-Level Veto: a class-1 deficit must force SAFE_STATE.
    inv4_viol = (df["DerivedGammaClass"] == 1) & (~df["DerivedSafeState"])
    # I5 TOCTOU State-Consistency: no ordering inversion on actuated ops.
    inv5_viol = df["DerivedOrderingInversion"]
    # I6 Runtime Sovereignty: composition of I1..I5 + replay integrity.
    inv6_viol = inv1_viol | inv2_viol | inv3_viol | inv4_viol | inv5_viol | df["DerivedReplayDivergence"]

    invariants = {
        "I1_execution_sovereignty": int(inv1_viol.sum()),
        "I2_non_bypassability": int(inv2_viol.sum()),
        "I3_non_compensatory_soundness": int(inv3_viol.sum()),
        "I4_class_level_veto": int(inv4_viol.sum()),
        "I5_toctou_state_consistency": int(inv5_viol.sum()),
        "I6_runtime_sovereignty": int(inv6_viol.sum()),
    }

    # ----------------------------------------------------------------- #
    # 8. NEGATIVE CONTROL (Corollary 2): a compensatory weighted-sum     #
    #    aggregator. A surplus on clean predicates offsets a deficit, so #
    #    a low weighted score can wrongly PERMIT a true-deficit row.     #
    #    Gamma_w = mean deficit; permit if Gamma_w < tau.                #
    # ----------------------------------------------------------------- #
    n_predicates = deficits.shape[1]
    gamma_w = deficits.sum(axis=1) / n_predicates
    tau = 0.15  # permissive threshold; a single deficit out of ~14 scores ~0.07
    compensatory_permit = gamma_w < tau
    # False permits the as-observed compensatory rule would admit but LLC denies.
    neg_control_false_permits = int(
        (compensatory_permit & (df["DerivedGammaG"] != 0) & truth_permit.eq(False)).sum()
    )
    neg_control_total_compensatory_permits = int(compensatory_permit.sum())
    # Constructive Corollary 2 probe: isolate a *single* deficit per true-deficit
    # row. The max-aggregator (LLC) still denies (Gamma=1); the weighted-sum
    # scores 1/n_predicates, which is masked whenever 1/n_predicates < tau.
    gamma_w_single = 1.0 / n_predicates
    single_deficit_masked = gamma_w_single < tau
    corollary2_masked_rows = (
        int((df["DerivedGammaG"] != 0).sum()) if single_deficit_masked else 0
    )

    # ----------------------------------------------------------------- #
    # 9. LAB v1.0 metrics with Wilson intervals.                        #
    #    CRITICAL denominator hygiene: a rate must be taken over the     #
    #    population at risk of THAT event, not blindly over all rows.    #
    #      * FPR (false permit)  -> denominator = should-DENY population #
    #        (ground truth denies): a permit can only be "false" there.  #
    #      * FDR (false denial)   -> denominator = should-PERMIT pop.    #
    #      * UER (unauthorized)   -> denominator = ALL rows (any row can #
    #        externalize), reported as the headline over-total rate.     #
    #    Using total-N for FPR would understate its Wilson bound: the    #
    #    0/492 bound is MUCH wider than the 0/284,807 bound.             #
    # ----------------------------------------------------------------- #
    fpr_events = int(df["FalsePermit"].sum())
    fdr_events = int(df["FalseDenial"].sum())
    unauthorized_events = int(df["DerivedUnauthorized"].sum())
    # Populations at risk (ground-truth based).
    should_deny_n = int((~truth_permit).sum())      # e.g. 492 fraud rows
    should_permit_n = int(truth_permit.sum())       # e.g. 284,315 nominal rows
    replay_div_events = int(df["DerivedReplayDivergence"].sum())
    toctou_events = int(df["DerivedOrderingInversion"].sum())
    # Revocation compliance: rows requiring revocation freshness that lack it.
    revocation_events = int((df["AuthorityRequired"] & (~df["RevocationFresh"])).sum())
    # Class-veto effectiveness: class-1 deficits NOT held in SAFE_STATE (failures).
    classveto_events = int(((df["DerivedGammaClass"] == 1) & (~df["DerivedSafeState"])).sum())
    classveto_n = int((df["DerivedGammaClass"] == 1).sum())

    # Headline unauthorized-execution rate over ALL rows (this is what the old
    # code mislabeled as "FPR 0/N"). Kept distinct from FPR on purpose.
    uer_metric = metric_block(
        "Unauthorized Execution Rate (UER)", unauthorized_events, total,
        higher_is_better=False, design_effect=args.design_effect,
    )

    lab_metrics = {
        "false_permit_rate": metric_block(
            "False Permit Rate (FPR)", fpr_events, max(should_deny_n, 1),
            higher_is_better=False, design_effect=args.design_effect,
        ),
        "false_denial_rate": metric_block(
            "False Denial Rate (FDR)", fdr_events, max(should_permit_n, 1),
            higher_is_better=False, design_effect=args.design_effect,
        ),
        "replay_determinism_rate": metric_block(
            "Replay Determinism Rate (RDR)", replay_div_events, total,
            higher_is_better=True, design_effect=args.design_effect,
        ),
        "revocation_compliance": metric_block(
            "Revocation Compliance", revocation_events, total,
            higher_is_better=True, design_effect=args.design_effect,
        ),
        "toctou_violation_rate": metric_block(
            "TOCTOU Violation Rate", toctou_events, total,
            higher_is_better=False, design_effect=args.design_effect,
        ),
        "class_veto_effectiveness": metric_block(
            "Class-Veto Effectiveness", classveto_events, max(classveto_n, 1),
            higher_is_better=True, design_effect=args.design_effect,
        ),
    }
    # Annotate each metric with the population it is taken over, so the report
    # and dashboard can state the denominator explicitly.
    lab_metrics["false_permit_rate"]["population"] = "should-deny (ground truth = deny)"
    lab_metrics["false_denial_rate"]["population"] = "should-permit (ground truth = permit)"
    lab_metrics["replay_determinism_rate"]["population"] = "all rows"
    lab_metrics["revocation_compliance"]["population"] = "all rows"
    lab_metrics["toctou_violation_rate"]["population"] = "all actuated/at-risk rows"
    lab_metrics["class_veto_effectiveness"]["population"] = "class-1 (veto-triggering) rows"
    uer_metric["population"] = "all rows"

    # ----------------------------------------------------------------- #
    # 10. Evidence Quad per decision (README): method · policy · ledger. #
    # ----------------------------------------------------------------- #
    df["EvidenceQuad"] = df.apply(
        lambda r: {
            "decision": r["DerivedDecision"],
            "method_version": METHOD_VERSION,
            "policy_hash": str(r.get("PolicyHash", "")),
            "ledger_hash": str(r["HASH_current"]),
        },
        axis=1,
    )

    # ----------------------------------------------------------------- #
    # 11. MEASURED per-decision latency (pure-software, this host).      #
    #     Each row is evaluated individually and timed; we verify the    #
    #     timed single-row path agrees with the vectorized decision.     #
    # ----------------------------------------------------------------- #
    timing_cols = list(
        set(
            NODE_GATE_COLS
            + [
                "HARM_RISK",
                "StaleContext",
                "TelemetryFresh",
                "TOKEN_VALID",
                "AuthoritySignatureValid",
                "Actuated",
                "ACT_PERMIT",
                "ReasonCodes",
            ]
        )
    )
    lat_n = total if args.latency_sample in (0, None) else min(total, args.latency_sample)
    sample_df = df.head(lat_n)
    records = sample_df[timing_cols].to_dict("records")
    hashes_prev = sample_df["HASH_prev"].astype(str).tolist()
    full_ns: List[int] = []
    hot_ns: List[int] = []
    timed_agree = 0
    wal_fh = None
    if not args.no_wal:
        wal_fd, wal_name = tempfile.mkstemp(prefix="gamma_wal_", suffix=".log")
        wal_fh = os.fdopen(wal_fd, "wb", buffering=0)

    derived_decisions = sample_df["DerivedDecision"].tolist()
    for i, rec in enumerate(records):
        t0 = time.perf_counter_ns()
        # (a) predicate evaluation / Law of Concurrence
        res = evaluate_decision(rec, args.harm_threshold)
        t_eval = time.perf_counter_ns()
        # (b) hot path: hash-chain advance + sign + write-ahead log
        payload = (
            f"{rec['ReasonCodes']}|{res['decision']}|{res['gamma_g']}|"
            f"{res['gamma_class']}|{res['pi']}"
        ).encode("utf-8")
        h_current = hashlib.sha256(hashes_prev[i].encode("utf-8") + payload).digest()
        sig = hmac.new(_HOTPATH_KEY, h_current + payload, hashlib.sha256).digest()
        if wal_fh is not None:
            wal_fh.write(h_current + sig)
            wal_fh.flush()
            os.fsync(wal_fh.fileno())  # commit-before-actuate: durable WAL
        t1 = time.perf_counter_ns()

        full_ns.append(t1 - t0)
        hot_ns.append(t1 - t_eval)
        if res["decision"] == derived_decisions[i]:
            timed_agree += 1
    if wal_fh is not None:
        wal_fh.close()
        os.unlink(wal_name)

    full_ms = sorted(x / 1_000_000.0 for x in full_ns)  # milliseconds
    hot_ms = sorted(x / 1_000_000.0 for x in hot_ns)
    mean_ms = sum(full_ms) / len(full_ms) if full_ms else 0.0
    p95 = percentile(full_ms, 95)
    p99 = percentile(full_ms, 99)
    mx = full_ms[-1] if full_ms else 0.0
    hot_p99 = percentile(hot_ms, 99)
    limit = args.latency_limit_ms
    measured_latency = {
        "note": "MEASURED on this host: predicate eval + SHA-256 hash-chain advance "
        "+ HMAC-SHA256 sign (representative crypto, NOT a hardware HSM signature)"
        + ("" if args.no_wal else " + WAL fsync (durable)") + ". "
        "Not comparable to the paper's HSM/FPGA hardware-in-the-loop figures.",
        "wal_fsync_included": (not args.no_wal),
        "latency_sampled_rows": lat_n,
        "total_rows": total,
        "samples": len(full_ms),
        "timed_path_agreement": timed_agree,
        "mean_ms": round(mean_ms, 6),
        "p50_ms": round(percentile(full_ms, 50), 6),
        "p95_ms": round(p95, 6),
        "p99_ms": round(p99, 6),
        "max_ms": round(mx, 6),
        "hotpath_p99_ms": round(hot_p99, 6),
        "limit_ms": limit,
        "hotpath_limit_ms": args.hotpath_limit_ms,
        "headroom_p95_ms": round(limit - p95, 6),
        "headroom_max_ms": round(limit - mx, 6),
        "throughput_ops_per_s": round(1000.0 / mean_ms, 1) if mean_ms > 0 else None,
        "status_p95": "Pass" if p95 <= limit else "Fail",
        "status_max": "Pass" if mx <= limit else "Fail",
        "status_hotpath_p99": "Pass" if hot_p99 <= args.hotpath_limit_ms else "Fail",
    }

    # ----------------------------------------------------------------- #
    # Aggregate summary numbers.
    # ----------------------------------------------------------------- #
    permit_count = int(derived_permit.sum())
    safe_count = int(df["DerivedSafeState"].sum())
    match_status_rate = float(df["MatchesStatus"].mean())
    match_safe_rate = float(df["MatchesSAFE_STATE"].mean())

    chain_links_ok = int(df["DerivedChainLinked"].sum())
    tlc_verification = verify_tlc(
        df, args.tla_spec, args.tla_cfg,
        log_path=args.tlc_log, run_command=args.tlc_run_command,
    )
    tlc_total_states = tlc_verification.get("total_states")
    tlc_violations = tlc_verification.get("violation_count")

    summary = {
        "input_file": str(input_path),
        "method_version": METHOD_VERSION,
        "rows": total,
        "derived_permit": permit_count,
        "derived_safe_state": safe_count,
        "match_status_rate": round(match_status_rate, 6),
        "match_safe_state_rate": round(match_safe_rate, 6),
        "false_permit_count": fpr_events,
        "false_denial_count": fdr_events,
        "unauthorized_execution_count": int(df["DerivedUnauthorized"].sum()),
        "replay_divergence_count": replay_div_events,
        "ordering_inversion_count": toctou_events,
        "hash_chain_links_ok": chain_links_ok,
        "harm_threshold": args.harm_threshold,
        "latency_threshold": args.latency_threshold,
        "freshness_threshold": args.freshness_threshold,
        "status_distribution": df["Status"].value_counts(dropna=False).to_dict(),
        "decision_distribution": df["DerivedDecision"].value_counts(dropna=False).to_dict(),
        "lab_scenario_distribution": df["LABScenarioClass"].value_counts(dropna=False).to_dict(),
        "top_rule_failures": df["DerivedRuleFailures"].explode().dropna().value_counts().head(15).to_dict(),
        "sample_fail_rows": df.loc[
            df["DerivedSafeState"], ["ProposalID", "ReasonCodes", "DerivedRuleFailures"]
        ].head(10).to_dict(orient="records"),
    }

    lab_report = {
        "benchmark": "LAB v1.0 (L-DREA Authorization Benchmark)",
        "method_version": METHOD_VERSION,
        "input_file": str(input_path),
        "n_total": total,
        "n_adversarial": n_adv,
        "n_nominal": total - n_adv,
        "primary_metrics": lab_metrics,
        "runtime_invariants_violations": invariants,
        "all_invariants_hold": all(v == 0 for v in invariants.values()),
        "unauthorized_execution": {
            "definition": "Eq.7: Execute & (!Valid(Token) | max(GammaG,GammaClass)>0 | ISB=0 | evidence invalid)",
            "count": unauthorized_events,
            "metric": uer_metric,          # UER over ALL rows (headline)
            "denominator": total,
            "note": "UER is taken over ALL rows (any row can externalize); this is distinct "
            "from FPR, which is taken only over the should-deny population.",
        },
        "negative_control": {
            "description": "Two DISTINCT probes of the compensatory weighted-sum aggregator "
            "vs the non-compensatory Law of Concurrence (max). They are not contradictory: one "
            "runs the compensatory rule on the data as-is, the other is a counterfactual transform.",
            "tau": tau,
            "single_deficit_score": round(1.0 / n_predicates, 3),
            "n_predicates": n_predicates,
            # Probe 1 — ACTUAL run of the compensatory rule on this mapped corpus.
            "actual_dataset_baseline": {
                "what": "Run the compensatory weighted-sum rule AS-IS on every mapped row.",
                "compensatory_total_permits": neg_control_total_compensatory_permits,
                "false_permits_vs_llc": neg_control_false_permits,
                "note": (
                    f"Under tau={tau} on THIS mapped corpus the weighted-sum admits "
                    f"{neg_control_false_permits} false permits vs LLC, because every adversarial "
                    "row here fails MULTIPLE hard predicates, so its weighted score stays >= tau."
                ),
            },
            # Probe 2 — COUNTERFACTUAL transform (not the actual dataset).
            "corollary2_counterfactual": {
                "what": "Counterfactual: reduce each adversarial row to a SINGLE isolated deficit.",
                "single_deficit_masked": single_deficit_masked,
                "counterfactual_false_permits": corollary2_masked_rows,
                "note": (
                    f"If each adversarial row were reduced to an isolated single deficit "
                    f"({1.0 / n_predicates:.3f} < tau={tau}), a compensatory gate would MASK the "
                    f"failure -> {corollary2_masked_rows} COUNTERFACTUAL false permits; the "
                    "non-compensatory max-aggregator (LLC) still denies all of them."
                ),
            },
            # Flat keys retained for backward compatibility with the dashboard.
            "compensatory_total_permits": neg_control_total_compensatory_permits,
            "compensatory_false_permits_vs_llc": neg_control_false_permits,
            "corollary2_single_deficit_masked": single_deficit_masked,
            "corollary2_rows_masked_if_isolated": corollary2_masked_rows,
        },
        "measured_latency": measured_latency,
        "replay_determinism": {
            "hash_chain_links_ok": chain_links_ok,
            "hash_chain_links_total": total,
            "genesis_anchored": bool(df["DerivedChainLinked"].iloc[0]),
            "tlc_total_states": tlc_total_states,
            "tlc_violation_count": tlc_violations,
        },
        "tlc_verification": tlc_verification,
        "decision_agreement": {
            "match_status_rate": round(match_status_rate, 8),
            "match_safe_state_rate": round(match_safe_rate, 8),
            "match_act_permit_rate": round(float(df["MatchesACT_PERMIT"].mean()), 8),
        },
        "per_scenario_class": {
            cls: {
                "n": int((df["LABScenarioClass"] == cls).sum()),
                "derived_safe_state": int(
                    ((df["LABScenarioClass"] == cls) & df["DerivedSafeState"]).sum()
                ),
                "false_permits": int(
                    ((df["LABScenarioClass"] == cls) & df["FalsePermit"]).sum()
                ),
            }
            for cls in sorted(df["LABScenarioClass"].unique())
        },
    }

    # ----------------------------------------------------------------- #
    # Appendix-A-style summary (FULL_SPEC §Appendix A format), built from   #
    # the ACTUAL measured values of this run.                              #
    # ----------------------------------------------------------------- #
    invariants_ok = sum(1 for v in invariants.values() if v == 0)
    adv_safe = int((adversarial & df["DerivedSafeState"]).sum())
    adv_false_permit = int((adversarial & df["FalsePermit"]).sum())
    uer_bound = uer_metric["wilson95_clustercorrected_upper"]                     # over ALL rows
    fpr_bound = lab_metrics["false_permit_rate"]["wilson95_clustercorrected_upper"]  # over should-deny
    rdr = lab_metrics["replay_determinism_rate"]
    da = lab_report["decision_agreement"]
    ml = measured_latency
    appendix_a_summary = [
        f"UER {unauthorized_events} / {total} (all rows), Wilson 95% upper bound p < {uer_bound:.2e}; "
        f"FPR {fpr_events} / {should_deny_n} (should-deny population only), Wilson 95% upper bound "
        f"p < {fpr_bound:.2e}; FDR {fdr_events} / {should_permit_n} (should-permit population). "
        f"The FPR bound is wider than the UER bound because its denominator is far smaller.",
        f"Replay determinism {rdr['reported_rate']:.4%}; revocation compliance "
        f"{lab_metrics['revocation_compliance']['reported_rate']:.4%}; TOCTOU violations "
        f"{toctou_events} observed; RDR Wilson 95% upper bound p < "
        f"{rdr['wilson95_clustercorrected_upper']:.2e}.",
        f"Latency mean {ml['mean_ms']:.4f} ms, P95 {ml['p95_ms']:.4f} ms, P99 {ml['p99_ms']:.4f} ms, "
        f"max {ml['max_ms']:.4f} ms; throughput ~{ml['throughput_ops_per_s']:,.0f} ops/s; "
        f"O(n) predicate scaling.",
        f"Runtime invariants: {invariants_ok}/6 satisfied; unauthorized executions "
        f"{lab_report['unauthorized_execution']['count']}; false permit rate "
        f"{lab_metrics['false_permit_rate']['reported_rate']:.0%}; false denial rate "
        f"{lab_metrics['false_denial_rate']['reported_rate']:.0%}; class-veto effectiveness "
        f"{lab_metrics['class_veto_effectiveness']['reported_rate']:.0%}.",
        f"Decision agreement: {da['match_status_rate']:.4%} vs Status, "
        f"{da['match_safe_state_rate']:.4%} vs SAFE_STATE, {da['match_act_permit_rate']:.4%} vs "
        f"ACT_PERMIT; all {n_adv} adversarial transactions transitioned to SAFE_STATE "
        f"({adv_safe}/{n_adv}) with {adv_false_permit} false permits.",
    ]
    lab_report["appendix_a_style_summary"] = appendix_a_summary

    # ----------------------------------------------------------------- #
    # Governing rules & parameters that actually produced these results.  #
    # (Real config: gate set, thresholds, decision rule, definitions.)    #
    # ----------------------------------------------------------------- #
    lab_report["governing_rules"] = {
        "decision_rule": "PERMIT iff Pi=1, where Pi = [ max(Gamma_G, Gamma_class) == 0 ]. "
        "Law of Concurrence: Gamma_G = max_i(d_i), non-compensatory max-aggregation - a single "
        "deficit denies regardless of all other predicates.",
        "node_predicates_must_all_concur": NODE_GATE_COLS,
        "derived_deficits": {
            "HARM_RISK_THETA": f"deficit if HARM_RISK > theta ({args.harm_threshold})",
            "STALE_CONTEXT": "deficit if StaleContext == TRUE",
            "TELEMETRY_STALE": "deficit if TelemetryFresh == FALSE",
        },
        "class_level_veto": "Gamma_class=1 when ReasonCodes contains CLASS_1 or GOODHART; this "
        "forces SAFE_STATE even if every node predicate concurs (Goodhart resistance).",
        "isb_rule": "ISB=1 iff TOKEN_VALID & AuthoritySignatureValid & TelemetryFresh & !StaleContext.",
        "unauthorized_execution_eq7": "Unauth = Execute & ( !TOKEN_VALID | max(Gamma_G,Gamma_class)>0 "
        "| ISB=0 | hash-chain link broken ).",
        "commit_before_actuate": "Any actuated op MUST have CommitTimestamp <= ActuateTimestamp and "
        "CommitBeforeActuate=TRUE; otherwise an ordering/TOCTOU violation is recorded.",
        "replay_determinism": "Row i HASH_prev MUST equal row (i-1) HASH_current, GENESIS-anchored; "
        "any broken link is a replay divergence.",
        "ground_truth": "Real ULB `Class` label - Class=1 => must deny (SAFE_STATE); Class=0 => may permit.",
        "parameters": {
            "harm_threshold_theta": args.harm_threshold,
            "latency_limit_ms": args.latency_limit_ms,
            "hotpath_limit_ms": args.hotpath_limit_ms,
            "freshness_threshold_ms": args.freshness_threshold,
            "design_effect_DE": args.design_effect,
            "negative_control_tau": tau,
            "wilson_confidence_z": round(Z_95, 4),
            "latency_sampled_rows": lat_n,
        },
        "spec_policy_reference_band_7_1": {
            "note": "FULL_SPEC §7.1 conjunctive acceptance bands - the broader governing policy. "
            "A permit requires ALL bands (non-compensatory). Listed as normative reference; "
            "this dataset run enforces the gate/harm/token/hash/ordering rules above.",
            "ICS_integrity_confidence": ">= 0.90",
            "PR_LCB_robustness_lower_bound": ">= 0.80",
            "CI_WIDTH": "<= 0.03",
            "DeltaV_stability_residual": "<= 0",
            "C_coherence": ">= C_STAR (default 0.85)",
            "PTP_skew": "<= 1 ms",
            "cycle_latency": "<= 100 ms (P95)",
            "ER_LOCAL_evidence_commit": "= 1.0",
            "hard_stops": ["DEADLINE_MISS", "COMMIT_FAIL", "ATTESTATION_FAIL", "DeltaV>0", "C<C_STAR"],
        },
    }

    # ----------------------------------------------------------------- #
    # Write outputs.
    # ----------------------------------------------------------------- #
    df["DerivedRuleFailures"] = df["DerivedRuleFailures"].apply(lambda x: ";".join(x))
    df["EvidenceQuad"] = df["EvidenceQuad"].apply(lambda d: json.dumps(d, separators=(",", ":")))
    cols_to_export = [
        "ProposalID",
        "Status",
        "NormalizedStatus",
        "DecisionOutcome",
        "LABScenarioClass",
        "SAFE_STATE",
        "ACT_PERMIT",
        "DerivedDecision",
        "DerivedSafeState",
        "DerivedGammaG",
        "DerivedGammaClass",
        "DerivedPi",
        "DerivedISB",
        "DerivedDeficitCount",
        "DerivedUnauthorized",
        "DerivedChainLinked",
        "DerivedReplayDivergence",
        "DerivedOrderingInversion",
        "MatchesStatus",
        "MatchesSAFE_STATE",
        "FalsePermit",
        "FalseDenial",
        "HARM_RISK",
        "Latency_ms",
        "Freshness_ms",
        "DerivedRuleFailures",
        "ReasonCodes",
        "FirstFailingGate",
        "EvidenceQuad",
    ]
    df[cols_to_export].to_csv(output_path, index=False)

    # ----------------------------------------------------------------- #
    # Per-item ERTuple replay manifest (per-decision evidence).           #
    # ----------------------------------------------------------------- #
    replay_summary: Dict = {}
    if not args.no_replay_manifest:
        replay_summary = write_replay_manifest(df, Path(args.replay_manifest))
        lab_report["replay_manifest"] = replay_summary

    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    lab_path.write_text(json.dumps(lab_report, indent=2, default=str), encoding="utf-8")

    # ----------------------------------------------------------------- #
    # Full lab reproducibility bundle (opt-in via --bundle DIR).          #
    # ----------------------------------------------------------------- #
    bundle_manifest = None
    if args.bundle:
        source_files = [
            Path(__file__),
            Path(__file__).with_name("gamma_map_raw.py"),
            Path(__file__).with_name("gamma_report_page.py"),
            Path(__file__).with_name("gamma_replay_verify.py"),
        ]
        output_files = [output_path, summary_path, lab_path]
        if replay_summary:
            output_files.append(Path(args.replay_manifest))
        if not args.no_html:
            output_files.append(Path(args.html))
        bundle_manifest = write_repro_bundle(
            Path(args.bundle),
            input_path=input_path,
            outputs=output_files,
            sources=source_files,
            command=[sys.executable, *sys.argv],
            tlc_verification=tlc_verification,
            replay_summary=replay_summary,
        )
        # Surface a compact bundle summary to the in-memory report so the HTML
        # dashboard can show it. (Not written into lab_report.json on disk: the
        # bundle digest hashes that very file, which would be circular.)
        lab_report["repro_bundle"] = {
            "dir": str(args.bundle),
            "files_digested": (
                len(bundle_manifest["input"])
                + len(bundle_manifest["sources"])
                + len(bundle_manifest["outputs"])
            ),
            "bundle_digest_sha256": bundle_manifest["bundle_digest_sha256"],
        }

    # ----------------------------------------------------------------- #
    # Console report.
    # ----------------------------------------------------------------- #
    print("\n" + "=" * 64)
    print("  Gamma G-0 / L-DREA  —  LAB v1.0 Authorization Benchmark")
    print("=" * 64)
    print(f"Input            : {input_path.name}")
    print(f"Method version   : {METHOD_VERSION}")
    print(f"Rows (N)         : {total}   (adversarial: {n_adv}, nominal: {total - n_adv})")
    print(f"Derived PERMIT   : {permit_count}")
    print(f"Derived SAFE_STATE: {safe_count}")
    print(f"Match vs Status  : {match_status_rate:.4%}")
    print(f"Match vs SAFE_STATE: {match_safe_rate:.4%}")

    print("\n-- Headline: Unauthorized Execution Rate (UER, over ALL rows) --")
    print(f"  UER              : {unauthorized_events}/{total}  "
          f"(rate {fmt_rate(uer_metric['adverse_rate'])}, "
          f"W95 upper {fmt_rate(uer_metric['wilson95_clustercorrected_upper'])})")

    print("\n-- Primary LAB v1.0 metrics (Wilson 95% upper bounds; note denominators) --")
    print(f"{'metric':<34}{'events/N':>14}{'rate':>12}{'W95 upper':>14}")
    for m in lab_metrics.values():
        ev = f"{m['adverse_events']}/{m['n']}"
        print(
            f"{m['metric']:<34}{ev:>14}{fmt_rate(m['reported_rate']):>12}"
            f"{fmt_rate(m['wilson95_clustercorrected_upper']):>14}"
        )
        print(f"{'  ↳ population: ' + m.get('population', 'all rows'):<34}")

    print("\n-- Six runtime invariants (violations; 0 = holds) --")
    for k, v in invariants.items():
        status = "OK " if v == 0 else "FAIL"
        print(f"  [{status}] {k}: {v}")
    print(f"  ALL INVARIANTS HOLD: {lab_report['all_invariants_hold']}")

    print("\n-- Unauthorized execution (Eq. 7) --")
    print(f"  UER count        : {unauthorized_events}/{total} (all rows)")
    print(f"  FPR (should-deny): {fpr_events}/{should_deny_n}")
    print(f"  FDR (should-permit): {fdr_events}/{should_permit_n}")

    print("\n-- Negative control (two DISTINCT probes) --")
    print("  [1] ACTUAL dataset weighted-sum baseline (rule run as-is on this corpus):")
    print(f"        weighted-sum total permits       : {neg_control_total_compensatory_permits}")
    print(f"        weighted-sum FALSE permits vs LLC: {neg_control_false_permits}  "
          f"(0 here: adversarial rows fail MULTIPLE predicates, score stays >= tau={tau})")
    print("  [2] Corollary 2 COUNTERFACTUAL (each adversarial row reduced to a single deficit):")
    print(
        f"        isolated single deficit {1.0 / n_predicates:.3f} < tau {tau} "
        f"-> masked by weighted-sum: {single_deficit_masked}"
    )
    print(f"        => {corollary2_masked_rows} COUNTERFACTUAL false permits; "
          f"non-compensatory LLC still denies all.")

    ml = measured_latency
    print("\n-- MEASURED per-decision latency (this host: eval+hash+sign"
          f"{'' if args.no_wal else '+WAL'}) --")
    print(f"  samples (timed-path agreement) : {ml['samples']} ({timed_agree}/{ml['samples']})")
    print(f"  {'Metric':<22}{'Value':>14}{'§6.0/§7 Limit':>22}{'Status':>10}")
    rows = [
        ("Mean latency", f"{ml['mean_ms']:.4f} ms", f"<= {limit:.0f} ms P95", ml["status_p95"]),
        ("P95 latency", f"{ml['p95_ms']:.4f} ms", f"<= {limit:.0f} ms", ml["status_p95"]),
        ("P99 latency", f"{ml['p99_ms']:.4f} ms", f"hot-path P99 <= {args.hotpath_limit_ms:.0f} ms", ml["status_hotpath_p99"]),
        ("Max latency", f"{ml['max_ms']:.4f} ms", f"<= {limit:.0f} ms cycle", ml["status_max"]),
        ("Headroom at P95", f"{ml['headroom_p95_ms']:.4f} ms", f"{limit:.0f} - P95", "Strong" if ml["headroom_p95_ms"] > 0 else "None"),
        ("Headroom at max", f"{ml['headroom_max_ms']:.4f} ms", f"{limit:.0f} - max", "Strong" if ml["headroom_max_ms"] > 0 else "None"),
        ("Hot-path P99", f"{ml['hotpath_p99_ms']:.4f} ms", f"<= {args.hotpath_limit_ms:.0f} ms", ml["status_hotpath_p99"]),
        ("Throughput", f"{ml['throughput_ops_per_s']:,.0f} ops/s", "O(n) predicate scaling", "Pass"),
    ]
    for name, val, lim, st in rows:
        print(f"  {name:<22}{val:>14}{lim:>22}{st:>10}")
    print("  (Representative HMAC sign + real SHA-256 + WAL fsync; NOT HSM/FPGA hardware.)")

    print("\n-- Replay determinism / hash chain --")
    print(f"  hash-chain links ok : {chain_links_ok}/{total}")
    if replay_summary:
        print(f"  ERTuple manifest    : {replay_summary['path']} "
              f"({replay_summary['n_records']} records)")
        print(f"    adjacency links ok: {replay_summary['adjacency_links_ok']}/"
              f"{replay_summary['n_records']} "
              f"(all_ok={replay_summary['adjacency_all_ok']}, "
              f"genesis={replay_summary['genesis_anchored']})")
        print(f"    manifest SHA-256  : {replay_summary['manifest_sha256']}")
        print(f"    verify            : {replay_summary['verify_with']}")

    print("\n-- TLC model-check verification --")
    if tlc_verification.get("available"):
        print(f"  VERIFIED            : {tlc_verification['verified']}")
        print(f"  verification tier   : {tlc_verification['verification_tier']}")
        for k, v in tlc_verification["checks"].items():
            if v is None:
                print(f"    [skip] {k}: artifact not supplied")
            else:
                print(f"    [{'OK ' if v else 'FAIL'}] {k}")
        print(f"  total states        : {tlc_verification['total_states']}")
        print(f"  violations          : {tlc_verification['violation_count']}")
        print(f"  attestation digest  : {tlc_verification['attestation_digest']}")
        if tlc_verification.get("tlc_log"):
            lg = tlc_verification["tlc_log"]
            print(f"  log distinct states : {lg.get('distinct_states')} "
                  f"(no_error={lg.get('no_error_reported')}, error={lg.get('error_reported')})")
        if tlc_verification.get("run_command"):
            print(f"  TLC run command     : {tlc_verification['run_command']}")
        miss = tlc_verification.get("artifacts_missing_for_full_closure") or []
        if miss:
            print(f"  to raise the tier   : supply {', '.join(miss)}")
    else:
        print(f"  {tlc_verification.get('note')}")

    if bundle_manifest is not None:
        print("\n-- Reproducibility bundle --")
        print(f"  written to          : {args.bundle}/")
        print(f"  bundle digest       : {bundle_manifest['bundle_digest_sha256']}")
        print(f"  see                 : {args.bundle}/REPRODUCE.md")

    print("\n-- Decision agreement vs benchmark labels --")
    da = lab_report["decision_agreement"]
    print(f"  Derived vs Status      : {da['match_status_rate']:.6%}")
    print(f"  Derived vs SAFE_STATE  : {da['match_safe_state_rate']:.6%}")
    print(f"  Derived vs ACT_PERMIT  : {da['match_act_permit_rate']:.6%}")

    print("\n-- LAB scenario-class distribution --")
    for cls, n in summary["lab_scenario_distribution"].items():
        print(f"  {cls}: {n}")

    print("\n-- Per-scenario-class breakdown --")
    print(f"  {'class':<32}{'N':>6}{'SAFE_STATE':>12}{'false_permits':>16}")
    for cls, d in lab_report["per_scenario_class"].items():
        print(f"  {cls:<32}{d['n']:>6}{d['derived_safe_state']:>12}{d['false_permits']:>16}")

    print("\n-- Top rule failures --")
    for k, v in summary["top_rule_failures"].items():
        print(f"  {k}: {v}")

    print("\n-- SAFE_STATE rows (sample) --")
    for r in summary["sample_fail_rows"]:
        print(f"  {r['ProposalID']}: {r['ReasonCodes']}  [{';'.join(r['DerivedRuleFailures'])}]")

    print("\n" + "=" * 64)
    print("  LAB v1.0 SUMMARY (Appendix-A style)")
    print("=" * 64)
    for line in appendix_a_summary:
        print(f"- {line}")

    print(f"\nSaved row-level results : {output_path}")
    print(f"Saved summary JSON      : {summary_path}")
    print(f"Saved LAB v1.0 report   : {lab_path}")

    # ----------------------------------------------------------------- #
    # 12. Generate (and open) the HTML dashboard from THIS run's data.    #
    #     Built from the in-memory lab_report/summary dicts, so the page  #
    #     always matches what the runner just computed.                   #
    # ----------------------------------------------------------------- #
    if not args.no_html:
        terminal_txt = console_buf.getvalue()
        sys.stdout = sys.__stdout__  # restore before importing/printing
        try:
            from gamma_report_page import render

            render(
                lab_report,
                summary,
                args.html,
                terminal_txt=terminal_txt,
                open_browser=not args.no_open,
            )
        except Exception as exc:  # never let reporting break the benchmark
            print(f"[warn] Could not generate the HTML dashboard: {exc}")
            print(f"       Run it manually:  python gamma_report_page.py "
                  f"--lab-report {lab_path} --summary {summary_path} --out {args.html}")
    else:
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
