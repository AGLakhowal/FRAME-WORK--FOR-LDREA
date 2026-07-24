# FINAL SCIENTIFIC AUDIT — COMMITTEE REPORT (Pre-Submission, IEEE Access)

**Panel:** Associate Editor · Transactions Reviewer · Formal-Methods Researcher · Runtime-Verification
Researcher · Reproducibility Auditor · Artifact-Evaluation Member · Independent-Verification Expert.
**Stance:** assume nothing; trust nothing; every statement is grounded in a repository artifact
inspected on 2026-07-09. Where the repository cannot support a claim, this report says so explicitly.
**Read-only.** No project code, math, or experiment was created or modified for this audit.

---

## 0. Two facts that frame the entire audit

**F1 — The paper itself is not in the repository.** A search for `*.tex / *.pdf / *paper*.md / *.docx`
returns only `PAPER_NUMBER_AUDIT.md`. Therefore Parts 2–4 ("Paper Definition → Equation → …") **cannot
be audited against the paper as a primary artifact.** They can only be audited against the paper's
*proxies* in-repo (README §7/§8, `full_spec_conformance.py`, the frozen manifests). Any claim of
"paper ↔ code identity" is, at best, "code ↔ README-encoded-spec identity." This is stated once here
and inherited by every part below.

**F2 — Only 23 files are under version control.** `git ls-files` = 23 tracked files (the original
Gamma runner + JSON reports + README). The entire `agentdojo_integration/` tree, `runtime_context/`,
`tests/`, the interception layer, **and the new `independent_verifier.py`** are **untracked working-tree
files.** The dataset (`GAMMA_G0_CREDITCARD_FULL_mapped.csv`, 451 MB) and `gamma_replay_manifest.jsonl`
(200 MB) are **not tracked and not in Git-LFS.** An artifact-evaluation committee clones the repo and
gets *none* of the verification apparatus this audit depends on.

Neither F1 nor F2 is a math error. Both are hard publication/reproducibility blockers. They dominate
the scoring.

---

## PART 1 — Scientific Gap Analysis (does the verifier close the gaps?)

The independent verifier (65,536 states, IDENTICAL, 0 mismatch — re-executed this session, exit 0)
is **real and strong for what it covers**, but it covers **only `evaluate_decision`**. It does not
touch the AgentDojo external-validation gaps. Mapping the standing concerns:

| # | Reviewer concern | Current evidence | Artifact | Remaining weakness | Verdict |
|---|---|---|---|---|---|
| G1 | Decision logic matches the specified equations | Exhaustive 2¹⁶ enumeration, 0/7-field mismatch | `independent_verifier_report.json` | Verifies code↔README-spec, **not** code↔paper (F1); abstracts HARM to 1 bit, ReasonCodes to 1 bit (see Part 7) | **FULLY RESOLVED** (internal consistency of the decision core) |
| G2 | Non-compensatory safety (no permit under deficit) | 0 states with Π=1 ∧ Γ>0 over full space | `STATE_SPACE_VERIFICATION.md` | none for the core | **FULLY RESOLVED** |
| G3 | Determinism / replay determinism | pure-fn (1000× identical); 284,807/284,807 chain links OK | `gamma_summary.json` | replay is empirical on one corpus, not exhaustive | **FULLY RESOLVED** (decision) / **PARTIALLY** (chain, empirical) |
| G4 | AgentDojo integration actually runs | 33 episodes, 14 decisions, artifacts present | `audit_run/summary/statistics.json` | weak local model; n=14 | **PARTIALLY RESOLVED** |
| G5 | **False-permit soundness under attack** | **FPR undefined, n=0 malicious actions adjudicated** | `fpr_fdr.json` (`malicious_actions: 0`) | **the monitor was never made to block a real attacker-targeted EEA in the external benchmark** | **NOT RESOLVED** |
| G6 | Statistical honesty (no cherry-picking) | frozen stats engine; 21 unit tests claimed; Wilson CIs | `statistics.json`, `REVIEWER_CLOSURE_REPORT.md` | tests untracked (F2) | **PARTIALLY RESOLVED** |
| G7 | Runtime-layer enforcement of commit-before-actuate | measured as a trace invariant (0 inversions) | `gamma_summary.json` | **not enforced at `run_function`**; measured post-hoc only | **PARTIALLY RESOLVED** |
| G8 | Complete mediation / non-bypassability | unknown→SAFE_STATE (executed); Merkle tamper trips error | `governed_runtime.py`, executed | rests on AgentDojo routing assumption A1; architectural universality not machine-proven | **PARTIALLY RESOLVED** |
| G9 | Reproducibility by a third party | hash-pinned `uv` lock exists | `agentdojo_requirements.lock` | dataset + verifier + tests untracked (F2); no top-level requirements; two venvs; needs Ollama+model | **PARTIALLY RESOLVED** |

