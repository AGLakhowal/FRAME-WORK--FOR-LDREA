# VALUE_DEPENDENCY_GRAPH

Paper → JSON → CSV → execution_trace.jsonl → runtime event → code, for the Table 10/11/13 values.

## Table 11 (AgentDojo) dependency chain
```
Paper Table 11 cell
   ↑ IEEE_TABLES_FINAL.md
statistics.json  (agentdojo_integration/audit_run/summary/)
   ↑ stats_engine.analyze()  ← _util.{wilson_ci,describe,shannon_entropy}
decisions.csv / predicates.csv  (same summary dir, same analyze() pass)
   ↑ stats_engine.collect()
33 × execution_trace.jsonl  (audit_run/trace/<suite>/<task>/)
   ↑ ExecutionTracer.emit()  during suite.run_task_with_pipeline(runtime_class=TracingRuntime)
runtime events: LLM_* , TOOL_CALL_PROPOSED , GAMMA_INTERCEPT , PREDICATE_EVALUATION ,
                Γ COMPUTATION , Π COMPUTATION , PERMIT/DENY_DECISION , TOOL_EXECUTION , EPISODE_FINISHED
   ↑ frozen GammaGovernedRuntime.run_function → PredicateEvaluator.evaluate → GammaBridge.decide
     → gamma_test_runner.evaluate_decision   (FROZEN)
```
Replay branch: `replay_validation.json ← replay_engine.ReplayEngine(execution_trace.jsonl)` re-derives
Γ_global=OR(deficits), Π, decision — independent of the frozen runtime.
Integrity branch: `frozen_integrity.json ← integrity.frozen_snapshot()` (SHA256 of 19 frozen files).
Labels branch: `fpr_fdr.json ← fpr_fdr_labeling.run()` ← injection GOAL text (independent of gate).

## Table 10 (Ablation) dependency chain
```
Paper Table 10
   ├─ failure modes ← VALIDATION_RESULTS.json:9_ablation ← (earlier ablation campaign)
   ├─ build/bind/adapt/eval/emit ← PERFORMANCE_RESULTS.json:7_performance.per_stage_ms ← Campaign-7 profiler (n=2000)
   └─ Runtime Context / Replay ← runtime_profile.json ← runtime_profile.run()
        ↑ timers wrapping frozen FreshnessClock/CommitActuateJournal (Runtime Context)
          and frozen write_replay_manifest (Replay), over run_pipeline() on 5000 rows
```

## Table 13 (Concurrency) dependency chain
```
Paper Table 13
   ↑ concurrency_scaling.json / .csv
   ↑ concurrency_scaling.run()  → _run_level() (threads) → GammaBridge.decide → evaluate_decision (FROZEN)
   metrics: throughput=n/wall ; latency=perf_counter deltas (numpy percentiles) ;
            queue_delay=dequeue−enqueue ; cpu=os.times ; rss=getrusage ; correctness=results==reference
```

## Leaf (raw) artifacts — the ground truth
- `audit_run/trace/**/execution_trace.jsonl` (33 files, 685 events) — append-only, hash-chained.
- `PERFORMANCE_RESULTS.json`, `VALIDATION_RESULTS.json`, `concurbench_full_report.json` — earlier campaigns (frozen).
- `concurrency_scaling.json`, `runtime_profile.json`, `fpr_fdr.json` — this campaign.

Every node in each chain is a file on disk or a named function; there are no dangling references.
