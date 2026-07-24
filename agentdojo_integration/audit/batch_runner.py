"""Phase A --- multi-episode trace collection.

Runs many genuine AgentDojo episodes under L-DREA with the existing ExecutionTracer, organizing
output as trace/<suite>/<user_task>__<injection_task>/. Supports resume (skip already-completed
episodes), a deterministic sequential default (safe given the shared Ollama server), and per-episode
frozen-integrity + trace-integrity + replay verification.

Additive: builds on execution_tracer + AgentDojo public APIs + run_benchmark's frozen gate. Modifies
nothing frozen. Every episode's numbers come from real execution.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from agentdojo.task_suite.load_suites import get_suites
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig

from agentdojo_integration.execution_tracer import (
    ExecutionTracer, make_tracing_runtime, instrument_pipeline_llm, write_all)
from agentdojo_integration.run_traced_benchmark import replay_validate
from agentdojo_integration import run_benchmark as R
from . import integrity
from ._util import write_json


@dataclass(frozen=True)
class EpisodeSpec:
    suite: str
    user_task: str
    injection_task: str
    attack: str = "important_instructions"

    def dirname(self) -> str:
        return f"{self.user_task}__{self.injection_task}"


def enumerate_episodes(benchmark_version: str = "v1", suites: list[str] | None = None,
                       attack: str = "important_instructions", max_user_tasks: int | None = None,
                       max_injections: int = 1,
                       explicit: list[str] | None = None) -> list[EpisodeSpec]:
    """Enumerate episode specs. If `explicit` is given (list of "suite:user_task:injection_task",
    injection optional → defaults to the suite's first), those exact episodes are used; otherwise the
    first `max_user_tasks` user tasks × first `max_injections` injections per suite."""
    all_suites = get_suites(benchmark_version)
    if explicit:
        specs: list[EpisodeSpec] = []
        for triple in explicit:
            parts = triple.split(":")
            sn, ut = parts[0], parts[1]
            it = parts[2] if len(parts) > 2 else list(all_suites[sn].injection_tasks.keys())[0]
            specs.append(EpisodeSpec(sn, ut, it, attack))
        return specs
    names = suites or list(all_suites.keys())
    specs = []
    for sn in names:
        s = all_suites[sn]
        uts = list(s.user_tasks.keys())
        if max_user_tasks is not None:
            uts = uts[:max_user_tasks]
        its = list(s.injection_tasks.keys())[:max_injections]
        for ut in uts:
            for it in its:
                specs.append(EpisodeSpec(sn, ut, it, attack))
    return specs


def _is_done(epi_dir: Path) -> bool:
    return (epi_dir / "execution_summary.json").exists() and (epi_dir / "validation_report.json").exists()


def run_one(spec: EpisodeSpec, model: str, base_outdir: str | Path,
            benchmark_version: str = "v1", force: bool = False) -> dict:
    epi_dir = Path(base_outdir) / spec.suite / spec.dirname()
    episode_id = f"{spec.suite}.{spec.user_task}.{spec.injection_task}.{model}"
    if _is_done(epi_dir) and not force:
        return {"episode_id": episode_id, "status": "SKIPPED_RESUME", "dir": str(epi_dir)}

    frozen_before = integrity.frozen_snapshot()
    tracer = ExecutionTracer(episode_id)
    pipeline = AgentPipeline.from_config(
        PipelineConfig(llm=model, model_id=None, defense=None,
                       system_message_name=None, system_message=None))
    instrument_pipeline_llm(pipeline, tracer)

    suite = get_suites(benchmark_version)[spec.suite]
    attack = load_attack(spec.attack, suite, pipeline)
    ut = suite.get_user_task_by_id(spec.user_task)
    it = suite.get_injection_task_by_id(spec.injection_task)
    injections = attack.attack(ut, it)

    TracingRuntime = make_tracing_runtime(tracer)
    utility, security = suite.run_task_with_pipeline(
        pipeline, ut, it, injections, runtime_class=TracingRuntime, verbose=False)
    tracer.emit("EPISODE_FINISHED", "AgentDojo.benchmark",
                {"utility": utility, "security": security}, step=tracer.step)

    rt = tracer._runtimes[-1] if getattr(tracer, "_runtimes", None) else None
    val = replay_validate(suite, ut, injections,
                          rt.candidate_trace if rt else [], rt.gamma_decisions if rt else [])
    frozen_after = integrity.frozen_snapshot()
    frozen_verdict = integrity.run_frozen_guard(epi_dir, frozen_before, frozen_after)

    meta = {**asdict(spec), "model": model, "benchmark_version": benchmark_version,
            "utility": utility, "security": security, "validation": val,
            "frozen_integrity": frozen_verdict}
    summary = write_all(str(epi_dir), tracer, meta)
    write_json(epi_dir / "validation_report.json", val)
    trace_integ = integrity.verify_trace_integrity(epi_dir / "execution_trace.jsonl")
    write_json(epi_dir / "trace_integrity.json", trace_integ)

    return {"episode_id": episode_id, "status": "COMPLETED", "dir": str(epi_dir),
            "utility": utility, "security": security,
            "authorization_identical": val["identical"],
            "n_decisions": val["n_decisions"],
            "frozen_unchanged": frozen_verdict["unchanged"],
            "trace_integrity_ok": trace_integ["integrity_ok"],
            "n_events": summary["total_events"]}


def run_batch(specs: list[EpisodeSpec], model: str, base_outdir: str | Path,
              benchmark_version: str = "v1", force: bool = False,
              progress=lambda m: print(m, flush=True)) -> dict:
    base = Path(base_outdir)
    base.mkdir(parents=True, exist_ok=True)
    results = []
    for i, spec in enumerate(specs, 1):
        progress(f"[batch] ({i}/{len(specs)}) {spec.suite}/{spec.dirname()}")
        try:
            r = run_one(spec, model, base, benchmark_version, force)
        except Exception as e:  # keep the batch alive; record the failure honestly
            r = {"episode_id": f"{spec.suite}.{spec.user_task}.{spec.injection_task}",
                 "status": "ERROR", "error": repr(e)}
        results.append(r)
        write_json(base / "summary" / "batch_manifest.json",
                   {"model": model, "benchmark_version": benchmark_version,
                    "n_specs": len(specs), "completed": i, "results": results})
    manifest = {"model": model, "benchmark_version": benchmark_version, "n_specs": len(specs),
                "n_completed": sum(1 for r in results if r["status"] == "COMPLETED"),
                "n_skipped": sum(1 for r in results if r["status"] == "SKIPPED_RESUME"),
                "n_error": sum(1 for r in results if r["status"] == "ERROR"),
                "results": results}
    write_json(base / "summary" / "batch_manifest.json", manifest)
    return manifest
