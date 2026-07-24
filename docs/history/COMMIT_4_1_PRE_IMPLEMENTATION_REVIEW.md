# COMMIT 4.1 — PRE-IMPLEMENTATION REVIEW (fast-track: review REQUIRED by trigger)

**Review only. No code, no file modified, no implementation.** Next roadmap commit after 3.1 is **Commit 4.1** (`ENGINEERING_MIGRATION_ROADMAP.md:151-159`, Phase 4).

**Why this commit is NOT fast-tracked.** The fast-track rule skips the pre-implementation review *unless* a commit touches Gamma / authorization / replay. Commit 4.1 **modifies `gamma_test_runner.py`** (the frozen engine file) on the **authorization input path**, is rated **High engineering risk**, and its entire correctness rests on a **zero-logic-diff** contract. That squarely hits the trigger, so the review is mandatory. A wrong edit here silently breaks LAB parity and replay — the single most dangerous change in the migration.

**Roles:** Lead Runtime-Systems Architect · Software-Verification Engineer · IEEE Artifact Engineer · Runtime-Governance Engineer · Repository-Migration Engineer.

---

## PART 1 — Purpose

Add an **input adapter** so the engine's decision path can be fed from an **Execution Evidence Bundle** *instead of* raw CSV columns — with the **decision logic byte-for-byte unchanged** and behind a **default-OFF flag**. Default runs stay on the current CSV path. This is the first step of engine *consumption* of the EEB substrate built in Phase 2; it is deliberately neutral (flag OFF) and only *enables* an opt-in EEB path for later validation.

**Neutrality contract (the whole point):**
- **Flag OFF (default):** the input path is byte-untouched ⇒ LAB report, metrics, and replay identical to today (0.1 fixtures).
- **Flag ON (controlled arm):** the adapter must reproduce the engine's **exact decision inputs** from an EEB, so every `DerivedGammaG` / `DerivedPi` / `DerivedDecision` equals the CSV-path result on the same evidence — **zero-logic-diff**.

## PART 2 — Files

| File | Action | Why |
|---|---|---|
| `runtime_context/eeb_to_engine.py` | **CREATE** | pure field-mapping adapter: EEB payload → the exact column schema the decision reads. No interpretation. |
| `gamma_test_runner.py` | **MODIFY (input-source region only)** | add a default-OFF flag; branch the **input-marshalling** region (`:838-864`, `pd.read_csv` → `ensure_columns` → `to_bool`) to optionally build `df` from EEB(s). **The decision logic `:866-892+` is NOT touched.** |
| `tests/test_eeb_to_engine.py` (or similar) | **CREATE** | the zero-logic-diff gate + adapter unit tests |
| everything else (predicates, `:868-892`, replay, benchmarks, ports/RCL/interpreter/assembler) | **UNCHANGED** | logic frozen; adapter is additive |

## PART 3 — The engine's decision-input schema (what the adapter must reproduce EXACTLY)

The decision (`:866-931`) and `evaluate_decision` (`:133-178`) consume a **specific subset** of columns — the adapter targets *only* these, not all 112/`BOOL_COLS`:

| Engine column(s) | Used for | EEB payload source (2.1) | Representation gap? |
|---|---|---|---|
| `NODE_GATE_COLS` (Gate_A1..A7, Lambda_G, TOKEN_VALID, AuthoritySignatureValid) | node deficits `d_i` | `node_predicate_vector` (ordered bool `EvidenceField`s) | order/membership = **binding** (must match `NODE_GATE_COLS` exactly) |
| `HARM_RISK` (number) | `> θ` deficit | `harm_risk_score` | number → number (OK) |
| `StaleContext`, `TelemetryFresh` (bool) | freshness deficits | `stale_context`, `telemetry_fresh` | **DELTA vs BOOLEAN** — 2.3/2.5 carry deltas; the engine reads booleans (see HA-2) |
| `ReasonCodes` (str) | class veto `CLASS_1|GOODHART` | *(no direct field)* — `class_veto_evidence` is optional/non-Class | **coverage gap** (HA-3) |
| `Actuated`, `ACT_PERMIT` (bool) | execute / unauthorized term | `actuation_observation` | bool → bool (OK, if carried) |
| `HASH_prev`, `HASH_current` (str) | replay chain | `prior_ledger_link` (HASH_prev only) | `HASH_current` not in payload (HA-4) |
| `CommitTimestamp`, `ActuateTimestamp`, `CommitBeforeActuate` | ordering / I5 | `commit_timestamp`, `actuate_timestamp`, `commit_before_actuate` | OK (optionals) |

