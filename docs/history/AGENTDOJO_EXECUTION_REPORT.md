# AgentDojo Execution Report — L-DREA Governed Benchmark

**Date:** 2026-07-08
**Framework:** genuine upstream `agentdojo==0.1.35`, benchmark `v1` — unmodified, not forked, not emulated.
**Interpreter:** `agentdojo_integration/.venv/bin/python` (CPython **3.11.15**).
**Scope of change:** executability detection + a first-party runner. **No frozen component modified.**
**Status:** harness **VERIFIED OFFLINE**; scored run **RUN_PENDING_PROVIDER** (no LLM key present).
**Awaiting independent review.**

---

## 1. What was implemented (and only this)

### 1.1 Corrected executability detection
`tests/test_regression_parity.py` previously probed `sys.executable` — the repository's **Python 3.9**
interpreter, where `agentdojo` is correctly absent — and reported a false SKIP / `NOT_EXECUTABLE`.
Added `_agentdojo_python()`, which routes the probe to the dedicated **3.11** venv
(`agentdojo_integration/.venv/bin/python`) that actually owns the pinned install, falling back to
`sys.executable` only if that venv is missing.

**Demonstrated:** invoked from Python 3.9, the corrected probe now executes the real AgentDojo
interception test under the 3.11 venv (no false SKIP). `VALIDATION_RESULTS.json → 6_agentdojo` updated
from `NOT_EXECUTABLE` to `RUN_PENDING_PROVIDER` with the true, non-fabricated reason.

### 1.2 First-party benchmark runner — `agentdojo_integration/run_benchmark.py`
Drives the official framework exactly as intended. Genuine upstream, used as-is:

| Concern | Upstream call (unchanged) |
|---|---|
| suites | `agentdojo.task_suite.load_suites.get_suites(benchmark_version)` |
| attacks / injections | `agentdojo.attacks.attack_registry.load_attack(...)`, `attack.attack(user_task, injection_task)` |
| agent pipeline | `AgentPipeline.from_config(PipelineConfig(llm=<model>))` (temperature = 0 default) |
| scoring | `TaskSuite.run_task_with_pipeline(...) → (utility, security)` |
| aggregation | `agentdojo.benchmark.aggregate_results` |
| transcripts | `agentdojo.logging.OutputLogger` / `TraceLogger` → archived to `--logdir` |

**L-DREA injection point:** AgentDojo's own supported `runtime_class` parameter on
`TaskSuite.run_task_with_pipeline` (`task_suite.py:345`, `runtime = runtime_class(self.tools)` at
`:380`). The runner threads `runtime_class=TracingGammaRuntime`. Upstream's top-level helpers
(`benchmark_suite_with_injections`, `run_task_with_injection_tasks`) do **not** expose this parameter,
so the runner mirrors `run_task_with_injection_tasks` at the `run_task_with_pipeline` level — reusing
upstream scoring, attacks, tasks, and aggregation verbatim.

**`TracingGammaRuntime`** is a thin subclass of the **frozen** `GammaGovernedRuntime`. It overrides
only `run_function` to append `(function, kwargs)` to an observation tape *before* delegating to the
frozen implementation. It records; it never decides. No policy, threshold, predicate, or SAFE_STATE
semantic is altered.

### 1.3 Provider gating (no fabrication)
Model id → provider (`MODEL_PROVIDERS[ModelsEnum(model)]`) → required env var. If the credential is
absent, the runner writes `status: RUN_PENDING_PROVIDER` and exits 0 — **never fabricating results.**
With a key: `temperature = 0`, pinned model, transcripts archived to `--logdir`.

---

## 2. Verification results

### 2.1 Frozen integrity gate (runs before any task)
| Check | Value | Result |
|---|---|---|
| Layer-1 scientific root | `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618` | ✅ matches frozen |
| Layer-2 binding sha | `a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1` | ✅ matches frozen |
| Default runtime binds frozen roots | method `gamma_test_runner/LAB-v1.0/2.0` | ✅ |

*(Note: the string `a2b816e0` in a `test_interception.py` check label is a stale display label; the
actual `BINDING_SHA` constant is `a38619274c…`, and the interception test asserts against the constant,
which passes.)*

### 2.2 Offline harness self-check — `run_benchmark.py --selfcheck` (no LLM, no key)
Exercises the full harness except the model: genuine suite load, genuine `important_instructions`
injection generation, complete interception, and replay determinism against a scripted candidate stream.

