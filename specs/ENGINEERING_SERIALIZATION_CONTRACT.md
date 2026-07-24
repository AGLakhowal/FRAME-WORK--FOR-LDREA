# ENGINEERING SERIALIZATION CONTRACT — Class-blind Reported Artifact Emitter

**Engineering contract only. No code, no implementation, no repository modification, no redesign, no invented convention.** This document formalizes the **deterministic serialization conventions** the Class-blind Reported Artifact Emitter must reproduce. It defines **no** scientific behaviour, **no** policy, and **no** authorization. Its sole authoritative source is the **existing implementation conventions already present in `gamma_map_raw.py`**; the objective is to classify each convention as Class-blind / deterministic / reusable and therefore freezable verbatim — or as requiring owner ratification.

**Roles:** Principal Software Architect · Runtime Infrastructure Engineer · IEEE Artifact Engineer.

**Method.** Every entry is read directly from `gamma_map_raw.py` (cited by line) and `gamma_test_runner.py` (the frozen consumer). No convention is redesigned; where a convention leaks `Class` or cannot be confirmed Class-invariant, it is flagged — not fixed.

---

## 0. Shared primitives (Class-blind pure helpers)

| Primitive | Definition | Source | Class-blind | Deterministic |
|---|---|---|---|---|
| `h12(*parts)` | `sha256("\|".join(parts))[:12]` | `gamma_map_raw:69-70` | YES | YES |
| `h16(*parts)` | `sha256("\|".join(parts))[:16]` | `gamma_map_raw:73-74` | YES | YES |
| `iso_ms(dt)` | `%Y-%m-%dT%H:%M:%S.mmmZ` formatter | `gamma_map_raw:77-78` | YES | YES |
| `EPOCH_BASE` | `datetime(2013, 9, 1, tzinfo=utc)` | `gamma_map_raw:45` | YES | YES |

These are inert, label-free functions/constants of their inputs. **Freezable verbatim: YES.** They underpin the conventions below.

---

## 1. Convention register

Summary table; detailed entries follow. "Replay impact" = whether the field participates in the ledger canon / replay manifest / Evidence Quad.

| # | Convention | Reads Class? | Deterministic? | Replay impact | Freeze verbatim? | Requires modification? |
|---|---|---|---|---|---|---|
| C1 | ProposalID | **NO** | YES | HIGH (in canon) | **YES** | NO |
| C2 | PermitTokenID | **NO** | YES | HIGH (in canon) | **YES** | NO |
| C3 | SubjectProfileID | **NO** | YES | LOW (reported col) | **YES** | NO |
| C4 | ERTuple_ID | **NO** | YES | MED (replay record id) | **YES** | NO |
| C5 | Timestamp (base / `TimestampUTC`) | **NO** | YES | HIGH (in canon) | **YES** | NO |
| C6 | Commit timestamp offset (+10ms) | **NO** | YES | MED (ordering / I5) | **YES** | NO |
| C7 | Actuate timestamp offset (+25ms) | **NO** (offset) | YES | MED (ordering / I5) | **YES** (offset) | **YES** (emission gate) |
| C8 | EnvironmentContext | **YES** | YES | LOW (reported col) | **NO** | **YES** |
| C9 | Structural constants | **CONDITIONAL** | YES | HIGH (`PolicyHash`) | **CONDITIONAL** | **YES** (re-source) |
| C10 | Ledger canon composition | **NO** (composition) | YES | CRITICAL | **YES** (composition) | NO (values re-sourced) |
| C11 | HASH generation inputs | **NO** | YES | CRITICAL | **YES** | NO |

**Reading:** C1–C6, C10, C11 (and the primitives) are Class-blind, deterministic, and **freezable verbatim**. **C7** freezes the offset but its *emission gate* must be decision-driven. **C8** and **C9** are the two items that **cannot be frozen as-is** and require the owner.

---

## 2. Detailed entries

### C1 — ProposalID generation
- **Purpose:** stable per-row proposal identity; participates in the ledger canon.
- **Current implementation source:** `row["ProposalID"] = f"TXN_{idx:06d}"`, `idx = i + 1` (`gamma_map_raw:135`).
- **Reads Class? NO** — pure function of the row index.
- **Deterministic? YES** — index-derived.
- **Replay impact:** HIGH — first field of the ledger canon (C10).
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** index-only, Class-blind, already in the canon; reproducible on replay.

