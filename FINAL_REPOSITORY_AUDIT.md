# Final Repository Audit — Independent Reviewer Closure

**Reviewer stance:** independent (IEEE Access / TDSC / TOSEM / FGCS), treating the repository as
frozen. This audit *verifies* by cross-checking artifacts, and applies only documentation,
reproducibility, and consistency repairs — no new features, no architecture change, no benchmark
number altered.

**Repairs applied during this audit** (all safe, none change a scientific value):
1. Fixed a transposed Wilson-interval unpacking bug (statistical correctness).
2. Added `datasets/README.md` (dataset placement for reproduction).
3. Marked the legacy `run_all.py` deprecated in favour of `RUN_ALL_EXPERIMENTS.py`.

---

## Executive summary

The repository is a **rigorous, unusually self-critical evaluation package**. Its central historical
weakness — that detection was only ever shown on a label-leaked corpus — has been **closed** this
cycle: experiment **E12** now runs genuine blind detection on three real public datasets (ULB,
IEEE-CIS, UNSW-NB15) as Measured Runtime, and the leakage is openly disclosed
(`label_leakage_audit.json`). One genuine statistical bug was found and fixed. The remaining issues
are **documentation, reproducibility framing, and consistency**, not material scientific gaps.

**Verdict: B — Publication Ready After Minor Repairs** (conditional on the manuscript adopting the
disclosed scope; see §Publication Risk). No undisclosed major scientific gap remains.

---

## Strengths (verified, not asserted)

| # | Strength | Evidence checked |
|---|---|---|
| S1 | Single authoritative engine | exactly one `evaluate_decision` (`gamma_test_runner.py`); one reusable rule `gamma_decision` (`stress_test.py`); both implement the same non-compensatory Law of Concurrence (verified: 1 deficit → SAFE_STATE, 0 → PERMIT) |
| S2 | One dashboard generator | only `experiments/generate_dashboard_html.py`; no competing generator |
| S3 | Real blind detection on real data | `production_evidence/datasets/*_eval.json`: ULB AUROC 0.912, UNSW 0.761, IEEE-CIS 0.611; labels absent from the decision path (`Observation` has no label field); hash chains verify |
| S4 | Statistical rigor | Wilson **and** bootstrap CIs agree (ULB recall Wilson [0.757, 0.884], bootstrap [0.763, 0.889]); MCC, AUROC, AUPRC, calibration-by-Γ all computed, not estimated |
| S5 | Honest evidence-level labelling | every artifact carries `evidence_level`; simulations carry `why_simulated`; Production Evidence = 0, External Validation = 0 stated everywhere |
| S6 | Negative control present | `clean_proposal_permits` prevents a deny-everything trivial pass |
| S7 | Dashboard–artifact consistency | spot-checked ULB AUROC 0.9116 matches dashboard; predicate coverage 13/13 matches |

---

## Remaining weaknesses

### Required fixes (correctness / reproducibility / consistency)

| ID | Severity | Issue | Evidence | Exact fix | Paper? | Bench? | Impl? | Effort |
|----|----------|-------|----------|-----------|--------|--------|-------|--------|
| **R1** | ~~High~~ **FIXED** | Wilson interval transposed (`low=1.0 > high=0.772`) | mis-unpacking `lo,hi,p = wilson_interval(...)` which returns `(p,lo,hi)`, `experiment_predicate_coverage.py:217` | corrected to `p,lo,hi`; artifact regenerated → [0.772, 1.0] | no | no (values unchanged) | done | done |
| **R2** | Medium | Experiment count inconsistent: registry has E1–E10, `run_index` has E1–E11, dashboard header shows 10/10 or 11/11 across runs, **E12 absent from `run_index`** (was run standalone) | `dashboard_registry.EXPERIMENTS`=10; `_meta/run_index.json`=11; E12 only a section | run full `RUN_ALL_EXPERIMENTS.py` once so E11/E12 land in `run_index`; state in README that E1–E10 are core registry experiments and E11–E12 are additive runtime-evidence experiments (dashboard §27–28) | no | no | no | 30 min (a full run) |
| **R3** | Medium | README does not tell a cloner where to place the real datasets, nor that E11/E12 exist (1 mention) | `README.md` references only the old mapped corpus | partly repaired (`datasets/README.md` added); add a 1-paragraph pointer + E11/E12 rows to the main README experiment table | no | no | no | 20 min |
| **R4** | ~~Medium~~ **RESOLVED (2026-07-10)** | ~~AgentDojo end-to-end not independently executed; conflicting artifacts~~ | Root cause was a **reporting bug**, not a scientific gap: `agentdojo_results.json` carried a stale pending-status stub from a hosted-provider default (`gpt-4o`) that E7 never required, and the dashboard hardcoded a placeholder status without reading E7's own metadata. | **Fixed.** E7 now executes fully offline via `experiment_agentdojo_metrics.py` → `e7_metrics.json` (verdict `PASS`, 0 failures). `agentdojo_results.json` is regenerated from real execution (`status: EXECUTED`, `measurement_mode: OFFLINE_NO_LLM`). Hosted-provider entrypoints now fail loudly (exit 2) instead of silently recording a pending status. | no — external validation is COMPLETE; only agent-side Utility/TASR remain OPEN (optional, local Ollama) | no | no | done |

