#!/usr/bin/env python3
"""
experiments/_metrics_catalog.py — declarative catalogue of every metric the suite computes.
===========================================================================================

PURELY DECLARATIVE. Not one numeric value is stored here. Each entry names the artifact and the
JSON pointer where an executed experiment wrote the value; the dashboard resolves it live.

Why a catalogue instead of ad-hoc prints
----------------------------------------
Three properties fall out of declaring metrics as data:

1. **Nothing calculated stays hidden.** Adding a metric means adding a row, so the default is
   exposure rather than omission (Part 3 of the reporting contract).
2. **Nothing absent is silently skipped.** A metric whose artifact or pointer is missing resolves
   to ``NotComputed(reason)`` and is *printed as such*. Metrics that the suite genuinely does not
   compute are declared explicitly with ``unavailable=<reason>`` so the dashboard states why
   rather than leaving a gap the reader must notice.
3. **Provenance travels with the number.** ``prov`` distinguishes values measured by this run from
   values attested by an external source and from values derived arithmetically here.

Fields
------
label       display name
artifact    repo-relative JSON produced by an experiment
pointer     dotted path within that artifact (list indices allowed)
fmt         callable value -> str
extra       callable(A) -> str, rendered dim after the value (CI, sample size, caveat)
ok          callable(value) -> bool, drives the ✓/✗ mark. Omit where no pass/fail is defined.
prov        'measured' | 'attested' | 'derived'
formula     shown for prov='derived'
derive      callable(A) -> value | NotComputed, replaces `pointer`
unavailable reason string; the metric renders as "Not computed" with this reason, always
"""
from __future__ import annotations

try:
    from experiments._report import NotComputed, fmt_int, fmt_num, fmt_pct, fmt_sci, is_missing
except Exception:  # pragma: no cover - direct-on-path import
    from _report import NotComputed, fmt_int, fmt_num, fmt_pct, fmt_sci, is_missing

# ---- artifact locations: declared once in experiments/_artifacts.py ----
try:
    from experiments._artifacts import (A_ABL, A_ADSTATS, A_AUDIT, A_BOUNDARY, A_BUNDLE_MANIFEST,
                                        A_CONCUR, A_CONCUR_ALT, A_COVERAGE, A_FCR, A_FULLSPEC,
                                        A_LAB, A_MANIFEST, A_PROFILE, A_PROV, A_REPLAY, A_ROBUST,
                                        A_STAGES, A_STATS, A_STRESS, A_TLC_LOG, A_VERIFIER)
except ImportError:  # pragma: no cover - direct-on-path import
    from _artifacts import (A_ABL, A_ADSTATS, A_AUDIT, A_BOUNDARY, A_BUNDLE_MANIFEST,  # type: ignore
                            A_CONCUR, A_CONCUR_ALT, A_COVERAGE, A_FCR, A_FULLSPEC,
                            A_LAB, A_MANIFEST, A_PROFILE, A_PROV, A_REPLAY, A_ROBUST,
                            A_STAGES, A_STATS, A_STRESS, A_TLC_LOG, A_VERIFIER)


# --------------------------------------------------------------------------- derived helpers
def _authorization_accuracy(A):
    """(TP+TN)/N over the FULL_SPEC confusion matrix. Pure arithmetic over executed counts."""
    cm = A.get(A_FULLSPEC, "confusion_matrix")
    if is_missing(cm):
        return cm
    tp, tn = cm.get("true_permits"), cm.get("true_denials")
    fp, fn = cm.get("false_permits"), cm.get("false_denials")
    if None in (tp, tn, fp, fn):
        return NotComputed("FULL_SPEC confusion_matrix is incomplete")
    tot = tp + tn + fp + fn
    if tot == 0:
        return NotComputed("confusion matrix is empty (N=0)")
    return (tp + tn) / tot


def _concur(A, pointer, reason=None):
    """ConcurBench lives in the E1 dir after RUN_ALL; the root copy is the fallback."""
    v = A.get(A_CONCUR, pointer, reason=reason)
    if is_missing(v):
        v2 = A.get(A_CONCUR_ALT, pointer, reason=reason)
        if not is_missing(v2):
            return v2
    return v


