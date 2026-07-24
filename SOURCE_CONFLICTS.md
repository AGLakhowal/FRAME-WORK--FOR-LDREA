# SOURCE_CONFLICTS.md

Conflicts, gaps and resolutions found while inventorying sources for the
**Gamma G-0 — Complete Runtime Governance Laboratory** application.

Authority order applied: **A** FULL_SPEC.md → **B** Paper A (LLC) → **C** Master Operating
Model → **D** executed artifacts → **E** README → **F** existing demo.

Nothing below was reconciled silently, and no value was invented to fill a gap.

---

## 1. Verified counts (resolved — artifacts agree with the engineering review)

Verified directly from artifacts before display, as instructed.

| Quantity | Expected by brief | Verified | Source of truth |
| --- | --- | --- | --- |
| Executed experiments | 13 | **13** | `experiments/_meta/run_index.json` → `experiments` (dict, len 13) |
| Claims | 17 | **17** | `evidence_manifest.json` → `claims` (list, len 17) |
| Reviewer concerns | 12 incl. extended | **12** | `reviewer_mapping.md` → R1–R11 + R6-ext |

Detail worth carrying into the UI, because a naive regex gets these wrong:

- Experiment IDs are **E1–E12 plus E5b** — *not* a contiguous E1–E13. `last_run_scope`
  is a 13-element list in the same file.
- Claim IDs are **C1–C9, C10, C10b, C11–C16**. A `\bC\d+\b` scan returns only 16 unique
  IDs because **C10b** is missed. The list length (17) is authoritative, not the ID scan.
- Reviewer IDs are **R1–R11 plus R6-ext**. A `\bR\d+\b` scan returns 11 and misses
  **R6-ext**, the combined-ablation interaction concern.

**Resolution:** the application must read these from the artifacts at build time and must
not hard-code 13 / 17 / 12.

---

## 2. Authority-A source absent — `FULL_SPEC.md` (BLOCKING for full fidelity)

`FULL_SPEC.md` is **not present anywhere in the repository**. It is the highest-authority
source and the brief assigns it ownership of canonical definitions, namespaces,
conformance semantics and architecture.

Directly affected, currently unsourceable at authority A:

- canonical Permit-to-Act state machine, including whether `HELD_PENDING_COMMIT` is a real
  state (the brief itself hedges: *"if that state is consistent with the authoritative spec"*);
- canonical ERTuple field list;
- canonical namespaces and conformance semantics;
- the normative definition of the CL0/CL1/CL2 enforcement classes;
- authoritative wording for the substrate tiers (Tier-H/T/S/D/X);
- canonical predicate-manifest schema.

**Resolution:** these areas will be rendered from authority **D** (executed artifacts) and
**C** (Master Operating Model, supplied as the three-plane figure) where they exist, and
otherwise marked **`NOT AVAILABLE — awaiting FULL_SPEC.md`** in the UI. They will *not* be
guessed. Supplying `FULL_SPEC.md` unblocks them.

---

## 3. Authority-B source absent — Paper A (LLC)

No document for **Paper A — The Lakhowal Law of Concurrence** exists in the repository.
Present are only *generators and outputs* that reference it:
`generate_paper_tables.py`, `generate_paper_figures.py`, `reproduce_paper.py`,
`paper_tables/`, `paper_figures/`, `PAPER_CLAIM_VALIDATION.md`, `docs/PAPER_TRACEABILITY.md`.

Directly affected:

- theorem statements and assumptions for **T0–T9**;
- the ASB-G topology names and their formal definitions (brief §23);
- the formal derivation chain LLC → G-0.

**Resolution:** theorem *names* T0 (Bridge Equivalence) … T9 (Concurrence Closure) are
taken from the brief and cross-checked against the TLA+ invariants that exist. Theorem
*statements, assumptions and proofs* are marked **`NOT AVAILABLE`** rather than
paraphrased. The ASB-G topology section will render only if Paper A is supplied.

---

## 4. Authority-C source absent as a file — Master Operating Model

The 28-stage model exists only as the diagram supplied in conversation, not as a
repository document. The stage list, three planes and stage ordering are reproduced from
that figure and are already implemented in `docs/demo/gamma-wire.html`.

**Resolution:** treated as authority C for stage identity and ordering. Per-stage *owner,
formal rule, related theorem and related master section* fields are **`NOT AVAILABLE`**
until the document is supplied.

---

## 5. `run_index.json` path differs from the brief

Brief lists `run_index.json` at top level. It is actually at
**`experiments/_meta/run_index.json`**. `evidence_manifest.json` confirms:
`"generated_from": "experiments/_meta/run_index.json + claims registry"`.

**Resolution:** no conflict of substance — path corrected. A root-level `run_index.json`
does not exist and must not be referenced.

---

## 6. CONFLICT — a stale artifact contradicts an executed experiment

Two artifacts describe the same blind-detection experiment and disagree:

| Artifact | Claim |
| --- | --- |
| `runtime_detection_report.json` (repo root) | `"status": "BLOCKED"`, `"evidence_level": "Not executed"`, *"raw ULB dataset not found at creditcard.csv"* |
| `production_evidence/datasets/dataset_eval_summary.json` | `"status": "EXECUTED"`, `"evidence_level": "Measured Runtime"`, ULB AUROC **0.9116** |
| `experiments/_meta/run_index.json` → E12 | `"status": "EXECUTED"`, 281.31 s, *"ULB raw features now present"* |

