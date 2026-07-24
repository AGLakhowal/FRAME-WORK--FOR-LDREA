# PROJECT CONSISTENCY AUDIT

**A cross-document scientific-consistency audit — not proofreading, not implementation.** Determines whether the entire repository tells **one coherent scientific story** before external review. No document modified, no code written, no redesign.

**Panel:** IEEE Access Associate Editor · Reviewer #2 · Formal-Methods Reviewer · Runtime-Systems Architect · Software-Verification Engineer · Standards-Committee Reviewer · Artifact-Evaluation Committee.

**Evidence base:** direct enumeration of every `*.md`/`*.txt` in the tree (excl. `.venv`), term-presence grep across all docs, and the JSON artifacts. Citations are `file:line` or `file` where a whole document is at issue.

---

## Executive Summary

The repository is **internally rigorous at the audit/engineering layer** but does **not yet tell one coherent scientific story**, for one structural reason and one transitional reason.

- **Structural:** the three top authorities in the stated hierarchy — **IEEE Paper (L1), FULL_SPEC (L2), Execution Integrity (L3)** — **are not present as artifacts in the repository.** The paper is an external IEEE Access/Zenodo reference (`README.md:64-65`), `FULL_SPEC.md` is *referenced* (`README.md:136,319`) but **no such file exists** (only the implementation `full_spec_conformance.py`), and there is **no "Execution Integrity" document at all** (the term appears only in four secondary AgentDojo docs). Every terminology/claim "owned" by L1–L3 is therefore **unverifiable from within the artifact**.
- **Transitional:** the repo currently contains **both** the flawed original artifacts **and** the corrective audit chain that refutes them, **without cross-references between them.** The tautology headlines, `COMPLIANT_PASS`, and the fabricated `external_validation/` harness still stand in README and the design docs, while `IMPLEMENTATION_AUDIT_REPORT.md`, `AUDIT_VERIFICATION_REPORT.md`, and `FINAL_FORENSIC_AUTHORIZATION_AUDIT.md` document them as defects. A reviewer reading top-down sees **two contradictory stories** because the corrective documents are recommendations not yet applied.

Neither problem is fatal — the science (Γ, LLC, SAFE_STATE) is stable and the audit chain is honest — but the project is **not ready for external review** until (a) L1–L3 are placed in (or authoritatively linked from) the artifact and (b) the superseded artifacts are marked as such.

### Overall Score: **63 / 100**

Breakdown: terminology stability **+**, engineering discipline **+**, audit honesty **+**; missing in-repo authorities **−−**, coexisting contradictory headline claims **−−**, two competing AgentDojo narratives **−**, new concepts (RCL/EEB) not yet reflected in README/paper **−**.

---

## Critical Issues (must fix before implementation continues)

**CR-1 — The top three authorities are absent from the artifact.**
The hierarchy declares IEEE Paper, FULL_SPEC, and Execution Integrity as owning all science, semantics, and benchmark structure — yet none exists in-repo. `README.md:136` and `:319` reference `FULL_SPEC.md`; there is no such file. `README.md:64-65` cites the paper as an external IEEE Access 2026 work. "Execution Integrity" has no owning document. **Consequence:** the artifact cannot be checked against its own authorities; every `§V-B`/`Def. 2`/`Theorem T0–T9` citation across the engineering docs points outside the repository. **Required:** include (or immutably link, with hashes) the paper, FULL_SPEC, and an Execution Integrity document in the artifact.

**CR-2 — Contradictory headline claims coexist with their own refutations.**
`README.md:778` states the suite reaches **`COMPLIANT_PASS`**, while `IMPLEMENTATION_AUDIT_REPORT.md §9` shows the emitted `concurbench_full_report.json` reports **`INTERNAL_PASS`** (L4 `audit_packet_export=FAIL`). README even self-qualifies "(scope: internal + *simulated*-fleet)" in the same line — an internal contradiction. Likewise the tautology headlines (100% agreement, FPR 0/492) stand in README/reports while `AUDIT_VERIFICATION_REPORT.md` proves them tautological. **Required:** reconcile the headline word to the artifact's actual verdict and mark tautological figures as wiring/consistency checks (both already recommended, not applied).