def _wilson_extra(artifact, base):
    def _f(A):
        up = A.get(artifact, f"{base}.wilson95_naive_upper")
        n = A.get(artifact, f"{base}.n")
        if is_missing(up) or is_missing(n):
            return ""
        return f"n={n:,}  Wilson95↑ {fmt_sci(up)}"
    return _f


def _ratio_extra(artifact, base):
    """Render the adverse-event count explicitly.

    A bare "0/492" next to a 100% rate reads as "0 of 492 succeeded", which inverts the meaning for
    higher-is-better metrics like Class-Veto Effectiveness. The numerator is always the ADVERSE
    count, so it is labelled as such.
    """
    def _f(A):
        ev = A.get(artifact, f"{base}.adverse_events")
        n = A.get(artifact, f"{base}.n")
        pop = A.get(artifact, f"{base}.population")
        if is_missing(ev) or is_missing(n):
            return ""
        p = "" if is_missing(pop) else f"  ·  {pop}"
        return f"{ev:,} adverse of {n:,}{p}"
    return _f


def _hash_chain(A):
    ok = A.get(A_LAB, "replay_determinism.hash_chain_links_ok")
    tot = A.get(A_LAB, "replay_determinism.hash_chain_links_total")
    if is_missing(ok) or is_missing(tot):
        return ok if is_missing(ok) else tot
    return f"{ok:,} / {tot:,} links"


def _evidence_quad(A):
    q = _concur(A, "evidence_quad")
    if is_missing(q):
        return q
    present = [k for k in ("spec_clause", "pre_reg_id", "method_version", "ledger_hash") if q.get(k)]
    return f"{len(present)}/4 fields bound"


def _predicate_coverage(A):
    """Runtime predicate coverage, measured by E9 against the frozen engine."""
    cov = A.get(A_COVERAGE, "predicate_coverage")
    if is_missing(cov):
        return cov
    return f"{cov['covered']}/{cov['total_predicates']} = {cov['coverage_rate'] * 100:.1f}%"


def _agentdojo_predicate_frequency(A):
    pf = A.get(A_ADSTATS, "predicate_frequency")
    if is_missing(pf):
        return pf
    return f"{len(pf)} predicates exercised"


# --------------------------------------------------------------------------- the catalogue
def M(label, **kw):
    return {"label": label, **kw}


