# COMMIT 2.2 — PRE-IMPLEMENTATION REVIEW

**Review only. No code, no file modified, no implementation.** Reviews Commit 2.2 exactly as defined in `ENGINEERING_MIGRATION_ROADMAP.md`, in isolation (Commits 2.3–2.5 not anticipated).

**Roles:** Lead Runtime-Systems Architect · Software-Verification Engineer · IEEE Artifact Engineer · Repository-Migration Engineer · Systems-Reliability Engineer.

---

## RECONCILIATION REQUIRED (read first) — the prompt's "Expected Purpose" ≠ the roadmap's Commit 2.2

The prompt's **Expected Purpose** section says Commit 2.2 "introduces the **Runtime Context Layer producer** … collect runtime evidence and populate an Execution Evidence Bundle." **That is not the roadmap's Commit 2.2.** Per `ENGINEERING_MIGRATION_ROADMAP.md:97-105`:

> **Commit 2.2 — `feat(rcl): add read-only Authority/Governance/Policy ports (evidence-absent default)`**
> Purpose: typed read-only ports (EEB spec §4) that return **evidence-absent** when no producer is bound; PolicyPort reads existing frozen manifests read-only. Files created: `runtime_context/ports.py`.

The "RCL producer that collects runtime evidence" the prompt describes is actually:
- **Commit 2.3** — `add Runtime Context Layer plane-B objects` (the evidence *producers*: history window, freshness clock, commit/actuate journal, context record), and
- **Commit 2.5** — `add EEB assembler` (which *populates/seals* an EEB).

The task instruction is explicit: *"Review Commit 2.2 exactly as defined in ENGINEERING_MIGRATION_ROADMAP.md … Do NOT redesign it … Do NOT anticipate Commit 2.3 or later."* Those instructions bind me to the **roadmap's 2.2 (the ports)** and forbid me from reviewing the plane-B producer (2.3) under a "2.2" label. **I therefore review the ports (roadmap 2.2) below and do not implement or review the producer.** If you intended the RCL producer, that is Commit 2.3 — say so and I will review *that* next; I will not silently re-scope 2.2.

The remainder of this document reviews the **roadmap's Commit 2.2 (read-only ports)**.

---

## PART 1 — Purpose

**What it accomplishes.** Adds `runtime_context/ports.py`: three **typed, read-only ports** per EEB spec §4 —
- **AuthorityPort (plane C)** — surfaces authority evidence (`TOKEN_VALID`, `AuthoritySignatureValid`, approval/`Lambda_G` concurrence). In this arm **no producer is bound** → returns **evidence-absent**.
- **GovernancePort (plane D)** — surfaces governance evidence (`HARM_RISK`, sanctions/AML). No producer bound → **evidence-absent**.
- **PolicyPort** — reads the **existing frozen policy manifests** via `agentdojo_integration.interception.frozen_policy.ScientificPolicy` **read-only**, exposing verified policy metadata (Merkle root, directives) for shape/routing only.

It is an **interface/exposure layer only**: no producer for C/D exists yet, so those ports honestly report absence rather than fabricate. It **does not** authorize, evaluate, classify, compute predicates, invoke Gamma/SAFE_STATE/`evaluate_decision`, or change any runtime/benchmark path. No module consumes it.

**Why it follows 2.1.** A port's "evidence-absent signal" is an **EEB `EvidenceField`** (value `None`, provenance `evidence_quality=ABSENT`) — the ports **return the 2.1 contract types**. Without 2.1's `EvidenceField`/`ProvenanceDescriptor`/enums, the ports have no typed return.

**Why it cannot precede 2.1.** Same reason: the port return type *is* the EEB evidence type introduced in 2.1. 2.2 imports from `runtime_context.execution_evidence_bundle`.

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `runtime_context/ports.py` | **CREATE** | the three read-only ports |
| `tests/test_ports.py` | **CREATE** | mandated tests ("each port returns ABSENT with no producer; PolicyPort integrity read matches Merkle root") — standalone-runnable, matching the 0.1/0.2/2.1 pattern |
| `agentdojo_integration/interception/frozen_policy.py` | **UNCHANGED** | reused **read-only** by PolicyPort (roadmap: "Files modified: none") |
| `runtime_context/execution_evidence_bundle.py` | **UNCHANGED** | imported read-only for its types |
| everything else (engine, benchmarks, `run_all.py`, dashboard, registry) | **UNCHANGED** | ports are unconsumed |

**Not in 2.2:** `TransactionPort` (plane A) — it belongs to the Transaction Interpreter, **Commit 2.4**. 2.2 is exactly three ports. Do not add a fourth.

## PART 3 — Dependencies & hidden assumptions

