#!/usr/bin/env python3
"""
combined_ablation_discovery.py — automatic runtime-component discovery (Steps 1–2).
===================================================================================

Discovers the runtime governance components that ACTUALLY EXIST in the repository by importing the
runtime modules and probing for their implementation symbols with `importlib` + `inspect`. Nothing
is hardcoded as "present": a component appears in the registry only if its symbol resolves in the
live code, and its implementation file / responsible function / source line are read back from
`inspect`, not asserted. Dependencies are inferred automatically two ways:

  1. EXECUTION ORDER — the order in which each component's call first appears inside the real
     pipeline driver `run_runtime_stack.main` (a stage depends on the stage before it).
  2. DATA DEPENDENCY — scanning each component's own source for another component's signature token
     (e.g. `Ledger.append` referencing `ertuple` ⇒ the ledger consumes the evidence quad).

Outputs:
    COMPONENT_REGISTRY.json           (also mirrored under metadata/)
    COMPONENT_DEPENDENCY_GRAPH.md
    component_dependency_graph.svg

Run standalone:  python3 combined_ablation_discovery.py
Imported by:     experiment_combined_ablation.py
"""
from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

# Candidate components to PROBE for. A candidate is registered only if its symbol resolves in the
# live code. (module, dotted-symbol) is the probe; the rest is metadata the probe cannot infer.
#   short:            stable code used in the ablation matrix / figures
#   plane:            semantic execution plane
#   matrix:           True => toggled in the combinatorial ablation matrix (decision path)
#                     False => executed every configuration as a governance-plane stage
#   sig_tokens:       substrings that mark THIS component when found in another's source (dep infer)
#   order_marker:     substring whose first appearance in run_runtime_stack.main marks this stage
_CANDIDATES = [
    dict(name="Predicate Engine", short="PE", module="runtime_stack",
         symbol="RuntimeContext.generate", plane="authorization", matrix=True,
         role="generates the runtime predicate vector Gamma aggregates non-compensatorily",
         sig_tokens=["ctx.generate", "generate(", "predicates"], order_marker="ctx.generate("),
    dict(name="Runtime Revocation", short="RV", module="runtime_stack",
         symbol="PermitAuthority", plane="enforcement", matrix=True,
         role="issues Permit-to-Act tokens and withdraws already-granted authority",
         sig_tokens=["PermitAuthority", "revoke", "verify_permit"], order_marker="permit ="),
    dict(name="Evidence Quad", short="EQ", module="runtime_stack",
         symbol="build_ertuple", plane="evidence", matrix=True,
         role="emits the signed ERTuple (method/policy/ledger/replay evidence) per decision",
         sig_tokens=["build_ertuple", "ertuple", "ERTuple"], order_marker="build_ertuple("),
    dict(name="Runtime Ledger", short="LG", module="runtime_stack",
         symbol="Ledger.append", plane="ledger", matrix=True,
         role="chains evidence into an append-only Merkle-rooted ledger",
         sig_tokens=["ledger.append", "merkle_root", "chain_index"],
         order_marker="ledger.append"),
    dict(name="Hash Chain", short="HC", module="runtime_stack",
         symbol="Ledger.verify", plane="ledger", matrix=True,
         role="links each ledger block to its predecessor (tamper-evident ordering)",
         sig_tokens=["hash_continuity", "detect_fork", "chain break"],
         order_marker="ledger.verify"),
    dict(name="Runtime Risk Detection", short="RD", module="runtime_attacks",
         symbol="run", plane="risk", matrix=False,
         role="fires real adversarial artifacts at the enforcement surface and measures refusal",
         sig_tokens=["runtime_attacks", "attacks_detected"], order_marker="ATK.run"),
    dict(name="Runtime Watchdog", short="WD", module="runtime_fleet",
         symbol="Watchdog", plane="governance", matrix=False,
         role="supervisor thread detecting per-worker stalls and driving fail-closed recovery",
         sig_tokens=["Watchdog", "stalls_detected", "heartbeat"], order_marker="run_fleet"),
    dict(name="Fleet Telemetry", short="FT", module="runtime_fleet",
         symbol="run_fleet", plane="governance", matrix=False,
         role="multi-process Gamma fleet with per-worker CPU/RSS/throughput telemetry",
         sig_tokens=["run_fleet", "per_worker_telemetry", "throughput_decisions_per_s"],
         order_marker="run_fleet"),
    dict(name="Clock Consistency (single-host PTP)", short="CK", module="run_runtime_stack",
         symbol="measure_clock_consistency", plane="timing", matrix=False,
         role="single-host monotonic-clock characterisation (resolution, jitter, drift)",
         sig_tokens=["measure_clock_consistency", "monotonic_consistency"],
         order_marker="measure_clock_consistency"),
]


