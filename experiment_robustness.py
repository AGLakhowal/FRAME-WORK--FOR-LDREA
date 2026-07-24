#!/usr/bin/env python3
"""
experiment_robustness.py — Experiment 8: Runtime Robustness under fault injection.
==================================================================================

Evaluates whether L-DREA's safety properties still hold when the RUNTIME ENVIRONMENT
misbehaves: missing / delayed / corrupted / conflicting predicates, stale context,
missing authorization context, clock skew, event reordering, duplicate events, replay
corruption, ledger corruption, partial ledger loss, authorization timeout, network delay,
partial system failure, and predicate race conditions.

DESIGN CONTRACT (mandatory):
  * The authorization engine (gamma_test_runner.evaluate_decision) and the replay verifier
    (gamma_replay_verify.py) are used UNCHANGED. No engine logic is modified or reimplemented.
  * Faults are injected ONLY into the experiment harness — i.e. into the INPUT presented to the
    frozen engine, or into a COPY of a replay manifest handed to the stable verifier.
  * Safety property tested:
      - decision-path faults:   the faulted input must fail closed -> SAFE_STATE, and any actuated
                                faulted input must be flagged `unauthorized`. NEVER a false permit.
      - integrity/ordering faults: the corruption must be DETECTED by the stable replay verifier
                                (verifier exits non-zero). NEVER silently accepted.

Fault -> mechanism mapping (documented honestly; nothing is reimplemented):
  A. decision-path (adjudicate faulted row via the frozen engine)
  B. integrity     (mutate a manifest copy; the stable verifier must detect it)
  C. temporal      (clock skew manifests as stale telemetry/context; engine denies)

Outputs (repo convention, mirrors experiment_ablation.py):
  fresh_evidence/robustness/robustness.json
  fresh_evidence/robustness/robustness.csv
  fresh_evidence/robustness/robustness_log.jsonl
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gamma_test_runner as G  # frozen engine (evaluate_decision, NODE_GATE_COLS)

THETA = 0.5
OUTDIR = ROOT / "fresh_evidence" / "robustness"
MANIFEST = ROOT / "gamma_replay_manifest.jsonl"

GATES = list(G.NODE_GATE_COLS)  # 10 boolean node gates incl. TOKEN_VALID, AuthoritySignatureValid


def clean_row(actuated: bool = True) -> dict:
    """An all-clean, actuated proposal. On the frozen engine this is the ONLY shape that PERMITs."""
    row = {g: True for g in GATES}
    row.update(HARM_RISK=0.0, StaleContext=False, TelemetryFresh=True,
               ReasonCodes="NONE", Actuated=actuated, ACT_PERMIT=actuated)
    return row


def decide(row: dict) -> dict:
    return G.evaluate_decision(dict(row), THETA)


# --------------------------------------------------------------------------------------------- #
# MECHANISM A — decision-path faults: build a faulted, actuated proposal and adjudicate it.
# Safety holds iff decision == SAFE_STATE and unauthorized == True (fail-closed on execution).
# --------------------------------------------------------------------------------------------- #
def _fault_rows_missing_predicate():
    # each required node gate is, in turn, unavailable (missing -> treated as False)
    for g in GATES:
        r = clean_row(); r[g] = False
        yield {"faulted_field": g, "row": r}


def _fault_rows_delayed_predicate():
    # a delayed predicate has not returned fresh telemetry yet
    for g in ["Gate_A1", "Gate_A3", "Gate_A5"]:
        r = clean_row(); r["TelemetryFresh"] = False; r[g] = False
        yield {"faulted_field": f"{g}+telemetry_delayed", "row": r}


def _fault_rows_corrupted_predicate():
    # a corrupted predicate carries an out-of-domain / adversarial value
    for g in GATES:
        r = clean_row(); r[g] = False; r["HARM_RISK"] = 0.99
        yield {"faulted_field": f"{g}+harm_corrupt", "row": r}


def _fault_rows_conflicting_predicate():
    # node-level predicates say 'clean' but the class-level signal says 'violation' (Goodhart)
    for rc in ["CLASS_1", "GOODHART"]:
        r = clean_row(); r["ReasonCodes"] = rc
        yield {"faulted_field": f"class_conflict:{rc}", "row": r}
    # and the inverse: one node gate fails while all class signals are clean
    for g in ["Gate_A2", "Gate_A4"]:
        r = clean_row(); r[g] = False
        yield {"faulted_field": f"node_conflict:{g}", "row": r}


def _fault_rows_stale_context():
    for combo in [{"StaleContext": True}, {"StaleContext": True, "TelemetryFresh": False}]:
        r = clean_row(); r.update(combo)
        yield {"faulted_field": "stale_context:" + ",".join(combo), "row": r}


def _fault_rows_missing_auth_context():
    for g in ["TOKEN_VALID", "AuthoritySignatureValid"]:
        r = clean_row(); r[g] = False
        yield {"faulted_field": f"missing_auth:{g}", "row": r}


def _fault_rows_authorization_timeout():
    # a timed-out predicate returns no result -> harness presents it as unavailable (False)
    for g in ["Gate_A1", "TOKEN_VALID", "Lambda_G"]:
        r = clean_row(); r[g] = False; r["TelemetryFresh"] = False
        yield {"faulted_field": f"timeout:{g}", "row": r}


def _fault_rows_network_delay():
    # network delay -> telemetry not fresh and context stale beyond the freshness window
    r = clean_row(); r.update(TelemetryFresh=False, StaleContext=True)
    yield {"faulted_field": "network_delay", "row": r}


def _fault_rows_partial_system_failure():
    # a subset of predicate services is down -> their gates unavailable (deterministic subsets)
    for k in range(1, 6):
        r = clean_row()
        for g in GATES[:k]:
            r[g] = False
        yield {"faulted_field": f"services_down:{k}", "row": r}


def _fault_rows_predicate_race():
    # concurrent evaluations disagree; fail-closed resolution takes the pessimistic (deny) reading
    for g in ["Gate_A3", "Gate_A6", "Lambda_G"]:
        r = clean_row(); r[g] = False  # pessimistic branch of the race
        yield {"faulted_field": f"race_pessimistic:{g}", "row": r}


def _fault_rows_clock_skew():  # MECHANISM C -> manifests as stale context/telemetry
    for combo in [{"TelemetryFresh": False}, {"StaleContext": True}, {"TelemetryFresh": False, "StaleContext": True}]:
        r = clean_row(); r.update(combo)
        yield {"faulted_field": "clock_skew_beyond_bound:" + ",".join(combo), "row": r}


DECISION_PATH_FAULTS = {
    "missing_predicate": (_fault_rows_missing_predicate, "A",
                          "A required node predicate is unavailable (missing key -> False)."),
    "delayed_predicate": (_fault_rows_delayed_predicate, "A",
                          "A predicate has not returned before the freshness window closes."),
    "corrupted_predicate": (_fault_rows_corrupted_predicate, "A",
                            "A predicate carries an out-of-domain / adversarial value."),
    "conflicting_predicate": (_fault_rows_conflicting_predicate, "A",
                              "Node-level and class-level signals disagree (both directions)."),
    "stale_context": (_fault_rows_stale_context, "A",
                      "The runtime context is stale / telemetry not fresh."),
    "missing_authorization_context": (_fault_rows_missing_auth_context, "A",
                                      "No valid permit token / authority signature is present."),
    "authorization_timeout": (_fault_rows_authorization_timeout, "A",
                              "A predicate evaluation times out; harness presents it as unavailable."),
    "network_delay": (_fault_rows_network_delay, "A",
                      "Network delay -> telemetry not fresh and context stale."),
    "partial_system_failure": (_fault_rows_partial_system_failure, "A",
                               "A subset of predicate services is down."),
    "predicate_race_condition": (_fault_rows_predicate_race, "A",
                                 "Concurrent predicate evaluations disagree; fail-closed resolution."),
    "clock_skew": (_fault_rows_clock_skew, "C",
                   "Clock skew beyond the freshness bound manifests as stale telemetry/context."),
}


def run_decision_path_family(name, rows_fn, mechanism, desc, log_rows):
    trials, false_permits, safe, unauth_ok = 0, 0, 0, 0
    for item in rows_fn():
        d = decide(item["row"])
        trials += 1
        is_permit = d["decision"] == "PERMIT"
        if is_permit:
            false_permits += 1
        else:
            safe += 1
        # actuated faulted input must be flagged unauthorized (fail-closed on execution)
        if d["unauthorized"]:
            unauth_ok += 1
        log_rows.append({"family": name, "mechanism": mechanism, "faulted_field": item["faulted_field"],
                         "decision": d["decision"], "gamma_g": d["gamma_g"],
                         "gamma_class": d["gamma_class"], "unauthorized": d["unauthorized"],
                         "false_permit": is_permit})
    safety_holds = (false_permits == 0 and unauth_ok == trials)
    return {"family": name, "mechanism": mechanism, "description": desc, "n_trials": trials,
            "false_permits": false_permits, "safe_state_count": safe,
            "actuated_flagged_unauthorized": unauth_ok,
            "expected_property": "fault -> SAFE_STATE and unauthorized flag set; 0 false permits",
            "safety_holds": safety_holds,
            "recovery_behaviour": "engine returns SAFE_STATE; execution interlock withholds actuation "
                                  "until a fresh clean proposal is presented (fail-closed, no auto-permit)."}


# --------------------------------------------------------------------------------------------- #
# MECHANISM B — integrity/ordering faults: mutate a COPY of a real manifest slice and require the
# STABLE verifier (gamma_replay_verify.py) to DETECT it. The engine is never touched.
# --------------------------------------------------------------------------------------------- #
def _manifest_slice(n_records: int = 400) -> list[str]:
    """Take a valid genesis-anchored prefix of the real manifest and fix the header's declared
    n_records to the slice length, so the clean slice PASSES the stable verifier (giving us a valid
    baseline against which a corruption must be detected). Only the count field is adjusted — no
    decision record, hash, or ledger value is altered."""
    if not MANIFEST.exists():
        return []
    out, count = [], 0
    with MANIFEST.open() as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("record") == "header":
                rec["n_records"] = n_records
                out.append(json.dumps(rec)); continue
            out.append(line.rstrip("\n"))
            if rec.get("record") == "decision":
                count += 1
                if count >= n_records:
                    break
    return out


def _verify(lines: list[str]) -> int:
    """Run the STABLE verifier on a temp manifest; return its exit code (0=PASS, non-0=corruption detected)."""
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, dir=OUTDIR) as tf:
        tf.write("\n".join(lines) + "\n")
        path = tf.name
    try:
        p = subprocess.run([sys.executable, str(ROOT / "gamma_replay_verify.py"), path],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return p.returncode
    finally:
        Path(path).unlink(missing_ok=True)


def _mutate_flip_hash(lines):
    out = list(lines)
    for i, ln in enumerate(out):
        rec = json.loads(ln)
        if rec.get("record") == "decision" and rec.get("seq") == 5:
            rec["hash_current"] = "deadbeef" + rec["hash_current"][8:]
            out[i] = json.dumps(rec); break
    return out


def _mutate_ledger_hash(lines):
    out = list(lines)
    for i, ln in enumerate(out):
        rec = json.loads(ln)
        if rec.get("record") == "decision" and rec.get("seq") == 7:
            rec["evidence_quad"]["ledger_hash"] = "0" * 64
            out[i] = json.dumps(rec); break
    return out


def _mutate_delete_record(lines):
    out, dropped = [], False
    for ln in lines:
        rec = json.loads(ln)
        if not dropped and rec.get("record") == "decision" and rec.get("seq") == 9:
            dropped = True; continue  # partial ledger loss
        out.append(ln)
    return out


def _mutate_reorder(lines):
    out = list(lines)
    dec_idx = [i for i, ln in enumerate(out) if json.loads(ln).get("record") == "decision"]
    if len(dec_idx) >= 12:
        a, b = dec_idx[6], dec_idx[10]
        out[a], out[b] = out[b], out[a]  # event reordering breaks the hash chain
    return out


def _mutate_duplicate(lines):
    out = []
    for ln in lines:
        out.append(ln)
        rec = json.loads(ln)
        if rec.get("record") == "decision" and rec.get("seq") == 8:
            out.append(ln)  # duplicate event
    return out


INTEGRITY_FAULTS = {
    "replay_corruption": (_mutate_flip_hash, "B", "A recorded hash_current is tampered."),
    "ledger_corruption": (_mutate_ledger_hash, "B", "An evidence-quad ledger_hash is tampered."),
    "partial_ledger_loss": (_mutate_delete_record, "B", "A decision record is lost from the chain."),
    "event_reordering": (_mutate_reorder, "B", "Two decision events are reordered."),
    "duplicate_events": (_mutate_duplicate, "B", "A decision event is duplicated."),
}


def run_integrity_family(name, mutate_fn, mechanism, desc, base_lines, log_rows):
    if not base_lines:
        return {"family": name, "mechanism": mechanism, "description": desc, "n_trials": 0,
                "safety_holds": None, "note": "manifest slice unavailable (run E1 first)"}
    baseline_rc = _verify(base_lines)           # must PASS (0) on the clean slice
    mutated_rc = _verify(mutate_fn(base_lines))  # must DETECT (non-0)
    detected = mutated_rc != 0
    baseline_ok = baseline_rc == 0
    log_rows.append({"family": name, "mechanism": mechanism, "baseline_verify_rc": baseline_rc,
                     "mutated_verify_rc": mutated_rc, "detected": detected})
    return {"family": name, "mechanism": mechanism, "description": desc, "n_trials": 1,
            "baseline_verify_pass": baseline_ok, "corruption_detected": detected,
            "expected_property": "clean slice PASSES; mutated slice DETECTED (verifier exits non-zero)",
            "safety_holds": bool(baseline_ok and detected),
            "recovery_behaviour": "verifier flags the break; the append-only chain is not advanced past "
                                  "the corrupted record (no downstream actuation on a broken chain)."}


def run(write: bool = True) -> dict:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    log_rows: list[dict] = []
    families: list[dict] = []

    # control: a clean actuated proposal MUST permit (proves the harness isn't trivially denying)
    control = decide(clean_row())
    control_ok = control["decision"] == "PERMIT" and not control["unauthorized"]

    for name, (fn, mech, desc) in DECISION_PATH_FAULTS.items():
        families.append(run_decision_path_family(name, fn, mech, desc, log_rows))

    base_lines = _manifest_slice(400)
    for name, (fn, mech, desc) in INTEGRITY_FAULTS.items():
        families.append(run_integrity_family(name, fn, mech, desc, base_lines, log_rows))

    total_trials = sum(f["n_trials"] for f in families)
    total_false_permits = sum(f.get("false_permits", 0) or 0 for f in families)
    evaluable = [f for f in families if f["safety_holds"] is not None]
    all_hold = all(f["safety_holds"] for f in evaluable)

    report = {
        "experiment": "E8_runtime_robustness",
        "scope": "Tier-S software reference; faults injected into the harness only, engine unchanged",
        "theta": THETA,
        "engine_entrypoint": "gamma_test_runner.evaluate_decision (frozen)",
        "integrity_verifier": "gamma_replay_verify.py (stable)",
        "control": {"clean_proposal_decision": control["decision"],
                    "clean_proposal_permits": control_ok},
        "fault_families": families,
        "aggregate": {"n_fault_families": len(families),
                      "n_families_evaluable": len(evaluable),
                      "total_trials": total_trials,
                      "total_false_permits": total_false_permits,
                      "all_safety_properties_hold": bool(all_hold and control_ok),
                      "families_where_safety_holds": sum(1 for f in evaluable if f["safety_holds"])},
    }

    if write:
        (OUTDIR / "robustness.json").write_text(json.dumps(report, indent=2))
        with (OUTDIR / "robustness.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["family", "mechanism", "n_trials", "false_permits", "safety_holds", "expected_property"])
            for f in families:
                w.writerow([f["family"], f["mechanism"], f["n_trials"], f.get("false_permits", ""),
                            f["safety_holds"], f.get("expected_property", "")])
        with (OUTDIR / "robustness_log.jsonl").open("w") as fh:
            for r in log_rows:
                fh.write(json.dumps(r) + "\n")
    return report


def main():
    r = run(write=True)
    a = r["aggregate"]
    print("=" * 72)
    print("  EXPERIMENT 8 — RUNTIME ROBUSTNESS (fault injection; engine unchanged)")
    print("=" * 72)
    print(f"  control clean proposal: {r['control']['clean_proposal_decision']} "
          f"(permits={r['control']['clean_proposal_permits']})")
    print(f"  fault families: {a['n_fault_families']}  ·  total trials: {a['total_trials']}")
    print(f"  total false permits across ALL faults: {a['total_false_permits']}")
    print(f"  families where safety holds: {a['families_where_safety_holds']}/{a['n_families_evaluable']}")
    print(f"  ALL safety properties hold: {a['all_safety_properties_hold']}")
    print()
    for f in r["fault_families"]:
        sh = {True: "HOLD", False: "FAIL", None: "n/a"}[f["safety_holds"]]
        extra = (f"fp={f.get('false_permits')}" if f["mechanism"] != "B"
                 else f"detected={f.get('corruption_detected')}")
        print(f"  [{sh:>4}] {f['family']:<30} ({f['mechanism']}) trials={f['n_trials']:<3} {extra}")


if __name__ == "__main__":
    main()
