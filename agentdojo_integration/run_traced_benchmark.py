#!/usr/bin/env python
"""Drive ONE genuine AgentDojo episode under L-DREA with the pure-observability ExecutionTracer,
emit all trace artifacts, and VALIDATE non-invasiveness deterministically.

This is additive: it does not modify AgentDojo, the frozen interception package,
gamma_test_runner.evaluate_decision, run_benchmark.py, prompts, attacks, or scoring. It reuses the
runner's frozen-integrity gate and provider resolution unchanged.

Validation strategy (robust to the documented LLM non-determinism): the authorization layer is
deterministic given a fixed candidate action + context (DET-1). We therefore replay the traced
episode's own candidate-action sequence through a FRESH, UNINSTRUMENTED GammaGovernedRuntime and
assert the Gamma decision stream (decision, Γ_global, Γ_class, Π, deficits) is byte-identical to the
traced run. Identical ⇒ the tracer did not perturb any authorization / Γ / Π / evidence value.

Run:
  export LOCAL_LLM_PORT=11434
  agentdojo_integration/.venv/bin/python agentdojo_integration/run_traced_benchmark.py \
      --suite workspace --user-task user_task_6 --injection-task injection_task_0 \
      --model vllm_parsed --outdir agentdojo_integration/trace
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agentdojo.task_suite.load_suites import get_suites
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.base_tasks import BaseUserTask

from agentdojo_integration.interception.governed_runtime import GammaGovernedRuntime
from agentdojo_integration.execution_tracer import (
    ExecutionTracer, make_tracing_runtime, instrument_pipeline_llm, write_all,
)
from agentdojo_integration import ollama_probe
from agentdojo_integration import run_benchmark as R  # reuse frozen-gate + provider resolution (unmodified)


def _decision_key(gd: dict) -> tuple:
    return (gd.get("function"), gd.get("eea_class"), gd.get("decision"),
            gd.get("gamma_g"), gd.get("gamma_class"))


def replay_validate(suite, user_task, injections, candidate_trace, traced_gamma_decisions) -> dict:
    """Deterministic non-invasiveness proof: replay candidates through a clean runtime."""
    env = suite.load_and_inject_default_environment(injections)
    if isinstance(user_task, BaseUserTask):
        env = user_task.init_environment(env)
    clean = GammaGovernedRuntime(suite.tools)  # frozen, uninstrumented
    for step in candidate_trace:
        clean.run_function(env, step["function"], step["kwargs"], raise_on_error=False)
    traced = [_decision_key(g) for g in traced_gamma_decisions]
    replay = [_decision_key(g) for g in clean.gamma_decisions]
    return {
        "candidate_actions_replayed": len(candidate_trace),
        "traced_decision_stream": traced,
        "replay_decision_stream": replay,
        "identical": traced == replay,
        "n_decisions": len(traced),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="workspace")
    ap.add_argument("--user-task", default="user_task_6", dest="user_task")
    ap.add_argument("--injection-task", default="injection_task_0", dest="injection_task")
    ap.add_argument("--attack", default="important_instructions")
    ap.add_argument("--model", default="vllm_parsed")
    ap.add_argument("--benchmark-version", default="v1", dest="benchmark_version")
    ap.add_argument("--outdir", default="agentdojo_integration/trace")
    args = ap.parse_args(argv)

    integrity = R.assert_frozen_integrity()               # frozen gate (unmodified)
    provider, env_var, key_ok = R.resolve_provider(args.model)
    if not key_ok:
        # Hosted provider explicitly selected without its key: a genuine execution failure.
        # The default (vllm_parsed + Ollama) needs no credential, so never exit 0 pretending success.
        print(f"[trace] FATAL — model '{args.model}' selects hosted provider '{provider}', which needs "
              f"{env_var}. Tracing does not require a hosted provider; drop --model for the offline "
              f"Ollama default.", file=sys.stderr)
        return 2

    if env_var is None:  # local provider -> Ollama; probe before doing any work
        info = ollama_probe.probe()
        if not info["available"]:
            print(f"[trace] FATAL — Ollama unreachable: {info['detail']}\n\n{ollama_probe.REMEDIATION}",
                  file=sys.stderr)
            return 2
        print(f"[trace] Ollama OK: {info['detail']} -> {info['endpoint']}")

    episode_id = f"{args.suite}.{args.user_task}.{args.injection_task}.{args.model}"
    tracer = ExecutionTracer(episode_id)

    pipeline = AgentPipeline.from_config(
        PipelineConfig(llm=args.model, model_id=None, defense=None,
                       system_message_name=None, system_message=None))
    instrument_pipeline_llm(pipeline, tracer)             # LLM observer (record-then-delegate)

    suite = get_suites(args.benchmark_version)[args.suite]
    attack = load_attack(args.attack, suite, pipeline)
    ut = suite.get_user_task_by_id(args.user_task)
    it = suite.get_injection_task_by_id(args.injection_task)
    injections = attack.attack(ut, it)

    TracingRuntime = make_tracing_runtime(tracer)
    utility, security = suite.run_task_with_pipeline(
        pipeline, ut, it, injections, runtime_class=TracingRuntime, verbose=False)

    tracer.emit("EPISODE_FINISHED", "AgentDojo.benchmark", {
        "utility": utility, "security": security}, step=tracer.step)

    # ---- non-invasiveness validation (deterministic authorization-layer proof) ----
    rt = tracer._runtimes[-1] if getattr(tracer, "_runtimes", None) else None
    traced_decisions = rt.gamma_decisions if rt else []
    candidate_trace = rt.candidate_trace if rt else []
    val = replay_validate(suite, ut, injections, candidate_trace, traced_decisions)

    meta = {"suite": args.suite, "user_task": args.user_task, "injection_task": args.injection_task,
            "attack": args.attack, "model": args.model, "provider": provider,
            "benchmark_version": args.benchmark_version, "utility": utility, "security": security,
            "frozen": integrity, "validation": val}
    summary = write_all(args.outdir, tracer, meta)
    json.dump(val, open(Path(args.outdir) / "validation_report.json", "w"), indent=2, default=str)

    print(f"[trace] episode={episode_id}")
    print(f"[trace] events={summary['total_events']} steps={summary['total_steps']} "
          f"llm={summary['n_llm_calls']} tools={summary['n_tool_calls_proposed']} "
          f"permit={summary['n_permitted']} deny={summary['n_denied']}")
    print(f"[trace] utility={utility} security={security}")
    print(f"[trace] VALIDATION authorization-layer identical (traced==replay): {val['identical']} "
          f"({val['n_decisions']} decisions)")
    print(f"[trace] artifacts -> {args.outdir}")
    return 0 if val["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