**The verifier fully closes the *formal decision-core* gaps and closes nothing on the *external
empirical soundness* gap (G5), which is the load-bearing claim of a runtime-authorization paper.**

---

## PART 2 — Mathematical Traceability Audit

Chain target: `Paper Def → Eq → Impl → Independent verifier → Runtime evidence → Replay → Figure/Table`.

| Construct | Paper Def | Eq | Impl | Indep. verifier | Runtime | Replay | Table/Fig | Broken link |
|---|---|---|---|---|---|---|---|---|
| Γ_G (max-aggregation) | §IV-B (README proxy) | `Γ_G=maxᵢdᵢ` | `:140-158` | ✔ 65,536 | ✔ 284,807 | ✔ manifest | Tbl (SAFE counts) | **Paper doc absent (F1)** |
| Γ_class (veto) | §IV-B | substring | `:157` | ✔ | ✔ (492 rows) | ✔ | class-veto 100% | **F1** |
| Π / decision | §VIII-B | `Π=[max=0]` | `:159,176` | ✔ | ✔ | ✔ | permit/safe | **F1** |
| ISB | §V-B | 4-way ∧ | `:160-165` | ✔ | ✔ | — | — | **F1** |
| Eq. 7 (unauthorized) | §VIII-C | 5-disjunct | vec `:977-987`; **single-row omits chain** | ✔ (single-row form only) | ✔ UER=0 | ✔ | UER | **single-row ≠ full Eq.7 (scope)**; F1 |
| Non-compensatory / Corollary 2 | Cor. 2 | weighted-sum control | `:1055-1070` | not covered | ✔ (0 false permits) | — | neg-control | verifier does not cover the control probe |
| Commit-before-actuate | §V-F | ordering | `:964-970` | not covered | ✔ (0 inversions) | — | TOCTOU | **no runtime-layer enforcement (G7)** |

**Fully traceable end-to-end (modulo F1): Γ_G, Γ_class, Π, ISB.** **Incompletely traceable:** Eq. 7
(single-row is a scope-restriction), Corollary 2 (outside verifier scope), commit-before-actuate
(measured, not enforced). Every row inherits the F1 caveat: the left-most column is a README proxy,
not the paper.

---

## PART 3 — Theorem Audit

The repo contains a TLC-log parser (`gamma_test_runner.py:_parse_tlc_log`) implying a TLA+ model
existed, **but no `.tla`/`.cfg` spec file is present in the repository** — so any "model-checked
theorem" claim is **NOT currently substantiable from repository artifacts.**

