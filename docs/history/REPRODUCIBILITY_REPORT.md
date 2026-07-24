# REPRODUCIBILITY REPORT — Scientific Validation Campaign

**Reproducibility evidence only. No methodology or reported-output change.** This report lets an independent reviewer reproduce every result in `EXPERIMENTAL_VALIDATION_REPORT.md`.

---

## 1. Environment

| Item | Value |
|---|---|
| Repository HEAD | `763008a` (branch `main`) |
| Python | 3.9 (project `.venv`) |
| Libraries present | pandas, numpy |
| Libraries absent | matplotlib, scipy, **agentdojo** (→ figures as ASCII; Campaign 6 N/A) |
| Platform | darwin (single host) |
| Network | not required (all local, deterministic) |

## 2. Determinism basis (why results reproduce bit-for-bit)

- The pipeline is a **pure function** of its inputs: no wall clock (envelope labels derived from `run_id`+index), no randomness, no `Class` read.
- Evidence bundles and the Hydra Ledger use **SHA-256 over canonical JSON** (sorted keys); identical inputs → identical digests.
- Confirmed: **23 executions** (10 repeated + 5 replay re-emit + 8 concurrent) produced **1** distinct record hash, **1** manifest SHA, **1** ledger head → determinism rate **1.000**.

## 3. Canonical reproduction hashes

| Quantity | Value |
|---|---|
| 24-row reference record SHA-256 | `0e71f595053c1ccebbb44684551bfe55555251a49e4588cd5316ea145e7325a4` |
| 24-row reference manifest SHA-256 | `ca1ab9fc9d6bd24f3d343506647f34553aacdd21c1065358d3f21a4ad1151134` |
| Class-blind record SHA-256 (0/1/absent) | `ae97aa24814d093ec879d233466978fef0f331efd21a1b3d9c2165b29ade86d7` |
| Class-blind manifest SHA-256 | `522e14f1e7b6c5d0afc9d2d1c1c7db9928ab01418b66d70116bc9f7929fe301a` |
| Frozen engine (`gamma_test_runner.py:119-178`) | byte-identical to HEAD |

A reviewer re-running the campaign must reproduce these exact hashes.

## 4. Commands to reproduce

```bash
# Frozen-component test suites (all green):
for t in test_execution_evidence_bundle test_ports test_context_objects test_transaction_interpreter \
         test_assembler test_eeb_to_engine test_evidence_trace_builder test_predicate_binding \
         test_reported_artifact_emitter test_emitter_replay_integration test_class_blind_pipeline \
         test_emitter_failclosed_serialization; do .venv/bin/python tests/$t.py; done

# Regression / benchmark parity (read-only comparison; no artifact regeneration):
.venv/bin/python tests/test_regression_parity.py            # 6/6

# Independent replay verification:
.venv/bin/python gamma_replay_verify.py gamma_replay_manifest.jsonl   # RESULT: PASS

# End-to-end pipeline demo:
.venv/bin/python -m runtime_context.class_blind_pipeline
```

The campaign harness itself was executed from the session scratchpad (not committed) and wrote only `VALIDATION_RESULTS.json` and `PERFORMANCE_RESULTS.json`; benchmarks were run with `write=False` and all manifests to temp dirs, so no reported artifact was regenerated.

## 5. Neutrality evidence

| Check | Result |
|---|---|
| `concurbench_full_report.json` mtime | unchanged (pre-campaign) |
| `gamma_summary.json` mtime | unchanged |
| Regression parity | 6/6 passed |
| `evaluate_decision` + `NODE_GATE_COLS` vs HEAD | IDENTICAL |
| Frozen component SHAs (binding/adapter/EEB/emitter) | unchanged during the campaign |

## 6. Replay reproducibility

- Manifest generation is deterministic (5× → 1 SHA).
- The independent verifier (`gamma_replay_verify.py`) re-derives adjacency, evidence-quad ledger binding, and self-consistency **without** pandas or the runner → RESULT: PASS, 0 failures.
- Large-batch (5,000-row) manifest also verifies PASS.

## 7. Known non-reproducible / outstanding items

1. **AgentDojo (Campaign 6)** — requires provisioning the genuine `agentdojo` package; not reproducible here. No synthetic substitute was used.
2. **Absolute latency** — wall-clock, host-dependent; varies run-to-run (relative structure and determinism reproduce; absolute ms do not).
3. **Discriminative confusion matrix** — a Phase-B artifact (requires a declared deployment policy); the neutral pipeline reproducibly yields the degenerate all-SAFE_STATE matrix.

## 8. Analysis-tooling correction (transparency)

During analysis, the harness's Wilson-interval helper unpacked the engine's `(point, lower, upper)` tuple in the wrong order, mislabeling CI fields in the first JSON write. This was a **bug in the analysis code only** (not in any frozen component); it was corrected by recomputing the three affected proportion CIs from the stored `successes`/`n`. Corrected values: authorization 24/24 = 1.000 [0.862, 1.000]; determinism 10/10 = 1.000 [0.722, 1.000]; fail-closed 5/5 = 1.000 [0.566, 1.000]. No measured count changed.

---

*Reproducibility report only. No methodology or reported-output change. Awaiting independent review.*