### C2 — PermitTokenID generation
- **Purpose:** per-row permit token identity; participates in the ledger canon.
- **Current implementation source:** `f"PERMIT_{h16('permit', idx)}"` (`gamma_map_raw:185`).
- **Reads Class? NO** — `h16` over the constant tag `'permit'` + index.
- **Deterministic? YES.**
- **Replay impact:** HIGH — fifth field of the ledger canon (C10).
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** index-derived hash, Class-blind, in the canon.

### C3 — SubjectProfileID generation
- **Purpose:** synthetic subject-profile identity (reported column).
- **Current implementation source:** `f"CARDPROFILE_SYN_{h12('profile', idx)}"` (`gamma_map_raw:139`).
- **Reads Class? NO.**
- **Deterministic? YES.**
- **Replay impact:** LOW — reported column; not in the canon or Evidence Quad.
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** index-derived; Class-blind.

### C4 — ERTuple_ID generation
- **Purpose:** evidence-tuple identity; surfaced in the replay manifest record.
- **Current implementation source:** `f"ERT_{h16('ertuple', idx)}"` (`gamma_map_raw:186`).
- **Reads Class? NO.**
- **Deterministic? YES.**
- **Replay impact:** MEDIUM — appears as `ertuple_id` in each replay record (`write_replay_manifest`).
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** index-derived; Class-blind; the frozen replay emitter reads it verbatim.

### C5 — Timestamp generation (base / `TimestampUTC`)
- **Purpose:** the decision timestamp; participates in the ledger canon.
- **Current implementation source:** `base_ts = EPOCH_BASE + timedelta(seconds=t_sec)`, `t_sec` from the observable `Time` column (NaN-safe → 0.0), `TimestampUTC = iso_ms(base_ts)` (`gamma_map_raw:122-137`).
- **Reads Class? NO** — `Time` is a plane-A observable, not the label.
- **Deterministic? YES** — function of the observable time + fixed epoch.
- **Replay impact:** HIGH — sixth field of the ledger canon (C10).
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** derived from a plane-A observable + a fixed epoch; Class-blind; the emitter (like the substrate) is not a wall-clock time source — time is derived from the observable.

### C6 — Commit timestamp offset
- **Purpose:** fixed offset from base to the commit event; reported as `CommitTimestamp`.
- **Current implementation source:** `commit_ts = base_ts + timedelta(milliseconds=10)` (`gamma_map_raw:142`).
- **Reads Class? NO.**
- **Deterministic? YES.**
- **Replay impact:** MEDIUM — ordering fact; interacts with **Invariant I5** (commit-before-actuate).
- **Can be frozen verbatim? YES.**
- **Requires modification? NO.**
- **Reason:** a fixed constant; Class-blind. Because it encodes I5 ordering, it must be **reused, not re-chosen**.

### C7 — Actuate timestamp offset
- **Purpose:** fixed offset from base to the actuation event; reported as `ActuateTimestamp`.
- **Current implementation source:** `actuate_ts = base_ts + timedelta(milliseconds=25)` (`gamma_map_raw:143`). **Emission** is currently `Class`-branched: `ActuateTimestamp = iso_ms(actuate_ts)` for the legit branch, `""` for the fraud branch (`gamma_map_raw:164, 180`).
- **Reads Class?** the **offset: NO**; the **emission gate: YES** (currently keyed on `is_fraud`).
- **Deterministic? YES.**
- **Replay impact:** MEDIUM — ordering; I5.
- **Can be frozen verbatim?** the **offset: YES**.
- **Requires modification? YES** — the **emission gate** (whether an actuate timestamp exists) must be driven by the **frozen decision** (actuated ⇔ PERMIT / not actuated ⇔ SAFE_STATE), **not** by `Class`. This is a **decision-carry** re-sourcing, not a change to the offset convention.
- **Reason:** the offset is a Class-blind constant (freeze verbatim); the *presence* of actuation is a decision fact that must come from the frozen engine output, not the label.