| Theorem/property | Formal statement | Impl | Indep. verified? | Experimental | Remaining assumption | Classification | Strength |
|---|---|---|---|---|---|---|---|
| T1 Non-compensatory soundness (I3) | ¬∃ Π=1 ∧ Γ>0 | `:159` | **Yes, exhaustive** | 0 false permits/284k | none (core) | **Mechanically verified** | Strong |
| T2 Determinism | pure fn | `:133-178` | Yes (1000×) + enumeration | — | none | **Mechanically verified** | Strong |
| T3 Class veto (I4) | class token ⇒ SAFE_STATE | `:157,159` | Yes | 492/492 fraud held | veto vocabulary complete (A3) | **Mechanically verified** (core) + **Experimentally validated** | Strong |
| T4 Eq. 7 execution integrity | no unauth externalization | vec `:977-987` | single-row only | UER=0/284k | corpus-specific | **Experimentally validated** | Moderate |
| T5 Complete mediation (Def 2i) | every EEA adjudicated | `governed_runtime.py:50-81` | No | executed branches | **A1 routing** | **Engineering claim** | Moderate |
| T6 Non-bypassability (I2) | no path avoids monitor | `:50,55-59` | No | tamper/unknown blocked | **A1**; architecture not model-checked | **Engineering claim** | Moderate |
| T7 Replay determinism | hash-chain linkage | `:954-958` | No | 284,807 links OK | one corpus | **Experimentally validated** | Moderate |
| T8 Commit-before-actuate | commit ≤ actuate | `:964-970` | No | 0 inversions | measured, not enforced (G7) | **Empirical observation** | Weak-Moderate |
| "Model-checked invariants" | TLC no-error | log parser only | — | **no spec in repo** | — | **Speculation until `.tla` is committed** | **Unsupported** |

No theorem is left ambiguous. **The one claim that must be downgraded outright** is any assertion of
formal model-checking: without a `.tla`/`.cfg` artifact it is **Speculation**, not a verified theorem.

---

## PART 4 — Equation Coverage

| Eq | Purpose | Code | Verifier cov. | Runtime | Replay | Status |
|---|---|---|---|---|---|---|
| E1 dᵢ=¬gᵢ | node deficit | `:142-145` | full | ✔ | ✔ | **Complete** |
| E2 d=max(0,m−θ) | threshold deficit | `:146-154` | **2 HARM values only** | ✔ | ✔ | **Partial** (numeric layer not exhaustive) |
| E3 Γ_G=max | aggregation | `:140,171` | full | ✔ | ✔ | **Complete** |
| E4 Γ_class | veto | `:157` | **2 ReasonCodes values only** | ✔ | ✔ | **Partial** (string-match layer not exhaustive) |
| E5 Π/decision | decision | `:159,176` | full | ✔ | ✔ | **Complete** |
| E6 ISB | sufficiency | `:160-165` | full | ✔ | — | **Complete** (no replay column) |
| E7 Eq.7 | unauthorized | `:166-169` / `:977-987` | single-row form | ✔ UER=0 | ✔ | **Partial** (single-row ≠ full Eq.7) |

**Publication gaps in equation coverage:** E2 and E4 are exhaustively verified only at the *boolean
abstraction* (`HARM>θ` collapsed to {0.0, 0.8}; ReasonCodes collapsed to {CLASS_1, NONE}). The
*arithmetic* of the threshold comparison and the *substring/lowercase parsing* of ReasonCodes are
**not** exhaustively tested. A formal-methods reviewer will note "100 % state-space coverage" refers
to a 16-bit abstraction, not the raw input domain.

---

## PART 5 — Figure & Table Provenance

Spot-audited the headline values; each traces to a real artifact:

| Value | Claimed in | Traces to | Reproducible? |
|---|---|---|---|
| 284,315 PERMIT / 492 SAFE_STATE | README, IEEE tables | `gamma_summary.json` | **Yes** (re-derivable from CSV via `gamma_test_runner.py`, but CSV is untracked — F2) |
| Class-veto 100 % (492/492) | README | `gamma_summary.json` top_rule_failures | **Yes** |
| UER=0, 0 false permits | README, tables | `gamma_summary.json` | **Yes** |
| Permit 0.786 [0.524, 0.924] | Table 11 | `statistics.json` (n=14) | **Yes**, but n=14 |
| FPR (Table 11) | Table 11 | `fpr_fdr.json` | **Value is "undefined (n=0)"** — correctly reported as undefined, **not** as 0 |
| Overhead 0.0216 ms | Table 10/11 | `PERFORMANCE_RESULTS.json`, `runtime_profile.json` | **Yes** |

