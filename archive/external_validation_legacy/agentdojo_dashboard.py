#!/usr/bin/env python3
"""Generate a simple HTML dashboard for the AgentDojo validation harness."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict


def render(report: Dict[str, Any], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    summary = report.get("summary", {})
    rows = "".join(
        f"<tr><td>{html.escape(str(item['id']))}</td><td>{html.escape(str(item['scenario'].get('tool', '')))}</td><td>{html.escape(str(item['result']['decision']))}</td></tr>"
        for item in report.get("decisions", [])
    )
    html_doc = f"""<!doctype html>
<html>
  <head><meta charset='utf-8'><title>AgentDojo External Validation</title></head>
  <body>
    <h1>Independent Validation</h1>
    <p>AgentDojo provides an independent external evaluation environment for Gamma/L-DREA.</p>
    <ul>
      <li>Tasks executed: {summary.get('tasks_executed', 0)}</li>
      <li>Actions intercepted: {summary.get('actions_intercepted', 0)}</li>
      <li>PERMIT count: {summary.get('permit_count', 0)}</li>
      <li>SAFE_STATE count: {summary.get('safe_state_count', 0)}</li>
      <li>Unauthorized executions: {summary.get('unauthorized_executions', 0)}</li>
      <li>Replay verification: {summary.get('replay_verification', False)}</li>
    </ul>
    <table>
      <thead><tr><th>#</th><th>Tool</th><th>Decision</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </body>
</html>"""
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path