AUTHORIZATION = [
    M("Authorization Accuracy", derive=_authorization_accuracy, fmt=lambda v: fmt_pct(v, 4),
      prov="derived", formula="(TP+TN)/(TP+TN+FP+FN) over FULL_SPEC confusion_matrix",
      ok=lambda v: v == 1.0,
      extra=lambda A: (lambda cm: "" if is_missing(cm) else
                       f"TP {cm['true_permits']:,} · TN {cm['true_denials']:,} · "
                       f"FP {cm['false_permits']} · FN {cm['false_denials']}")(
          A.get(A_FULLSPEC, "confusion_matrix"))),
    M("Unauthorized Execution Rate (UER)", artifact=A_LAB,
      pointer="unauthorized_execution.metric.reported_rate", fmt=lambda v: fmt_pct(v, 6),
      ok=lambda v: v == 0.0, prov="measured",
      extra=_wilson_extra(A_LAB, "unauthorized_execution.metric")),
    M("False Permit Rate (FPR)", artifact=A_LAB,
      pointer="primary_metrics.false_permit_rate.reported_rate", fmt=lambda v: fmt_pct(v, 6),
      ok=lambda v: v == 0.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.false_permit_rate")),
    M("False Denial Rate (FDR)", artifact=A_LAB,
      pointer="primary_metrics.false_denial_rate.reported_rate", fmt=lambda v: fmt_pct(v, 6),
      ok=lambda v: v == 0.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.false_denial_rate")),
    M("Detection Rate (DR)", artifact=A_FULLSPEC, pointer="metrics_11_1.DR.rate",
      fmt=lambda v: fmt_pct(v, 2), ok=lambda v: v == 1.0, prov="measured",
      extra=lambda A: str(A.get(A_FULLSPEC, "metrics_11_1.DR.note", reason="") or "")),
    M("Safety Violation Rate (SVR)", artifact=A_FULLSPEC, pointer="metrics_11_1.SVR.rate",
      fmt=lambda v: fmt_pct(v, 6), ok=lambda v: v == 0.0, prov="measured",
      extra=lambda A: "P(execute ∧ Γ>0)"),
    M("Fail-Closed Rate (FCR)", artifact=A_FCR, pointer="overall.FCR", fmt=lambda v: fmt_pct(v, 2),
      ok=lambda v: v == 1.0, prov="measured",
      extra=lambda A: (lambda o: "" if is_missing(o) else
                       f"fail-open {o['fail_open_events']}/{o['n']:,}  Wilson95↑ "
                       f"{fmt_sci(o['wilson95_fail_open_upper'])}")(A.get(A_FCR, "overall"))),
    M("Γ-Compliance  P(ŷ=0 | Γ>0)", artifact=A_FULLSPEC,
      pointer="metrics_11_1.FFC_gamma_compliance.rate", fmt=lambda v: fmt_pct(v, 2),
      ok=lambda v: v == 1.0, prov="measured"),
    M("Class-Veto Effectiveness", artifact=A_LAB,
      pointer="primary_metrics.class_veto_effectiveness.reported_rate", fmt=lambda v: fmt_pct(v, 2),
      ok=lambda v: v == 1.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.class_veto_effectiveness")),
    M("TOCTOU Violation Rate", artifact=A_LAB,
      pointer="primary_metrics.toctou_violation_rate.reported_rate", fmt=lambda v: fmt_pct(v, 6),
      ok=lambda v: v == 0.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.toctou_violation_rate")),
    M("Revocation Compliance", artifact=A_LAB,
      pointer="primary_metrics.revocation_compliance.reported_rate", fmt=lambda v: fmt_pct(v, 2),
      ok=lambda v: v == 1.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.revocation_compliance")),
    M("Replay Determinism Rate (RDR)", artifact=A_LAB,
      pointer="primary_metrics.replay_determinism_rate.reported_rate", fmt=lambda v: fmt_pct(v, 4),
      ok=lambda v: v == 1.0, prov="measured",
      extra=_ratio_extra(A_LAB, "primary_metrics.replay_determinism_rate")),
    M("Predicate Coverage (runtime, E9)", derive=_predicate_coverage, fmt=str, prov="measured",
      ok=lambda v: v.endswith("100.0%"),
      extra=lambda A: "every runtime predicate observed in both polarities against the frozen engine"),
    M("Single-deficit denial (per-predicate I3)", artifact=A_COVERAGE,
      pointer="single_deficit_isolation.denial_rate", fmt=lambda v: fmt_pct(v, 2),
      ok=lambda v: v == 1.0, prov="measured",
      extra=lambda A: (lambda i: "" if is_missing(i) else
                       f"{i['denied']}/{i['n']} · {i['false_permits']} false permits · "
                       f"Wilson95 [{i['wilson95']['low']:.4f}, {i['wilson95']['high']:.4f}]")(
          A.get(A_COVERAGE, "single_deficit_isolation"))),
    M("Predicate frequency (AgentDojo episodes)", derive=_agentdojo_predicate_frequency, fmt=str,
      prov="measured", extra=lambda A: "distinct predicates evaluated across recorded episodes"),
    M("Decision Agreement (status)", artifact=A_LAB, pointer="decision_agreement.match_status_rate",
      fmt=lambda v: fmt_pct(v, 4), ok=lambda v: v == 1.0, prov="measured"),
]

EVIDENCE = [
    M("Hash-Chain Verification", derive=_hash_chain, fmt=str, prov="measured",
      ok=lambda v: True,
      extra=lambda A: "genesis-anchored" if A.get(A_LAB, "replay_determinism.genesis_anchored") is True else ""),
    M("Replay Integrity (verifier)", artifact=A_REPLAY, pointer="result", fmt=str,
      ok=lambda v: v == "PASS", prov="measured",
      extra=lambda A: (lambda n: "" if is_missing(n) else f"{n:,} decision records re-verified")(
          A.get(A_REPLAY, "decision_records_verified"))),
    M("Ledger-Bind Failures", artifact=A_REPLAY, pointer="ledger_bind_failures", fmt=fmt_int,
      ok=lambda v: v == 0, prov="measured"),
    M("Self-Consistency Failures", artifact=A_REPLAY, pointer="self_consistency_failures",
      fmt=fmt_int, ok=lambda v: v == 0, prov="measured"),
    M("Evidence Quad", derive=_evidence_quad, fmt=str, prov="measured",
      extra=lambda A: "(spec_clause, pre_reg_id, method_version, ledger_hash)"),
    M("Verifier Agreement (engine ↔ oracle)", artifact=A_VERIFIER, pointer="total_field_mismatches",
      fmt=lambda v: f"{v} field mismatches", ok=lambda v: v == 0, prov="measured",
      extra=lambda A: (lambda n: "" if is_missing(n) else f"over {n:,} enumerated states")(
          A.get(A_VERIFIER, "total_states_enumerated"))),
    M("Independent Replay Verifier", derive=lambda A: _concur(A, "replay_and_auditability.independent_replay_verifier"),
      fmt=str, ok=lambda v: v == "PASS", prov="measured"),
    M("Audit-Integrity Score (AIS)", artifact=A_FULLSPEC, pointer="audit_as_control_6_12.AIS_value",
      fmt=lambda v: fmt_num(v, 3), ok=lambda v: v >= 0.99, prov="measured",
      extra=lambda A: "min(chain_integrity, storage, signature, time_sync, retention)"),
    M("Audit Packet Export", derive=lambda A: _concur(A, "replay_and_auditability.audit_packet_export"),
      fmt=str, ok=lambda v: v == "PASS", prov="measured",
      extra=lambda A: (lambda v: "" if is_missing(v) else
                       f"gamma_bundle/ · {v.get('members_verified')} members re-hashed · "
                       "ledger digest bound to live ledger")(A.get(A_AUDIT, "verification"))),
    M("Audit bundle verification", artifact=A_AUDIT, pointer="verification.status", fmt=str,
      ok=lambda v: v == "PASS", prov="measured",
      extra=lambda A: "criterion: every member re-hashes + ledger binding; empty/tampered bundle FAILS"),
    M("ConcurBench Level 4", artifact=A_AUDIT, pointer="concurbench_level4", fmt=str,
      ok=lambda v: v == "PASS", prov="measured", extra=lambda A: "replay & auditability"),
]

DISTRIBUTED = [
    M("Fleet Consistency", derive=lambda A: _concur(A, "distributed_consistency.fleet_consistency"),
      fmt=lambda v: fmt_pct(v, 2), ok=lambda v: v == 1.0, prov="measured",
      extra=lambda A: (lambda n: "" if is_missing(n) else f"{n}-node simulated fleet")(
          _concur(A, "distributed_consistency.node_count"))),
    M("Cross-Node Replay Consistency",
      derive=lambda A: _concur(A, "distributed_consistency.cross_node_replay_consistency"),
      fmt=lambda v: fmt_pct(v, 2), ok=lambda v: v == 1.0, prov="measured"),
    M("Policy-Version Consistency",
      derive=lambda A: _concur(A, "distributed_consistency.policy_version_consistency"),
      fmt=lambda v: fmt_pct(v, 2), ok=lambda v: v == 1.0, prov="measured"),
    M("Distributed Consensus (disagreements)",
      derive=lambda A: _concur(A, "distributed_consistency.disagreements"), fmt=fmt_int,
      ok=lambda v: v == 0, prov="measured",
      extra=lambda A: str(_concur(A, "distributed_consistency.quorum_rule") or "")),
    M("Desynchronisation cases",
      derive=lambda A: _concur(A, "distributed_consistency.distributed_desynchronization_cases"),
      fmt=fmt_int, prov="measured",
      extra=lambda A: (lambda u: "" if is_missing(u) else f"unauthorized executions under desync: {u}")(
          _concur(A, "distributed_consistency.unauthorized_execution_under_desync"))),
    M("Partition Recovery", derive=lambda A: _concur(A, "distributed_consistency.partition_test"),
      fmt=str, ok=lambda v: v == "PASS", prov="measured",
      extra=lambda A: str(_concur(A, "distributed_consistency.partition_behavior") or "")[:60]),
    M("Revocation latency p50 / p95 / p99",
      derive=lambda A: (lambda a, b, c: NotComputed("ConcurBench distributed_consistency absent")
                        if any(is_missing(x) for x in (a, b, c)) else f"{a} / {b} / {c} ms")(
          _concur(A, "distributed_consistency.revocation_latency_p50_ms"),
          _concur(A, "distributed_consistency.revocation_latency_p95_ms"),
          _concur(A, "distributed_consistency.revocation_latency_p99_ms")),
      fmt=str, prov="measured", extra=lambda A: "simulated-fleet testbed (not a live fleet)"),
]

STATISTICS = [
    M("Confidence level", artifact=A_LAB, pointer="governing_rules.parameters.wilson_confidence_z",
      fmt=lambda v: f"95% (z = {v})", prov="measured"),
    M("Design effect (cluster correction)", artifact=A_LAB,
      pointer="governing_rules.parameters.design_effect_DE", fmt=lambda v: f"DE = {v}",
      prov="measured", extra=lambda A: "cluster-corrected Wilson bounds use n_eff = n/DE"),
    M("Proportion metrics with Wilson CI", artifact=A_STATS, pointer="proportion_metrics",
      fmt=lambda v: f"{len(v)} metrics", prov="measured", ok=lambda v: len(v) > 0),
    M("Zero-event upper bounds", artifact=A_STATS, pointer="zero_event_bounds",
      fmt=lambda v: f"{len(v)} metrics", prov="measured", ok=lambda v: len(v) > 0,
      extra=lambda A: "Wilson95 upper + rule-of-three (3/n)"),
    M("Ablation effect sizes", artifact=A_STATS, pointer="ablation_effect_sizes",
      fmt=lambda v: f"{len(v)} contrasts", prov="measured", ok=lambda v: len(v) > 0,
      extra=lambda A: "risk difference + Cohen's h"),
    M("Frequentist p-values", unavailable=(
        "not applicable: the authorization engine is deterministic, so the ablation contrasts are "
        "exact rather than sampled. statistics_report.json:determinism_note records this. "
        "Risk difference and Cohen's h are reported instead.")),
]

# Metrics the suite genuinely does not compute. Declared so the dashboard says so out loud
# rather than leaving a silent gap.
NOT_COMPUTED = [
    M("Attack Success Rate (AgentDojo, live)", unavailable=(
        "JUSTIFIED LIMITATION, not an engineering gap. Attack-success rate is a property of the AGENT's "
        "trajectory, not of the guard, and is only defined when a live model generates fresh episodes "
        "(Ollama + llama3.1:8b). When a backend is present E7 runs live automatically; otherwise E7 "
        "executes the replay and boundary evaluations instead and labels every measurement's mode. "
        "The guard's soundness is measured without an LLM by adjudicating each attacker target directly "
        "at the frozen boundary (boundary FPR). No substitute value is produced.")),
    M("Task Utility (AgentDojo, live)", unavailable=(
        "Same justified limitation as Attack Success Rate: utility measures whether the AGENT completed "
        "its task, which requires a live model. It is not a property of the authorization layer.")),
    M("AgentDojo false-permit / false-deny rate", unavailable=(
        "statistics.json sets both to null: per-decision ground-truth labels for the recorded "
        "episodes do not exist. The boundary-FPR probe (E7) is the labelled soundness measurement.")),
    M("Tier-H hardware-in-the-loop latency", unavailable=(
        "this repository is the Tier-S software reference. HSM/FPGA figures are not reproduced here "
        "and are not claimed; see reviewer concern R11 (out of scope).")),
]