**Provenance is clean and honest** — notably, FPR is reported as *undefined*, not silently as 0.
**The one reproducibility flag is F2:** the raw 451 MB trace that underlies the flagship 284k numbers
is not in version control, so an external party cannot regenerate the primary table without obtaining
the dataset out-of-band.

---

## PART 6 — Documentation Audit

- **Stale references — CONFIRMED.** README maps §IV-B to `gamma_test_runner.py:407-434` and Eq. 7 to
  `:469-484`; those lines now hold `fmt_rate`, `derive_lab_class`, `_parse_tlc_log`. The real logic is
  `:133-178` and `:914-987`. **Broken citation, must fix.**
- **No single FULL_SPEC.** "FULL_SPEC.md" is cited across the codebase and this package but **no such
  file exists**; the spec is distributed. Terminology promises a document that isn't there.
- **Terminology sprawl / duplication.** ~75 top-level `.md` files, many overlapping (multiple
  "AUDIT", "TRACEABILITY", "SPECIFICATION", "VALIDATION" reports). Risk of *conflicting* terminology
  across them; an AE committee will struggle to find the canonical document.
- **Notation.** `Γ`, `Gamma_G`, `Γ_G`, `gamma_g`, `DerivedGammaG` all denote the same quantity across
  paper-proxy/code/reports — internally consistent but inconsistent in surface form.
- **Missing diagram:** no single architecture figure ties Layer-0→Layer-2→engine→evidence in the
  tracked docs (the new `IMPLEMENTATION_GRAPH.md` supplies one but is untracked).

Verdict: **extensive but not yet publication-clean.** Stale citations and the phantom FULL_SPEC are
concrete, must-fix documentation defects.

---

## PART 7 — Formal Verification Independence Audit

Direct inspection of `independent_verifier.py`:

- **Does it call implementation decision code?** For *reference answers*, **no** — `reference_decision()`
  re-derives Γ/Π/decision itself. It imports `gamma_test_runner.evaluate_decision` **only as an oracle**
  to compare against, and passes it a fresh `dict(row)` copy. ✔ genuinely separate control flow.
- **Does it reuse implementation constants?** **Partially — yes.** θ=0.5, `HARM_RISK∈{0.0,0.8}`, the
  `"CLASS_1"/"NONE"` tokens, and the gate list are hand-transcribed but *identical* to the
  implementation's. The gate list is cross-checked equal at runtime (good), but the numeric/string
  constants are shared.
- **Does it reuse implementation predicates?** No — the deficit/veto/Π logic is re-expressed.
- **Silent import of logic?** No.
- **Could implementation bugs propagate in?** No — a bug would surface as a mismatch (the whole point).
- **Could *paper/spec* errors propagate in?** **YES — this is the key limitation.** The verifier's
  reference equations were transcribed from the **same README** the implementation follows. If the
  README/paper equation is itself wrong, the verifier and the implementation agree on the wrong thing.
  The verifier proves **code ↔ spec consistency**, *not* **spec correctness**.
- **Coverage limitation:** it verifies `evaluate_decision` only — not `GammaBridge`, `PredicateEvaluator`,
  `ScientificPolicy`, or `run_function`. And it exhausts a 16-bit *abstraction*, not the raw domain
  (Part 4, E2/E4).

**Independence rating: STRONG (control-flow / decision-logic independence, exhaustive on the abstracted
core) but MODERATE as a check of specification correctness and MODERATE in scope.** Honest overall:
**Strong-for-what-it-covers; it is a consistency proof, not a correctness oracle, and it does not reach
the runtime path.**

---

## PART 8 — Reproducibility Audit

