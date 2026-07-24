# Combined Component Ablation Framework (E5b)

One-command, publication-grade combinatorial ablation measuring INTERACTION EFFECTS between runtime components. Extends the single-component ablation (E5).

## Run

```bash
python3 experiment_combined_ablation.py            # full (n=6000/config)
python3 experiment_combined_ablation.py --fast     # quick (n=2400/config)
python3 RUN_ALL_EXPERIMENTS.py --only combined_ablation
```

## What it produces

- `experiments/combined_ablation/combined_ablation.json` — 19 configurations, all metrics, interactions, per-config statistics, governance.
- `paper_tables/table_combined_ablation_{A,B,C}.{md,csv,tex}` — publication tables.
- `paper_figures/` + `experiments/combined_ablation/figures/` — 7 figures (heatmap, security/performance degradation, interaction matrix, latency, dependency graph, graceful curve).
- `dashboard/combined_runtime_ablation.html` — standalone dashboard.
- `metadata/COMPONENT_REGISTRY.json`, `metadata/COMPONENT_DEPENDENCY_GRAPH.md` — auto-discovery.
- `COMBINED_ABLATION_ANALYSIS.md`, `GRACEFUL_DEGRADATION_ANALYSIS.md`, `COMBINED_ABLATION_IMPLEMENTATION_REPORT.md`.

## Discovered components (9)

- **PE — Predicate Engine** (authorization): generates the runtime predicate vector Gamma aggregates non-compensatorily. deps=—; `experiments/runtime_stack.py`.
- **RV — Runtime Revocation** (enforcement): issues Permit-to-Act tokens and withdraws already-granted authority. deps=—; `experiments/runtime_stack.py`.
- **EQ — Evidence Quad** (evidence): emits the signed ERTuple (method/policy/ledger/replay evidence) per decision. deps=['PE']; `experiments/runtime_stack.py`.
- **LG — Runtime Ledger** (ledger): chains evidence into an append-only Merkle-rooted ledger. deps=['EQ']; `experiments/runtime_stack.py`.
- **HC — Hash Chain** (ledger): links each ledger block to its predecessor (tamper-evident ordering). deps=['EQ', 'LG']; `experiments/runtime_stack.py`.
- **RD — Runtime Risk Detection** (risk): fires real adversarial artifacts at the enforcement surface and measures refusal. deps=['PE', 'RV']; `experiments/runtime_attacks.py`.
- **WD — Runtime Watchdog** (governance): supervisor thread detecting per-worker stalls and driving fail-closed recovery. deps=—; `experiments/runtime_fleet.py`.
- **FT — Fleet Telemetry** (governance): multi-process Gamma fleet with per-worker CPU/RSS/throughput telemetry. deps=['PE', 'RV', 'WD']; `experiments/runtime_fleet.py`.
- **CK — Clock Consistency (single-host PTP)** (timing): single-host monotonic-clock characterisation (resolution, jitter, drift). deps=—; `experiments/run_runtime_stack.py`.

## Scientific guarantees

- Frozen Gamma engine unmodified (components wrapped at call sites only).
- Every value measured from execution; no analytical estimation.
- Interaction effects computed on measured Runtime Integrity Score; effect sizes via Cohen's d, Cliff's delta, Mann–Whitney U, two-proportion z (see `combined_ablation_stats.py`).