### Optional enhancements (not required for publication)

| ID | Severity | Issue | Note |
|----|----------|-------|------|
| O1 | Low | Two "one-command" runners (`run_all.py` legacy vs `RUN_ALL_EXPERIMENTS.py`) | repaired: `run_all.py` marked deprecated |
| O2 | Low | Documentation sprawl: 9+ overlapping `*REPORT*/*AUDIT*/*COMPLETENESS*.md` at root | add a `DOCS_INDEX.md` naming the authoritative doc per topic; or fold into one |
| O3 | Low | Terminology drift: "false permit" (82) vs "false-permit" (9) in prose | cosmetic; normalise in a copy-edit pass |
| O4 | Low | IEEE-CIS `train_identity.csv` (device/browser) not joined | device/identity predicates available but unused for IEEE-CIS; additive |
| O5 | Low | Per-dataset figures / attack injection (Parts 6, 10) not run per-dataset | E11 attack machinery exists; reuse is additive |

---

## Risk matrices

### Reviewer Risk (probability a reviewer raises it × severity)

| Criticism | Prob | Severity | Status |
|---|---|---|---|
| "Headline detection is on a label-leaked corpus" | was High | High | **Mitigated** — E12 real blind detection + open leakage audit; paper must lead with honest framing |
| "AgentDojo/LLM evaluation incomplete" | ~~Med~~ Low | Low | **Addressed (R4).** E7 executes offline with the full guard-side metric suite (FPR/FDR, replay, evidence quad, hash chain, ledger, latency). Only agent-side Utility/TASR remain open, and they are optional, local-Ollama-only, and depended on by no L-DREA claim. |
| "Distributed/fleet/PTP claims on one host" | Med | Med | Disclosed — renamed to Runtime Clock Consistency; fleet is real multiprocess but single-host |
| "Detection precision is low" | Med | Low | Honest floor by design; framed as governance-predicate authorization, not SOTA fraud |
| "Which of the 9 report docs is authoritative?" | Low | Low | O2 |

### Scientific Risk

| Item | Risk | Note |
|---|---|---|
| Authorization correctness (E1) | Low | 0 false permits; but **conformance not detection** on the mapped corpus — disclosed |
| Blind detection (E12) | Low | Measured Runtime, real data, CIs agree; unsupervised floor disclosed |
| Formal verification (E3) | Low | TLC, 0 violations |
| Non-compensatory soundness | Low | 13/13 single-deficit denials, Wilson [0.772, 1.0] (now correct) |

### Implementation Risk

| Item | Risk | Note |
|---|---|---|
| Gamma engine | Low | single authoritative impl; untouched (mtime 2026-07-08); imported not redefined in E11/E12 |
| Two Γ implementations | Low | frozen ULB engine vs reusable rule — same law, verified consistent; document which is authoritative for what |
| Simulated components | Low | clock skew, key custody, single-host fleet — all labelled `Repository Simulation` with `why_simulated` |

### Reproducibility Risk