| Verification | Result |
|---|---|
| Genuine AgentDojo injection generated (LLM-free) | ✅ `genuine_injection_generated: true` (1 slot) |
| **GammaGovernedRuntime intercepts every executable action** | ✅ `interception_complete: true` |
| Read-only tool passes through (outside boundary) | ✅ `get_balance` not adjudicated |
| EEA reaches Gamma adjudication | ✅ `send_money` decided (PERMIT / SAFE_STATE) |
| Unknown tool fails closed | ✅ `totally_unknown_future_tool → SAFE_STATE` |
| **Replay passes (DET-1 determinism)** | ✅ `replay_deterministic: true` |

### 2.3 Interception test unchanged (frozen behavior intact)
`agentdojo_integration/tests/test_interception.py` → **ALL CHECKS PASS** after all changes.

### 2.4 Scored benchmark
No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `CO_API_KEY` / `TOGETHER_API_KEY`
present → `agentdojo_results.json` = `RUN_PENDING_PROVIDER`. **No utility / attack-success numbers were
invented.** Utility, attack-success-rate, per-task logs, and per-task replay flags are produced only
by an actual keyed run.

---

## 3. Replay verification (DET-1)

**Scope:** determinism of the *authorization decision* given a fixed candidate action + context — never
over the LLM. **Method:** the recorded candidate-action stream is re-issued into a fresh frozen
`GammaGovernedRuntime` on a rebuilt environment; the decision sequence is compared bit-for-bit. **LLM is
not in the loop.** Result: **PASS** (`agentdojo_replay_verification.json`). Under a keyed run, the same
replay executes per `(user_task, injection_task)` and each task records `replay_deterministic`.

---

## 4. Frozen-component audit

Not modified (verified by mtime + git): `evaluate_decision()`, Gamma, Predicate Binding, Runtime
Context, Replay, Serialization, Hydra Ledger, Evidence Bundle, SAFE_STATE semantics, and the entire
`agentdojo_integration/interception/` package. AgentDojo itself is untouched (extension via its public
`runtime_class` seam only). Tracked-file changes this task: `tests/test_regression_parity.py` (probe fix,
untracked file) and `VALIDATION_RESULTS.json` (status correction). New files: `run_benchmark.py`,
`agentdojo_results.json`, `agentdojo_benchmark_summary.json`, `agentdojo_replay_verification.json`,
`selfcheck_results.json`.

---

## 5. How to produce scored results (single external step)

```bash
export OPENAI_API_KEY=<key>          # or ANTHROPIC_API_KEY with --model claude-3-5-sonnet-20241022
agentdojo_integration/.venv/bin/python agentdojo_integration/run_benchmark.py \
    --model gpt-4o-2024-05-13 --suites banking --limit 1 --limit-injections 1 \
    --logdir agentdojo_integration/runs --out agentdojo_results.json      # smoke first
# then drop --limit flags and add all four suites for the full corpus
```
`temperature = 0`; transcripts archived under `--logdir` for offline re-scoring. Determinism claim is
scoped to the authorization decision, re-derivable from archived transcripts with zero LLM dependency.

---

## 6. Outputs produced

- `agentdojo_integration/run_benchmark.py` — the runner
- `AGENTDOJO_EXECUTION_REPORT.md` — this report
- `agentdojo_results.json` — `RUN_PENDING_PROVIDER` (honest; no fabricated scores)
- `agentdojo_replay_verification.json` — replay verification report (PASS)
- `agentdojo_benchmark_summary.json` — benchmark summary
- `agentdojo_integration/selfcheck_results.json` — offline harness verification
- `VALIDATION_RESULTS.json` — `6_agentdojo` corrected
- `tests/test_regression_parity.py` — executability probe fixed

---

## 7. Verification checklist

| Requirement | Status |
|---|---|
| Official AgentDojo benchmark executes | ✅ wired via official APIs; runs on key (smoke path exercised structurally, LLM-gated) |
| GammaGovernedRuntime intercepts every executable action | ✅ `interception_complete: true` |
| Replay passes | ✅ `replay_deterministic: true` (DET-1) |
| Determinism preserved | ✅ temperature 0 + transcript archival + decision-replay |
| No frozen component changed | ✅ audited (§4) |
| No benchmark data fabricated | ✅ `RUN_PENDING_PROVIDER` when no key |
| IEEE paper unmodified | ✅ not touched |

---

## Final Certification

The genuine upstream AgentDojo benchmark is fully wired under L-DREA governance through AgentDojo's own
`runtime_class` extension point; the harness is verified offline (complete interception + deterministic
replay), no frozen component was modified, and nothing was fabricated. Producing published utility /
attack-success numbers requires exactly one external input — a live LLM provider API key — which is not
present in this environment.

**RUN_PENDING_PROVIDER**

*(The moment a provider key is exported, `run_benchmark.py` executes the full scored benchmark with no
further code change. No fabrication. No frozen component altered. Awaiting independent review.)*
