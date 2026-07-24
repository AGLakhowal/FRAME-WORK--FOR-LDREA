# AgentDojo Executability — Root Cause Report & Implementation Plan

**Status of task:** Analysis only. No changes implemented. Awaiting independent review.
**Date:** 2026-07-08
**Scope guard:** No frozen runtime component was touched. `evaluate_decision()`, Gamma,
Predicate Binding, Replay, Runtime Context, Serialization, and the Hydra Ledger are untouched
and are *not* required to change for this work.

---

## 0. Executive summary

The repository-level claim

> `"6_agentdojo": { "status": "NOT_EXECUTABLE", "reason": "genuine 'agentdojo' package not installed" }`
> (`VALIDATION_RESULTS.json:110`)

**is stale.** The genuine upstream `agentdojo==0.1.35` **is installed and functional** in the
dedicated interpreter `agentdojo_integration/.venv` (CPython 3.11.15). The suites load, and the
L-DREA interception layer (`GammaGovernedRuntime`) runs against the real AgentDojo runtime today —
verified live (all Phase-3A checks PASS, see §3).

The "not installed" reason is an artifact of **which interpreter reports it**: the top-level
`.venv` and the system interpreter are **Python 3.9.6**, and `agentdojo` is not installed there
(and cannot be — see §4). The validation harness evaluated executability from the 3.9 interpreter,
not from the 3.11 venv that actually holds the package.

What is genuinely **not yet in place** is the **scored end-to-end benchmark run** (utility +
attack-success-rate over the task/injection corpus). That requires two things:

1. **An LLM agent pipeline** — i.e. a live model provider **API key** (external, not present).
2. **A thin in-repo benchmark driver** that threads `runtime_class=GammaGovernedRuntime` through
   AgentDojo's own scoring loop, because upstream's top-level benchmark helpers do not expose that
   parameter (the low-level entry point does — see §4). This uses genuine AgentDojo scoring; it
   emulates nothing.

**Verdict:** the engineering support is **ready to implement now**. The only thing outside our
control is a runtime LLM API key, which is a user-supplied input at execution time, not a code
blocker. See the final line.

---

## 1. Root Cause Report

### 1.1 What "NOT_EXECUTABLE" actually means here