## PART 4 — Hidden assumptions & findings (the real risk surface)

- **HA-1 — Flag default OFF, input-region branch only.** Add `--eeb-input PATH` (default `None`) to `parse_args` (insert near `:315`). In `main()`, branch: `if args.eeb_input: df = eeb_to_engine.frame_from_eeb(...)` else the unchanged `pd.read_csv(input_path)`. **Do not touch `:866+`.** With the flag unset, the code path is identical to today (neutrality by construction).
- **HA-2 — The adapter must NOT threshold (delta→boolean).** The RCL `FreshnessClock` emits **deltas**; the engine reads **booleans** `StaleContext`/`TelemetryFresh`. The adapter converting a delta to a boolean would be **interpretation/authorization** (a θ comparison) — forbidden, and it would break the zero-logic-diff contract. **Resolution:** for 4.1's equivalence test, the EEB is **constructed from CSV rows carrying the engine's boolean values directly** (round-trip), so the adapter is a pure remap. The delta→boolean resolution is a *later* (Phase 5) concern, not 4.1. **Binding.**
- **HA-3 — `ReasonCodes` coverage gap.** The engine's class veto reads `ReasonCodes ~ CLASS_1|GOODHART`. The EEB payload has no `ReasonCodes` field (by design — that string encodes the label; it is the Phase-5 leakage target). For 4.1's controlled equivalence test, the adapter must obtain the veto signal from a carried field (e.g., `class_veto_evidence`) or the test EEB must carry `ReasonCodes` verbatim as an opaque carrier. **This must be decided explicitly** — it determines whether 4.1's ON-path can even reproduce the current decision. Flag: 4.1 is a *plumbing* commit; it must not smuggle the Phase-5 methodology change. Recommend the equivalence EEB carry the veto input verbatim (no re-derivation).
- **HA-4 — `HASH_current` / replay columns.** The payload carries `prior_ledger_link` (= `HASH_prev`) but not `HASH_current`. The replay-chain check (`:908-911`) needs both. **Resolution:** the adapter reproduces replay columns from carried fields where present; the zero-logic-diff test scopes to the **decision** (Γ/π/DerivedDecision) as the roadmap specifies ("every DerivedDecision/Γ/π equals the flag-OFF result"), and replay-chain parity is asserted separately under flag OFF (unchanged path).
- **HA-5 — Adapter target = decision-consumed columns only.** Do **not** reconstruct all `BOOL_COLS`/112 columns — only the schema in Part 3. Missing non-decision columns are irrelevant to Γ/π. Keep the adapter minimal.
- **HA-6 — Purity / guardrail.** `eeb_to_engine.py` is scanned by the guardrail (`runtime_context` not excluded). It must not author decisions — no `gamma_g`/`pi`/`permit` assignments, no `"PERMIT"`/`"SAFE_STATE"` literals. It remaps fields into a DataFrame; it never decides.
- **HA-7 — No new import cycle.** `gamma_test_runner.py` would import `runtime_context.eeb_to_engine`. `runtime_context.*` imports only 2.1 types + (ports) `agentdojo_integration.interception.frozen_policy`; none import `gamma_test_runner`. Verify no cycle before wiring (the adapter should import the **EEB types**, not the runner).

## PART 5 — Data flow

```
 default (flag OFF):   CSV ──pd.read_csv──► df[engine schema] ──► (frozen decision :866-931) ──► identical output
 opt-in (flag ON):     EEB ──eeb_to_engine──► df[engine schema] ──► (SAME frozen decision) ──► identical decision
                                              ▲ pure field remap; NO threshold, NO interpretation, NO Class
```

## PART 6 — Risks (engineering)

