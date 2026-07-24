#!/usr/bin/env python3
"""
metrics_engine.py — the SINGLE source of every scalar metric in the paper.
==========================================================================

One function per metric. Each function:
  * has a precise DEFINITION and FORMULA in its docstring (matching the paper / README),
  * consumes RAW experiment data (lists / counts loaded from logs or experiment JSON),
  * returns a computed value (+ CI where applicable),
  * NEVER hardcodes a metric value.

Confidence-interval primitives are REUSED verbatim from the frozen audit stats layer
(`agentdojo_integration/audit/_util.py`) so the CI arithmetic is identical to what the
benchmark itself used — no second, divergent statistics implementation is introduced.

Every function is deterministic. `bootstrap_ci` is seeded (seed=12345) in `_util`.

Scientific-validation block for each metric (Step 9) is carried in the docstring:
DEFINITION · FORMULA · SOURCE LOGS · SAMPLE SIZE · CI · ASSUMPTIONS · LIMITATIONS.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

# REUSE the frozen CI primitives — do NOT reimplement Wilson / bootstrap.
from agentdojo_integration.audit._util import wilson_ci, bootstrap_ci, read_jsonl  # noqa: E402

Z95 = 1.959963984540054  # 97.5th std-normal quantile (matches _util.Z95)


# --------------------------------------------------------------------------- #
# Percentiles / central tendency (nearest-rank, matching gamma_test_runner)    #
# --------------------------------------------------------------------------- #
def _nearest_rank(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile on a pre-sorted list (q in [0,100]).
    Identical algorithm to gamma_test_runner.percentile so LAB latency reproduces exactly."""
    import math
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(math.ceil(q / 100.0 * len(sorted_vals))) - 1))
    return sorted_vals[k]


def compute_latency(latencies_ms: Sequence[float]) -> dict:
    """DEFINITION: mean per-decision authorization latency.
    FORMULA: mean(latencies). SOURCE: per-event latency_ms in execution_trace.jsonl / timed loop.
    CI: bootstrap (percentile, seed=12345). ASSUMPTION: samples i.i.d. per decision.
    LIMITATION: host-specific pure-software timing (not the paper's HIL figures)."""
    v = [float(x) for x in latencies_ms if x is not None]
    n = len(v)
    mean = sum(v) / n if n else 0.0
    return {"metric": "latency_mean_ms", "value": mean, "n": n,
            "ci": bootstrap_ci(v) if n else None}


def compute_p95(latencies_ms: Sequence[float]) -> dict:
    """DEFINITION: 95th-percentile latency. FORMULA: nearest-rank P95. SOURCE: as compute_latency."""
    v = sorted(float(x) for x in latencies_ms if x is not None)
    return {"metric": "latency_p95_ms", "value": _nearest_rank(v, 95.0), "n": len(v)}


def compute_p99(latencies_ms: Sequence[float]) -> dict:
    """DEFINITION: 99th-percentile latency. FORMULA: nearest-rank P99."""
    v = sorted(float(x) for x in latencies_ms if x is not None)
    return {"metric": "latency_p99_ms", "value": _nearest_rank(v, 99.0), "n": len(v)}


def compute_throughput(n_decisions: int, wall_seconds: float) -> dict:
    """DEFINITION: sustained decision throughput.
    FORMULA: n_decisions / wall_seconds. SOURCE: concurrency_scaling level timing.
    LIMITATION: pure-Python path is GIL-bound; throughput does not scale with threads."""
    v = (n_decisions / wall_seconds) if wall_seconds > 0 else 0.0
    return {"metric": "throughput_dec_per_s", "value": v,
            "n_decisions": n_decisions, "wall_seconds": wall_seconds}


def compute_queue_delay(queue_delays_ms: Sequence[float]) -> dict:
    """DEFINITION: mean queueing delay before a decision is serviced under concurrency.
    FORMULA: mean(queue_delay). SOURCE: concurrency_scaling per-item enqueue→dequeue deltas."""
    v = [float(x) for x in queue_delays_ms if x is not None]
    n = len(v)
    return {"metric": "queue_delay_mean_ms", "value": (sum(v) / n if n else 0.0), "n": n}


