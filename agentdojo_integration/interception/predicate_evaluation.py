"""PredicateEvaluator --- instantiate frozen predicate families against a candidate action.

All POLICY is read from the manifests via injected loaders:
  * the per-tool argument_binding (which arg, recognized-set, normalizer)              -> passed in from ExecutionBinding.tool_binding (Layer 2)
  * the threshold directive (membership / env_upper_bound / structural)                -> ExecutionBinding.family_threshold (Layer 2)
  * whether a family is APPLICABLE_ENV_DERIVED / EXCLUDED_BY_POLICY / AGGREGATOR       -> ExecutionBinding.family_status (Layer 2)
  (Layer 2 is itself deterministically derived from, and provenance-linked to, the frozen Layer-1
   scientific manifests; it introduces no scientific content.)

This module holds NO tool->arg map and NO threshold constant. It only:
  (a) reads env state to compute a NAMED recognized-set (a mechanical env-field read, not policy), and
  (b) interprets the manifest's machine-readable threshold directive.
Structural predicates are explicitly reported as EXCLUDED_BY_POLICY (never "silently passing").

Spec: refactor items 2, 3, 5; Recipient Derivation Manifest (#4).
"""
from __future__ import annotations
from typing import Mapping, Any


# ---- env-field readers (mechanical; implement the Recipient Manifest's NAMED recognized-sets) ----
def _aslist(v):
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple, set)) else [v]


def _emails(env) -> set:
    out = set()
    ib = getattr(env, "inbox", None)
    if ib is not None:
        ae = getattr(ib, "account_email", None)
        if ae:
            out.add(str(ae).lower())
        for c in _aslist(getattr(ib, "contact_list", [])):
            e = getattr(c, "email", None)
            if e:
                out.add(str(e).lower())
        for coll in ("emails", "initial_emails"):
            for m in _aslist(getattr(ib, coll, [])):
                s = getattr(m, "sender", None)
                if s:
                    out.add(str(s).lower())
                for fld in ("recipients", "cc", "bcc"):
                    for r in _aslist(getattr(m, fld, [])):
                        out.add(str(r).lower())
    return out


def _ibans(env) -> set:
    out = set()
    ba = getattr(env, "bank_account", None)
    if ba is not None:
        if getattr(ba, "iban", None):
            out.add(str(ba.iban))
        for coll in ("transactions", "scheduled_transactions"):
            for t in _aslist(getattr(ba, coll, [])):
                for fld in ("recipient", "sender"):
                    v = getattr(t, fld, None)
                    if v:
                        out.add(str(v))
    return out


def _slack_users(env) -> set:
    sl = getattr(env, "slack", None)
    return {str(u) for u in _aslist(getattr(sl, "users", []))} if sl is not None else set()


def _slack_channels(env) -> set:
    sl = getattr(env, "slack", None)
    return {str(c) for c in _aslist(getattr(sl, "channels", []))} if sl is not None else set()


def _urls(env) -> set:
    web = getattr(env, "web", None)
    if web is None:
        return set()
    wc = getattr(web, "web_content", {}) or {}
    return {str(k) for k in (wc.keys() if hasattr(wc, "keys") else [])}


def _resources(env, kind) -> set:
    obj = getattr(env, kind, None)
    if obj is None:
        return set()
    candidates = obj if isinstance(obj, list) else []
    if not candidates:
        for a in list(getattr(type(obj), "model_fields", {}).keys()):
            v = getattr(obj, a, None)
            if isinstance(v, list):
                candidates += v
    return {str(getattr(c, "name")) for c in candidates if getattr(c, "name", None)}


# named recognized-set registry (keys match the Tool Mapping Manifest recognized_set_catalog)
_RECOGNIZED_SETS = {
    "ibans": _ibans, "emails": _emails, "slack_users": _slack_users,
    "slack_channels": _slack_channels, "urls": _urls,
    "resources:hotels": lambda e: _resources(e, "hotels"),
    "resources:restaurants": lambda e: _resources(e, "restaurants"),
    "resources:car_rental": lambda e: _resources(e, "car_rental"),
}
_NORMALIZERS = {"exact": lambda x: str(x).strip(), "lower": lambda x: str(x).strip().lower()}


def _resolve_env_ref(env, ref: str):
    obj = env
    for part in ref.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


class PredicateEvaluator:
    def __init__(self, binding):
        self.binding = binding  # ExecutionBinding (Layer 2): family status + threshold directives

    def evaluate(self, env, tool: str, args: Mapping[str, Any], families: list, binding: dict) -> dict:
        """Return {'deficits': {family: 0/1}, 'status': {family: <evaluation_status>}}.

        Only families the manifest marks APPLICABLE_ENV_DERIVED and that this tool binds are
        evaluated from env; all others are reported EXCLUDED_BY_POLICY / AGGREGATOR (not passed silently).
        """
        args = dict(args or {})
        deficits = {f: 0 for f in families}
        status = {f: self.binding.family_status(f) for f in families}

        recog = (binding or {}).get("recognition")
        if recog:
            fam = recog["family"]
            extractor = _RECOGNIZED_SETS[recog["recognized_set"]]
            norm = _NORMALIZERS[recog["normalizer"]]
            th = self.binding.family_threshold(fam)  # authoritative threshold directive
            if th.get("kind") == "membership" and fam in deficits:
                recognized = {norm(x) for x in extractor(env)}
                targets = []
                for a in recog["args"]:
                    targets += _aslist(args.get(a))
                targets = [t for t in targets if t not in (None, "")]
                miss = any(norm(t) not in recognized for t in targets) if targets else False
                deficits[fam] = 1 if miss else 0
                status[fam] = "EVALUATED_DEFICIT" if miss else "EVALUATED_PASS"

        amt = (binding or {}).get("amount")
        if amt:
            fam = amt["family"]
            th = self.binding.family_threshold(fam)
            if th.get("kind") == "env_upper_bound" and fam in deficits:
                value = args.get(amt["arg"])
                bound = _resolve_env_ref(env, th["env_ref"])
                if value is not None and bound is not None:
                    try:
                        over = float(value) > float(bound)  # operator 'le' per directive; deficit if gt
                        deficits[fam] = 1 if over else 0
                        status[fam] = "EVALUATED_DEFICIT" if over else "EVALUATED_PASS"
                    except (TypeError, ValueError):
                        deficits[fam] = 0
                        status[fam] = "EVALUATED_PASS"
        return {"deficits": deficits, "status": status}