| Requirement | Present? | Note |
|---|---|---|
| Python version | Partial | lock says 3.11; running `.venv` is **3.9.6** — mismatch |
| Package versions (hashed) | **Yes** | `agentdojo_requirements.lock` (uv, `--generate-hashes`) — strong |
| Top-level `requirements.txt`/`pyproject` | **No** | none at repo root |
| Seeds | Not found | LLM temp=0 noted, but no RNG-seed artifact for bootstraps |
| Manifest hashes | **Yes** | scientific root `ce8c8467…`, binding `a3861927…` (verified) |
| Dataset | **No (in VCS)** | 451 MB CSV + 200 MB JSONL untracked; no LFS |
| AgentDojo version | **Yes** | `agentdojo==0.1.35` pinned |
| Model version | Partial | `llama3.1:8b` named; not content-hashed |
| Hardware | Partial | latency is host-specific; "not the paper's HIL figures" is stated |
| Environment | Partial | two separate venvs; provisioning record exists in manifests |
| Verifier + tests in VCS | **No** | untracked (F2) |

**Missing to enable third-party reproduction:** (1) commit the verification apparatus and tests;
(2) commit or LFS-host (or provide a fetch script + checksum for) the dataset; (3) a root
`requirements.txt`/`environment.yml` and a single reconciled Python version; (4) recorded bootstrap
seeds; (5) a content hash for the model. The cryptographic pinning that *does* exist is a genuine
strength.

---

## PART 9 — Scientific Integrity Audit (overclaim scan)

The in-repo prose is, on the whole, **unusually disciplined** — FPR is reported "undefined (n=0)",
GIL-bound throughput and content-layer scope are stated honestly. Words to police before submission:

| Wording | Where it's safe | Where it must be softened |
|---|---|---|
| "proves" / "proven" | the mechanized decision core (T1, T2) — **supported** | do **not** apply to mediation/non-bypassability (engineering claims, A1) |
| "100 % coverage" | the 16-bit abstraction — **must say so** | not the raw input domain (E2/E4) |
| "verified" | `evaluate_decision` — supported | not the runtime path or "the paper" (F1) |
| "guarantees" / "impossible" | avoid | soundness rests on A1 + corpus; an attack was never adversarially blocked externally (G5) |
| "FULL_SPEC-conformant" | conformance *script* passes | there is no FULL_SPEC *document* (Part 6) |
| "independent verification" | control-flow independent — supported | it is consistency, not spec-correctness (Part 7) |

No fabrication detected. The required edits are **scoping qualifiers**, not retractions.

---

## PART 10 — Publication Readiness Scores (/100)

| Dimension | Score | One-line justification |
|---|---:|---|
| Scientific novelty | 78 | Non-compensatory reference monitor at the execution boundary is a solid, publishable idea; not paradigm-shifting. |
| Formal rigor | 84 | Exhaustive mechanized decision core is strong; theorems T5–T8 are engineering/empirical, no committed model-checker spec. |
| Implementation quality | 86 | Clean layered DI, single-engine static guard, integrity-checked manifests. |
| Experimental rigor | 60 | 284k synthetic corpus strong; external validation n=14 with FPR n=0 is thin. |
| Independent validation | 80 | New verifier genuinely independent and exhaustive on the core; consistency-only, core-only. |
| Reviewer closure | 68 | 9/12 closed; G5/R8 (FPR) genuinely open; G7 measured-not-enforced. |
| Artifact quality | 64 | Rich artifacts, but verification apparatus + dataset untracked (F2). |
| Documentation | 66 | Comprehensive but stale citations, phantom FULL_SPEC, 75-file sprawl. |
| Reproducibility | 63 | Excellent dep-hashing undercut by untracked dataset/verifier, version mismatch, no root manifest. |
| **Overall publication readiness** | **72** | Formally excellent core; empirical-soundness and artifact-hygiene gaps hold it below the bar. |

---

## PART 11 — Final Remaining Gaps (genuine blockers only; cosmetics excluded)

