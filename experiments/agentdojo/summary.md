# Experiment 7 — AgentDojo Runtime Governance

Status: **EXECUTED** · 10.33s

## Boundary FPR (direct adjudication, NO LLM)
- Adversarial actions adjudicated: 70
- **FPR on genuinely-foreign attacker targets: 0/62 = 0.0** (Wilson95↑ 5.834e-02)
- Recognized-identifier sends (correct-by-policy): 8/8

## Re-derived from 33 recorded episodes (no LLM)
- Episodes: 33 · adjudicated decisions: 14
- Permit rate: 0.786 (Wilson95 [0.524, 0.924])
- Authorization stability: 0.9667

## E7 metrics (offline — no LLM, no API credential)
- Scenarios: 33 · tool calls: 42 · authorized/denied: 11/3
- False permit rate (soundness): 0.0 (0/62)
- False denial rate: 0.0
- Replay determinism: 1.0
- Evidence quad completeness: 1.0
- Hash chain integrity: 1.0 (33/33)
- Ledger integrity: 1.0 (33/33)
- Runtime risk detection: 1.0
- Failures: 0 · warnings: 0

## Optional live arm — agent-side Utility / TASR
- Status: **NOT_RUN** (OPTIONAL — agent-side metrics only)
- Missing dependency: `local Ollama server` (optional; no L-DREA metric depends on it)
- Rerun: `ollama serve & ollama pull llama3.1:8b && export LOCAL_LLM_PORT=11434; then agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run`