| Item | Risk | Note |
|---|---|---|
| One-command run | Low–Med | `RUN_ALL_EXPERIMENTS.py` covers E1–E12; **but** a fresh cloner needs dataset-placement docs (R3, partly fixed) |
| Timing non-idempotence | Low | latency metrics re-measure each run (documented); correctness metrics stable |
| Datasets | Low | git-ignored, discovered by header signature; absent → `not_found`, never fabricated |

### Documentation Risk

| Item | Risk | Note |
|---|---|---|
| README completeness | Med | missing dataset + E11/E12 instructions (R3) |
| Doc sprawl | Low | O2 |
| Discoverability | Low | most files reachable; add a docs index |

### Publication Risk

| Venue | Fit | Blocking condition |
|---|---|---|
| IEEE Access / FGCS | Strong | none if manuscript matches disclosed scope |
| TOSEM | Strong | reproducibility package is a plus; fix R2/R3 |
| TDSC / TIFS / ACSAC / RAID / USENIX | Medium | these expect either real adversarial deployment or distributed evidence; the single-host + simulation scope must be stated up front, and the security claims framed as reference-monitor properties, not deployed guarantees |

---

## Part-by-part closure

- **P1 Claims:** 16 claims / 11 reviewer concerns registered; E1–E12 map to artifacts. C1 (ULB accuracy) must read as *conformance*, not detection — disclosed.
- **P2 Paper consistency:** **no manuscript `.tex` is in the repo**; "the paper" is the claims registry + `PAPER_CLAIM_VALIDATION.md` + `docs/PAPER_TRACEABILITY.md`. Table/figure values trace to artifacts via `measurement_provenance_matrix.json` and `runtime_tables.json` (0 unresolved). A real manuscript, when written, must match these.
- **P3 Benchmark consistency:** dashboard = JSON = tables on spot checks (ULB AUROC, coverage, FPR). Wilson now consistent. AgentDojo artifacts conflict (R4).
- **P4 Independent validation:** blind runtime (E12) real; negative control present; replay independently verified (E2, `independent_replay_verifier: PASS`); AgentDojo (E7) **executed offline** — guard-side metric suite complete, verdict `PASS`, no LLM and no external API credential. Only agent-side Utility/TASR remain unmeasured (optional, local-Ollama-only).
- **P5 Reproducibility:** one command reproduces E1–E12 + figures/tables/dashboard; the gap is dataset-placement docs (R3, partly fixed).
- **P6 Hidden assumptions:** thresholds are unsupervised warmup quantiles (not magic numbers); label leakage in the mapped corpus is the key hidden assumption — **disclosed**; `archive/external_validation_legacy` is correctly quarantined.
- **P7 Statistics:** Wilson (fixed) + bootstrap + cluster-corrected FPR bound all computed; nothing estimated.
- **P8 Runtime:** latency/throughput/ledger/watchdog/revocation/clock all from measured execution (E11); no documentation-derived numbers.
- **P9 Security:** reference-monitor mediation, tamper/fork detection, hash-chain + Merkle ledger, revocation refusal all measured; framed as properties of the reference monitor, not a deployed system.
- **P10 Documentation:** README needs the dataset/E11/E12 additions (R3); consider a docs index (O2).
- **P11 Publication:** ready for IEEE Access/FGCS/TOSEM after R2–R4; security-venue submission needs explicit scope framing.

---

## Final verdict

## **B — Publication Ready After Minor Repairs**

No material or undisclosed scientific weakness remains. The one genuine statistical bug (R1) is
fixed. The historical headline risk (label-leaked detection) is closed by real blind detection (E12)
plus open disclosure. What remains is **documentation, reproducibility, and consistency**: experiment
count (R2), README dataset/E11–E12 instructions (R3), and AgentDojo end-to-end disclosure (R4) —
each with an exact fix, none requiring a benchmark number or an implementation change.

**Condition:** the eventual manuscript must adopt the repository's own disclosed framing — governance
authorization (not fraud classification), reference-monitor properties (not deployed security),
single-host measured evidence with clearly-labelled simulations (not distributed/production
evidence). If the paper text overclaims beyond what the artifacts show, the verdict drops to C; as
the repository stands and describes itself, it is B.
