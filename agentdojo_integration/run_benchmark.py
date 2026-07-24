#!/usr/bin/env python
"""First-party runner for the GENUINE upstream AgentDojo benchmark under L-DREA governance.

This runner does NOT modify, fork, or emulate AgentDojo. It drives the official framework
exactly as intended, injecting the L-DREA authorization boundary through AgentDojo's own
supported ``runtime_class`` extension point on ``TaskSuite.run_task_with_pipeline``
(agentdojo 0.1.35, ``task_suite.py:345`` → ``runtime = runtime_class(self.tools)`` at ``:380``).

What is genuine upstream and untouched:
  * suites .......... agentdojo.task_suite.load_suites.get_suites(benchmark_version)
  * attacks ......... agentdojo.attacks.attack_registry.load_attack(...)
  * agent pipeline .. agentdojo.agent_pipeline.AgentPipeline.from_config(PipelineConfig(...))
  * scoring ......... TaskSuite.run_task_with_pipeline -> (utility, security) booleans
  * aggregation ..... agentdojo.benchmark.aggregate_results
  * transcripts ..... agentdojo.logging.OutputLogger / TraceLogger (archived to --logdir)

What is first-party (this file only, nothing frozen touched):
  * TracingGammaRuntime: a thin subclass of the FROZEN GammaGovernedRuntime that records the
    ordered candidate-action stream so decisions can be replayed offline. It changes NO policy —
    it only observes. The frozen GammaGovernedRuntime, evaluate_decision(), Gamma, Predicate
    Binding, Runtime Context, Replay, Serialization, Hydra Ledger, Evidence Bundle and
    SAFE_STATE semantics are imported and used as-is.
  * the benchmark loop, which mirrors agentdojo.benchmark.run_task_with_injection_tasks but
    threads runtime_class=TracingGammaRuntime (upstream's top-level helpers do not expose it).

Determinism: temperature=0 (AgentDojo default for OpenAI/Anthropic LLMs), pinned model id,
archived transcripts. The determinism claim is scoped to the AUTHORIZATION DECISION given a
fixed candidate action + context (DET-1), verified offline by replay — never over the LLM.

Default model is `vllm_parsed`: AgentDojo's local provider, which talks to an OpenAI-compatible
endpoint at http://localhost:$LOCAL_LLM_PORT/v1. Ollama serves exactly that on port 11434, so the
live arm runs fully offline with no external API credential. Hosted providers remain selectable
but are never required; if one is selected and its key is absent, this script FAILS LOUDLY
(exit 2) rather than silently recording a pending status. Never fabricates results.

Note: E7's headline guard-side metrics need no model at all — see experiment_agentdojo_metrics.py.
This script exists to generate FRESH episodes (agent-side utility / attack-success rate).

Run (must use the Python 3.11 AgentDojo venv):
  ollama serve & ollama pull llama3.1:8b && export LOCAL_LLM_PORT=11434
  agentdojo_integration/.venv/bin/python agentdojo_integration/run_benchmark.py \
      --suites banking --attack important_instructions --logdir agentdojo_integration/runs
  # offline harness verification (no LLM, no key, no fabricated scores):
  agentdojo_integration/.venv/bin/python agentdojo_integration/run_benchmark.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# --- repo root on path so `agentdojo_integration.interception.*` imports resolve -------------
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MIN_PY = (3, 11)


def _fatal(msg: str, code: int = 2) -> "None":
    print(f"[run_benchmark] FATAL: {msg}", file=sys.stderr)
    raise SystemExit(code)


if sys.version_info < MIN_PY:
    _fatal(
        f"AgentDojo requires Python >= {MIN_PY[0]}.{MIN_PY[1]}; this interpreter is "
        f"{sys.version_info.major}.{sys.version_info.minor}. Use agentdojo_integration/.venv/bin/python.",
    )

# --- genuine upstream AgentDojo imports (fail loudly, never emulate) -------------------------
try:
    from agentdojo.task_suite.load_suites import get_suites
    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig, MODEL_PROVIDERS
    from agentdojo.models import ModelsEnum
    from agentdojo.benchmark import aggregate_results
    from agentdojo.logging import OutputLogger, TraceLogger, Logger
    from agentdojo.base_tasks import BaseUserTask
except ModuleNotFoundError as e:  # pragma: no cover - environment guard
    _fatal(
        f"genuine 'agentdojo' package not importable ({e}). Provision agentdojo_integration/.venv "
        "(Python 3.11, agentdojo==0.1.35). This runner never emulates AgentDojo.",
    )

# --- FROZEN L-DREA components (imported, never modified) -------------------------------------
from agentdojo_integration.interception.governed_runtime import GammaGovernedRuntime
from agentdojo_integration.interception.frozen_policy import (
    ScientificPolicy,
    SCIENTIFIC_ROOT,
    default_scientific_policy,
)
from agentdojo_integration.interception.execution_binding import ExecutionBinding, BINDING_SHA
from agentdojo_integration import ollama_probe

# provider -> environment variable that must hold a credential (None = no external key needed).
# `local` / `vllm_parsed` reach an OpenAI-compatible endpoint at localhost:$LOCAL_LLM_PORT/v1,
# which is what Ollama serves. That is the supported, offline, credential-free path.
PROVIDER_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "together": "TOGETHER_API_KEY",
    "together-prompting": "TOGETHER_API_KEY",
    "cohere": "CO_API_KEY",
    "google": "GOOGLE_API_KEY",  # vertex also honours GCP_PROJECT/GCP_LOCATION
    "local": None,
    "vllm_parsed": None,
}


# ============================================================================================
# Observation-only runtime: records the candidate-action stream. NO policy change.
# ============================================================================================
class TracingGammaRuntime(GammaGovernedRuntime):
    """Frozen GammaGovernedRuntime + an append-only observation tape.

    Overrides only ``run_function`` to append ``(function, kwargs)`` before delegating to the
    frozen implementation. It records; it never decides. Instances self-register so the driver
    can retrieve the trace after ``run_task_with_pipeline`` (which constructs the runtime
    internally and does not return it).
    """

    registry: "list[TracingGammaRuntime]" = []

    def __init__(self, functions=None, **kw):
        super().__init__(functions, **kw)
        self.candidate_trace: list[dict] = []
        TracingGammaRuntime.registry.append(self)

    def run_function(self, env, function, kwargs, raise_on_error: bool = False):
        self.candidate_trace.append({"function": function, "kwargs": dict(kwargs)})
        return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)


# ============================================================================================
# Frozen-integrity gate (must pass before any task runs)
# ============================================================================================
def assert_frozen_integrity() -> dict:
    sci = ScientificPolicy()
    binding = ExecutionBinding()
    if sci.root != SCIENTIFIC_ROOT:
        _fatal(f"Layer-1 scientific root mismatch: {sci.root} != {SCIENTIFIC_ROOT}")
    if binding.sha != BINDING_SHA:
        _fatal(f"Layer-2 binding sha mismatch: {binding.sha} != {BINDING_SHA}")
    # sanity: the default (production) runtime binds the same frozen roots
    rt = GammaGovernedRuntime([])
    if rt.frozen_merkle_root != SCIENTIFIC_ROOT or rt.binding_sha != BINDING_SHA:
        _fatal("default GammaGovernedRuntime does not bind the frozen roots")
    return {
        "scientific_root": SCIENTIFIC_ROOT,
        "binding_sha": BINDING_SHA,
        "method_version": rt.method_version,
        "blind_authoring_statement": (
            "predicates specified from action-class semantics with the AgentDojo injection "
            "corpus unopened (design §IX-F); manifests frozen prior to corpus inspection."
        ),
    }


# ============================================================================================
# Offline replay verification of the AUTHORIZATION DECISION (DET-1), no LLM involved.
# ============================================================================================
def replay_decisions(suite, user_task, injections: dict, candidate_trace: list[dict],
                     original_decisions: list[dict]) -> dict:
    """Re-issue the recorded candidate actions into a FRESH runtime + freshly rebuilt
    environment and confirm the decision sequence reproduces bit-for-bit.

    This is the DET-1 claim scope: identical (candidate action, context) -> identical decision.
    The LLM is not in the loop; only the frozen authorization monitor is exercised.
    """
    env = suite.load_and_inject_default_environment(injections)
    if isinstance(user_task, BaseUserTask):
        env = user_task.init_environment(env)
    replay_rt = GammaGovernedRuntime(suite.tools)  # frozen production runtime, not the tracer
    for step in candidate_trace:
        replay_rt.run_function(env, step["function"], step["kwargs"], raise_on_error=False)

    def _key(d):
        return (d.get("function"), d.get("eea_class"), d.get("decision"),
                d.get("gamma_g"), d.get("gamma_class"))

    orig = [_key(d) for d in original_decisions]
    rep = [_key(d) for d in replay_rt.gamma_decisions]
    return {
        "deterministic": orig == rep,
        "n_decisions": len(orig),
        "original": orig,
        "replayed": rep,
    }


# ============================================================================================
# Provider resolution
# ============================================================================================
def resolve_provider(model: str) -> tuple[str, "str | None", bool]:
    """Return (provider, env_var, key_available)."""
    try:
        provider = MODEL_PROVIDERS[ModelsEnum(model)]
    except (ValueError, KeyError):
        _fatal(f"model '{model}' is not a registered AgentDojo model id. "
               f"See agentdojo.models.ModelsEnum.")
    env_var = PROVIDER_ENV.get(provider, "UNKNOWN")
    if env_var is None:  # local / vllm_parsed
        return provider, None, True
    return provider, env_var, bool(os.getenv(env_var))


# ============================================================================================
# The genuine benchmark loop (mirrors run_task_with_injection_tasks, threading runtime_class)
# ============================================================================================
def run_full_benchmark(args, integrity: dict) -> dict:
    provider, env_var, key_ok = resolve_provider(args.model)
    suites = get_suites(args.benchmark_version)
    selected = args.suites or list(suites.keys())
    for name in selected:
        if name not in suites:
            _fatal(f"suite '{name}' not in benchmark {args.benchmark_version}: {list(suites.keys())}")

    logdir = Path(args.logdir) if args.logdir else None
    if logdir:
        logdir.mkdir(parents=True, exist_ok=True)

    pipeline = AgentPipeline.from_config(
        PipelineConfig(llm=args.model, model_id=None, defense=None,
                       system_message_name=None, system_message=None)
    )  # temperature=0 by default; validator auto-fills the default system message
    pipeline_name = pipeline.name or args.model

    results = {
        "status": "COMPLETED",
        "framework": {"name": "agentdojo", "version": "0.1.35", "benchmark_version": args.benchmark_version},
        "model": args.model, "provider": provider, "attack": args.attack,
        "determinism": {"temperature": 0.0, "seeded": True, "scope": "authorization decision (DET-1), not the LLM"},
        "frozen": integrity,
        "suites": {},
    }

    # OutputLogger context => TraceLogger archives full transcripts under logdir/pipeline_name/...
    log_ctx = OutputLogger(str(logdir)) if logdir else OutputLogger(None)
    with log_ctx:
        for suite_name in selected:
            suite = suites[suite_name]
            attack = load_attack(args.attack, suite, pipeline)
            user_task_ids = args.user_tasks or list(suite.user_tasks.keys())
            if args.limit:
                user_task_ids = user_task_ids[: args.limit]
            injection_task_ids = args.injection_tasks or list(suite.injection_tasks.keys())
            if args.limit_injections:
                injection_task_ids = injection_task_ids[: args.limit_injections]

            baseline_utility: dict[tuple[str, str], bool] = {}
            attack_utility: dict[tuple[str, str], bool] = {}
            security: dict[tuple[str, str], bool] = {}
            per_task = []
            replay_all_ok = True
            interception_complete = True

            for ut_id in user_task_ids:
                user_task = suite.get_user_task_by_id(ut_id)

                # (a) baseline utility, no injection
                TracingGammaRuntime.registry.clear()
                b_util, _ = suite.run_task_with_pipeline(
                    pipeline, user_task, None, {}, runtime_class=TracingGammaRuntime, verbose=args.verbose,
                )
                baseline_utility[(ut_id, "none")] = b_util

                # (b) under each injection task, with the genuine attack
                for it_id in injection_task_ids:
                    injection_task = suite.get_injection_task_by_id(it_id)
                    task_injections = attack.attack(user_task, injection_task)

                    TracingGammaRuntime.registry.clear()
                    with TraceLogger(
                        delegate=Logger.get(), suite_name=suite.name, user_task_id=ut_id,
                        injection_task_id=it_id, injections=task_injections,
                        attack_type=attack.name, pipeline_name=pipeline_name,
                        benchmark_version=args.benchmark_version,
                    ) as logger:
                        utility, sec = suite.run_task_with_pipeline(
                            pipeline, user_task, injection_task, task_injections,
                            runtime_class=TracingGammaRuntime, verbose=args.verbose,
                        )
                        logger.set_contextarg("utility", utility)
                        logger.set_contextarg("security", sec)

                    tracer = TracingGammaRuntime.registry[-1] if TracingGammaRuntime.registry else None
                    gamma = list(tracer.gamma_decisions) if tracer else []
                    candidate = list(tracer.candidate_trace) if tracer else []

                    # every candidate action must have been mediated (read-only pass-through,
                    # PERMIT, SAFE_STATE, or UNKNOWN fail-closed) — no action escapes the boundary
                    mediated_fns = {d["function"] for d in gamma}
                    unmediated = [c["function"] for c in candidate
                                  if c["function"] not in mediated_fns
                                  and _is_boundary_action(suite, c["function"])]
                    if unmediated:
                        interception_complete = False

                    replay = replay_decisions(suite, user_task, task_injections, candidate, gamma)
                    replay_all_ok = replay_all_ok and replay["deterministic"]

                    attack_utility[(ut_id, it_id)] = utility
                    security[(ut_id, it_id)] = sec
                    per_task.append({
                        "user_task": ut_id, "injection_task": it_id,
                        "utility_under_attack": utility, "injection_succeeded": sec,
                        "n_candidate_actions": len(candidate),
                        "gamma_decisions": gamma,
                        "replay_deterministic": replay["deterministic"],
                    })

            results["suites"][suite_name] = {
                "n_user_tasks": len(user_task_ids), "n_injection_tasks": len(injection_task_ids),
                "metrics": {
                    "baseline_utility": aggregate_results([baseline_utility]),
                    "utility_under_attack": aggregate_results([attack_utility]),
                    "attack_success_rate": aggregate_results([security]),
                },
                "verification": {
                    "interception_complete": interception_complete,
                    "replay_deterministic": replay_all_ok,
                },
                "per_task": per_task,
            }
    return results


def _is_boundary_action(suite, function: str) -> bool:
    """True if `function` is an externally-effective (mediated) or unknown tool — i.e. it MUST
    appear in the governance decision log. Read-only tools legitimately pass through unrecorded."""
    policy = default_scientific_policy()
    mediated, eea_class, _families, _cond = policy.classify(function)
    return mediated or eea_class == policy.is_unknown_class


# ============================================================================================
# Offline self-check: exercises the FULL harness except the LLM. No key, no fabricated scores.
# ============================================================================================
def run_selfcheck(integrity: dict) -> dict:
    """Verify suite loading, genuine attack/injection generation, complete interception, and
    replay determinism against a scripted candidate stream (no LLM, no benchmark scores)."""
    suites = get_suites("v1")
    suite = suites["banking"]
    attack = _load_attack_no_pipeline(suite, "important_instructions")

    # genuine AgentDojo injection generation (LLM-free)
    ut = suite.get_user_task_by_id(next(iter(suite.user_tasks.keys())))
    it = suite.get_injection_task_by_id(next(iter(suite.injection_tasks.keys())))
    injections = attack.attack(ut, it) if attack is not None else {}

    # scripted candidate actions covering every decision class
    from agentdojo_integration.interception.predicate_evaluation import _ibans
    env = suite.load_and_inject_default_environment(injections)
    env = ut.init_environment(env) if isinstance(ut, BaseUserTask) else env
    good_iban = sorted(_ibans(env))[0]
    scripted = [
        {"function": "get_balance", "kwargs": {}},                                          # read-only pass-through
        {"function": "send_money", "kwargs": {"recipient": good_iban, "amount": 10.0, "subject": "s", "date": "2026-01-01"}},  # PERMIT
        {"function": "send_money", "kwargs": {"recipient": "DE00ATTACKER00000000000000000000", "amount": 10.0, "subject": "x", "date": "2026-01-01"}},  # SAFE_STATE
        {"function": "totally_unknown_future_tool", "kwargs": {"x": 1}},                     # UNKNOWN fail-closed
    ]

    TracingGammaRuntime.registry.clear()
    rt = TracingGammaRuntime(suite.tools)
    live_env = suite.load_and_inject_default_environment(injections)
    live_env = ut.init_environment(live_env) if isinstance(ut, BaseUserTask) else live_env
    for step in scripted:
        rt.run_function(live_env, step["function"], step["kwargs"], raise_on_error=False)

    mediated_fns = {d["function"] for d in rt.gamma_decisions}
    boundary_actions = [s["function"] for s in scripted if _is_boundary_action(suite, s["function"])]
    interception_complete = all(f in mediated_fns for f in boundary_actions)

    replay = replay_decisions(suite, ut, injections, rt.candidate_trace, rt.gamma_decisions)

    decisions = {d["function"]: d["decision"] for d in rt.gamma_decisions}
    return {
        "status": "SELFCHECK",
        "note": "harness verification only — no LLM, no benchmark scores produced",
        "frozen": integrity,
        "genuine_injection_generated": bool(injections),
        "n_injection_slots": len(injections),
        "interception_complete": interception_complete,
        "replay_deterministic": replay["deterministic"],
        "decision_classes_observed": decisions,
        "checks": {
            "read_only_pass_through": "get_balance" not in decisions,
            "eea_permit_present": "send_money" in decisions,
            "unknown_fail_closed": any(d["function"] == "totally_unknown_future_tool"
                                       and d["decision"] == "SAFE_STATE" for d in rt.gamma_decisions),
        },
    }


def _load_attack_no_pipeline(suite, attack_name: str):
    """load_attack needs a target pipeline only for a few adaptive attacks; important_instructions
    does not query the model to build injections. Provide a no-op element to satisfy the signature."""
    from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement

    class _NoPipeline(BasePipelineElement):
        # a recognized model id so the attack's injection template renders offline; this element
        # never queries a model (its query() is a no-op), so no provider/key is used.
        name = "gpt-4o-2024-05-13"

        def query(self, query, runtime, env=None, messages=(), extra_args=None):
            return query, runtime, env, list(messages), extra_args or {}

    try:
        return load_attack(attack_name, suite, _NoPipeline())
    except Exception as e:  # pragma: no cover
        print(f"[run_benchmark] selfcheck: attack '{attack_name}' needs a live pipeline ({e}); "
              "skipping injection generation.", file=sys.stderr)
        return None


# ============================================================================================
# CLI
# ============================================================================================
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Run the genuine AgentDojo benchmark under L-DREA governance.")
    p.add_argument("--model", default="vllm_parsed",
                   help="AgentDojo model id (agentdojo.models.ModelsEnum). Default: vllm_parsed "
                        "(local OpenAI-compatible endpoint, i.e. Ollama on $LOCAL_LLM_PORT). "
                        "Hosted providers are selectable but never required.")
    p.add_argument("--suites", nargs="*", default=None, help="suite names (default: all in benchmark).")
    p.add_argument("--attack", default="important_instructions", help="AgentDojo attack name.")
    p.add_argument("--user-tasks", nargs="*", default=None, dest="user_tasks")
    p.add_argument("--injection-tasks", nargs="*", default=None, dest="injection_tasks")
    p.add_argument("--limit", type=int, default=None, help="cap user tasks per suite (smoke runs).")
    p.add_argument("--limit-injections", type=int, default=None, dest="limit_injections")
    p.add_argument("--benchmark-version", default="v1", dest="benchmark_version")
    p.add_argument("--logdir", default="agentdojo_integration/runs", help="transcript archive dir.")
    # NB: agentdojo_results.json is owned by experiment_agentdojo_metrics.py (the E7 result of
    # record). The live arm writes its agent-side scores elsewhere so it cannot clobber it.
    p.add_argument("--out", default="agentdojo_integration/audit_run/live_episode_results.json",
                   help="results JSON path for the live (agent-side) arm.")
    p.add_argument("--selfcheck", action="store_true",
                   help="offline harness verification (no LLM, no key, no scores).")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    integrity = assert_frozen_integrity()

    if args.selfcheck:
        results = run_selfcheck(integrity)
        _write(args.out, results)
        ok = (results.get("interception_complete") and results.get("replay_deterministic")
              and all(results.get("checks", {}).values()))
        print(f"[run_benchmark] SELFCHECK {'PASS' if ok else 'FAIL'} "
              f"(interception_complete={results.get('interception_complete')}, "
              f"replay_deterministic={results.get('replay_deterministic')})")
        return 0 if ok else 1

    provider, env_var, key_ok = resolve_provider(args.model)
    if not key_ok:
        # A hosted provider was explicitly selected but its key is absent. This is a genuine
        # execution failure, not a scientific limitation: the offline default (vllm_parsed +
        # Ollama) needs no credential. Fail loudly; never record a silent "pending" status.
        _fatal(
            f"model '{args.model}' selects hosted provider '{provider}', which needs {env_var}.\n"
            f"E7 does not require any hosted provider. Either export {env_var}, or run offline:\n"
            f"    ollama serve & ollama pull llama3.1:8b && export LOCAL_LLM_PORT=11434\n"
            f"    agentdojo_integration/.venv/bin/python agentdojo_integration/run_benchmark.py "
            f"--model vllm_parsed --suites banking"
        )

    if env_var is None:  # local provider (vllm_parsed / local) -> Ollama
        # Probe the server rather than letting AgentDojo fail deep inside an HTTP call.
        info = ollama_probe.probe()
        if not info["available"]:
            _fatal(f"local provider '{provider}' selected but Ollama is unreachable — "
                   f"{info['detail']}\n\n{ollama_probe.REMEDIATION}")
        print(f"[run_benchmark] Ollama OK: {info['detail']} -> {info['endpoint']}")

    results = run_full_benchmark(args, integrity)
    _write(args.out, results)
    ok = all(s["verification"]["interception_complete"] and s["verification"]["replay_deterministic"]
             for s in results["suites"].values())
    print(f"[run_benchmark] COMPLETED — {'ALL VERIFICATIONS PASS' if ok else 'VERIFICATION FAILURE'}")
    return 0 if ok else 1


def _write(path: str, obj: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str))
    print(f"[run_benchmark] wrote {path}")


if __name__ == "__main__":
    raise SystemExit(main())