The raw file **is** present at `dataset/ieee-fraud-detection/creditcard.csv` — 150,828,752
bytes, 284,807 rows, 492 fraud — byte-identical to the size recorded in the E12 summary.
The BLOCKED report looks for it at repo root only.

**Resolution:** two artifacts of the same authority tier (D) disagree; the **more recent
and corroborated** pair (`run_index.json` + `dataset_eval_summary.json`) wins.
`runtime_detection_report.json` is **superseded** and must not be surfaced as a current
result. Recommend regenerating or deleting it. The application will show the conflict
explicitly in the Artifact Explorer rather than hiding the loser.

---

## 7. CONFLICT — E1's headline is conformance, not detection

`gamma_summary.json` reports a perfect result on the mapped credit-card corpus:
284,807 rows, 284,315 PERMIT, 492 SAFE_STATE, `match_status_rate 1.0`,
`false_permit_count 0`.

`label_leakage_audit.json` — a read-only audit of the same corpus — establishes that
**5 of the 12 inputs the engine reads are derived from the ground-truth label**:
`Gate_A3`, `Gate_A7`, `Lambda_G`, `HARM_RISK`, `ReasonCodes`. Each has value sets
**perfectly disjoint** across the two classes over all 284,807 rows, i.e. each alone is a
100 %-accurate classifier. `ReasonCodes` contains `CLASS_1_FRAUD` verbatim.

**Resolution:** not a contradiction but a *framing* conflict that prose could easily get
wrong. E1 is an **oracle-conformance** result and must be labelled as such everywhere it
appears. It must never be displayed as detection performance, and its 0-false-permit
figure must never be merged into a detection metric. The audit explicitly preserves E2
(replay), E3 (formal), E9 (coverage) and non-compensatory soundness as unaffected.

---

## 8. CONFLICT — E5b metric is not the R1/R8 authorization FPR

`reviewer_mapping.md` R6-ext states plainly: *"E5b reports blind-detection metrics —
URR/BFR — NOT the authorization FPR of R1/R8."*

**Resolution:** the metrics dashboard must keep **authorization FPR**, **blind-detection
metrics** and **fraud-classification metrics** in separate, non-summable groups, exactly as
brief §24 requires. The ablation laboratory must label E5b's axis as blind-detection
(URR/BFR), not authorization FPR.

---

## 9. Independent recomputation of E12 does not exactly reproduce the published run

Re-running the documented E12 procedure (first 75,000 rows, 25 % unlabeled warmup,
Q = 99.5, the five ULB predicates from `experiments/dataset_adapters.py`,
non-compensatory aggregation) against the byte-identical `creditcard.csv`:

| Metric | Published (E12) | Recomputed | Δ |
| --- | --- | --- | --- |
| precision | 0.1099 | 0.1101 | +0.0002 |
| F1 | 0.1941 | 0.1938 | −0.0003 |
| recall | 0.8296 | **0.8100** | **−0.0196** |

Precision and F1 agree to ~2e-4. Recall differs materially: the recomputation finds
**100** fraud rows in the post-warmup scored partition; the published precision/recall pair
implies **112 / 135**.

**Resolution:** unresolved. Both figures are retained and shown side by side in the
Real-Dataset Run page rather than averaged or silently corrected. This is a genuine open
item — the partitioning in the recorded run appears to differ from what the current code
does. It does not change the qualitative finding (strong separability, weak precision at
low prevalence), but it should be reconciled before external review.

---

## 10. TLA+ result is bounded — must be labelled as such

From `evaluation_package/formal/tlc_output.log` (2026-07-09):

- **1,340,006** states generated, **40,192** distinct, **0** left on queue
- complete state-graph depth **6**
- **"Model checking completed. No error has been found."**
- fingerprint-collision probability: 2.8e-9 optimistic / 2.1e-11 actual

Invariants checked (`formal/ExternalizationMonitor.cfg`): `ExecutionSovereignty`,
`NonBypassability`, `StructuralInvariant`. Constants: `Tokens = {t1,t2,t3}`,
`Epochs = {e1,e2}`, `ClassMetrics = {c1,c2}`, `NodeMetrics = {n1,n2,n3}`,
`MaxClockSkew = 1`.

**Resolution:** display as **"mechanically verified within the declared bounded model"**
with the constants visible. Never as exhaustive proof of unbounded production behaviour.

---

## 11. README is authority E and is stale in places

`README.md` (157 KB) carries result tables that duplicate artifact values. Where README and
artifacts disagree, **artifacts win** per the authority order. One live example: README
cites `datasets/ulb_eval.json` as the source for ULB AUROC 0.912, but that path does not
exist — the value lives in `production_evidence/datasets/dataset_eval_summary.json`.

**Resolution:** the application reads all numbers from artifacts. README is used only for
narrative navigation, never as a numeric source.

---

## Open items requiring input

1. Supply **FULL_SPEC.md** — unblocks canonical Permit state machine, ERTuple schema,
   CL0/CL1/CL2 semantics, namespaces, manifest schema.
2. Supply **Paper A** — unblocks T0–T9 statements/assumptions and the ASB-G topologies.
3. Supply the **Master Operating Model** as a document — unblocks per-stage owner, formal
   rule and theorem linkage.
4. Decide the fate of **`runtime_detection_report.json`** (regenerate or delete).
5. Reconcile the **E12 recall discrepancy** in §9.