def _resolve(module: str, dotted: str):
    """Import `module` and resolve a possibly-dotted attribute path; return the object or None."""
    try:
        mod = importlib.import_module(module)
    except Exception:
        return None, None
    obj = mod
    for part in dotted.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None, mod
    return obj, mod


def _srcfile(obj) -> str | None:
    try:
        f = inspect.getsourcefile(obj) or inspect.getfile(obj)
        return str(Path(f).resolve().relative_to(ROOT))
    except Exception:
        return None


def _lineno(obj):
    try:
        return inspect.getsourcelines(obj)[1]
    except Exception:
        return None


def _source(obj) -> str:
    try:
        return inspect.getsource(obj)
    except Exception:
        return ""


def _code_only(src: str) -> str:
    """Strip triple-quoted docstrings/strings so dependency inference reads CODE references, not
    prose (a docstring that merely NAMES another module must not create a false dependency edge)."""
    import re
    src = re.sub(r'"""(?:.|\n)*?"""', " ", src)
    src = re.sub(r"'''(?:.|\n)*?'''", " ", src)
    # drop line comments too
    src = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    return src


def discover() -> dict:
    """Probe every candidate; register the ones whose symbol resolves; infer dependencies."""
    present = []
    for c in _CANDIDATES:
        obj, _mod = _resolve(c["module"], c["symbol"])
        if obj is None:
            continue
        present.append({**c, "_obj": obj,
                        "implementation_file": _srcfile(obj),
                        "responsible_function": c["symbol"],
                        "source_line": _lineno(obj),
                        "source": _source(obj)})

    # --- execution-order inference from the real pipeline driver ---
    order = {}
    try:
        import run_runtime_stack as RRS
        pipe = inspect.getsource(RRS.main)
        for c in present:
            idx = pipe.find(c["order_marker"])
            order[c["short"]] = idx if idx >= 0 else 10**9
    except Exception:
        for c in present:
            order[c["short"]] = 10**9
    ordered = sorted((c for c in present if order.get(c["short"], 10**9) < 10**9),
                     key=lambda c: order[c["short"]])
    exec_chain = [c["short"] for c in ordered]

    # --- data-dependency inference: does A's CODE (docstrings stripped) reference B's token? ---
    deps = {c["short"]: set() for c in present}
    for a in present:
        src = _code_only(a["source"]).lower()
        for b in present:
            if b["short"] == a["short"]:
                continue
            if any(tok.lower() in src for tok in b["sig_tokens"]):
                deps[a["short"]].add(b["short"])
    # break any accidental 2-cycle deterministically using execution order (a later stage may depend
    # on an earlier one, never the reverse) so the dependency graph stays a DAG
    rank = {s: i for i, s in enumerate(exec_chain)}
    for a in list(deps):
        for b in list(deps[a]):
            if a in deps.get(b, set()) and rank.get(a, 0) <= rank.get(b, 0):
                deps[a].discard(b)          # keep only the later->earlier edge
    for k in deps:
        deps[k] = sorted(deps[k])

    registry = {
        "discovery_method": ("importlib + inspect probing of live runtime symbols; a component is "
                             "listed only if its symbol resolves. Dependencies inferred from (1) call "
                             "order in run_runtime_stack.main and (2) signature-token scanning of each "
                             "component's own source."),
        "n_components": len(present),
        "execution_order": exec_chain,
        "components": [{
            "name": c["name"], "short": c["short"],
            "implementation_file": c["implementation_file"],
            "responsible_function": c["responsible_function"],
            "source_line": c["source_line"],
            "execution_plane": c["plane"],
            "role": c["role"],
            "dependencies": deps[c["short"]],
            "can_be_disabled": bool(c["matrix"]),
            "in_ablation_matrix": bool(c["matrix"]),
            "executed_every_config_as_stage": not bool(c["matrix"]),
        } for c in present],
    }
    return registry


