import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_validation.agentdojo_adapter import build_eea, evaluate_action


def test_build_eea_and_evaluate_action() -> None:
    action = {
        "tool": "browser.purchase",
        "target": "https://store.test/checkout",
        "amount": 29.99,
        "user": "alice",
        "metadata": {"risk": "high"},
    }
    eea = build_eea(action)
    assert eea["action_type"] == "financial"
    assert eea["decision"] == "SAFE_STATE"
    decision = evaluate_action(action)
    assert decision["decision"] == "SAFE_STATE"
    assert decision["policy"] == "gamma_g0"


def test_report_generation_outputs_files(tmp_path: Path) -> None:
    from external_validation.agentdojo_report import generate_report

    out_dir = tmp_path
    report = generate_report(output_dir=out_dir, scenarios=[
        {"tool": "file.delete", "target": "/tmp/example.txt", "user": "alice"},
        {"tool": "browser.purchase", "target": "https://store.test/checkout", "amount": 10.0, "user": "alice"},
    ])
    assert report["summary"]["tasks_executed"] == 2
    assert (out_dir / "agentdojo_report.json").exists()
    assert (out_dir / "agentdojo_manifest.jsonl").exists()
    assert (out_dir / "agentdojo_replay_manifest.json").exists()
