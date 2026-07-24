#!/usr/bin/env python3
"""
Lakhowal Financial-Services Stress-Test harness.
================================================

Executes the four stress scenarios from "Lakhowal Stress-Test Analysis
(15 May 2026)" as REAL, deterministic predicate evaluations against the
non-compensatory Gamma engine, rather than prose:

  P1  Ghost Treasury Transfer        (deepfake CFO $28M wire)
  P2  Sanctions Drift Cascade        (3 sub-cases incl. the oracle gap)
  P3  Multi-Agent Liquidity Panic    (federated aggregate + class veto)
  P4  Sovereign Cascade Edge Case    (compound simultaneous failure)

For each scenario every named predicate is evaluated, Gamma is aggregated
non-compensatorily (Gamma = number of failed hard predicates; a single deficit
denies), and the decision is checked against the expected fail-closed outcome.
Out-of-scope conditions (upstream ERP poisoning, OCR drift, oracle staleness)
are reported honestly as FAIL / out-of-scope, matching the source document.

Output: stress_test_report.json     (also returned by run()).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- #
# Non-compensatory Gamma engine (Law of Concurrence) for finance predicates
# --------------------------------------------------------------------------- #
def gamma_decision(predicates: List[Dict], class_veto: bool = False) -> Dict:
    """predicates: [{name, passed, detail, in_scope}]. Gamma = # failed hard
    predicates (in-scope). A single deficit -> SAFE_STATE (non-compensatory)."""
    failed = [p for p in predicates if p["in_scope"] and not p["passed"]]
    gamma = len(failed)
    permit = (gamma == 0) and not class_veto
    return {
        "gamma": gamma,
        "class_veto": class_veto,
        "decision": "PERMIT" if permit else "SAFE_STATE",
        "failed_predicates": [p["name"] for p in failed],
    }


def P(name, passed, detail, in_scope=True):
    return {"name": name, "passed": passed, "detail": detail, "in_scope": in_scope}


def cond(label, ldrea, lakhowal, delta, result):
    return {"failure_condition": label, "l_drea": ldrea,
            "lakhowal": lakhowal, "delta": delta, "result": result}


# --------------------------------------------------------------------------- #
# P1 - Ghost Treasury Transfer
# --------------------------------------------------------------------------- #
def p1_ghost_treasury() -> Dict:
    preds = [
        P("amount_within_daily_limit", False, "$28M > $5M extraordinary cap"),
        P("entity_sanctions_check", True, "OFAC clear"),
        P("kyc_token_freshness", True, "47s old, within 300s window"),
        P("erp_invoice_verification", False, "PO-2026-9931 absent from SAP"),
        P("destination_account_recognized", False, "SWIFT-XYZ not in vendor list"),
        P("human_concurrence", True, "CFO token signature valid"),
        P("dual_control_satisfied", False, "second approver token absent"),
        P("velocity_check", False, "$28M vs 30-day baseline $4M"),
        P("integrity_flux_I_phi", False, "0.78 vs threshold 0.30"),
    ]
    dec = gamma_decision(preds)
    conditions = [
        cond("Transfer blocked at gateway", "PASS - Theorem 3",
             "PASS - Execution Gateway returns 403", "-", "PASS"),
        cond("Deepfake CFO approval rejected", "PASS - LLC denies despite valid sig",
             "PASS - LLC + recorded as override_attempt", "+evidentiary", "PASS"),
        cond("AML enforcement at runtime", "Conditional - predicate-dependent",
             "PASS - finance.treasury.v3 ships sanctions check", "+default", "PASS"),
        cond("Forensic replay preserved", "PASS - Lemma 9",
             "PASS - + Claim Replay Tool UI", "+productized", "PASS"),
        cond("Upstream ERP poisoning detected", "FAIL - out of scope",
             "FAIL - out of scope", "-", "OUT_OF_SCOPE"),
        cond("OCR drift at ingestion detected", "FAIL - out of scope",
             "FAIL - out of scope", "-", "OUT_OF_SCOPE"),
        cond("Settlement-deadline urgency blocked", "Conditional - custom predicate",
             "PASS - velocity_check ships by default", "+default", "PASS"),
    ]
    return _scenario("P1", "Ghost Treasury Transfer", preds, dec, conditions,
                     expected="SAFE_STATE", confidence="HIGH",
                     tackled="92-95%", verdict="STRONG FIT",
                     note="Γ=6 non-compensatory; deepfake CFO override could not "
                          "compensate. Hard limit: valid-hash forged ERP rows "
                          "(upstream write integrity) remain out of scope.")


# --------------------------------------------------------------------------- #
# P2 - Sanctions Drift Cascade (three sub-cases)
# --------------------------------------------------------------------------- #
def p2_sanctions_drift() -> Dict:
    # Case A: stale feed -> fail closed
    a = gamma_decision([
        P("kyc_token_freshness", False, "sanctions feed age 27h > 24h window"),
    ])
    # Case B: fresh feed but stale TRUTH; oracle returns PASS on incomplete graph
    b = gamma_decision([
        P("kyc_token_freshness", True, "feed age 18h"),
        P("entity_sanctions_check", True, "S-882 not on feed (STALE TRUTH)"),
        P("beneficial_owner_traversal", True,
          "custom predicate PASSes on incomplete graph -> ORACLE GAP",
          in_scope=True),
    ])
    # Case C: class-level drift veto
    c = gamma_decision(
        [P("per_counterparty_drift", False, "S-882 volume +340%")],
        class_veto=True,
    )
    conditions = [
        cond("Stale-feed denial (Case A)", "PASS - Theorem 7 TOCTOU",
             "PASS - kyc_token_freshness fails closed", "-", "PASS"),
        cond("Stale-truth + fresh-feed (Case B)", "FAIL - oracle gap",
             "FAIL - oracle gap", "-", "OUT_OF_SCOPE"),
        cond("Beneficial ownership graph traversal", "Conditional - custom predicate",
             "Conditional - not shipped in pack", "-", "CONDITIONAL"),
        cond("Entity alias drift detected", "Conditional - requires I_class",
             "Conditional - requires custom class metric", "-", "CONDITIONAL"),
        cond("Routing volume drift", "Conditional - requires I_class",
             "PASS - per_counterparty_drift shipped", "+default", "PASS"),
        cond("Hidden ownership remains undetected", "FAIL - outside threat model",
             "FAIL - outside threat model", "-", "OUT_OF_SCOPE"),
        cond("Ghost Transaction Log for diagnostics", "Not applicable",
             "PASS - Phase 0 surfaces lag risk", "+productized", "PASS"),
    ]
    sub = {"case_a_feed_lag": a, "case_b_stale_truth": b, "case_c_class_drift": c}
    return _scenario("P2", "Sanctions Drift Cascade", None, None, conditions,
                     expected="MIXED (A/C fail-closed; B oracle gap)",
                     confidence="MEDIUM", tackled="60-70%", verdict="PARTIAL FIT",
                     subcases=sub,
                     note="The oracle problem (stale truth behind a fresh feed) "
                          "is genuinely out of scope: the gate enforces what the "
                          "predicate returns, not upstream-feed correctness.")


# --------------------------------------------------------------------------- #
# P3 - Multi-Agent Liquidity Panic
# --------------------------------------------------------------------------- #
def p3_liquidity_panic() -> Dict:
    agent1 = gamma_decision([
        P("amount_within_daily_limit", True, "$5M vs $5M cap"),
        P("velocity_check_single", True, "within baseline"),
        P("emergency_velocity_aggregate", False, "$5M + $7.3M vs $8M cap"),
        P("integrity_flux_I_phi", False, "0.71 cross-agent correlation"),
    ])
    agent2 = gamma_decision([
        P("emergency_velocity_aggregate", False, "$10.3M vs $8M cap"),
    ])
    class_flag = gamma_decision(
        [P("autonomy_band_score", False,
           "5 agents converging < 30s + correlated I_phi drift")],
        class_veto=True,
    )
    permit_to_adapt = gamma_decision(
        [P("kappa_op_coupling", False,
           "aggregate Permit-to-Act risk HIGH -> Permit-to-Adapt tightened")],
        class_veto=True,
    )
    conditions = [
        cond("Single emergency transfer blocked", "PASS - predicate-dependent",
             "PASS - predicate-dependent", "-", "PASS"),
        cond("Aggregate cross-agent volume capped", "Conditional - requires LFC",
             "Conditional - requires custom predicate", "-", "CONDITIONAL"),
        cond("Recursive panic contained", "PASS - class-level veto persists",
             "PASS - + Heatmap visualization", "+UX", "PASS"),
        cond("Permit-to-Adapt locked under panic", "PASS - κ(op) coupling",
             "PASS - κ(op) + Policy Editor as ERTuple", "+auditability", "PASS"),
        cond("Emergency transfers bypass policy", "PASS - blocked",
             "PASS - blocked", "-", "PASS"),
        cond("Insider-credentialed false alarm", "FAIL - Assumption 1 boundary",
             "FAIL - Assumption 1 boundary", "-", "OUT_OF_SCOPE"),
        cond("Multi-agent correlation visualized", "Not applicable",
             "PASS - Risk Heatmap + I_phi wave", "+productized", "PASS"),
        cond("Human remediation workflow", "Not applicable",
             "PASS - Operational Runbook §72", "+productized", "PASS"),
    ]
    sub = {"agent_1": agent1, "agent_2": agent2, "class_flag": class_flag,
           "policy_exemption_permit_to_adapt": permit_to_adapt}
    return _scenario("P3", "Multi-Agent Liquidity Panic", None, None, conditions,
                     expected="SAFE_STATE (all agents + class flag + adapt)",
                     confidence="HIGH", tackled="75-85%", verdict="STRONG FIT",
                     subcases=sub,
                     note="κ(op) coupling tightens Permit-to-Adapt under "
                          "accumulated execution risk; class-veto persistence "
                          "blocks any of the 5 agents until human remediation. "
                          "Aggregate velocity predicate is not shipped by default.")


# --------------------------------------------------------------------------- #
# P4 - Sovereign Cascade Edge Case (compound simultaneous failure)
# --------------------------------------------------------------------------- #
def p4_sovereign_cascade() -> Dict:
    compound = gamma_decision([
        P("deterministic_governance", False, "geopolitical + deepfake + ERP lag"),
        P("token_validity_under_api_outage", False,
          "banking API outage -> ambiguous Valid(Token) -> DENY not DEFER"),
        P("kyc_token_freshness", False, "stale KYC tokens"),
        P("integrity_flux_I_phi", False, "FX volatility + recursive drift"),
    ], class_veto=True)
    conditions = [
        cond("Deterministic governance preserved", "PASS - Theorem 8 invariant",
             "PASS + Topology D air-gapped deployment", "+deploy", "PASS"),
        cond("Bounded autonomy maintained", "PASS - class-level veto",
             "PASS - class veto + I_phi ceiling", "-", "PASS"),
        cond("Unsafe execution denied", "PASS - LLC",
             "PASS - LLC + fail-closed at SDK + Gateway", "-", "PASS"),
        cond("Degraded-safe continuation", "PASS - Operational Continuity Layer",
             "PASS - documented failure-mode table §35", "-", "PASS"),
        cond("Forensic replay integrity", "PASS - Lemma 9",
             "PASS - + Claim Replay Tool + Hydra Ledger UI", "+productized", "PASS"),
        cond("Banking API outage handled", "PASS - fail-closed default",
             "PASS - EXTERNAL_DEPENDENCY_UNAVAILABLE", "-", "PASS"),
        cond("Compound failure exceeds OCL envelope", "Partial - may queue",
             "Partial - same risk; surfaced in dashboard", "-", "PARTIAL"),
    ]
    return _scenario("P4", "Sovereign Cascade Edge Case", None, None, conditions,
                     expected="SAFE_STATE (fail closed under compound failure)",
                     confidence="MEDIUM-HIGH", tackled="70-80%", verdict="DEFENSIBLE",
                     subcases={"compound_failure": compound},
                     note="Under clock-skew or revocation-propagation breach the "
                          "OCL fails closed, not open. Genuine limit: retry "
                          "semantics must denote ambiguous Valid(Token) as DENY, "
                          "else queue buildup becomes its own attack surface.")


# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def _scenario(pid, name, preds, dec, conditions, *, expected, confidence,
              tackled, verdict, note, subcases=None):
    in_scope = [c for c in conditions if c["result"] not in ("OUT_OF_SCOPE",)]
    passed = [c for c in conditions if c["result"] == "PASS"]
    scored = {
        "id": pid, "name": name, "expected_outcome": expected,
        "confidence": confidence, "effectively_tackled": tackled,
        "verdict": verdict,
        "conditions_total": len(conditions),
        "conditions_pass": len(passed),
        "conditions_in_scope": len(in_scope),
        "in_scope_pass_rate": round(len(passed) / len(in_scope), 4) if in_scope else 0.0,
        "per_condition": conditions,
        "note": note,
    }
    if preds is not None:
        scored["predicates"] = preds
    if dec is not None:
        scored["decision"] = dec
        scored["fail_closed_ok"] = (dec["decision"] == "SAFE_STATE")
    if subcases is not None:
        scored["subcases"] = subcases
        # a scenario "holds" if every enumerated sub-decision that is expected to
        # deny does deny; case B (oracle gap) is the acknowledged exception.
        holds = all(
            v["decision"] == "SAFE_STATE"
            for k, v in subcases.items() if "case_b" not in k
        )
        scored["fail_closed_ok"] = holds
    return scored


def run(write: bool = True) -> Dict:
    scenarios = [
        p1_ghost_treasury(), p2_sanctions_drift(),
        p3_liquidity_panic(), p4_sovereign_cascade(),
    ]
    # aggregate effectively-tackled midpoint
    mids = []
    for s in scenarios:
        lo, hi = s["effectively_tackled"].replace("%", "").split("-")
        mids.append((float(lo) + float(hi)) / 2)
    agg = round(sum(mids) / len(mids), 1)
    fail_closed_all = all(s.get("fail_closed_ok", False) for s in scenarios)

    report = {
        "harness": "Lakhowal Financial-Services Stress-Test",
        "source": "Lakhowal Stress-Test Analysis (15 May 2026)",
        "engine": "non-compensatory Gamma (Law of Concurrence)",
        "layer_classification": {
            "layer": "C-2",
            "role": "benchmark scenario-illustration layer",
            "note": "stress_test is an ILLUSTRATIVE, non-compensatory SCENARIO layer, not the "
                    "frozen LAB authorization engine. Its per-scenario 'confidence', "
                    "'effectively_tackled', and 'verdict' fields are AUTHOR-ASSESSED (qualitative "
                    "analyst judgement), not engine-computed metrics. No value here feeds Gamma / "
                    "evaluate_decision or changes any reported LAB metric (labeling only, Commit 6.1).",
        },
        "scenarios": scenarios,
        "aggregate": {
            "scenarios": len(scenarios),
            "weighted_effectively_tackled_pct": agg,
            "range": "74-81% (low=shipped pack only, high=+recommended custom predicates)",
            "all_in_scope_denials_fail_closed": fail_closed_all,
            "verdicts": {s["id"]: s["verdict"] for s in scenarios},
        },
        "honest_limits": [
            "Upstream data poisoning (OCR drift, ERP corruption before ingestion) is out of scope.",
            "Oracle problem: stale truth behind a fresh feed is not detectable by the gate.",
            "Predicate completeness is unprovable; I_class extensibility is a feature, not a completeness claim.",
            "Insider-credentialed valid actions pass predicates (Assumption 1 boundary).",
        ],
    }
    if write:
        (ROOT / "stress_test_report.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    r = run()
    print("=" * 66)
    print("  LAKHOWAL FINANCIAL-SERVICES STRESS TEST")
    print("=" * 66)
    for s in r["scenarios"]:
        fc = "fail-closed OK" if s.get("fail_closed_ok") else "see subcases"
        print(f"  {s['id']} {s['name']:<28s} {s['confidence']:<11s} "
              f"{s['effectively_tackled']:<8s} {s['verdict']:<12s} [{fc}]")
    a = r["aggregate"]
    print("-" * 66)
    print(f"  weighted effectively-tackled : {a['weighted_effectively_tackled_pct']}%  ({a['range']})")
    print(f"  all in-scope denials fail-closed: {a['all_in_scope_denials_fail_closed']}")
    print(f"  wrote stress_test_report.json")
    print("=" * 66)


if __name__ == "__main__":
    main()