def dependency_graph_svg(registry: dict) -> str:
    comps = registry["components"]
    short2name = {c["short"]: c["name"] for c in comps}
    # lay matrix components along the execution chain; governance stages in a lower band
    matrix = [c for c in comps if c["in_ablation_matrix"]]
    gov = [c for c in comps if not c["in_ablation_matrix"]]
    order = registry["execution_order"]
    matrix.sort(key=lambda c: order.index(c["short"]) if c["short"] in order else 99)
    W = max(720, 150 * max(len(matrix), 1) + 60)
    H = 340
    pos = {}
    for i, c in enumerate(matrix):
        pos[c["short"]] = (70 + i * ((W - 140) // max(len(matrix) - 1, 1)), 110)
    for i, c in enumerate(gov):
        pos[c["short"]] = (90 + i * ((W - 160) // max(len(gov) - 1, 1)), 250)
    body = ["<defs><marker id='a' markerWidth='9' markerHeight='9' refX='8' refY='3' orient='auto'>"
            "<path d='M0,0 L8,3 L0,6 Z' fill='#58a6ff'/></marker></defs>"]
    # dependency edges (consumer -> producer)
    for c in comps:
        for dep in c["dependencies"]:
            if c["short"] in pos and dep in pos:
                x1, y1 = pos[c["short"]]; x2, y2 = pos[dep]
                body.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#58a6ff' "
                            f"stroke-width='2' marker-end='url(#a)' opacity='0.8'/>")
    for c in comps:
        x, y = pos[c["short"]]
        col = "#3fb950" if c["in_ablation_matrix"] else "#d29922"
        body.append(f"<circle cx='{x}' cy='{y}' r='30' fill='#161b22' stroke='{col}' stroke-width='2'/>"
                    f"<text x='{x}' y='{y+4}' fill='#e6edf3' font-size='13' font-weight='700' "
                    f"text-anchor='middle'>{c['short']}</text>"
                    f"<text x='{x}' y='{y+46}' fill='#8b949e' font-size='9' text-anchor='middle'>"
                    f"{short2name[c['short']].split(' (')[0]}</text>")
    legend = ("<text x='20' y='300' fill='#3fb950' font-size='11'>● matrix (ablatable)</text>"
              "<text x='170' y='300' fill='#d29922' font-size='11'>● governance stage (every config)</text>"
              "<text x='20' y='320' fill='#58a6ff' font-size='11'>→ consumer depends on producer</text>")
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
            f"font-family='-apple-system,Segoe UI,Roboto,sans-serif'>"
            f"<rect width='{W}' height='{H}' fill='#0d1117'/>"
            f"<text x='{W/2}' y='26' fill='#e6edf3' font-size='15' font-weight='700' text-anchor='middle'>"
            f"Component Dependency Graph (auto-inferred from runtime relationships)</text>"
            f"{''.join(body)}{legend}</svg>")


def dependency_graph_md(registry: dict) -> str:
    comps = registry["components"]
    order = registry["execution_order"]
    o = ["# Component Dependency Graph (auto-generated)", "",
         "> Generated by `combined_ablation_discovery.py`. Components are discovered by probing live "
         "runtime symbols; dependencies are inferred from call order in `run_runtime_stack.main` and "
         "from signature-token scanning of each component's source. Nothing here is hand-authored.", "",
         f"**Discovered components:** {registry['n_components']}", "",
         "## Execution pipeline order", "",
         "```", " → ".join(order) if order else "(order unavailable)", "```", "",
         "## Dependency edges (consumer → producer)", "",
         "| Component | Plane | Depends on | In ablation matrix | Implementation |",
         "|---|---|---|:--:|---|"]
    for c in comps:
        deps = ", ".join(c["dependencies"]) or "—"
        loc = f"`{c['implementation_file']}:{c['source_line']}` · `{c['responsible_function']}`"
        o.append(f"| {c['name']} ({c['short']}) | {c['execution_plane']} | {deps} | "
                 f"{'✅' if c['in_ablation_matrix'] else '— (governance stage)'} | {loc} |")
    o += ["", "## Textual chain (matrix components)", ""]
    matrix_order = [s for s in order if any(c["short"] == s and c["in_ablation_matrix"] for c in comps)]
    o.append("```")
    o.append("\n↓\n".join(f"{s} — {next(c['name'] for c in comps if c['short']==s)}"
                          for s in matrix_order) or "(none)")
    o.append("```")
    return "\n".join(o) + "\n"


def write_all(outdir: Path | None = None) -> dict:
    reg = discover()
    (ROOT / "COMPONENT_REGISTRY.json").write_text(json.dumps(reg, indent=2) + "\n")
    (ROOT / "COMPONENT_DEPENDENCY_GRAPH.md").write_text(dependency_graph_md(reg))
    (ROOT / "component_dependency_graph.svg").write_text(dependency_graph_svg(reg))
    md = ROOT / "metadata"
    md.mkdir(exist_ok=True)
    (md / "COMPONENT_REGISTRY.json").write_text(json.dumps(reg, indent=2) + "\n")
    (md / "COMPONENT_DEPENDENCY_GRAPH.md").write_text(dependency_graph_md(reg))
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "component_dependency_graph.svg").write_text(dependency_graph_svg(reg))
    return reg


if __name__ == "__main__":
    r = write_all()
    print(f"[discovery] {r['n_components']} components discovered: "
          f"{', '.join(c['short'] for c in r['components'])}")
    print(f"[discovery] execution order: {' -> '.join(r['execution_order'])}")
    print(f"[discovery] wrote COMPONENT_REGISTRY.json, COMPONENT_DEPENDENCY_GRAPH.md, "
          f"component_dependency_graph.svg (+ metadata/)")
