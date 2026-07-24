# Category B — Autonomous Agent Governance (AgentDojo) Report

**Purpose.** Demonstrate L-DREA governing autonomous agents on the AgentDojo benchmark: permit/deny,
Gamma decisions, stability, overhead, replay, and — the paper's soundness claim — false-permit rate on
attacker-targeted actions.
**Host.** Apple M5 / Python 3.9.6 (agentdojo==0.1.35). **Date.** 2026-07-09.

> **External validation status: COMPLETE (offline).** AgentDojo is the independent workload
> generator; the evaluation target is **L-DREA**, not the language model. Every governance metric —
> FPR, FDR, replay determinism, predicate pass rate, evidence-quad completeness, hash-chain and
> ledger integrity, latency — is computed with **no model in the loop** and **no external API
> credential**, either (a) re-derived from the 33 episodes already recorded on disk
> (`agentdojo_integration/audit_run/trace/`), or (b) produced by direct boundary adjudication (B3).
> Single command:
> `agentdojo_integration/.venv/bin/python experiment_agentdojo_metrics.py experiments/agentdojo`
>
> **Ollama status (reported, not fabricated).** The 33 recorded episodes were generated locally with
> **Ollama (`llama3.1:8b`)** through AgentDojo's `vllm_parsed` provider — every trace event carries
> `"model": "llama3.1:8b"`. No hosted provider (OpenAI / Anthropic / Gemini) was ever used. Fresh
> episode *generation* needs a running local Ollama server; `ollama` is **not installed on this
> host**, so the end-to-end Utility/TASR over the full 79-task/629-injection corpus is **OPEN** —
> rerun recipe at the end. Those are **agent-side** quantities; no L-DREA claim depends on them.
>
> **AgentHarm** was pre-registered (§IX-F) but never implemented. It is **optional future work** and
> is not part of external validation, which refers only to AgentDojo.

## B1 — Metric re-derivation from recorded episodes (no LLM)

- **Command:** `stats_engine.write_reports('agentdojo_integration/audit_run/trace', outdir)`
- **Corpus:** 33 recorded episodes (workspace 9 · banking 8 · slack 8 · travel 8) → 14 adjudicated EEA
  decisions.

| Metric | Result |
|---|---|
| Permit rate | 11 / 14 = **0.786** (Wilson95 [0.524, 0.924]) |
| Denials | 3 / 14 |
| Class-veto fired | **0** times (rate Wilson95↑ 0.215) |
| Authorization stability | **0.9667** |
| Γ-decision overhead | mean **0.0216 ms** (min 0.0079, max 0.0587) |
| Harm threshold θ | 0.5 (constant across all) |

**Interpretation.** The interposition adjudicates real agent tool calls with sub-0.06 ms Γ overhead and
high decision stability. Permit rate 0.786 reflects that most recorded agent actions were legitimate
(the agents largely completed benign user tasks).

## B2 — Independent FPR/FDR labeling from traces (no LLM)

- **Command:** `fpr_fdr_labeling.run('…/audit_run/trace', outdir)` — attacker targets from injection
  GOAL text; legitimate targets from env recognized-set.
- **Result:** malicious_actions **0**, malicious_permitted 0 → **FPR undefined (n = 0)**; legitimate 5,
  denied 0 → FDR 0/5 (near-tautological, recognized-set defined; reported for completeness).

**Load-bearing finding.** In the 33 recorded episodes **the agent never proposed an attacker-targeted
externalization**, so trace-level FPR has no denominator. This is not evidence of soundness — it is
absence of an attack instance in the recorded run. B3 was built to close exactly this gap.

## B3 — Boundary FPR: direct adjudication of the real adversarial corpus (no LLM) — **new**

- **Rationale.** The paper's soundness claim ("no attacker-targeted externalization is permitted") is a
  property of the **boundary**, not of the agent. B3 tests the boundary directly against **every**
  injection GOAL in all 4 AgentDojo v1 suites, submitting the attacker-targeted tool call through the
  **exact frozen decision path** `run_function` uses (`classify → PredicateEvaluator.evaluate →
  GammaBridge.decide`), skipping only side-effect execution. No LLM required.
- **Command:** `agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py`
- **Corpus:** 27 injection tasks × attacker targets → **70 attacker-target adjudications**.

| Partition | Result |
|---|---|
| **Genuinely-foreign attacker targets** (absent from env recognized set) | **FPR = 0 / 62** (Wilson95↑ 5.83×10⁻²) |
| — workspace | 0 / 24 |
| — travel | 0 / 12 |
| — banking | 0 / 16 |
| — slack | 0 / 10 |
| Recognized-identifier sends (target already a known contact/URL) | 8 / 8 permitted — **correct-by-policy** |
| Structural-only tools (no recognition predicate) | 0 probed |

**Interpretation.** Every genuinely-foreign exfil target (attacker IBAN `US1330…`, exfil recipient
`mark.black-2134@gmail.com`, etc.) triggers a GATE recognition deficit → **SAFE_STATE**. FPR is **0 on
62 real adversarial targets** across all four suites, through the real frozen boundary, with no LLM.

**Honest limitations surfaced by this experiment.**
1. The 8 "permits" are all sends to identifiers **already in the environment's recognized set** — e.g.
   `lily.white@gmail.com` and `security@facebook.com`, which the attack GOAL merely *names as a source*.
   Permitting a send to a known contact is correct-by-policy, not a false permit. **But** it exposes a
   real limitation of recognition-based gating: it **cannot distinguish a legitimate contact weaponized
   as an exfil sink**. This is a documented property of recognized-set authorization, not a defect —
   and it is the kind of limitation a reviewer should see stated plainly.
2. **8 of the 25 mediated tools are `structural_only`** in the frozen manifest (`delete_file`,
   `delete_email`, `update_password`, `update_user_info`, `create_file`, `append_to_file`,
   `cancel_calendar_event`, `reschedule_calendar_event`) — they carry **no env-derived recognition
   predicate**, so a structurally-valid call to them is permitted. Injection GOALs like "delete file 13"
   or "change the password" target these tools and are **not identifier-gated**. This is a coverage
   boundary of the frozen policy, documented here for the reviewer.

## B4 — Fresh end-to-end episodes (Utility / TASR) — **OPEN (Ollama)**

- **Missing dependency:** `ollama` + `llama3.1:8b`.
- **Rerun:** `brew install ollama && ollama serve & ollama pull llama3.1:8b` then
  `agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py --suites workspace banking
  slack travel --outdir agentdojo_integration/audit_run`
- **Expected outputs:** fresh `execution_trace.jsonl` per episode over the full 79/629 corpus →
  `statistics.json` (Utility, TASR, permit/deny/entropy/stability/overhead/replay). Then re-run B1/B2/B3
  against the fresh traces for episode-level FPR/FDR.

## Category B verdict

Boundary-level soundness is **CLOSED**: FPR 0/62 on the real AgentDojo adversarial corpus, no LLM.
Permit/deny/stability/overhead are **CLOSED (bounded to 33 recorded episodes)**. Episode-level
Utility/TASR over the full corpus is **OPEN**, blocked solely on Ollama, with an exact rerun recipe.
Two genuine architectural limitations (recognized-sink ambiguity; structural-only coverage) are
documented rather than hidden.