| Risk | Severity | Mitigation |
|---|---|---|
| Any edit leaks into `:866-892` decision logic | **High** | strict diff scope: only the input-source branch; decision block untouched (verified by diff + LAB parity) |
| Adapter thresholds a delta → decision drift + interpretation | High | HA-2: equivalence EEB carries booleans verbatim; adapter never thresholds |
| `ReasonCodes`/veto gap silently changes the veto | High | HA-3: carry the veto input verbatim; do not re-derive; do not import Phase-5 semantics |
| Flag-OFF path perturbed | High | branch is additive; default path is the untouched `pd.read_csv` line |
| Replay/LAB fixture drift | High | flag-OFF LAB parity vs 0.1 fixture + replay SHA unchanged (gates) |
| Guardrail flags the adapter | Low | HA-6: no decision literals/auth names |
| Import cycle | Low | HA-7: adapter imports EEB types, not the runner |

## PART 7 — Test plan

- **Zero-logic-diff gate (mandated):** for a controlled sample, build an EEB per row carrying the engine-schema values, run the decision via the ON path, and assert `DerivedGammaG`/`DerivedPi`/`DerivedDecision` (and `evaluate_decision` pi) **equal** the OFF (CSV) result row-for-row.
- **LAB parity, flag OFF (mandated):** full runner on the 0.1 input → `gamma_lab_v1_report.json` / `gamma_summary.json` byte-identical to `tests/fixtures/baseline/`; replay manifest SHA unchanged.
- **AgentDojo tests green** (`agentdojo_integration/tests/test_interception.py`).
- **Adapter unit tests:** field remap correctness; no interpretation; guardrail-clean; no import cycle.
- **Full regression:** the eight existing suites green; six baseline reports byte-identical; `import run_all` clean.

## PART 8 — Scientific / architecture check

| Concern | Changed? |
|---|---|
| Authorization semantics / predicates / Γ / SAFE_STATE | **NO** — decision logic byte-untouched (`:866-892+`) |
| Gamma | **NO (behaviourally)** — only the input-source region gains an additive, default-OFF branch |
| Replay / metrics | **NO** — flag-OFF parity gated; flag-ON scoped to decision equivalence |
| Benchmark methodology | **NO** — default path unchanged |
| Class-blindness | **must be preserved** — the adapter carries evidence verbatim; it must not re-introduce `Class`/label via the `ReasonCodes` gap (HA-3) |

**No semantic change while OFF; ON is a validated equivalence.** The only architectural danger is scope leakage into the decision block or the adapter interpreting evidence — both explicitly forbidden above.

## PART 9 — Certification

1. **Fully specified?** **YES**, once two bindings are ruled: HA-2 (equivalence EEB carries booleans, adapter never thresholds) and HA-3 (veto input carried verbatim, not re-derived — 4.1 does not import Phase-5 semantics).
2. **Only engineering decisions remaining?** **YES** — flag name, adapter schema, how the equivalence EEB is constructed from CSV. No scientific decision (logic frozen).
3. **Introduces scientific change?** **NO** while OFF (byte-identical); ON is a decision-equivalence path, not a new decision.
4. **Can implementation begin safely?** **YES**, conditional on: touch only the input-source region; adapter is a pure remap (no threshold/interpretation/Class); flag default OFF; both parity gates green.
5. **Scope reducible?** **YES** — adapter targets only decision-consumed columns (Part 3), not all 112; construct equivalence EEBs from CSV; no new abstraction beyond the one adapter module.

---

## Decision required

- **(A)** Proceed with **Commit 4.1** as reviewed: additive `eeb_to_engine.py` (pure remap) + a default-OFF `--eeb-input` flag branching only the input-source region of `gamma_test_runner.py`; decision logic untouched; HA-2/HA-3 held (no thresholding, veto carried verbatim, no Phase-5 semantics); zero-logic-diff + flag-OFF LAB parity gated. **Recommended.**
- **(B)** Defer 4.1 pending a ruling on HA-3 (the `ReasonCodes`/veto carrier), since it determines whether the ON path can reproduce today's decision without importing Phase-5's Class-blind methodology.

I will not implement until you confirm. Per fast-track, this is the one remaining engine-touching, trigger-hitting commit that warranted a pre-implementation gate; subsequent neutral commits (5.1 flag-OFF parallel path, 6.x docs/gates) can be fast-tracked to direct implementation.

---

*Pre-implementation review only. No code, no modification, no implementation. Reviewed Commit 4.1 against the actual engine input schema (`gamma_test_runner.py:838-931`, `NODE_GATE_COLS`, `BOOL_COLS`) and the 2.1 EEB payload; surfaced the delta→boolean and `ReasonCodes`/veto representation gaps as the binding risks; the decision logic remains frozen. Awaiting approval.*
