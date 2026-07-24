# L-DREA Experimental Evaluation Package

IEEE-Access experimental evaluation for **L-DREA — a deterministic runtime-authorization architecture
for autonomous AI systems**. The datasets and benchmarks here are *evidence*; the object under
evaluation is the **architecture**. Every number was produced by an experiment executed on 2026-07-09
(Apple M5, Python 3.9.6), or is explicitly marked OPEN/BLOCKED with an exact rerun recipe. **No number
is estimated, reused as a substitute, or fabricated.**

## What this package establishes (one line each)

- **Correct** — UER 0/284,807; boundary FPR 0/62 on the real AgentDojo adversarial corpus; independent
  verifier IDENTICAL over all 2¹⁶ decision states.
- **Deterministic** — replay determinism 100.0000%; 284,807/284,807 manifest records independently
  re-verify; replay-consistent at every thread count and every ablation.
- **Safe / fail-closed** — class-veto 492/492; Fail-Closed Rate 1.0 (0 fail-open over 20,492 cases);
  0 false permits at 1–64 threads.
- **Reproducible** — correctness/safety results reproduce **bitwise** across fresh runs; timing is
  host-dependent and always reported with its host.
- **Scalable** — safety invariants hold at 1–64 threads; **throughput does NOT scale up (GIL-bound) —
  reported honestly as a limitation, not hidden.**
- **Domain-independent** — the *same* frozen engine governs a 284,807-row financial corpus and 4
  AgentDojo agent suites.

## The one thing a reader must know first

The paper's **headline tables (3–5, §IX latency) are Tier-H** — FPGA + SGX + HSM hardware, N = 1.2×10⁶,
360,000 adversarial. **That hardware and the LAB v1.0 1.2 M generator are not in this repository.** This
host is **Tier-S software-only.** This package is therefore a rigorous **Tier-S architectural
validation** of the same frozen decision logic — it validates the mechanism, invariants, determinism,
and fail-closed behaviour, and it does **not** reproduce the Tier-H sample sizes, HSM latency, or
absolute FPR percentages. Those are OPEN, each with an exact dependency + rerun recipe.

## Contents

| File | Deliverable |
|---|---|
| `00_EXPERIMENT_CATALOG.md` | Every experiment: purpose, hypothesis, setup, command, sample size, metrics, result, limitations, output |
| `01_EVALUATION_MATRIX.md` | Architectural property × experiment × result × status; metric-coverage checklist |
| `03_RUNTIME_CORRECTNESS_REPORT.md` | Category A — correctness / fail-closed / class-veto / replay / integrity |
| `04_AGENTDOJO_EVALUATION_REPORT.md` | Category B — agent governance; **boundary FPR 0/62 (no LLM)** |
| `05_PERFORMANCE_REPORT.md` | Category C — 1–64 thread scaling; safety holds, throughput does not |
| `06_FORMAL_VERIFICATION_REPORT.md` | Category D — exhaustive 2¹⁶ verifier + Appendix-D TLA+/TLC |
| `07_ABLATION_STUDY_REPORT.md` | Category E — class-veto / Γ / auth-layer leak-count ablation |
| `08_THREATS_TO_VALIDITY.md` | Every gap + BLOCKED item with exact dependency/install/rerun/expected |
| `09_REPRODUCIBILITY_REPORT.md` | Environment, one-command re-runs, artifact SHA-256, fresh-vs-prior |
| `10_REVIEWER_CLAIM_MATRIX.md` | Every paper claim → evidence → experiment → artifact → OPEN/CLOSED |
| `PROVENANCE.json` | Host + SHA-256 of every fresh artifact |
| `evidence/` | Fresh JSON/CSV/SVG for Categories B, C |
| `baseline_artifacts_prior/` | Prior artifacts preserved for the reproducibility comparison |
| `logs/` | stdout of every executed experiment |
| `../formal/` | `ExternalizationMonitor.tla`/`.cfg` — Appendix-D spec, verbatim, for TLC |

## Reading order for a reviewer

1. `10_REVIEWER_CLAIM_MATRIX.md` — the claim-by-claim verdict.
2. `01_EVALUATION_MATRIX.md` — the six-property summary.
3. Category reports `03`–`07` for detail.
4. `08_THREATS_TO_VALIDITY.md` — what is OPEN and exactly why.
5. `09_REPRODUCIBILITY_REPORT.md` — re-run it yourself.

## Honesty ledger (the findings a reviewer would otherwise catch)

1. **Throughput does not scale** (GIL-bound Python path) — Category C, stated as NEGATIVE.
2. **FPR bound is wide** (492 denominator → 1.31×10⁻², not the paper's 8.3×10⁻⁶) — needs the 360 k
   generator.
3. **Recognition-set gating** can't flag a known contact weaponized as an exfil sink, and 8 mediated
   tools are `structural_only` (ungated) — Category B.
4. **Ablation is a leak-count**, not the paper's hardware FPR% — Category E.
5. **AgentDojo end-to-end (Utility/TASR)** needs Ollama — OPEN.
6. **Appendix-D TLA+ was actually model-checked** (TLC: no error, 40,192 distinct states, 0 invariant
   violations); only the manuscript's *larger* 2,489,446-state count needs the authors' bigger config.
7. Two of the three Appendix-D theorems are near-definitional; Invariants 2–6 are not fully mechanized
   (the paper itself defers them to LAB v1.1).
