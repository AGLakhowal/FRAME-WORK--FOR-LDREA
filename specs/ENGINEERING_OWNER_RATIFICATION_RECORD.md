# ENGINEERING OWNER RATIFICATION DECISION RECORD

**Engineering governance record only. No code, no repository modification, no scientific-specification change, no implementation, no redesign.** This document captures the owner's ratification of the three engineering serialization conventions that `ENGINEERING_SERIALIZATION_CONTRACT.md` identified as not freezable verbatim. It records the current implementation, why automatic reuse is not permitted, why owner approval is required, the constraints each decision must respect, and the decision to be approved. **The decision fields are intentionally left blank for the owner to complete.**

**Roles:** Principal Software Architect · Engineering Governance Lead · IEEE Artifact Engineer.

**Governing source:** `ENGINEERING_SERIALIZATION_CONTRACT.md` (approved) — items **C7**, **C8**, **C9**. This record introduces no new science, no policy, and no architecture; it ratifies engineering conventions only.

---

## 1. Executive Summary

The Engineering Serialization Contract froze the majority of the Class-blind Reported Artifact Emitter's serialization surface verbatim (primitives, `ProposalID`, `PermitTokenID`, `SubjectProfileID`, `ERTuple_ID`, timestamp derivation, commit offset, ledger canon composition, and the hash algorithm). Three conventions **could not** be frozen automatically and are escalated here for owner ratification:

1. **Actuation emission gate (C7)** — the actuate-timestamp *offset* is Class-blind, but its *emission gate* is currently keyed on `Class` and must be re-sourced from the frozen decision.
2. **EnvironmentContext (C8)** — a reported field that **leaks `Class`**; its Class-blind replacement content is undefined.
3. **Structural constants (C9)** — copied from a `Class`-selected template row whose Class-invariance is **unconfirmed** (the template file is absent from the repository) and whose sourcing must be re-anchored to a Class-independent origin.

None of the three is science, policy, or architecture. Each is a deterministic engineering convention whose reuse would silently inherit a `Class`-keyed decision, a `Class` leak, or an unverified assumption — which is why explicit owner ratification is required before the emitter may be implemented. Upon ratification, the emitter becomes pure engineering to a fully frozen serialization contract.

---

## 2. Scope

**In scope:** owner ratification of the three engineering conventions C7, C8, C9, each constrained by the frozen architecture, replay determinism, and Class-blindness.

**Out of scope (explicitly):** any new scientific methodology; any change to `evaluate_decision`, Γ, SAFE_STATE, Predicate Binding, or the frozen specifications; the signed *reported metric change* and *replay/ledger rebaseline* (those belong to Commit 5.2 activation, not to this record); the emitter implementation itself (a later commit, gated on this record).

**Effect of ratification:** completes the Engineering Serialization Contract so the Class-blind emitter can be implemented as flag-OFF/parallel scaffolding without inventing any convention. Ratification does **not** authorize activation (5.2) and does **not** change any reported artifact.

---

## 3. Ratification sections

### Section 1 — Actuation emission gate (Contract item C7)

- **Current implementation.** The actuate-timestamp offset is a fixed constant — `actuate_ts = base_ts + timedelta(milliseconds=25)` (`gamma_map_raw:143`). The **emission** of `ActuateTimestamp` is currently `Class`-branched: the legit branch writes `iso_ms(actuate_ts)`, the fraud branch writes `""` (`gamma_map_raw:164, 180`). The presence/absence of an actuate timestamp is therefore keyed on `is_fraud = (Class == 1)`.
- **Why automatic reuse is not permitted.** Reusing the branch verbatim would carry a **`Class`-keyed gate** into the Class-blind emitter — the presence of an actuation record would still be a function of the ground-truth label, violating Class-blindness. The offset may be reused; the **gate** may not.
- **Why owner approval is required.** The correct source of "was this actuated?" is the **frozen decision** (actuated ⇔ PERMIT; not actuated ⇔ SAFE_STATE), not the label. Re-sourcing the gate is mechanical, but changes *what determines* a reported field and must be explicitly ratified as decision-driven, not `Class`-driven, so no reviewer can later mistake it for a silent behavioural change.
- **Constraints imposed by the frozen architecture.** The offset encodes commit-before-actuate ordering (**Invariant I5**); it must be **reused, not re-chosen**. Actuation is a *post-observation* fact (Predicate Binding Invariants; Gap 1), non-material to Γ/Π; the gate must record it, never compute a decision from it.
- **Constraints imposed by replay determinism.** The gate must be a pure function of the frozen decision + injected time; identical inputs → identical emission; no wall clock, no randomness (DET1). `CommitTimestamp`/`ActuateTimestamp` are reported ordering facts and must reproduce byte-identically.
- **Constraints imposed by Class blindness.** The emission gate must read **no** `Class` field/value/derivative; the only admissible determinant is the frozen engine's decision outcome.
- **Decision to be approved by the owner.** Ratify that the actuate-timestamp **offset (+25ms) is frozen verbatim**, and that the **emission gate is re-sourced from the frozen decision** (actuated ⇔ PERMIT), with **no** dependence on `Class`.

  **OWNER DECISION:** ______________________________________________

---

### Section 2 — EnvironmentContext (Contract item C8)

