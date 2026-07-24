"""Phase F --- runtime visualization graphs (Mermaid + Graphviz DOT + interactive HTML).

Emits, from real recorded data:
  * benchmark_flow.mmd        Mermaid flowchart: LLM → ToolCall → Gamma → Predicates → Decision → Exec
  * authorization_graph.dot   Graphviz: tool → policy-class → decision, weighted by frequency
  * tool_graph.dot            Graphviz: per-tool permit/deny counts
  * decision_sankey.mmd       Mermaid: PERMIT/SAFE_STATE flow with counts
  * explorer.html             interactive HTML (decision-tree / predicate / timeline explorers)
No external tool is required to emit these text/HTML artifacts (rendering is downstream).
"""
from __future__ import annotations

import json
from pathlib import Path

from ._util import write_text
from . import stats_engine


def _dot_escape(s: str) -> str:
    return str(s).replace('"', "'")


def authorization_graph_dot(stats: dict) -> str:
    L = ["digraph authorization {", '  rankdir=LR; node [style=filled,fontname="sans-serif"];']
    L.append('  PERMIT [fillcolor="#cdebc5"]; SAFE_STATE [fillcolor="#f2c9c0"];')
    for cls, n in stats["policy_utilization"].items():
        L.append(f'  "{_dot_escape(cls)}" [shape=box,fillcolor="#dbe6f2",label="{_dot_escape(cls)}\\n(n={n})"];')
    for tool, v in stats["tool_frequency"].items():
        L.append(f'  "{_dot_escape(tool)}" [fillcolor="#f7f2cf"];')
        if v["permit"]:
            L.append(f'  "{_dot_escape(tool)}" -> PERMIT [label="{v["permit"]}"];')
        if v["deny"]:
            L.append(f'  "{_dot_escape(tool)}" -> SAFE_STATE [label="{v["deny"]}"];')
    L.append("}")
    return "\n".join(L)


def tool_graph_dot(stats: dict) -> str:
    L = ["digraph tools {", '  node [shape=record,style=filled,fillcolor="#eef",fontname="sans-serif"];']
    for tool, v in sorted(stats["tool_frequency"].items(), key=lambda kv: -kv[1]["n"]):
        L.append(f'  "{_dot_escape(tool)}" [label="{{{_dot_escape(tool)}|permit={v["permit"]} '
                 f'deny={v["deny"]} n={v["n"]}}}"];')
    L.append("}")
    return "\n".join(L)


def benchmark_flow_mmd(stats: dict) -> str:
    L = ["flowchart TD", "  U[User task] --> L[LLM (Ollama)]",
         "  L -->|tool_calls| T[ToolsExecutor]", "  T --> G[GammaGovernedRuntime]",
         "  G --> P[PredicateEvaluator]", "  P --> D[DecisionEngine Γ,Π]",
         f"  D -->|Π=1| PERMIT[PERMIT n={stats['n_authorizations_permit']}]",
         f"  D -->|Π=0| DENY[SAFE_STATE n={stats['n_denials']}]",
         "  PERMIT --> F[Tool executes → Observation]", "  DENY --> B[Blocked → SAFE_STATE]",
         "  F --> L", "  B --> L"]
    return "\n".join(L)


def decision_sankey_mmd(stats: dict) -> str:
    # Mermaid sankey-beta with real counts (tool -> decision)
    L = ["sankey-beta", ""]
    for tool, v in stats["tool_frequency"].items():
        if v["permit"]:
            L.append(f"{tool},PERMIT,{v['permit']}")
        if v["deny"]:
            L.append(f"{tool},SAFE_STATE,{v['deny']}")
    return "\n".join(L)


def explorer_html(stats: dict, root: str) -> str:
    decisions = stats_engine.collect(root)["decisions"]
    predicates = stats_engine.collect(root)["predicates"]
    data = {"decisions": decisions, "predicates": predicates,
            "policy_utilization": stats["policy_utilization"],
            "tool_frequency": stats["tool_frequency"]}
    payload = json.dumps(data, default=str)
    return ("<!doctype html><meta charset='utf-8'><title>L-DREA Runtime Explorer</title>"
            "<style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:4px 8px;font-size:13px}"
            "button{margin:4px;padding:6px 10px}.panel{margin-top:1rem}</style>"
            "<h1>Runtime Explorer</h1>"
            "<div><button onclick=\"show('decisions')\">Decision-tree explorer</button>"
            "<button onclick=\"show('predicates')\">Predicate explorer</button>"
            "<button onclick=\"show('timeline')\">Timeline explorer</button></div>"
            "<div id='panel' class='panel'></div>"
            f"<script>const D={payload};"
            "function tbl(rows,cols){let h='<table><tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'</tr>';"
            "for(const r of rows){h+='<tr>'+cols.map(c=>'<td>'+(r[c]??'')+'</td>').join('')+'</tr>';}return h+'</table>';}"
            "function show(k){const p=document.getElementById('panel');"
            "if(k==='decisions')p.innerHTML=tbl(D.decisions,['episode','step','tool','class','gamma_global','gamma_class','pi','decision','blocking_predicate','executed']);"
            "else if(k==='predicates')p.innerHTML=tbl(D.predicates,['episode','step','predicate','deficit','status']);"
            "else p.innerHTML=tbl(D.decisions,['episode','step','tool','decision']);}"
            "show('decisions');</script>")


def generate(root: str | Path, outdir: str | Path, stats: dict | None = None) -> dict:
    out = Path(outdir); (out / "graphs").mkdir(parents=True, exist_ok=True)
    stats = stats or stats_engine.analyze(root)
    write_text(out / "graphs" / "authorization_graph.dot", authorization_graph_dot(stats))
    write_text(out / "graphs" / "tool_graph.dot", tool_graph_dot(stats))
    write_text(out / "graphs" / "benchmark_flow.mmd", benchmark_flow_mmd(stats))
    write_text(out / "graphs" / "decision_sankey.mmd", decision_sankey_mmd(stats))
    write_text(out / "explorer.html", explorer_html(stats, str(root)))
    return {"graphs": ["authorization_graph.dot", "tool_graph.dot", "benchmark_flow.mmd",
                       "decision_sankey.mmd"], "explorer": str(out / "explorer.html")}