### C8 — EnvironmentContext  ⚠️ LEAKS CLASS
- **Purpose:** free-text provenance/environment descriptor (reported column).
- **Current implementation source:** `f"ULB_2013_EU_CARD;source_time_sec={int(t_sec)};amount={amount:g};class={classes[i]};source=anonymized_PCA"` (`gamma_map_raw:140-143`).
- **Reads Class? YES.**
- **Deterministic? YES.**
- **Replay impact:** LOW — reported column; **not** in the ledger canon or Evidence Quad.
- **Can be frozen verbatim? NO.**
- **Requires modification? YES.**
- **Reason:** embeds the ground-truth label (`class={classes[i]}`), a direct Class leak into the reported artifact (violates EEB §9 / RCL §8 Class-blindness). See §3 — described, **not** replaced here.

### C9 — Structural constants  ⚠️ CLASS-INVARIANCE UNCONFIRMED
- **Purpose:** schema constants making the emitted file a valid golden trace: `PolicyHash`, `SpecVersion`, `NodeID`, `TLC*` hashes, substrate ids.
- **Current implementation source:** copied from a **`Class`-selected** template row — `row = dict(fraud_tpl if is_fraud else legit_tpl)` (`gamma_map_raw:107-108, 122`); `gamma_map_raw:19-23` states these constants are "copied from the sample template."
- **Reads Class? CONDITIONAL** — the **row selection is `Class`-driven**; whether the constant **values differ** between the legit and fraud template rows is **UNCONFIRMED** (the template file `GAMMA_G0_..._sample_master112_1000.csv` is **not present in the repository**, so it could not be verified).
- **Deterministic? YES** (copied constants).
- **Replay impact:** HIGH for `PolicyHash` — it is the Evidence Quad `policy_hash`.
- **Can be frozen verbatim? CONDITIONAL** — only if (a) the constants are confirmed **identical across both template rows**, and (b) they are sourced from a **single `Class`-independent origin**. For `PolicyHash` specifically, an authoritative Class-independent source already exists — the **frozen `ScientificPolicy` Merkle root** (Deployment Profile Contract D1/D10) — which should be the source rather than a copied template value.
- **Requires modification? YES** — the **sourcing** must change from "copy a `Class`-selected template row" to "read from a confirmed `Class`-independent origin," even if the values turn out identical.
- **Reason:** the selection mechanism is `Class`-keyed; freezing verbatim would inherit that keying. The values' Class-invariance cannot be confirmed here (template absent). **Owner verification + a Class-independent sourcing decision required.**

### C10 — Ledger canon composition
- **Purpose:** the canonical per-row core string the Hydra Ledger hashes.
- **Current implementation source:** `f"{ProposalID}|{Status}|{Gamma}|{harm:.6f}|{PermitTokenID}|{TimestampUTC}"` (`gamma_map_raw:~200`).
- **Reads Class?** the **composition (fields / order / `:.6f` precision): NO**. The **current values** of `Status` / `Gamma` / `harm` are `Class`-derived *in `gamma_map_raw`* — but in the emitter they are **engine/pipeline-derived** (Class-blind): `Status`/`Gamma` from the frozen decision, `harm` from Predicate Binding (absent → `0.0`).
- **Deterministic? YES.**
- **Replay impact:** CRITICAL — this string defines the chain; the frozen verifier checks **adjacency**, not composition, so the composition must be stable to keep the chain reproducible.
- **Can be frozen verbatim? YES** for the composition (fields, order, precision), with the **values re-sourced** from the frozen decision/pipeline.
- **Requires modification? NO** to the composition; the value **source** changes (decision-sourced, not `Class`-sourced).
- **Reason:** the composition is a Class-blind structural convention; its Class-blind re-instantiation produces a **new chain instance** — the deliberate **signed replay/ledger rebaseline**, which is scoped to **Commit 5.2 activation**, not to building this emitter as flag-OFF scaffolding.

### C11 — HASH generation inputs
- **Purpose:** the Hydra Ledger hash-chain step.
- **Current implementation source:** `cur = sha256((prev_hash + "||" + canon))`, genesis anchor `"GENESIS"`, `HASH_prev = prev_hash`, `HASH_current = cur` (`gamma_map_raw:~203-206`).
- **Reads Class? NO** (given a Class-blind canon, C10).
- **Deterministic? YES.**
- **Replay impact:** CRITICAL.
- **Can be frozen verbatim? YES** — and the **chain algorithm is already frozen and independently verified** (`gamma_replay_verify.py` + `write_replay_manifest`: `hash_prev[i] == hash_current[i-1]`, genesis-anchored).
- **Requires modification? NO.**
- **Reason:** the hashing algorithm is the existing, verifier-enforced chain; only the canon *values* it consumes (C10) become Class-blind.

