#!/usr/bin/env python3
"""build_execution_binding.py --- LAYER 2 (implementation) generator.

Deterministically derives Execution_Binding_Manifest.json FROM the frozen Layer-1 scientific
manifests (root ce8c8467...) + PUBLIC AgentDojo v0.1.35 tool signatures. It contains NO scientific
decision: only a runtime translation of the frozen specification into lookup structures
(gamma-slot routing, tool argument bindings, recognized-set names, env field refs, evaluation
status, unknown-tool fail-closed policy). It NEVER modifies the scientific manifests.

Re-run must be byte-identical (sorted keys, constant date). The output records the frozen scientific
Merkle root it was derived from (provenance) and validates every binding against the frozen tool
mapping and the public tool signatures.

Re-run: agentdojo_integration/.venv/bin/python agentdojo_integration/manifests/build_execution_binding.py
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FROZEN_DATE = "2026-07-07"
SCIENTIFIC_ROOT = "ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


# --- read frozen Layer-1 scientific manifests (source of truth) -------------
tm = json.loads((HERE / "tool_mapping_manifest.json").read_text())
pm = json.loads((HERE / "predicate_manifest.json").read_text())
recorded_root = json.loads((HERE / "merkle_root.json").read_text())["merkle_root"]
assert recorded_root == SCIENTIFIC_ROOT, f"scientific root drift: {recorded_root} != {SCIENTIFIC_ROOT}"

sci_families = set()
for cls, d in pm["action_class_predicate_binding"].items():
    sci_families.update(d["predicates"])
eea_rows = {r["tool"]: r for r in tm["tools"] if r["mediated"]}

# --- deterministic derivation (implementation translation only) -------------
_STRUCTURAL = {"kind": "structural", "deficit": 0, "status": "EXCLUDED_BY_POLICY_TIER_S"}
_MEMBERSHIP = {"kind": "membership", "deficit_if": "target_not_in_recognized_set"}
FAMILY_META = {
    "CTR_ISB":                      {"gamma_slot": "__StaleContext__",      "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "GAMMA":                        {"gamma_slot": "__aggregator__",        "evaluation_status": "AGGREGATOR_NOT_A_PREDICATE", "threshold": {"kind": "aggregator"}},
    "GATE_recipient_recognition":   {"gamma_slot": "Gate_A1", "evaluation_status": "APPLICABLE_ENV_DERIVED", "threshold": dict(_MEMBERSHIP)},
    "GATE_identity_recognition":    {"gamma_slot": "Gate_A1", "evaluation_status": "APPLICABLE_ENV_DERIVED", "threshold": dict(_MEMBERSHIP)},
    "GATE_destination_recognition": {"gamma_slot": "Gate_A1", "evaluation_status": "APPLICABLE_ENV_DERIVED", "threshold": dict(_MEMBERSHIP)},
    "GATE_resource_recognition":    {"gamma_slot": "Gate_A1", "evaluation_status": "APPLICABLE_ENV_DERIVED", "threshold": dict(_MEMBERSHIP)},
    "GATE_amount_limit":            {"gamma_slot": "Gate_A2", "evaluation_status": "APPLICABLE_ENV_DERIVED", "threshold": {"kind": "env_upper_bound", "env_ref": "bank_account.balance", "operator": "le", "deficit_if": "value_gt_bound"}},
    "GATE_scope":                   {"gamma_slot": "Gate_A3", "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "GATE_ownership":               {"gamma_slot": "Gate_A4", "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "AUTH_TOKEN":                   {"gamma_slot": "__TOKEN_VALID__",       "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "TRACE":                        {"gamma_slot": "Gate_A6", "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "INTERLOCK":                    {"gamma_slot": "Gate_A7", "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
    "CLASS_velocity":               {"gamma_slot": "__ReasonCodes_CLASS__", "evaluation_status": "EXCLUDED_BY_POLICY_TIER_S", "threshold": dict(_STRUCTURAL)},
}


def _recog(fam, args, rset, norm):
    return {"recognition": {"family": fam, "args": args, "recognized_set": rset, "normalizer": norm}}


TOOL_BINDING = {
    "send_money":            {**_recog("GATE_recipient_recognition", ["recipient"], "ibans", "exact"), "amount": {"family": "GATE_amount_limit", "arg": "amount"}},
    "schedule_transaction":  {**_recog("GATE_recipient_recognition", ["recipient"], "ibans", "exact"), "amount": {"family": "GATE_amount_limit", "arg": "amount"}},
    # ACCOUNT_MUTATION's frozen families are GATE_ownership + GATE_amount_limit (NO recipient recognition);
    # the binding must respect the frozen science -> amount-limit only (recipient recognition NOT assigned).
    "update_scheduled_transaction": {"recognition": None, "amount": {"family": "GATE_amount_limit", "arg": "amount"}},
    "send_email":            _recog("GATE_recipient_recognition", ["recipients"], "emails", "lower"),
    "send_direct_message":   _recog("GATE_recipient_recognition", ["recipient"], "slack_users", "exact"),
    "send_channel_message":  _recog("GATE_recipient_recognition", ["channel"], "slack_channels", "exact"),
    "add_calendar_event_participants": _recog("GATE_recipient_recognition", ["participants"], "emails", "lower"),
    "create_calendar_event": _recog("GATE_recipient_recognition", ["participants"], "emails", "lower"),
    "add_user_to_channel":   _recog("GATE_identity_recognition", ["user"], "slack_users", "exact"),
    "remove_user_from_slack":_recog("GATE_identity_recognition", ["user"], "slack_users", "exact"),
    "invite_user_to_slack":  _recog("GATE_identity_recognition", ["user_email"], "emails", "lower"),
    "share_file":            _recog("GATE_identity_recognition", ["email"], "emails", "lower"),
    "reserve_hotel":         _recog("GATE_resource_recognition", ["hotel"], "resources:hotels", "exact"),
    "reserve_restaurant":    _recog("GATE_resource_recognition", ["restaurant"], "resources:restaurants", "exact"),
    "reserve_car_rental":    _recog("GATE_resource_recognition", ["company"], "resources:car_rental", "exact"),
    "get_webpage":           _recog("GATE_destination_recognition", ["url"], "urls", "exact"),
    "post_webpage":          _recog("GATE_destination_recognition", ["url"], "urls", "exact"),
    "update_user_info":      {"recognition": None, "structural_only": True},
    "update_password":       {"recognition": None, "structural_only": True},
    "create_file":           {"recognition": None, "structural_only": True},
    "append_to_file":        {"recognition": None, "structural_only": True},
    "delete_file":           {"recognition": None, "structural_only": True},
    "delete_email":          {"recognition": None, "structural_only": True},
    "cancel_calendar_event": {"recognition": None, "structural_only": True},
    "reschedule_calendar_event": {"recognition": None, "structural_only": True},
}

# --- validation against the FROZEN scientific manifests --------------------
for f in FAMILY_META:
    assert f in sci_families, f"binding family {f} not in scientific predicate manifest"
assert set(TOOL_BINDING) == set(eea_rows), (
    f"binding tools must exactly equal the 25 frozen EEA tools; "
    f"missing={set(eea_rows) - set(TOOL_BINDING)} extra={set(TOOL_BINDING) - set(eea_rows)}"
)
for tool, b in TOOL_BINDING.items():
    recog = b.get("recognition")
    if recog:
        assert recog["family"] in eea_rows[tool]["predicate_families"], (tool, recog["family"])
        assert recog["family"] in FAMILY_META
    if b.get("amount"):
        assert b["amount"]["family"] in eea_rows[tool]["predicate_families"], (tool, "amount")

# --- validation against PUBLIC tool signatures (deterministic, pinned v0.1.35) ---
from agentdojo.task_suite.load_suites import get_suites  # noqa: E402
sigs = {}
for s in get_suites("v1").values():
    for t in s.tools:
        sigs.setdefault(t.name, sorted(t.parameters.model_fields.keys()))
for tool, b in TOOL_BINDING.items():
    params = set(sigs.get(tool, []))
    recog = b.get("recognition")
    if recog:
        for a in recog["args"]:
            assert a in params, f"{tool}: bound arg '{a}' not in public signature {sorted(params)}"
    if b.get("amount"):
        assert b["amount"]["arg"] in params, f"{tool}: bound amount arg not in public signature"
signature_snapshot_sha = sha(canon(sigs))

binding = {
    "manifest": "Execution Binding Manifest",
    "layer": "2-IMPLEMENTATION",
    "frozen_date": FROZEN_DATE,
    "purpose": "Runtime-only translation of the frozen Layer-1 scientific manifests into lookup structures. Contains NO scientific decision, predicate, threshold, authorization logic, benchmark configuration, or theorem change.",
    "derived_from_scientific_root": SCIENTIFIC_ROOT,
    "generation": "Deterministically generated by build_execution_binding.py from the 7 frozen scientific manifests + PUBLIC AgentDojo v0.1.35 tool signatures. Re-run is byte-identical (sorted keys, constant date).",
    "validated_against_frozen_tool_mapping": True,
    "validated_against_public_signatures": True,
    "public_signature_snapshot_sha256": signature_snapshot_sha,
    "family_metadata": FAMILY_META,
    "tool_argument_binding": TOOL_BINDING,
    "recognized_set_catalog": ["ibans", "emails", "slack_users", "slack_channels", "urls", "resources:hotels", "resources:restaurants", "resources:car_rental"],
    "env_field_references": {
        "ibans": ["bank_account.iban", "bank_account.transactions[].recipient|sender", "bank_account.scheduled_transactions[].recipient|sender"],
        "emails": ["inbox.account_email", "inbox.contact_list[].email", "inbox.emails[].sender|recipients|cc|bcc"],
        "slack_users": ["slack.users"], "slack_channels": ["slack.channels"],
        "urls": ["web.web_content.keys"], "resources:*": ["<kind>[].name"], "amount_bound": ["bank_account.balance"],
    },
    "gamma_slot_semantics": {
        "Gate_A1..A7": "a NODE_GATE_COLS deficit slot in the reused Gamma engine",
        "__TOKEN_VALID__": "ISB token channel", "__StaleContext__": "ISB context channel",
        "__ReasonCodes_CLASS__": "class-veto channel", "__aggregator__": "GAMMA is the LLC aggregator (not a node predicate)",
    },
    "unknown_tool_handling": {
        "handling": "SAFE_STATE_FAIL_CLOSED",
        "rule": "a tool absent from the frozen Tool Mapping Manifest is denied (SAFE_STATE) and never executed",
        "not_a_new_policy": "This is NOT a new scientific policy. It is the runtime consequence of Definition 2(i) (complete mediation: every candidate action must be mediated) applied to an unclassified tool, resolved to SAFE_STATE (FULL_SPEC Section 0.10 non-default-permit). No predicate, threshold, or authorization rule is introduced.",
        "derived_from": "Definition 2(i) complete mediation; SAFE_STATE (FULL_SPEC Section 2.3, 0.10 non-default-permit)",
    },
    "provenance_note": "Regenerable NON-scientific artifact. The 7 scientific manifests (root ce8c8467...) remain immutable and are not modified by this generator.",
}

out = HERE / "Execution_Binding_Manifest.json"
out.write_text(json.dumps(binding, indent=2) + "\n")
print("Execution_Binding_Manifest.json written")
print("binding canonical sha256   :", sha(canon(binding)))
print("derived_from_scientific_root:", SCIENTIFIC_ROOT)
print("public_signature_snapshot   :", signature_snapshot_sha)
print("EEA tools bound             :", len(TOOL_BINDING))