| Candidate blocker | Finding |
|---|---|
| **Missing package** | **FALSE.** `agentdojo 0.1.35` present in `agentdojo_integration/.venv/lib/python3.11/site-packages/agentdojo`. `import agentdojo.task_suite, agentdojo.functions_runtime, agentdojo.benchmark` all succeed. |
| **API changes** | **NO break.** The integration already targets the installed API. `TaskSuite.run_task_with_pipeline(..., runtime_class=...)` exists (`task_suite.py:345`, constructs `runtime = runtime_class(self.tools)` at `:380`) — the exact injection point the design assumes. |
| **Dependency conflict** | **NONE observed.** The frozen lockfile (`manifests/requirements-frozen.txt`) resolves inside the 3.11 venv; `pydantic 2.13.4`, `openai 2.44.0`, `anthropic 0.116.0`, `deepdiff 9.1.0` all import. |
| **Python version** | **Root cause of the misleading report.** `agentdojo` requires Python ≥3.11 (matched by the nested venv). System + top-level venv are 3.9.6, where the package is absent/uninstallable. Any executability probe run under 3.9 will (correctly, for *that* interpreter) say "not installed". |
| **Missing model provider** | **TRUE — the real remaining blocker for *scored* results.** No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` in the environment. A scored benchmark run cannot proceed without a live provider (or an archived transcript set). |
| **Environment configuration** | Partial: the correct interpreter must be selected (3.11 venv), and a provider key exported. Both are setup steps, not engineering blockers (§2). |
| **Broken integration** | **NO.** Interception verified live end-to-end (§3). |
| **Repository structure** | Minor: the validation harness probes the wrong interpreter. Fixable by pointing status derivation at the 3.11 venv. |

### 1.2 Precise root cause

There are **two distinct causes**, and they have been conflated under one status string:

- **Cause A (reporting defect):** the "package not installed" status is produced by an interpreter
  (Python 3.9) that is *not* the one AgentDojo lives in. Under the correct interpreter
  (`agentdojo_integration/.venv`, 3.11), the package is installed and importable. **This blocker is
  false and should be retracted.**

- **Cause B (genuine gap):** a *scored* AgentDojo benchmark (utility / UER / FPR over the corpus)
  has never been executed because (i) no LLM provider credential is available, and (ii) no in-repo
  driver yet threads the L-DREA runtime through AgentDojo's own `run_task_with_pipeline` scoring
  loop. (ii) is a small piece of first-party glue code; (i) is external.

---

## 2. Environment Requirements

**Interpreter (already provisioned):**
- CPython **3.11.15** at `agentdojo_integration/.venv/bin/python` (uv-created).
- Do **not** use the top-level `.venv` (3.9.6) or system Python for anything AgentDojo-related.

**Provider credential (must be supplied to *execute*):** one of
- `export OPENAI_API_KEY=...`  (e.g. `--model gpt-4o-2024-05-13`)
- `export ANTHROPIC_API_KEY=...` (e.g. `--model claude-3-5-sonnet-20241022`)
- `export GOOGLE_API_KEY=...` (Gemini) / `CO_API_KEY` (Cohere)

26 model ids are registered upstream (`agentdojo.models.ModelsEnum`), spanning OpenAI, Anthropic,
Google, Cohere, Mistral/Llama (TogetherAI), and `local`/`vllm_parsed` for a self-hosted server.

**Determinism policy for a publishable run** (already specified in the design docs; restated for the
runner): `temperature = 0`, pin `model_id` + provider version, set provider `seed` where supported,
and **archive full AgentDojo transcripts** so the ERTuple stream can be re-derived offline — the
determinism claim is scoped to the *authorization decision given a fixed candidate action + CTR*,
never the LLM.

**No-key fallback (keeps the artifact reproducible without spending tokens):** run once with a key,
archive the AgentDojo logs, and replay/score from the archived transcripts. `local`/`vllm_parsed`
against a self-hosted model is also viable and needs no external key.

---

## 3. Live verification performed (this session)

Run under `agentdojo_integration/.venv/bin/python`:

- `import agentdojo` + core submodules → **OK**.
- `get_suites("v1")["banking" | "workspace"]` load + `load_and_inject_default_environment` → **OK**.
- `agentdojo_integration/tests/test_interception.py` → **ALL CHECKS PASS**:
  read-only pass-through; recognized-IBAN PERMIT+execute; unrecognized-IBAN SAFE_STATE; over-balance
  SAFE_STATE; workspace recipient PERMIT / SAFE_STATE; unknown-tool fail-closed; Layer-1 root
  `ce8c8467…` immutable; Layer-2 binding `a2b816e0…`; tamper/missing/provenance integrity all trip.

This proves the genuine framework + L-DREA interception are wired and working. The gap is purely the
**scored LLM-in-the-loop run**, not the integration.

---

## 4. Dependency Analysis & Required Integration Changes

### 4.1 Dependencies — resolved
Installed and importable in the 3.11 venv: `agentdojo 0.1.35`, `pydantic 2.13.4`,
`openai 2.44.0`, `anthropic 0.116.0`, `google-genai 2.10.0`, `cohere 7.0.5`, `deepdiff 9.1.0`,
`langchain/langgraph` stack. Frozen in `manifests/requirements-frozen.txt` +
`manifests/agentdojo_requirements.lock`. A vendored source tarball
(`manifests/agentdojo-v0.1.35.tar.gz` + `.sha256`) is present for offline/air-gapped reinstall.
**No new dependency is required.**

### 4.2 The one genuine integration change

Upstream's convenience entry points do **not** thread the runtime class:

- `benchmark.benchmark_suite_with_injections(...)` — **no** `runtime_class` param.
- `benchmark.run_task_with_injection_tasks(...)` — **no** `runtime_class` param; internally calls
  `suite.run_task_with_pipeline(...)` **without** passing one (so it defaults to the vanilla
  `FunctionsRuntime`, bypassing L-DREA).
- `TaskSuite.run_task_with_pipeline(..., runtime_class=FunctionsRuntime)` — **DOES** accept it
  (`task_suite.py:345`) and does `runtime = runtime_class(self.tools)` (`:380`).

**Required adaptation (first-party, no AgentDojo edit, no frozen edit):** a small driver that
reproduces AgentDojo's own benchmark loop at the `run_task_with_pipeline` level, passing
`runtime_class=GammaGovernedRuntime`, and reuses AgentDojo's native scoring (`user_task.utility(...)`,
`injection_task.security(...)`) and its `aggregate_results` / `SuiteResults`. Concretely it:

1. builds the pipeline: `AgentPipeline.from_config(PipelineConfig(llm=<provider>, model_id=<model>))`;
2. loads the attack: `agentdojo.attacks.load_attack("important_instructions", suite, pipeline)`
   (and the no-injection baseline for utility);
3. for each `(user_task, injection_task)` in the suite, calls
   `suite.run_task_with_pipeline(pipeline, user_task, injection_task, attack, runtime_class=GammaGovernedRuntime, logdir=<archive>)`;
4. records upstream utility/security booleans **plus** the L-DREA `gamma_decisions` trace from the
   runtime, and aggregates UER/FPR with the Group-II/III accounting the design docs pre-register.

This is genuine AgentDojo end-to-end — its suites, its attacks, its tasks, its scoring. The only
custom object is the runtime, which is the intended, upstream-supported extension seam.

*Alternative (even smaller):* monkeypatch the module-level default so
`run_task_with_pipeline`'s `runtime_class` defaults to `GammaGovernedRuntime`, then call the stock
`benchmark_suite_with_injections`. Functionally equivalent; the explicit driver is preferred for
auditability and because it lets us capture the `gamma_decisions` trace cleanly.

### 4.3 Reporting fix
Update the executability probe to evaluate `agentdojo` **from the 3.11 venv** and rewrite the
`6_agentdojo` block: distinguish "package available: YES" from "scored run pending provider key".

---

## 5. Exact Implementation Plan (proposed — not executed)

1. **Retract the false blocker.** Fix the probe to import `agentdojo` under
   `agentdojo_integration/.venv`; change `VALIDATION_RESULTS.json` `6_agentdojo.status` from
   `NOT_EXECUTABLE` to `PACKAGE_AVAILABLE_RUN_PENDING_PROVIDER` (or equivalent) with the true reason.
2. **Add `agentdojo_integration/run_benchmark.py`** (new file; touches nothing frozen): the driver
   of §4.2 with CLI `--suite --model --user-tasks --injection-tasks --logdir --attack`.
3. **Pre-registration guard.** Assert the predicate/allowlist manifests (roots `ce8c8467…`,
   `a2b816e0…`) are loaded and unmodified before any task runs; emit the blind-authoring statement
   into the results header (per design §IX-F).
4. **Provider-gated execution.** If no key is present, exit cleanly with
   `status = RUN_PENDING_PROVIDER` — never fabricate. If a key is present, run `temperature=0`,
   archive transcripts to `--logdir`.
5. **Results + replay.** Emit `agentdojo_ldrea_results.json` (utility, UER, FPR, Group I/II/III
   counts, per-task `gamma_decisions`) and verify the archived transcripts re-derive the same
   ERTuple stream offline (replay determinism, no LLM).
6. **Smoke first.** Validate on a 1-task × 1-injection slice before the full corpus.

---

## 6. Estimated Engineering Effort

| Item | Effort |
|---|---|
| Probe/reporting fix (§5.1) | ~0.5 day |
| Benchmark driver `run_benchmark.py` (§5.2–5.4) | ~1.5–2 days |
| Results/replay emission + aggregation (§5.5) | ~1 day |
| Smoke + one full suite pass (§5.6) | ~0.5 day (wall-clock dominated by LLM latency/cost) |
| **Total engineering** | **~3.5–4 days**, no frozen-component changes |

Provider cost (separate from engineering): a full multi-suite injected run is on the order of a few
hundred to a few thousand LLM calls per model; budget dominated by model choice and corpus size.

---

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| **No provider key → cannot score** | High (blocks *execution*, not *implementation*) | User exports one key; or use `local`/`vllm_parsed`; or replay from an archived transcript set once produced. |
| **Circularity** (predicates fit to the injection corpus) | High (scientific validity) | Enforce blind-authoring pre-registration (§5.3); predicates already frozen at `ce8c8467…` *before* corpus inspection; report honest false permits (Group II). |
| **Upstream default bypasses L-DREA** (runtime not threaded) | Medium | Driver calls `run_task_with_pipeline` with explicit `runtime_class`; add an assertion that the runtime instance is `GammaGovernedRuntime` and that `gamma_decisions` is populated. |
| **Weak agent never proposes the EEA** → vacuous denials | Medium | Pin a capable model; report per-task whether the injected EEA reached the monitor (§IX-C accounting). |
| **LLM nondeterminism** breaks reproducibility | Medium | `temperature=0` + seed + transcript archival; determinism claim scoped to the authorization decision, not the LLM. |
| **Python-version drift** (someone runs under 3.9) | Low | Runner hard-checks `sys.version_info >= (3, 11)` and refuses otherwise. |
| **Cost/rate limits** on full corpus | Low–Med | Smoke slice first; checkpoint via `logdir` + `force_rerun=False` to resume. |
| **Provider model deprecation** | Low | Vendored tarball + archived transcripts make the artifact re-scorable offline. |

---

## Conclusion

The stated blocker ("agentdojo not installed") is a reporting artifact of probing a Python-3.9
interpreter; the genuine framework is installed and the L-DREA interception runs against it live.
The only remaining need to produce **scored** results is (a) a first-party benchmark driver that
threads the existing `runtime_class` seam — implementable now — and (b) a runtime LLM provider key,
which is a user-supplied execution input, not an engineering blocker.

**READY TO IMPLEMENT AGENTDOJO SUPPORT**

*(Execution to produce published numbers additionally requires the user to export one LLM provider
API key — a runtime input, not a code dependency. No changes implemented; awaiting independent
review.)*
