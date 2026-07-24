"""Phase C --- human-readable reviewer audit reports.

One report per episode (tool, policy class, per-predicate PASS/FAIL, Γ_global, Γ_class, Π, decision,
reason, environment-modified, replay-verified, evidence hash) plus a Master Report across the
benchmark. All values are read from the recorded trace + validation/integrity sidecars.
"""
from __future__ import annotations

from pathlib import Path

from ._util import read_jsonl, write_text, sha256_hex


def _episode_dirs(root: str | Path) -> list[Path]:
    return sorted(p.parent for p in Path(root).rglob("execution_trace.jsonl"))


def _load(epi_dir: Path) -> dict:
    events = read_jsonl(epi_dir / "execution_trace.jsonl")
    import json
    val = json.loads((epi_dir / "validation_report.json").read_text()) if (epi_dir / "validation_report.json").exists() else {}
    integ = json.loads((epi_dir / "trace_integrity.json").read_text()) if (epi_dir / "trace_integrity.json").exists() else {}
    return {"events": events, "validation": val, "integrity": integ}


def _steps(events: list[dict]) -> dict:
    from collections import defaultdict
    s = defaultdict(dict)
    for e in events:
        st = e.get("step_number")
        et = e.get("event_type")
        if et == "GAMMA_INTERCEPT":
            s[st]["tool"] = e.get("tool_proposed"); s[st]["class"] = e.get("policy_class")
        elif et == "PREDICATE_EVALUATION":
            s[st].setdefault("predicates", []).append(
                (e["predicate_name"], "FAILED" if e.get("deficit") == 1 else "PASSED", e.get("evaluation_status")))
        elif et == "Γ COMPUTATION":
            s[st]["gamma_global"] = e.get("gamma_global"); s[st]["gamma_class"] = e.get("gamma_class")
        elif et == "Π COMPUTATION":
            s[st]["pi"] = e.get("final_pi")
        elif et in ("PERMIT_DECISION", "DENY_DECISION"):
            s[st]["decision"] = e.get("decision"); s[st]["reason"] = e.get("reason")
            s[st]["blocking"] = e.get("blocking_predicate")
        elif et == "TOOL_EXECUTION":
            s[st]["executed"] = e.get("executed"); s[st]["env_delta"] = e.get("env_effect_delta")
    return s


def episode_report(epi_dir: Path) -> str:
    d = _load(epi_dir)
    steps = _steps(d["events"])
    val = d["validation"]
    epi_id = next((e.get("episode_id") for e in d["events"] if e.get("episode_id")), epi_dir.name)
    fin = next((e for e in d["events"] if e.get("event_type") == "EPISODE_FINISHED"), {})
    L = [f"# Reviewer Audit Report — {epi_id}", "",
         f"- Episode dir: `{epi_dir}`",
         f"- Utility: {fin.get('utility')} · Security: {fin.get('security')}",
         f"- Replay verified (authorization identical): {val.get('identical')}",
         f"- Trace integrity ok: {d['integrity'].get('integrity_ok')} · chain root: `{d['integrity'].get('chain_root','')[:16]}…`",
         ""]
    adjudications = [st for st in sorted(steps) if "decision" in steps[st]]
    if not adjudications:
        L += ["_No externally-effective action reached Gamma in this episode "
              "(no EEA proposed by the model, or only read-only tools). No authorization decision to audit._", ""]
    for st in adjudications:
        s = steps[st]
        L += [f"## Step {st} — Tool Proposed: `{s.get('tool')}`", "",
              f"- Policy Class: **{s.get('class')}**", "", "### Predicates", "",
              "| predicate | result | status |", "|---|---|---|"]
        for name, res, status in s.get("predicates", []):
            L.append(f"| {name} | {res} | {status} |")
        evidence = sha256_hex({"tool": s.get("tool"), "class": s.get("class"),
                               "predicates": s.get("predicates"), "gamma_global": s.get("gamma_global"),
                               "gamma_class": s.get("gamma_class"), "pi": s.get("pi"),
                               "decision": s.get("decision")})
        L += ["",
              f"- Γ_Global: **{s.get('gamma_global')}**",
              f"- Γ_Class: **{s.get('gamma_class')}**",
              f"- Π: **{s.get('pi')}**",
              f"- Decision: **{s.get('decision')}**",
              f"- Reason: {s.get('reason')}",
              f"- Environment modified: **{'YES' if (s.get('env_delta') or 0) != 0 else 'NO'}**",
              f"- Replay verified: **{'YES' if val.get('identical') else 'NO'}**",
              f"- Evidence hash: `{evidence}`", ""]
    return "\n".join(L)


def generate(root: str | Path, outdir: str | Path) -> dict:
    out = Path(outdir); (out / "episodes").mkdir(parents=True, exist_ok=True)
    dirs = _episode_dirs(root)
    rows = []
    for ed in dirs:
        rep = episode_report(ed)
        name = f"{ed.parent.name}__{ed.name}.md"
        write_text(out / "episodes" / name, rep)
        d = _load(ed)
        steps = _steps(d["events"])
        adj = [steps[st] for st in steps if "decision" in steps[st]]
        rows.append({"episode": f"{ed.parent.name}/{ed.name}",
                     "n_adjudications": len(adj),
                     "permits": sum(1 for a in adj if a.get("decision") == "PERMIT"),
                     "denials": sum(1 for a in adj if a.get("decision") == "SAFE_STATE"),
                     "replay_ok": d["validation"].get("identical"),
                     "integrity_ok": d["integrity"].get("integrity_ok")})
    master = ["# Master Reviewer Report", "", f"Episodes audited: {len(rows)}", "",
              "| episode | adjudications | permits | denials | replay ok | integrity ok |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        master.append(f"| {r['episode']} | {r['n_adjudications']} | {r['permits']} | {r['denials']} | "
                      f"{r['replay_ok']} | {r['integrity_ok']} |")
    write_text(out / "MASTER_REPORT.md", "\n".join(master))
    return {"n_episode_reports": len(rows), "rows": rows}
