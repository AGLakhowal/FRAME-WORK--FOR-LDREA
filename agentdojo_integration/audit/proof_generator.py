"""Phase E --- scientific proof-chain generator.

For every authorization decision, emit a proof chain:
  Predicate → Deficit → Γ_global → Γ_class → Π → Authorization → Execution → Environment → Evidence
  → Replay → Verification
as Markdown and JSON (Markdown is pandoc/PDF-ready). Each link states the concrete recorded value and
the rule that connects it to the next, so a reviewer can follow the derivation end-to-end.
"""
from __future__ import annotations

import json
from pathlib import Path

from ._util import read_jsonl, write_json, write_text, sha256_hex


def _episode_dirs(root: str | Path) -> list[Path]:
    return sorted(p.parent for p in Path(root).rglob("execution_trace.jsonl"))


def _collect(events: list[dict]):
    from collections import defaultdict
    s = defaultdict(dict)
    for e in events:
        st = e.get("step_number"); et = e.get("event_type")
        if et == "GAMMA_INTERCEPT":
            s[st].update(tool=e.get("tool_proposed"), policy_class=e.get("policy_class"))
        elif et == "PREDICATE_EVALUATION":
            s[st].setdefault("predicates", []).append(
                {"name": e["predicate_name"], "deficit": e.get("deficit"), "status": e.get("evaluation_status")})
        elif et == "Γ COMPUTATION":
            s[st].update(gamma_global=e.get("gamma_global"), gamma_class=e.get("gamma_class"),
                         gamma_equation=e.get("equation"))
        elif et == "Π COMPUTATION":
            s[st].update(pi=e.get("final_pi"), pi_equation=e.get("equation"))
        elif et in ("PERMIT_DECISION", "DENY_DECISION"):
            s[st].update(decision=e.get("decision"), reason=e.get("reason"))
        elif et == "TOOL_EXECUTION":
            s[st].update(executed=e.get("executed"), env_delta=e.get("env_effect_delta"))
    return s


def _proof_for_step(episode_id: str, st: int, s: dict, replay_ok) -> dict:
    active = [p["name"] for p in s.get("predicates", []) if p.get("deficit") == 1]
    chain = [
        {"stage": "Predicate", "value": s.get("predicates"),
         "rule": "Each frozen predicate family evaluated against the candidate action + environment."},
        {"stage": "Deficit", "value": {"active_deficits": active},
         "rule": "deficit_i = 1 iff predicate i fails its threshold directive (binary)."},
        {"stage": "Γ_global", "value": s.get("gamma_global"),
         "rule": s.get("gamma_equation", "Gamma_G = max_i deficit_i (non-compensatory)")},
        {"stage": "Γ_class", "value": s.get("gamma_class"),
         "rule": "class veto = 1 iff ReasonCodes ∈ {CLASS_1, GOODHART}."},
        {"stage": "Π", "value": s.get("pi"),
         "rule": s.get("pi_equation", "Pi = 1 iff (Gamma_G==0 AND Gamma_class==0)")},
        {"stage": "Authorization", "value": s.get("decision"),
         "rule": "PERMIT iff Pi==1 else SAFE_STATE."},
        {"stage": "Execution", "value": {"executed": s.get("executed")},
         "rule": "tool executes iff PERMIT; SAFE_STATE blocks it (fail-closed)."},
        {"stage": "Environment", "value": {"env_delta": s.get("env_delta")},
         "rule": "environment mutates only if the tool executed; blocked ⇒ delta 0."},
    ]
    evidence = sha256_hex({"episode": episode_id, "step": st, "chain": chain})
    chain += [
        {"stage": "Evidence", "value": evidence,
         "rule": "sha256 over (episode, step, derivation chain) — tamper-evident evidence quad."},
        {"stage": "Replay", "value": {"authorization_identical": replay_ok},
         "rule": "candidate action re-run through a clean frozen runtime reproduces the decision."},
        {"stage": "Verification", "value": {"proof_consistent": _consistent(s)},
         "rule": "Γ_global == OR(deficits) AND Pi == (Γ_global==0 ∧ Γ_class==0) AND decision matches Pi."},
    ]
    return {"episode": episode_id, "step": st, "tool": s.get("tool"),
            "policy_class": s.get("policy_class"), "decision": s.get("decision"),
            "evidence_hash": evidence, "chain": chain}


def _consistent(s: dict) -> bool:
    deficits = [p.get("deficit") for p in s.get("predicates", [])]
    g = 1 if any(d == 1 for d in deficits) else 0
    pi = 1 if (g == 0 and (s.get("gamma_class") or 0) == 0) else 0
    dec = "PERMIT" if pi == 1 else "SAFE_STATE"
    return (g == s.get("gamma_global") and pi == s.get("pi")
            and (s.get("decision") is None or dec == s.get("decision")))


def _render_md(proof: dict) -> str:
    L = [f"### Proof — {proof['episode']} · step {proof['step']} · `{proof['tool']}` "
         f"({proof['policy_class']}) → **{proof['decision']}**", "",
         "```", "Predicate → Deficit → Γ_global → Γ_class → Π → Authorization → Execution → "
         "Environment → Evidence → Replay → Verification", "```", ""]
    for link in proof["chain"]:
        L.append(f"- **{link['stage']}** = `{json.dumps(link['value'], default=str)}`  \n  _rule:_ {link['rule']}")
    L += ["", f"Evidence hash: `{proof['evidence_hash']}`", ""]
    return "\n".join(L)


def generate(root: str | Path, outdir: str | Path) -> dict:
    out = Path(outdir); (out / "proofs").mkdir(parents=True, exist_ok=True)
    all_proofs = []
    for ed in _episode_dirs(root):
        events = read_jsonl(ed / "execution_trace.jsonl")
        episode_id = next((e.get("episode_id") for e in events if e.get("episode_id")), ed.name)
        val = {}
        vp = ed / "validation_report.json"
        if vp.exists():
            val = json.loads(vp.read_text())
        steps = _collect(events)
        md_parts, proofs = [], []
        for st in sorted(steps):
            if "decision" not in steps[st]:
                continue
            proof = _proof_for_step(episode_id, st, steps[st], val.get("identical"))
            proofs.append(proof); all_proofs.append(proof)
            md_parts.append(_render_md(proof))
        if proofs:
            name = f"{ed.parent.name}__{ed.name}"
            write_text(out / "proofs" / f"{name}.md", f"# Proof chains — {episode_id}\n\n" + "\n".join(md_parts))
            write_json(out / "proofs" / f"{name}.json", proofs)
    write_json(out / "all_proofs.json", all_proofs)
    n_consistent = sum(1 for p in all_proofs
                       if p["chain"][-1]["value"]["proof_consistent"])
    return {"n_proofs": len(all_proofs), "n_consistent": n_consistent,
            "all_consistent": n_consistent == len(all_proofs)}