**B1 — External soundness is untested (FPR n=0).** *Why it matters:* the paper's thesis is a monitor
that **denies unauthorized execution**; in the live external benchmark **no attacker-targeted EEA was
ever adjudicated**, so the deny-behavior was never exercised against a real attack. *How reviewers
attack it:* "Your soundness result is on a synthetic labeled corpus you generated; the one independent
benchmark produced zero positive test cases — you have not shown the monitor stops anything an attacker
would actually do." *Closing artifact:* re-run `run_audit.py` with a **stronger tool-calling model**
(hosted) and/or adversarial task selection so ≥1 attacker-targeted EEA reaches the gate and is denied;
report a real FPR with a CI. *Effort:* Medium (no code change; compute + a capable model). *Impact:*
**High — this is the difference between "feasibility demo" and "validated soundness."**

**B2 — Verification apparatus + dataset are not in version control (F2).** *Why:* an AE committee
clones 23 files and cannot run the verifier, the tests, or reproduce the 284k table. *Attack:* "Artifact
unavailable / not reproducible." *Closing artifact:* commit `independent_verifier.py`, `tests/`,
`agentdojo_integration/`, `runtime_context/`; LFS-host or provide a checksummed fetch script for the
dataset; add a root `requirements.txt`/`environment.yml`. *Effort:* Low. *Impact:* High for artifact
evaluation; blocks the "available/reproducible" badges.

**B3 — The paper is absent and paper↔code traceability is therefore unverifiable (F1).** *Why:* every
"matches the paper" claim is currently "matches the README." *Attack:* "Show the paper equation numbers
your code implements." *Closing artifact:* commit the paper (or a `FULL_SPEC.md` that is the single
normative source) and make the traceability tables cite it by equation number. *Effort:* Low. *Impact:*
Medium-High (unblocks Parts 2–4 as literal claims).

**B4 — "Formally model-checked" is unsubstantiated (no `.tla`/`.cfg`).** *Why:* a TLC log parser exists
but no spec. *Attack:* "Where is the TLA+ model?" *Closing artifact:* commit the `.tla`/`.cfg` + the TLC
log, or delete the model-checking claim. *Effort:* Low (if the spec exists) / Medium (if it must be
written — but writing new math is out of scope, so: **remove the claim** if the artifact can't be
produced). *Impact:* Medium (integrity).

Non-blockers deliberately excluded: file sprawl, notation surface-forms, dual venvs, the single-row
Eq. 7 scope note (already honestly documented).

---

## PART 12 — Final Verdict

> ## READY AFTER MINOR SCIENTIFIC ADDITIONS
>
> The **formal decision core is publication-strong**: `evaluate_decision` is mechanically and
> exhaustively verified against its specified equations (65,536 states, 0 mismatch), determinism and
> non-compensatory safety are proven, and the 284k-row synthetic corpus shows 0 false permits and 100 %
> class-veto with clean provenance and honest reporting. **What stands between this and submission is a
> small number of concrete additions, not a redesign:** (B1) exercise the monitor against at least one
> real attacker-targeted externally-effective action so the flagship FPR/soundness metric has a positive
> test case; (B2) place the verifier, tests, and dataset (or a checksummed fetch) under version control
> with a root dependency manifest; (B3) commit the paper / a single normative FULL_SPEC and cite it by
> equation number; (B4) either commit the TLA+ spec or drop the model-checking claim; plus the minor
> documentation fixes (stale README line citations, phantom FULL_SPEC reference).
>
> **Escalation clause (honest):** if the paper's *central contribution* is framed as *empirically
> validated real-world soundness via AgentDojo*, then B1 is load-bearing and the verdict escalates to
> **MAJOR SCIENTIFIC REVISION REQUIRED** until a non-zero attacker-targeted denominator exists. If
> AgentDojo is framed as an *integration-feasibility demonstration* and the soundness claim rests on the
> formal core + synthetic corpus (with the external result explicitly delimited), the **MINOR SCIENTIFIC
> ADDITIONS** verdict stands.

*No project code, mathematics, or experiment was created or modified in producing this audit. All
findings are reported; none were fixed.*
