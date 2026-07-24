# Reproduce E7 — AgentDojo External Validation of L-DREA

AgentDojo is the independent workload generator; the evaluation target is L-DREA, not the
language model. The core arm below runs **fully offline**: no LLM, no API credential.

## Core arm — all E7 metrics (no LLM, no credential)
```bash
agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py experiments/agentdojo/boundary
agentdojo_integration/.venv/bin/python -c "import sys; sys.path.insert(0,'.'); from agentdojo_integration.audit import stats_engine as s; s.write_reports('agentdojo_integration/audit_run/trace','experiments/agentdojo')"
agentdojo_integration/.venv/bin/python experiment_agentdojo_metrics.py experiments/agentdojo
```

## Optional live arm — regenerate fresh episodes via local Ollama
Measures AGENT-side task utility / attack-success rate. No L-DREA claim depends on it.
```bash
ollama serve & ollama pull llama3.1:8b && export LOCAL_LLM_PORT=11434; then agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run
```