**CR-3 — A rejected, fabricated subsystem is still documented as real.**
`external_validation/` is classified **DELETE (fabricated competing engine)** by `FINAL_FORENSIC_AUTHORIZATION_AUDIT.md` and `AUTHORIZATION_ENGINE_CLASSIFICATION.md`, yet its three design docs (`external_validation/AGENTDOJO_DESIGN.md`, `REAL_AGENTDOJO_DESIGN.md`, `MIGRATION_REPORT.md`) carry **no deprecation/superseded notice** (grep for `deprecat|reject|superseded|synthetic|fabricat` → none). Only `agentdojo_integration/TRACEABILITY.md:26` calls it "(historical)". **Required:** mark the `external_validation/*` docs superseded, or a reviewer will read `REAL_AGENTDOJO_DESIGN.md` as the live design.

---

## Major Issues (fix before IEEE resubmission)

**MJ-1 — Two competing AgentDojo integration narratives.**
Root-level `AGENTDOJO_LDREA_EXTERNAL_VALIDATION_DESIGN.md` + `_V2.md` + `AGENTDOJO_LDREA_SCIENTIFIC_CONSISTENCY_VERIFICATION.md` describe one AgentDojo story; `agentdojo_integration/` (the accepted Phase 3A) is another; `external_validation/` is a third (rejected). Five documents define "Externally Effective Action" across these strands. The accepted one is `agentdojo_integration/`, but nothing at the top level says so. **Effect:** architectural drift — the reader cannot tell which AgentDojo design is authoritative.

**MJ-2 — Unresolved paper-number reconciliation (79 vs 97 AgentDojo tasks).**
`PHASE_3A_CERTIFICATION.md:109` flags that paper §IX-F referred to "79" tasks while the pinned `v0.1.35` subset yields 97, and marks it `REQUIRED_PAPER_ACTION`. Honest disclosure, but an **open empirical-claim discrepancy** between paper and artifact that must be closed before resubmission.

**MJ-3 — README internal metric tension (78.4% vs 65–70%/85–92%).**
`README.md:608` narrates "enrichment ~65–70% / production ~85–92%" while `:794` reports the actual run at **≈78.4%**. Framed as different scenarios, but presented adjacently without a clear "current vs hypothetical" delimiter — reads as inconsistent (also logged as `IMPLEMENTATION_AUDIT_REPORT.md C-9`).

**MJ-4 — "Formal verification" language vs attested TLC.**
README §12.1 presents TLC "model-check verification (tiered)"; `AUDIT_VERIFICATION_REPORT.md Finding 2` proves the default run is **tier-0 attestation** (TLC not executed). The tiering *is* disclosed, but the section heading risks reading as executed formal verification. Align the heading with the tier-0 reality.

---

## Minor Issues (editorial consistency)

- **MN-1 — Hyphenation drift:** `Gamma G‑0` uses a non-breaking hyphen (U+2011) in `README.md:1` vs ASCII `Gamma G-0` elsewhere. Cosmetic but breaks exact-string search.
- **MN-2 — `Γ` vs `Gamma` vs `Gamma_G`** used interchangeably across docs; meaning identical, glyph inconsistent. Acceptable but worth a notation note.
- **MN-3 — "Law of Concurrence" vs "LLC" vs "non-compensatory aggregation"** — three names for one construct; all consistent in meaning, but no single doc defines the aliases together.

---

## Strengths

- **Terminology meaning is stable.** Across 15+ docs, `Gamma/Γ`, `SAFE_STATE`, `Evidence Quad`, `Hydra Ledger`, `Execution/Runtime Sovereignty`, `LUIPM`, `ConcurBench`, `LAB v1.0` are used with **consistent meaning and scope** (only glyph/hyphen drift, MN-1/2). No document redefines another's *meaning*.
- **The audit chain is honest and self-consistent.** `IMPLEMENTATION_AUDIT_REPORT` → `AUDIT_VERIFICATION_REPORT` → `FINAL_FORENSIC_AUTHORIZATION_AUDIT` → `AUTHORIZATION_ENGINE_CLASSIFICATION` → `ENGINEERING_MIGRATION_ROADMAP` form a coherent, cross-referenced corrective narrative.
- **`PHASE_3A_CERTIFICATION.md` is exemplary:** it certifies what did **not** change (byte-level), discloses Tier-S scope, and self-flags the 79/97 discrepancy — model artifact-evaluation discipline.
- **`agentdojo_integration/` preserves the frozen science:** reuses `evaluate_decision`, Merkle-frozen manifests, no monkey-patching (certified by inspection).