- **Current implementation.** A `;`-delimited reported provenance string (`gamma_map_raw:140-143`) with five tokens: (1) `ULB_2013_EU_CARD` (fixed dataset/region tag), (2) `source_time_sec={int(t_sec)}` (plane-A observable `Time`), (3) `amount={amount:g}` (plane-A observable `Amount`), (4) **`class={classes[i]}`** (the ground-truth `Class` label), (5) `source=anonymized_PCA` (fixed provenance tag).
- **Why automatic reuse is not permitted.** Token (4) embeds the ground-truth label verbatim into a **reported artifact column**, a direct `Class` leak. Reusing the field as-is would defeat Class-blindness and contaminate every downstream consumer of the reported trace. It cannot be frozen verbatim.
- **Why owner approval is required.** The field must be modified, and the **Class-blind replacement content is not specified by any frozen source**. What the field should contain after the `class=` token is removed is an owner **authoring decision** (this record and the contract deliberately propose **no** replacement).
- **Constraints imposed by the frozen architecture.** `Class` has no field and enters only at Ground-Truth Evaluation (EEB §9; RCL §8). The field is provenance/serialization only — it must assert **no** decision, policy, or predicate value; tokens (1),(2),(3),(5) are already admissible (constants + plane-A observables).
- **Constraints imposed by replay determinism.** The replacement must be a pure, deterministic function of Class-blind inputs (constants + observables); identical inputs → identical string (DET1). `EnvironmentContext` is **not** part of the ledger canon, so it does not affect the hash chain, but it must still reproduce byte-identically for trace reproduction.
- **Constraints imposed by Class blindness.** The `class={…}` token (token 4) must be **removed**, not re-encoded; the replacement must read/embed no `Class` field, value, or derivative.
- **Decision to be approved by the owner.** Ratify that the `class={classes[i]}` token is **removed**, that the Class-blind replacement content satisfies the constraints above (Class-blind, deterministic, replay-stable, provenance-faithful), and provide/authorize the **owner-defined replacement content** for the field.

  **OWNER DECISION:** ______________________________________________

---

### Section 3 — Structural constants (Contract item C9)

- **Current implementation.** Schema constants (`PolicyHash`, `SpecVersion`, `NodeID`, `TLC*` hashes, substrate ids) are copied from a **`Class`-selected** template row — `row = dict(fraud_tpl if is_fraud else legit_tpl)` (`gamma_map_raw:107-108, 122`), which `gamma_map_raw:19-23` describes as "copied from the sample template."
- **Why automatic reuse is not permitted.** The template **row is selected by `Class`**. Freezing the copy verbatim would inherit that `Class`-keyed selection. Whether the constant *values* actually differ between the legit and fraud template rows is **unconfirmed**: the template file `GAMMA_G0_..._sample_master112_1000.csv` is **not present in the repository** and could not be verified.
- **Why owner approval is required.** Two owner acts are needed: (a) **confirm Class-invariance** — verify the structural constants are identical across the template rows (so no value leaks `Class`); and (b) **approve a Class-independent sourcing** — the constants must be read from a single `Class`-independent origin rather than a `Class`-selected row. Neither can be resolved from the repository as-is.
- **Constraints imposed by the frozen architecture.** `PolicyHash` has an authoritative Class-independent source — the **frozen `ScientificPolicy` Merkle root** (Deployment Profile Contract D1/D10) — which should be its source rather than a copied template value. The other constants must resolve to a single, frozen, Class-independent origin.
- **Constraints imposed by replay determinism.** `PolicyHash` is the Evidence Quad `policy_hash`; it and the other constants must be fixed and reproduced byte-identically across runs (DET1). A constant that varied by row or by `Class` would break both determinism and Class-blindness.
- **Constraints imposed by Class blindness.** The sourcing mechanism must read **no** `Class`; the constants' values must be confirmed identical regardless of `Class`.
- **Decision to be approved by the owner.** Ratify (a) the **confirmation of Class-invariance** of the structural constants, and (b) the **Class-independent sourcing** (`PolicyHash` ← frozen scientific Merkle root; remaining constants ← a named single Class-independent origin), replacing the `Class`-selected template copy.

  **OWNER DECISION:** ______________________________________________

---

## 4. Owner signature block

By signing, the owner ratifies (or amends) the three decisions above as engineering conventions only, introducing no new science, policy, or architecture, and authorizes the Class-blind emitter to be implemented to the completed Engineering Serialization Contract (as flag-OFF/parallel scaffolding; activation remains separately gated under Commit 5.2).

| Role | Name | Signature | Date |
|---|---|---|---|
| Engineering Owner | ____________________ | ____________________ | __________ |
| Software Architect (verifier) | ____________________ | ____________________ | __________ |
| IEEE Artifact Engineer (verifier) | ____________________ | ____________________ | __________ |

**Ratification outcome (owner to complete):** ☐ Approved as written ☐ Approved with amendments (recorded above) ☐ Rejected

---

## 5. Date

- **Record prepared:** 2026-07-08
- **Ratification date:** __________ *(owner to complete)*

---

## 6. Repository version

- **Branch:** `main`
- **HEAD commit:** `763008a32e9225f5086eb8c6794625c88da0bf1b` (`763008a`)
- **Governing contract:** `ENGINEERING_SERIALIZATION_CONTRACT.md` (approved)
- **Scope of record:** Contract items **C7**, **C8**, **C9** only.

---

# AWAITING OWNER RATIFICATION

---

*Engineering governance record only. No code, no repository modification, no scientific-specification change, no implementation, no redesign, no proposed EnvironmentContext replacement. Decision fields left blank for the owner. Every referenced convention is cited to the approved Engineering Serialization Contract and the existing `gamma_map_raw.py` implementation. Awaiting owner approval before any implementation.*
