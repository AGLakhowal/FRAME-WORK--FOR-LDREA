# LIMITATIONS AND NEGATIVE RESULTS (auto-generated)

Transparency over persuasion: every limitation, negative result, blocked experiment, and unclaimed capability, derived from the executed run index and claim statuses.

## Negative results (disclosed, not hidden)
- **C9** — Throughput does NOT scale with threads on the pure-Python decision path (GIL-bound); this is reported as a limitation, not a scaling claim. (status: Supported (negative result)).

## Blocked / dependency-limited experiments
- (none — all experiments executed, E7 included; see the optional live-arm note below)
- **E7 optional live arm (agent-side Utility/TASR)** — NOT_RUN. Missing: `local Ollama server` (a local Ollama server; no hosted provider is used). E7's own status is `EXECUTED` — every runtime-governance metric is measured offline. Rerun: `ollama serve & ollama pull llama3.1:8b && export LOCAL_LLM_PORT=11434; then agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking slack travel --outdir agentdojo_integration/audit_run`

## Partially supported claims
- **C12** — AgentDojo integration preserves authorization correctness: 0 false permits on genuinely-foreign attacker targets at the boundary (no LLM). — Boundary FPR is measured offline (no LLM, no API credential) and E7 is EXECUTED. The residual caveat is the recognition-set coverage boundary: structural-only mediated tools have n=0 adjudicated actions, so soundness there is undefined rather than demonstrated. Two recognition-set limitations documented.

## Explicitly not claimed (out of scope)
- **C14** — Hardware (Tier-H FPGA/SGX/HSM) deployment. — Under the Tier-S reference framing hardware deployment is explicitly out of scope; no hardware claim is made and none is evaluated.

## Known limitations (from executed evidence)
- Throughput is GIL-bound and does not scale with threads (E4/C9).
- The ULB should-deny denominator (492) gives a wide FPR confidence bound (E1).
- Recognition-set gating cannot flag a known contact weaponized as an exfil sink, and 8 mediated tools are structural-only (E7).
- Ablation and robustness use deterministic constructed workloads (E5/E8), not arbitrary field distributions.

## Future work
- Optionally run E7's live arm (start a local Ollama server) to add agent-side Utility/TASR. No runtime-governance claim depends on it.
- AgentHarm (pre-registered §IX-F, never implemented) as an optional second external replication benchmark.
- Multi-process / native substrate to convert safety-under-load into throughput scaling.
- Extend formal mechanization (TLC) to Invariants 2-6 and a larger bounded config.
- A second externally-authored adversarial corpus to strengthen external validity.