---

## Terminology Matrix

| Term | Canonical owner | Owner in repo? | Docs using it | Wording | Meaning | Scope |
|---|---|---|---|---|---|---|
| Gamma / Γ / Gamma G-0 | IEEE Paper (L1) | **NO (external)** | README + 14 docs | glyph drift (MN-1/2) | **identical** | identical |
| L-DREA | IEEE Paper | NO | most docs | identical | identical | identical |
| LUIPM | IEEE Paper | NO | 7 docs | identical | identical | identical |
| SAFE_STATE | IEEE Paper / FULL_SPEC | NO | all | identical | identical | identical |
| Externally Effective Action | IEEE Paper | NO | 5 docs (mostly AgentDojo strands) | identical | identical | identical |
| Execution / Runtime Sovereignty | IEEE Paper | NO | 8 docs | identical | identical | identical |
| Evidence Quad | IEEE Paper / FULL_SPEC | NO | 12 docs | identical | identical | identical |
| Hydra Ledger | IEEE Paper / FULL_SPEC | NO | 12 docs | identical | identical | identical |
| Law of Concurrence / LLC | IEEE Paper | NO | README, audits | 3 aliases (MN-3) | identical | identical |
| Execution Integrity | **Execution Integrity doc (L3)** | **NO — doc absent** | 4 secondary docs | inconsistent (no anchor) | **unanchored** | unverifiable |
| ConcurBench / LAB v1.0 / ASB | Execution Integrity (L3) | **NO — owner absent** | 15 / 9 / several | identical | identical | identical |
| Runtime Context Layer | Engineering (L5) | YES (5 eng docs) | RCL/arch/roadmap/traceability | identical | identical (engineering) | **new; not in L1–L4** |
| Execution Evidence Bundle | Engineering (L5) | YES (3 eng docs) | EEB/roadmap/traceability | identical | identical (engineering) | **new; not in L1–L4** |
| Permit-to-Act | IEEE Paper | NO | 1 doc only | identical | identical | under-propagated |

**Finding:** meaning is consistent everywhere; the failures are **owner-absence** (L1–L3 not in repo) and **two new engineering terms** (RCL/EEB) that have no upstream anchor because they are new proposals.

---

## Ownership Matrix (does any doc define what it does not own?)

| Concept | Rightful owner | Defined/redefined by | Verdict |
|---|---|---|---|
| Gamma / Γ semantics | IEEE Paper | engineering docs **reuse, never redefine** (explicit "frozen" language) | **OK** |
| Predicate semantics | IEEE Paper / FULL_SPEC | RCL/EEB specs **expose, never redefine** | **OK** |
| Runtime semantics | FULL_SPEC | `full_spec_conformance.py` **implements** §7.1; RCL spec cites, doesn't redefine | **OK** |
| Benchmark hierarchy (Execution Integrity) | Execution Integrity doc | **no owning doc exists**; ConcurBench/LAB/ASB used by many | **GAP (CR-1)** |
| "COMPLIANT_PASS" verdict | Execution Integrity / artifact | **README asserts a stronger verdict than the artifact emits** | **VIOLATION (CR-2)** |
| AgentDojo integration design | IEEE Paper §IX-F | three parallel design strands, one rejected-but-unmarked | **DRIFT (MJ-1, CR-3)** |
| RCL / EEB | Engineering (L5) — permitted | engineering docs only; classified "pure engineering" | **OK by rule** (but see Implementation Matrix) |

No engineering document redefines a paper/FULL_SPEC construct's *meaning* — the discipline held. The ownership failures are **absence** (no Execution Integrity doc) and **overclaim** (README verdict), not redefinition.

---

## Reviewer Coverage Matrix (Reviewer-2 concerns)

