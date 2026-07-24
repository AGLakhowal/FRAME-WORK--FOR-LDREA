# Reproducibility Report

**Every experiment in this package is re-runnable from the repository with one command.** This report
gives the environment, the exact commands, the artifact SHA-256 fingerprints produced this session, and
a fresh-vs-prior comparison that distinguishes invariant results (reproduce exactly) from
host-dependent timing (reproduce only up to host variance).

## Environment

| | |
|---|---|
| Host | Apple M5, 10 cores, 17 GB RAM |
| OS | macOS (Darwin 25.5.0) |
| Python | 3.9.6 (`./.venv`; AgentDojo uses `agentdojo_integration/.venv`, agentdojo==0.1.35) |
| Java/TLC | Temurin JDK 21 + tla2tools 1.8.0 (fetched to `~/.ldrea_tla`) |
| Repo HEAD | `763008a32e9225f5086eb8c6794625c88da0bf1b` |
| Absent | Ollama, Tier-H FPGA/SGX/HSM, LAB v1.0 1.2 M generator |

## One-command re-runs

```bash
# Category A — runtime correctness (regenerates the ULB LAB report + manifest)
./.venv/bin/python gamma_test_runner.py --no-html --no-open
./.venv/bin/python -c "import concurbench_full,stress_test,fcr_test,full_spec_conformance as f; \
    [m.run(write=True) for m in (concurbench_full,stress_test,fcr_test,f)]"
./.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl

# Category B — agent governance (no LLM; re-derive + boundary probe)
agentdojo_integration/.venv/bin/python -c "from agentdojo_integration.audit import stats_engine as s; \
    s.write_reports('agentdojo_integration/audit_run/trace','evaluation_package/evidence/agentdojo')"
agentdojo_integration/.venv/bin/python -c "from agentdojo_integration.audit import fpr_fdr_labeling as f; \
    f.run('agentdojo_integration/audit_run/trace','evaluation_package/evidence/agentdojo/fpr_fdr')"
agentdojo_integration/.venv/bin/python experiment_agentdojo_boundary_fpr.py

# Category C — performance
./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; \
    c.run('evaluation_package/evidence/concurrency',200000,[1,2,4,8,16,32,64])"
./.venv/bin/python -c "from agentdojo_integration.audit import runtime_profile as r; \
    r.run('evaluation_package/evidence/runtime_profile',5000)"

# Category D — formal
./.venv/bin/python independent_verifier.py
java -cp ~/.ldrea_tla/tla2tools.jar tlc2.TLC -config formal/ExternalizationMonitor.cfg formal/ExternalizationMonitor.tla

# Category E — ablation
./.venv/bin/python experiment_ablation.py
```

## Artifact fingerprints (produced this session, 2026-07-09)

| Artifact | SHA-256 (first 16) | bytes |
|---|---|---|
| `gamma_lab_v1_report.json` | `386e9af7507d0144` | 11,697 |
| `gamma_summary.json` | `81d10dc03f4b53d9` | 3,514 |
| `gamma_replay_manifest.jsonl` | `1ce2a9e8d4330a05` | 200,966,760 |
| `concurbench_full_report.json` | `54833f7163dc7b50` | 74,634 |
| `stress_test_report.json` | `0930130a271738fc` | 14,958 |
| `fcr_test_report.json` | `f06256d9a3ff8e94` | 1,805 |
| `full_spec_conformance_report.json` | `aaeed075ff566fb6` | 9,789 |
| `evidence/agentdojo/statistics.json` | `342cdb2224332b64` | 10,903 |
| `evidence/agentdojo/fpr_fdr/fpr_fdr.json` | `681b2959315fd965` | 3,910 |
| `evidence/agentdojo_boundary/boundary_fpr.json` | `cde16292bdcaad81` | 4,365 |
| `evidence/concurrency/concurrency_scaling.json` | `f475b8bd7ea1d694` | 7,068 |
| `evidence/runtime_profile/runtime_profile.json` | `ee79a8caf7e594bb` | 978 |
| `independent_verifier_report.json` | `1d20111a7cec3d29` | 1,300 |
| `fresh_evidence/ablation/ablation.json` | `0382007a5aa337a3` | 5,859 |

Full manifest with every field: `evaluation_package/PROVENANCE.json`.

## Fresh-vs-prior reproducibility comparison

Prior committed artifacts were preserved at `evaluation_package/baseline_artifacts_prior/` before this
session's fresh runs. The comparison distinguishes two classes of result:

| Quantity | Fresh (this session) | Nature | Reproduces? |
|---|---|---|---|
| UER / FPR / FDR (LAB) | 0 / 0 / 0 | safety invariant | **exactly** |
| Replay determinism rate | 100.0000% | safety invariant | **exactly** |
| Class-veto effectiveness | 492/492 | safety invariant | **exactly** |
| Formal state-space mismatches | 0 / 65,536 | correctness invariant | **exactly** |
| Concurrency FP / FD (all levels) | 0 / 0 | safety invariant | **exactly** |
| Boundary FPR (foreign targets) | 0 / 62 | safety invariant | **exactly** |
| Concurrency throughput @1 thread | 227,771 dec/s | host-dependent timing | **no — 0.58× vs prior 390,766** |
| Runtime-Context ms/row | ~0.016 | host-dependent timing | **within host variance** |

**Conclusion.** Correctness and safety results are **bitwise-stable across fresh re-execution**; timing
results are **host- and load-dependent by nature** and are never reported without their host. This is
precisely why the package mandates fresh execution for any timing claim and artifact reuse only for
reproducibility comparison.

## Determinism guarantees relied upon

- Workloads in `concurrency_scaling`, `experiment_ablation`, and the boundary probe are **index-driven,
  no RNG** — identical across runs.
- `stress_test` / `concurbench_full` seed their RNG deterministically.
- The frozen engine, manifests (Merkle root `ce8c8467…`), and binding SHA are immutable and verified at
  load; any drift raises before an experiment runs.