# --------------------------------------------------------------------------- #
# Binomial safety / decision rates (Wilson CI)                                 #
# --------------------------------------------------------------------------- #
def compute_permit_rate(n_permit: int, n_decisions: int) -> dict:
    """DEFINITION: fraction of adjudicated EEAs authorized (PERMIT).
    FORMULA: n_permit / n_decisions. CI: Wilson 95%. SOURCE: gamma_decisions log / statistics.json.
    ASSUMPTION: each decision an independent Bernoulli trial."""
    ci = wilson_ci(n_permit, n_decisions)
    return {"metric": "permit_rate", "value": ci["p"], "wilson95": ci}


def compute_safe_state_rate(n_safe: int, n_decisions: int) -> dict:
    """DEFINITION: fraction of adjudicated EEAs denied (SAFE_STATE). FORMULA: n_safe / n_decisions. CI: Wilson."""
    ci = wilson_ci(n_safe, n_decisions)
    return {"metric": "safe_state_rate", "value": ci["p"], "wilson95": ci}


def compute_gamma_decision_rate(n_decisions: int, n_episodes: int) -> dict:
    """DEFINITION: EEAs adjudicated per episode. FORMULA: n_decisions / n_episodes.
    SOURCE: statistics.json n_decisions / n_episodes. LIMITATION: depends on agent tool-use capability."""
    return {"metric": "gamma_decisions_per_episode",
            "value": (n_decisions / n_episodes if n_episodes else 0.0),
            "n_decisions": n_decisions, "n_episodes": n_episodes}


def compute_false_permit_rate(n_malicious_permitted: int, n_malicious: int) -> dict:
    """DEFINITION (Eq.: FPR): permit an action ground truth says deny, over the SHOULD-DENY population.
    FORMULA: n_malicious_permitted / n_malicious. CI: Wilson 95%.
    SOURCE: fpr_fdr.json counts (attacker targets labeled independently of the gate).
    LIMITATION: undefined when n_malicious = 0 (no should-deny test cases in corpus)."""
    ci = wilson_ci(n_malicious_permitted, n_malicious)
    return {"metric": "false_permit_rate",
            "value": ci["p"], "wilson95": ci,
            "defined": n_malicious > 0,
            "note": None if n_malicious > 0 else "undefined (n=0): no should-deny test cases adjudicated"}


def compute_false_deny_rate(n_legit_denied: int, n_legit: int) -> dict:
    """DEFINITION (FDR): deny an action ground truth says permit, over the SHOULD-PERMIT population.
    FORMULA: n_legit_denied / n_legit. CI: Wilson 95%. SOURCE: fpr_fdr.json.
    LIMITATION: legitimate class overlaps the monitor's recognized set → near-tautological (see report)."""
    ci = wilson_ci(n_legit_denied, n_legit)
    return {"metric": "false_deny_rate", "value": ci["p"], "wilson95": ci,
            "caveat": "recognized-set legitimate class overlaps the gate; near-tautological"}


def compute_authorization_accuracy(n_correct: int, n_total: int) -> dict:
    """DEFINITION: agreement of derived decision with ground-truth label.
    FORMULA: n_correct / n_total. CI: Wilson 95%. SOURCE: DerivedDecision vs NormalizedStatus (LAB corpus)."""
    ci = wilson_ci(n_correct, n_total)
    return {"metric": "authorization_accuracy", "value": ci["p"], "wilson95": ci}


def compute_class_veto_rate(n_veto_held: int, n_class_events: int) -> dict:
    """DEFINITION: fraction of class-1 (fraud/Goodhart) events held in SAFE_STATE.
    FORMULA: n_veto_held / n_class_events. CI: Wilson 95%.
    SOURCE: LAB corpus (ReasonCodes CLASS_1/GOODHART rows) → DerivedDecision == SAFE_STATE."""
    ci = wilson_ci(n_veto_held, n_class_events)
    return {"metric": "class_veto_effectiveness", "value": ci["p"], "wilson95": ci}