| Depends on | Verdict |
|---|---|
| Commit 0.1 | No |
| Commit 0.2 | No functional dependency; **interaction**: `ports.py` will be scanned by the guardrail → must stay clean (0 unregistered) |
| Commit 1.1 | No |
| **Commit 2.1** | **YES (hard)** — imports `EvidenceField`, `ProvenanceDescriptor`, `OriginPlane`, `EvidenceQuality`, `TrustLevel`, `VerificationMethod` to construct evidence-absent returns |
| `agentdojo_integration.interception.frozen_policy` | **YES (PolicyPort, read-only)** — verified importable, Merkle-verifies (`ce8c8467…`), pulls in **no** heavy agentdojo runtime, and creates **no cycle** (`agentdojo_integration` does not import `runtime_context`) |

**Hidden engineering assumptions (all resolvable now; none scientific):**

- **HA-1 — Guardrail cleanliness.** `ports.py` must contain no bare decision literal (`"PERMIT"`/`"SAFE_STATE"`), no decision-literal `IfExp`, and no assignment to an auth-output name (`gamma_g`/`permit`/…). Surfacing field *names* like `TOKEN_VALID`/`AuthoritySignatureValid` is safe (not in the watched set). A read-only, evidence-absent port has no reason to author decisions. **Post-commit gate:** `check_single_engine.py` → 0 unregistered.
- **HA-2 — Namespace-package import.** `agentdojo_integration` has **no `__init__.py`** (it is an implicit namespace package); `interception` has one. The import `from agentdojo_integration.interception import frozen_policy` works on Python 3.3+ (verified). PolicyPort relies on this. Acceptable; flag it (a future move/rename of that package would break PolicyPort).
- **HA-3 — Evidence-absent construction.** An evidence-absent `EvidenceField` still needs a complete `ProvenanceDescriptor` (2.1's `validate_structure` requires non-empty `producer_id` and `observed_at`). **Resolution:** the port sets `evidence_quality=ABSENT`, `producer_id` a sentinel (e.g. `"unbound"`), and takes `observed_at` as a **parameter** (or a module sentinel constant) so the port is **not a time source** and stays deterministic. Do not call `datetime.now()` inside the port.
- **HA-4 — PolicyPort instantiation cost / failure mode.** `ScientificPolicy` does I/O (reads 7 manifests + Merkle-verify) at construction and raises `PolicyError` on integrity failure. **Resolution:** lazy-construct on first use (or accept eager — it's ~7 small JSON reads); propagate `PolicyError` (a genuine integrity failure should surface, not be swallowed). Read-only; never writes.
- **HA-5 — Method granularity.** EEB spec §4 names *what* each port surfaces, not exact signatures. **Resolution (minimization):** a small typed method set (Authority: `token_valid()`, `authority_signature_valid()`, `authority_concurrence()`; Governance: `harm_risk_score()`, `sanctions_clear()`; Policy: `merkle_root()`, `directive(name)`) each returning an `EvidenceField` (C/D → ABSENT) — or a single generic `get(name)` per port. Prefer the minimal set that satisfies the two mandated tests; do not build a registry/factory.

## PART 4 — Engineering impact

| Area | Change? | Why |
|---|---|---|
| Repository structure | **+1 module** (`ports.py`) + 1 test | additive |
| Imports | `ports.py` → `runtime_context.execution_evidence_bundle` (2.1) + `agentdojo_integration.interception.frozen_policy` (read-only) | **nothing imports `ports.py`** (no consumer) |
| Runtime / execution flow | **None** | unconsumed |
| Packaging | within `runtime_context/` | isolated |
| Benchmark pipeline | **None** | untouched; 6 reports stay byte-identical |
| Tests | **+1** | additive |
| Dashboard | **None** | `gamma_report_page.py` untouched |

**Everything except the two new files stays untouched.**

## PART 5 — Data flow

```
   (Authority/Governance: NO producer bound in this arm)
                    │
                    ▼
        AuthorityPort / GovernancePort  (read-only)
                    │  returns EvidenceField(value=None,
                    │           provenance.evidence_quality = ABSENT)   [2.1 type]
                    ▼
                  STOP   ── no consumer, no Gamma, no authorization, no benchmark

   frozen manifests (agentdojo_integration/manifests, Merkle ce8c8467…)
                    │  read-only
                    ▼
              PolicyPort  → verified policy metadata (root/directives)
                    │
                    ▼
                  STOP   ── read-only; never writes; no consumer
```

No path reaches `evaluate_decision`, Gamma, SAFE_STATE, the benchmark pipeline, or the dashboard. The ports terminate at their return value.

## PART 6 — Risks (engineering only; no scientific risk)

| Risk | Severity | Mitigation |
|---|---|---|
| Guardrail false-positive / decision-logic leak in `ports.py` | Low-Med | HA-1: no decision literals/auth-output names; verify 0 unregistered |
| Cross-package coupling `runtime_context → agentdojo_integration` (PolicyPort) | Low | verified no cycle, no heavy import; reuse is the roadmap's intent (minimization); document the edge |
| Namespace-package import fragility (HA-2) | Low | works on 3.3+; note the dependency on the package path |
| Mutable evidence returned | **None** | ports return frozen `EvidenceField` (2.1) → immutable by construction |
| PolicyPort I/O failure at construction | Low | HA-4: propagate `PolicyError`; lazy-construct |
| Import cycle | **None** | `agentdojo_integration` does not import `runtime_context` (verified) |
| Serialization drift | **None** | ports do not serialize; they return 2.1 types |
| Regression | **None** | unconsumed; benchmarks/engine untouched |

## PART 7 — Test plan

**New (`tests/test_ports.py`, hermetic where possible):**
- AuthorityPort and GovernancePort return **evidence-absent** — an `EvidenceField` with `evidence_quality == ABSENT` and the correct `origin_plane` (C / D), value `None`.
- The returned `EvidenceField` is **immutable** (frozen; mutation raises).
- **PolicyPort integrity read matches the frozen Merkle root** (`ce8c8467a3a9d60c…`) — reads the committed manifests (deterministic).
- (Optional) evidence-absent fields pass the EEB `validate_structure` provenance checks (HA-3 correctness).

**Regression (must stay green):**
- `python3 tools/check_single_engine.py` → exit 0 **and 0 unregistered** (HA-1 gate).
- `python3 tests/test_execution_evidence_bundle.py` → 6/6 (2.1).
- `python3 tests/test_single_engine_guardrail.py` → 6/6 (0.2).
- `python3 tests/test_baseline_fixtures.py` → 4/4 (0.1).
- Six benchmark reports byte-identical to `tests/fixtures/baseline/`.
- `python3 -c "import run_all"` → clean.
- **Repository verification:** `git status` shows only `runtime_context/ports.py` + the new test added; no existing file modified.

## PART 8 — Implementation minimization

- **Reuse 2.1 types for evidence-absent** — return `EvidenceField`/`ProvenanceDescriptor`; **introduce no new evidence/result type.** (Primary reduction.)
- **Reuse `ScientificPolicy`** for PolicyPort — do not re-implement policy loading or Merkle verification.
- **Three small classes, no hierarchy/factory.** AuthorityPort and GovernancePort are behaviorally identical for 2.2 (both return ABSENT, differing only in `origin_plane`) — a single tiny shared helper (`_absent(plane, observed_at)`) is acceptable; do **not** build an abstract base, protocol registry, or plugin system.
- **No TransactionPort** (2.4), **no bound producers** (later), **no assembler** (2.5).
- **Minimal method set** satisfying the two mandated tests; avoid speculative methods for fields no test exercises.

## PART 9 — Certification

1. **Is Commit 2.2 fully specified?** **YES for the roadmap's 2.2 (read-only ports)** — with HA-1…HA-5 resolved (guardrail-clean; namespace import; evidence-absent construction via sentinel + passed `observed_at`; lazy PolicyPort propagating `PolicyError`; minimal method set). **NO** if the prompt's "Expected Purpose" (RCL producer) was intended — that is Commit 2.3 and is out of scope here.
2. **Are only engineering decisions remaining?** **YES** (for the ports): construction detail, granularity, lazy/eager. No scientific decision.
3. **Does Commit 2.2 introduce scientific change?** **NO** — read-only exposure + evidence-absent defaults; touches no engine/predicate/benchmark/replay/metric; PolicyPort only *reads* the already-frozen, Merkle-verified manifests.
4. **Can implementation begin safely?** **YES for the ports**, **conditional on the reconciliation** at the top: confirm you mean the roadmap's 2.2 (ports). If yes, proceed with the file set of Part 2 and the HA resolutions.
5. **Can scope be reduced further?** **YES** — see Part 8: reuse 2.1 types (no new type), reuse `ScientificPolicy`, three minimal classes with a shared `_absent` helper, no base-class/factory, no TransactionPort, minimal methods. This is already the minimal realization of the roadmap's 2.2.

---

## Decision required

Before implementation, confirm one:
- **(A)** Proceed with the **roadmap's Commit 2.2 = read-only Authority/Governance/Policy ports** (`runtime_context/ports.py`) as reviewed here.
- **(B)** You actually intended the **RCL evidence producer** (collect runtime evidence / populate an EEB) — that is **Commit 2.3** (plane-B objects) and/or **2.5** (assembler). If so, ask for a **Commit 2.3 review**; I will not re-label it as 2.2.

I will not implement until you confirm. Nothing here changes Gamma, predicates, replay, benchmarks, or any scientific artifact.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed the roadmap's Commit 2.2 (ports) in isolation; flagged the mismatch with the prompt's stated purpose; did not anticipate Commits 2.3–2.5. Awaiting your reconciliation and approval.*
