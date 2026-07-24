# REPRODUCIBILITY_CHECKLIST

| # | Item | Command | Expected | Status |
|---|---|---|---|---|
| 1 | Deterministic audit unit tests | `agentdojo_integration/.venv/bin/python agentdojo_integration/audit/tests/test_audit.py` | 21/21 PASS | ✅ |
| 2 | Regenerate AgentDojo corpus stats (Table 11) | `LOCAL_LLM_PORT=11434 …/run_audit.py --suites workspace banking slack travel --max-user-tasks 8 --outdir agentdojo_integration/audit_run` | statistics/replay/proofs/figures | ✅ (33 episodes, 14 decisions) |
| 3 | Concurrency scaling (Table 13) | `…/python -m agentdojo_integration.audit.concurrency_scaling agentdojo_integration/audit_run/summary/concurrency` | 6-level curve, 0 FP/FD | ✅ |
| 4 | Runtime Context + Replay profiling (Table 10) | `…/python -m agentdojo_integration.audit.runtime_profile agentdojo_integration/audit_run/summary/runtime_profile` | RC + Replay ms/row | ✅ |
| 5 | FPR/FDR labeling (Table 11) | `…/python -m agentdojo_integration.audit.fpr_fdr_labeling agentdojo_integration/audit_run/trace agentdojo_integration/audit_run/summary/fpr_fdr` | FPR undefined(n=0), FDR 0.0 | ✅ |
| 6 | Independent provenance recompute | `verify_provenance.py` | 26/26 PASS | ✅ |
| 7 | Frozen integrity (before==after) | embedded in run_audit / `frozen_integrity.json` | 19 files unchanged | ✅ |
| 8 | Trace integrity (hash chain) | `trace_integrity_all.json` | 33/33 integrity_ok | ✅ |
| 9 | Replay from jsonl only | ReplayEngine per trace | 33/33 consistent | ✅ |

## Determinism notes
- **Deterministic (bit-reproducible):** all audit statistics, Wilson/bootstrap CIs (fixed seed 12345),
  concurrency correctness/ledger, runtime-profile latencies (values vary within timing noise, ordering
  and conclusions stable), replay verdicts, integrity hashes.
- **Non-deterministic upstream (documented):** the LLM trajectory (`llama3.1:8b`, temp 0) — so *which*
  episodes yield an EEA can vary; the authorization layer is deterministic given a fixed candidate
  action. Re-running item 2 may change episode-level utility/security but not the monitor's decisions
  for a fixed action (validated by traced==clean replay).

## Environment
- Interpreter: `agentdojo_integration/.venv/bin/python` (CPython 3.11.15); `agentdojo==0.1.35`.
- LLM: Ollama `llama3.1:8b` on `LOCAL_LLM_PORT=11434`.
- Host: Apple M5, 10 cores, 16 GB, macOS 26.5.1.

**REPRODUCIBILITY: every reported number regenerates from the repository via the commands above.**