---

## 3. Special requirement — EnvironmentContext (described, NOT replaced)

Per instruction, the replacement is **not** proposed; only the current field, its leak, and the required replacement properties are described.

**What the field currently contains** (`gamma_map_raw:140-143`), a `;`-delimited descriptor with five tokens:
1. `ULB_2013_EU_CARD` — a fixed dataset/region tag (constant).
2. `source_time_sec={int(t_sec)}` — the observable `Time` (plane-A observable).
3. `amount={amount:g}` — the observable `Amount` (plane-A observable).
4. `class={classes[i]}` — **the ground-truth `Class` label**.
5. `source=anonymized_PCA` — a fixed provenance tag (constant).

**Why it leaks `Class`:** token 4 embeds the ground-truth label verbatim into a **reported** artifact column. Under EEB §9 / RCL §8, `Class` must have no field and enter only at Ground-Truth Evaluation; a reported provenance string that carries `class={…}` places the label inside the decision-time artifact, defeating Class-blindness and contaminating any downstream consumer of the reported trace.

**Properties the replacement must satisfy** (constraints only — no content proposed):
- **Class-blind:** must read/embed no `Class` field, value, or derivative — tokens 1, 2, 3, 5 (constants + plane-A observables) are already Class-blind and admissible; token 4 must be **removed** (not re-encoded).
- **Deterministic:** a pure function of Class-blind inputs (constants + observables); no wall clock, no randomness.
- **Replay-stable:** identical inputs → identical string; since `EnvironmentContext` is **not** in the ledger canon (C10), its content does not alter the hash chain, but it must still be deterministic for byte-identical trace reproduction.
- **Provenance-faithful:** it must not fabricate evidence or assert any decision/policy value; it records environment/provenance facts only (consistent with the emitter's serialization-only role).
- **Owner-defined:** because the exact Class-blind content is **not** specified by any frozen source, the field's replacement content is an **owner authoring decision**; this contract only fixes the constraints it must meet.

---

## 4. What is ratifiable now vs. what needs the owner

**Freezable verbatim as engineering conventions now (no owner content decision):** the primitives (§0) and **C1, C2, C3, C4, C5, C6, C10 (composition), C11** — all Class-blind, deterministic, reusable, and (for canon/hash) already verifier-frozen. Plus **C7's offset**.

**Cannot be frozen as-is — owner ratification required:**
- **C7 emission gate** — must be re-sourced from the frozen decision (mechanical, but must be ratified as decision-driven, not `Class`-driven).
- **C8 EnvironmentContext** — leaks `Class`; the Class-blind replacement **content is undefined** and is an owner authoring decision (§3).
- **C9 structural constants** — Class-invariance **unconfirmed** (template absent) and the **sourcing must be re-anchored** to a Class-independent origin (`PolicyHash` → frozen Merkle root; others → confirmed single source).

---

## 5. Conclusion

The **majority** of the emitter's serialization conventions (the primitives, identifiers C1–C4, timestamps C5–C6, the ledger canon composition C10, and the hash algorithm C11) are demonstrably **Class-blind, deterministic, and reusable**, and are ready to be frozen verbatim as an engineering contract. However, **three items cannot be frozen as-is without an owner act**: the **C7** actuate-emission gate must be ratified as decision-driven; **C8 EnvironmentContext leaks `Class`** and its Class-blind replacement content is undefined (owner authoring decision); and **C9 structural constants** have unconfirmed Class-invariance (template not in the repository) and require a Class-independent sourcing decision. None of these is science, policy, or architecture — each is an engineering-contract ratification the owner must sign before the emitter can be implemented without invention.

# OWNER RATIFICATION REQUIRED

**Single sentence:** C1–C6, C10, C11 and the primitives are ready to freeze verbatim; but **C7 (emission gate re-sourcing), C8 (undefined Class-blind EnvironmentContext replacement), and C9 (unconfirmed structural-constant Class-invariance + re-sourcing)** each require an owner ratification/decision before the Class-blind emitter can be built.

---

*Engineering serialization contract only. No code, no implementation, no repository modification, no invented convention, no proposed EnvironmentContext replacement. Every convention is cited to the existing `gamma_map_raw.py` implementation and the frozen consumer; the three unresolved items are identified, not resolved. Awaiting independent review and owner ratification.*