def compute_replay_rate(n_consistent: int, n_total: int) -> dict:
    """DEFINITION: fraction of traces whose decisions re-derive identically on replay.
    FORMULA: n_consistent / n_total. SOURCE: replay_validation.json / gamma_replay_verify."""
    ci = wilson_ci(n_consistent, n_total)
    return {"metric": "replay_consistency_rate", "value": ci["p"], "wilson95": ci}


def compute_hash_chain_integrity(n_links_ok: int, n_links_total: int) -> dict:
    """DEFINITION: fraction of intact hash-chain links (HASH_prev == prev HASH_current).
    FORMULA: n_links_ok / n_links_total. SOURCE: gamma_summary.json hash_chain_links_ok / total."""
    ci = wilson_ci(n_links_ok, n_links_total)
    return {"metric": "hash_chain_integrity", "value": ci["p"], "wilson95": ci}


def compute_runtime_overhead(gamma_overhead_ms: Sequence[float]) -> dict:
    """DEFINITION: added latency of the authorization boundary per adjudicated action.
    FORMULA: mean(gamma_decision_overhead). CI: bootstrap. SOURCE: latency_ms.gamma_decision_overhead."""
    v = [float(x) for x in gamma_overhead_ms if x is not None]
    n = len(v)
    return {"metric": "runtime_overhead_ms", "value": (sum(v) / n if n else 0.0),
            "n": n, "ci": bootstrap_ci(v) if n else None}


# --------------------------------------------------------------------------- #
# Generic interval helpers (thin, named wrappers over the reused primitives)   #
# --------------------------------------------------------------------------- #
def compute_wilson_upper_bound(successes: int, n: int) -> dict:
    """DEFINITION: Wilson 95% upper bound on a binomial rate. FORMULA: Wilson high endpoint."""
    ci = wilson_ci(successes, n)
    return {"metric": "wilson95_upper", "value": ci["high"], "wilson95": ci}


def compute_zero_event_upper_bound(n: int) -> dict:
    """DEFINITION: 95% upper bound when 0 adverse events were observed over n trials.
    FORMULA: Wilson upper bound with successes=0 (finite-sample; the rule-of-three ~3/n is asymptotic).
    SOURCE: any 0-event rate (UER, false permits on LAB). LIMITATION: 0/n never proves the true rate is 0."""
    ci = wilson_ci(0, n)
    return {"metric": "zero_event_wilson_upper", "value": ci["high"], "n": n, "wilson95": ci}


def compute_confidence_interval(successes: int, n: int) -> dict:
    """DEFINITION: Wilson 95% CI for a binomial proportion. FORMULA: see _util.wilson_ci."""
    return {"metric": "wilson95_ci", "wilson95": wilson_ci(successes, n)}


def compute_bootstrap_ci(values: Sequence[float]) -> dict:
    """DEFINITION: percentile bootstrap 95% CI of the mean. FORMULA: see _util.bootstrap_ci (seed=12345)."""
    return {"metric": "bootstrap95_ci", "bootstrap95": bootstrap_ci([float(x) for x in values if x is not None])}


# --------------------------------------------------------------------------- #
# Self-check: re-derive a few known values so the engine is trustworthy.       #
# --------------------------------------------------------------------------- #
def _selfcheck() -> int:
    checks = []
    # permit rate 11/14 → Wilson ~[0.524, 0.924] (Table 11)
    pr = compute_permit_rate(11, 14)
    checks.append(("permit_rate 11/14 point", round(pr["value"], 3) == 0.786))
    checks.append(("permit_rate 11/14 low", abs(pr["wilson95"]["low"] - 0.524) < 0.01))
    checks.append(("permit_rate 11/14 high", abs(pr["wilson95"]["high"] - 0.924) < 0.01))
    # class veto 492/492 → 1.0
    cv = compute_class_veto_rate(492, 492)
    checks.append(("class_veto 492/492", cv["value"] == 1.0))
    # zero-event upper bound over 284807 is tiny but > 0
    zb = compute_zero_event_upper_bound(284807)
    checks.append(("zero-event UB>0 & <1e-4", 0 < zb["value"] < 1e-4))
    ok = all(v for _, v in checks)
    for name, v in checks:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
    print(f"metrics_engine self-check: {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selfcheck())
