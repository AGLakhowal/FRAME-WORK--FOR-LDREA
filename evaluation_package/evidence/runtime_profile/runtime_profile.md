# Runtime Context & Replay Profiling (measured)

- Rows: 5000 · end-to-end (incl. replay): 0.24810 ms/row

| stage | latency (ms/row) | % of end-to-end | isolation |
|---|---|---|---|
| Runtime Context (RCL plane-B) | 0.016734 | 6.74% | wrapped FreshnessClock + CommitActuateJournal (timers only) |
| Replay (ERTuple manifest) | 0.010167 | 4.10% | frozen write_replay_manifest (write_pipeline_manifest) |

> Runtime Context here = the RCL plane-B operations (freshness/velocity/commit-actuate ordering) that ablation `without_runtime_context` disables; measured by wrapping the frozen FreshnessClock/CommitActuateJournal with timers. Replay = the frozen ERTuple manifest emitter. No frozen logic modified.