#!/usr/bin/env python
"""Top-level orchestrator (ADDITIVE) — runs the full scientific audit end-to-end.

Phases: A batch trace collection · H frozen+trace integrity · D replay · B statistics ·
C reviewer reports · E proofs · F visualization · G dashboard · I summary · J supplementary.

Modifies nothing frozen. Every value comes from real execution. Emits a final completion report.

Run:
  export LOCAL_LLM_PORT=11434
  agentdojo_integration/.venv/bin/python agentdojo_integration/run_audit.py \
      --suites workspace banking --max-user-tasks 3 --outdir agentdojo_integration/audit_run
"""
from __future__ import annotations

import argparse
import resource
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from agentdojo_integration import ollama_probe
from agentdojo_integration import run_benchmark as R
from agentdojo_integration.audit import (
    batch_runner, integrity, replay_engine, stats_engine, reviewer_reports,
    proof_generator, visualize, dashboard, summary as summary_mod, supplementary)
from agentdojo_integration.audit._util import write_json, write_text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", nargs="*", default=["workspace"])
    ap.add_argument("--model", default="vllm_parsed")
    ap.add_argument("--benchmark-version", default="v1", dest="benchmark_version")
    ap.add_argument("--max-user-tasks", type=int, default=3, dest="max_user_tasks")
    ap.add_argument("--max-injections", type=int, default=1, dest="max_injections")
    ap.add_argument("--attack", default="important_instructions")
    ap.add_argument("--episodes", nargs="*", default=None,
                    help="explicit episodes as suite:user_task[:injection_task]; overrides --suites/--max-user-tasks")
    ap.add_argument("--outdir", default="agentdojo_integration/audit_run")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    out = Path(args.outdir); (out / "summary").mkdir(parents=True, exist_ok=True)
    trace_root = out / "trace"
    sumdir = out / "summary"

    integ_before = R.assert_frozen_integrity()
    provider, env_var, key_ok = R.resolve_provider(args.model)
    if not key_ok:
        # Hosted provider explicitly selected without its key: a genuine execution failure.
        # The default (vllm_parsed + Ollama) needs no credential, so never exit 0 pretending success.
        print(f"[audit] FATAL — model '{args.model}' selects hosted provider '{provider}', which needs "
              f"{env_var}. This audit does not require a hosted provider; drop --model to use the "
              f"offline Ollama default.", file=sys.stderr)
        return 2

    if env_var is None:  # local provider -> Ollama; probe before doing any work
        info = ollama_probe.probe()
        if not info["available"]:
            print(f"[audit] FATAL — Ollama unreachable: {info['detail']}\n\n{ollama_probe.REMEDIATION}",
                  file=sys.stderr)
            return 2
        print(f"[audit] Ollama OK: {info['detail']} -> {info['endpoint']}")

    frozen_before = integrity.frozen_snapshot()

    # ---- Phase A: batch trace collection ----
    specs = batch_runner.enumerate_episodes(
        args.benchmark_version, args.suites, args.attack, args.max_user_tasks, args.max_injections,
        explicit=args.episodes)
    print(f"[audit] enumerated {len(specs)} episodes"
          + (f" (explicit)" if args.episodes else f" across suites {args.suites}"))
    manifest = batch_runner.run_batch(specs, args.model, trace_root, args.benchmark_version, args.force)

    # ---- Phase H: frozen integrity (whole run) ----
    frozen_after = integrity.frozen_snapshot()
    frozen_verdict = integrity.run_frozen_guard(sumdir, frozen_before, frozen_after)

    # ---- Phase H: trace integrity for every episode ----
    trace_integrity = []
    for tf in sorted(trace_root.rglob("execution_trace.jsonl")):
        trace_integrity.append(integrity.verify_trace_integrity(tf))
    write_json(sumdir / "trace_integrity_all.json", trace_integrity)

    # ---- Phase D: replay every trace from jsonl only ----
    replay_reports = []
    for tf in sorted(trace_root.rglob("execution_trace.jsonl")):
        rep = replay_engine.replay_and_verify(tf, tf.parent / "replay_report.json")
        replay_reports.append({"episode": f"{tf.parent.parent.name}/{tf.parent.name}",
                               "all_steps_consistent": rep["all_steps_consistent"],
                               "n_authorization_steps": rep["n_authorization_steps"]})
    replay_agg = {"n_traces": len(replay_reports),
                  "all_consistent": all(r["all_steps_consistent"] for r in replay_reports),
                  "total_authorization_steps": sum(r["n_authorization_steps"] for r in replay_reports),
                  "reports": replay_reports}
    write_json(sumdir / "replay_validation.json", replay_agg)

    # ---- Phase B: statistics ----
    stats = stats_engine.write_reports(trace_root, sumdir)

    # ---- Phase C: reviewer reports ----
    reviewer = reviewer_reports.generate(trace_root, sumdir / "reviewer")

    # ---- Phase E: proofs ----
    proofs = proof_generator.generate(trace_root, sumdir)

    # ---- Phase F/G: visualization + dashboard ----
    graphs = visualize.generate(trace_root, sumdir, stats)
    figs = dashboard.generate(stats, sumdir)

    # ---- Phase I: benchmark-wide summary ----
    peak_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    resource_stats = {"peak_rss_bytes": peak_rss_kb if sys.platform == "darwin" else peak_rss_kb * 1024,
                      "note": "peak resident set size of the orchestrator process (getrusage), whole run."}
    bench_summary = summary_mod.build(stats, manifest, frozen_verdict, replay_agg, resource_stats)
    summary_mod.write(bench_summary, sumdir)

    # ---- Phase J: supplementary material ----
    supp = supplementary.generate(sumdir / "supplementary")

    # ---- Final completion report ----
    completion = {
        "outdir": str(out),
        "episodes": {"specs": manifest["n_specs"], "completed": manifest["n_completed"],
                     "skipped": manifest["n_skipped"], "errors": manifest["n_error"]},
        "validations": {
            "frozen_integrity_unchanged": frozen_verdict["unchanged"],
            "trace_integrity_all_ok": all(t["integrity_ok"] for t in trace_integrity),
            "replay_all_consistent": replay_agg["all_consistent"],
            "authorization_replay_identical": all(
                r.get("authorization_identical", True) for r in manifest["results"]
                if r["status"] == "COMPLETED"),
            "proofs_all_consistent": proofs["all_consistent"],
        },
        "statistics_headline": {
            "gamma_decisions": stats["n_decisions"], "permits": stats["n_authorizations_permit"],
            "denials": stats["n_denials"], "permit_rate_wilson95": stats["permit_rate_wilson"],
        },
        "artifacts": {
            "per_episode_dirs": [r["dir"] for r in manifest["results"] if r.get("dir")],
            "statistics": ["statistics.json", "statistics_tables.md", "decisions.csv", "predicates.csv"],
            "reviewer": ["reviewer/MASTER_REPORT.md", f"reviewer/episodes/ ({reviewer['n_episode_reports']} files)"],
            "proofs": ["all_proofs.json", f"proofs/ ({proofs['n_proofs']} proofs)"],
            "figures": figs["figures"], "graphs": graphs["graphs"],
            "dashboards": ["dashboard.html", "explorer.html"],
            "summary": ["BENCHMARK_SUMMARY.md", "BENCHMARK_SUMMARY.json"],
            "supplementary": supp["files"],
            "integrity": ["frozen_integrity.json", "trace_integrity_all.json", "replay_validation.json"],
        },
        "resource": resource_stats,
        "limitations": bench_summary["limitations"],
    }
    write_json(sumdir / "COMPLETION_REPORT.json", completion)
    _write_completion_md(sumdir / "COMPLETION_REPORT.md", completion, stats)

    print("\n=== AUDIT COMPLETE ===")
    print(f"episodes: {completion['episodes']}")
    print(f"validations: {completion['validations']}")
    print(f"stats: decisions={stats['n_decisions']} permit={stats['n_authorizations_permit']} deny={stats['n_denials']}")
    print(f"artifacts under: {sumdir}")
    ok = all(completion["validations"].values())
    print("ALL VALIDATIONS PASS" if ok else "SOME VALIDATION FAILED (see COMPLETION_REPORT.json)")
    return 0 if ok else 1


def _write_completion_md(path, c, stats):
    L = ["# Audit Completion Report", "",
         f"- Output: `{c['outdir']}`",
         f"- Episodes: {c['episodes']}",
         "", "## Validations", ""]
    for k, v in c["validations"].items():
        L.append(f"- {k}: **{v}**")
    L += ["", "## Statistics headline", "",
          f"- Gamma decisions: {stats['n_decisions']} (PERMIT {stats['n_authorizations_permit']}, "
          f"SAFE_STATE {stats['n_denials']})", "", "## Artifacts", ""]
    for group, items in c["artifacts"].items():
        L.append(f"- **{group}**: {items}")
    L += ["", "## Limitations", ""] + [f"- {x}" for x in c["limitations"]]
    write_text(path, "\n".join(L))


if __name__ == "__main__":
    raise SystemExit(main())