| Concern | Answered by | Consistent? | Weakened by implementation docs? |
|---|---|---|---|
| Proof dependency (theorems proved elsewhere) | `README.md:823`, `PHASE_3A` ("proved in Paper A, not here") | Yes | No |
| Mechanization / TLC | README §12.1; `AUDIT_VERIFICATION_REPORT` Finding 2 | **Partly** — heading vs tier-0 (MJ-4) | Heading overstates |
| Construct validity (tautology) | `AUDIT_VERIFICATION_REPORT`, `PREDICATE_GENERATION_REDESIGN` | Yes (in audits) | **README still shows tautological headlines** (CR-2) |
| Self-evaluation bias | `PHASE_3A`, `RUNTIME_EVIDENCE_ARCHITECTURE` | Yes | No |
| AgentDojo | `agentdojo_integration/TRACEABILITY.md`, `PHASE_3A` | **Partly** — 3 strands (MJ-1); 79/97 open (MJ-2) | external_validation unmarked (CR-3) |
| AgentHarm | `IMPLEMENTATION_AUDIT_REPORT` ("correctly not_run") | Yes | No |
| Threat model / limitations | `stress_test.py` honest_limits; audits | Yes | No |
| Benchmark scope | Execution Integrity **(owner absent)**; README §8 | **Gap** (CR-1) | n/a |
| External validation | classified fabricated (audits) | Yes in audits | **live docs still present** (CR-3) |

---

## Architecture Matrix (do arch docs preserve the frozen constructs?)

| Construct | RCL spec | EEB spec | Runtime-Evidence-Arch | Verdict |
|---|---|---|---|---|
| Gamma / Γ | reused, "frozen" | not touched | reused | **Preserved** |
| SAFE_STATE | exposed inputs only | no decision | preserved | **Preserved** |
| LUIPM / ISB | inputs exposed | transported | cited | **Preserved** |
| Execution/Runtime Sovereignty | invariant inputs only | replay contract | cited | **Preserved** |
| Evidence Quad / Hydra Ledger | reuse emitter | `prior_ledger_link` transport | reuse | **Preserved** |
| **New concepts introduced?** | RCL | EEB | RCL/ports | **Yes — but classified pure-engineering (see below)** |

The architecture docs **preserve every frozen construct** and repeatedly assert "no new scientific construct." The only additions are RCL/EEB, addressed next.

---

## Benchmark Matrix (Execution Integrity → ConcurBench → ASB → LAB v1.0)

| Hierarchy edge | Where stated | Preserved? | Notes |
|---|---|---|---|
| Execution Integrity is the top construct | **no owning doc** | **Unanchored (CR-1)** | term used in 4 docs, defined in none |
| ConcurBench under Execution Integrity | README §8, audits | Yes (usage) | consistent scope |
| ASB within ConcurBench | `concurbench_full.py:asb`, audits | Yes | consistent |
| LAB v1.0 as base benchmark | README §8, `gamma_test_runner` | Yes | consistent |
| Hierarchy reversed/weakened anywhere? | — | **No** | ordering consistent across docs |

The **ordering** is never reversed or weakened; the failure is the **missing owner document** for the top construct (CR-1), so the hierarchy is asserted but not authoritatively defined.

---

## Implementation Matrix (new concepts vs paper/FULL_SPEC/Execution Integrity)

| Concept | In paper/FULL_SPEC/EI? | Classification | Action needed |
|---|---|---|---|
| Runtime Context Layer | **No** | **Pure engineering** (exposes evidence L1 already assumes: freshness §V-B, ordering §V-F/I5) | README/paper pointer note; **no science change** |
| Execution Evidence Bundle | **No** | **Pure engineering** (transport contract; mirrors Evidence-Quad discipline) | same |
| Authority/Governance/Policy Ports | **No** | **Pure engineering** (read-only exposure) | same |
| Predicate Evaluator | Partially (Def. 1/2 predicate vector) | **Already implied** | none |
| Transaction Interpreter | **No** | **Pure engineering** (plane-A reader) | same |
| Runtime Evidence Architecture (the 5-plane model) | **No** | **Already implied** (planes restate where paper assumes evidence originates) | document as engineering framing |

**None of the new concepts is scientific drift** — each is classified pure-engineering by its own spec and adds no predicate/threshold/theorem. The residual risk is **traceability, not science**: these names exist only from L5 downward (next matrix).

---

## Cross-Document Traceability Matrix

Chain: **Paper (L1) → FULL_SPEC (L2) → Execution Integrity (L3) → README (L4) → Engineering (L5) → Code.**

