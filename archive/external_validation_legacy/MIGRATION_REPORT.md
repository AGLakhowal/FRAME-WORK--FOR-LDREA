# AgentDojo external validation migration report

## Summary

This change adds an independent AgentDojo-style validation harness to the existing Gamma/L-DREA benchmark suite without modifying the native LAB or AgentDojo benchmark logic. The new layer treats AgentDojo-style actions as Externally Effective Actions (EEAs) and routes them through a conservative Gamma-style authorization gate before any action is considered executable.

## What changed

- Added an external validation package under [external_validation](external_validation).
- Added an adapter that maps tool invocations into Gamma/L-DREA-style EEA records.
- Added a runtime bridge that acts as the interception point for candidate actions.
- Added a report generator that emits:
  - JSON report
  - JSONL manifest
  - replay manifest
  - HTML dashboard
- Updated [run_all.py](run_all.py) to invoke the new validation layer as part of the existing suite.
- Updated [gamma_report_page.py](gamma_report_page.py) to include an “Independent validation — AgentDojo” section in the unified dashboard.

## Files added

- [external_validation/__init__.py](external_validation/__init__.py)
- [external_validation/AGENTDOJO_DESIGN.md](external_validation/AGENTDOJO_DESIGN.md)
- [external_validation/agentdojo_adapter.py](external_validation/agentdojo_adapter.py)
- [external_validation/agentdojo_runtime_bridge.py](external_validation/agentdojo_runtime_bridge.py)
- [external_validation/agentdojo_report.py](external_validation/agentdojo_report.py)
- [external_validation/agentdojo_dashboard.py](external_validation/agentdojo_dashboard.py)
- [external_validation/MIGRATION_REPORT.md](external_validation/MIGRATION_REPORT.md)
- [tests/test_agentdojo_validation.py](tests/test_agentdojo_validation.py)

## Reproduction

Run:

```bash
/usr/bin/python3 run_all.py --reuse --no-open
```

Or generate only the AgentDojo artifacts:

```bash
/usr/bin/python3 - <<'PY'
from pathlib import Path
from external_validation.agentdojo_report import generate_report
from external_validation.agentdojo_dashboard import render
out = Path('external_validation')
report = generate_report(output_dir=out)
render(report, out / 'agentdojo_dashboard.html')
print(report['summary'])
PY
```

## Assumptions

- This workspace does not contain an AgentDojo source tree, so the integration is implemented as a self-contained harness that models the execution boundary rather than modifying AgentDojo internals.
- The new layer is intentionally conservative and fail-closed for sensitive actions.
- The output artifacts are deterministic given the same scenario list and environment.

## Paper sections that can now be updated

Potential updates for the IEEE resubmission include:

- Experimental setup: independent external validation environment
- Runtime governance under an external benchmark harness
- Replayability and evidence emission for externally effective actions
- Threat model and scope discussion for cross-benchmark validation
- Comparison of LAB v1.0 vs AgentDojo validation results