| Concept | L1 | L2 | L3 | L4 README | L5 Eng | Code | Break point |
|---|---|---|---|---|---|---|---|
| Γ / SAFE_STATE / LLC | ext | ext | — | ✓ | ✓ | ✓ `gamma_test_runner.py:133,868` | **L1–L3 not in repo (CR-1)** |
| Evidence Quad / Hydra Ledger | ext | ext | — | ✓ | ✓ | ✓ `:635,1099` | L1–L2 not in repo |
| ConcurBench / LAB / ASB | ext | — | **absent** | ✓ | ✓ | ✓ | **L3 owner absent (CR-1)** |
| Runtime Context Layer | — | — | — | **✗** | ✓ | (not yet coded) | **exists only L5+; no L4 anchor** |
| Execution Evidence Bundle | — | — | — | **✗** | ✓ | (not yet coded) | **exists only L5+** |
| external_validation harness | — | — | — | (implied) | classified DELETE | present in code | **live code contradicts L5 audit (CR-3)** |
| COMPLIANT_PASS verdict | — | — | ? | **README asserts** | audit refutes | code emits INTERNAL_PASS | **L4↔code contradiction (CR-2)** |

**Concepts existing only in code / only in engineering docs (flagged):** RCL, EEB, ports, Transaction Interpreter — all L5-only, no upward anchor (expected for new proposals, but must be noted in README before they are implemented). No construct exists *only in code* without an engineering-doc home.

---

## Final Certification

**1. Does the repository tell one coherent scientific story? — NO.**
The science (Γ/LLC/SAFE_STATE) is coherent, but the *artifact as a whole* tells two overlapping stories: the original (flawed) headline claims and the corrective audit chain, coexisting without cross-references, atop three authorities (paper/FULL_SPEC/Execution Integrity) that are not in the repository.

**2. Could an IEEE reviewer identify contradictions? — YES.** Enumerated:
- README `COMPLIANT_PASS` (`:778`) vs artifact `INTERNAL_PASS` (`concurbench_full_report.json`; `IMPLEMENTATION_AUDIT_REPORT §9`). [CR-2]
- Tautological 100%/FPR-0 headlines vs `AUDIT_VERIFICATION_REPORT` proof of tautology. [CR-2]
- `external_validation/*` design docs present live vs classified DELETE/fabricated. [CR-3]
- README 78.4% (`:794`) vs 65–70%/85–92% (`:608`). [MJ-3]
- TLC "verification" heading vs tier-0 attestation. [MJ-4]
- Paper "79" vs pinned "97" AgentDojo tasks. [MJ-2]

**3. Could an independent engineer implement without scientific decisions? — NO (for the credit-card arm).**
The `ENGINEERING_MIGRATION_ROADMAP` is executable for all science-neutral commits, but the methodology-flip (commit 5.2) and five owner rulings (`IMPLEMENTATION_TRACEABILITY_SPECIFICATION §10`) remain open scientific decisions. Pure-engineering commits (0.1–5.1, 6.x): **YES**.

**4. Does any document redefine another document's authority? — NO (redefinition), YES (overclaim).**
No engineering doc redefines a paper/FULL_SPEC construct's meaning (discipline held). But README **overclaims a verdict** (COMPLIANT_PASS) the artifact does not emit, which usurps the artifact's authority over its own result. [CR-2]

**5. Are there hidden terminology inconsistencies? — YES (minor).**
Glyph/hyphen drift (`Gamma G‑0` U+2011 vs ASCII; `Γ`/`Gamma`/`Gamma_G`), and three un-unified aliases for the Law of Concurrence. Meaning is consistent; only surface strings drift. [MN-1/2/3]

---

### Readiness verdict

**NOT READY for external review.** The blocking items are **CR-1** (place/link the three missing authorities in the artifact), **CR-2** (reconcile the headline verdict and tautology framing to the artifact's actual output), and **CR-3** (mark the rejected `external_validation/*` docs superseded). Once CR-1–CR-3 are resolved and MJ-1–MJ-4 addressed, the repository's stable terminology, disciplined audit chain, and preserved frozen constructs position it well for resubmission. The corrective plan already exists in-repo; it simply has not been applied to the top-level narrative.

---

*Consistency audit only. No document modified, no code written, no redesign. All citations are `file:line` from the current working tree; where an authority is external (paper/FULL_SPEC/Execution Integrity) that absence is itself the finding (CR-1).*
