# AgentDojo Integration — Traceability Matrix

Every engineering artifact maps to a frozen scientific contribution. Regenerated after each completed phase.

## Phase 2A — Environment Provisioning (COMPLETE)

| Paper Section | Definition | Theorem | Architecture Component | Implementation Artifact | Status | Evidence |
|---|---|---|---|---|---|---|
| §IX-F (pre-registered independent eval); §IX-F.2 (protocol freeze) | — | — | External validation environment (capability plane C host) | Pinned AgentDojo v0.1.35 in isolated CPython 3.11.15 venv | COMPLETE | `environment_provisioning_record.json`; `agentdojo == 0.1.35` verified via importlib.metadata |
| §IX-F.2 (SHA-256 manifest freeze); V2 Part 2; Verification Part 5 leaf #6 (Version Manifest) | — | — | Reproducibility substrate | Hashed lockfile + frozen versions | COMPLETE | `agentdojo_requirements.lock` (sha256 `810945…ca9a`, `--generate-hashes`); `requirements-frozen.txt` (sha256 `311647…ab8d`) |
| V2 Part 1 (complete-mediation chokepoint) | Def. 2(i) Complete mediation | — | Externalization boundary (interception site) | Interception point verified in INSTALLED pkg | COMPLETE (verified, not yet used) | `tool_execution.py:103 → runtime.run_function(...)`; `functions_runtime.py:246` |
| §III (capability plane is adversarial) | Def. 4 (capability–authority partition) | Lemma 1 | Plane C = AgentDojo agent loop | Suite registry loads offline | COMPLETE | Smoke test PASS: suites `[banking, slack, travel, workspace]` load without LLM |
| §V-G (Tier taxonomy); Verification Part 2 (Tier-S coverage bound) | — | Inv. 1–2 substrate dependence NOT exercised at Tier-S | Tier-S software substrate | Env is software-only; no HSM/FPGA | COMPLETE (scope recorded) | provisioning record `not_touched` + Tier-S disclosure |

## Scientific-preservation check (Phase 2A)

| Frozen construct | Changed in Phase 2A? | Evidence |
|---|---|---|
| Gamma / Gamma G-0 / L-DREA / LUIPM | NO | no source touched |
| Γ authorization / SAFE_STATE | NO | no decision code written yet |
| Execution Integrity / Evidence Quad / Hydra Ledger | NO | reporting infra untouched |
| Runtime Sovereignty / Execution Sovereignty | NO | theorems untouched |
| LAB / ConcurBench / ASB | NO | native benchmarks untouched |
| AgentDojo source | NO | installed as dependency; not edited |
| Paper | NO | not modified |
| `external_validation/` (historical) | NO | preserved untouched (per governance §1) |

**Phase 2A verdict:** no frozen contribution altered; environment reproducibly provisioned; interception point verified in the installed package; live-execution credential blocker (BLOCKER-3) remains open and is not required until Phase 6.

## Phase 2B — Scientific Pre-registration (COMPLETE)

Canonical frozen experiment identifier (Merkle root): **`ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618`**

| Paper Section | Definition | Theorem | Architecture Component | Implementation Artifact | Status | Evidence |
|---|---|---|---|---|---|---|
| §IV-A/B (Def. 2, LLC), §X (domain instantiations); LCP-6 R1–R6 | Def. 1, Def. 2 | Inv. 3 (LLC) | Predicate vector (instances of Def. 1) | `predicate_manifest.json` | FROZEN | leaf `288c7a26…3511`; blind-authored from §X; existing families only |
| §IV-B (`d_i=max(0,m_i−θ_i)`) | — | — | Threshold vector θ | `threshold_manifest.json` | FROZEN | leaf `edb59650…447b`; binary/structural, one env-derived numeric (amount≤balance), no tuned constant |
| Def. 1/2 (complete mediation); V2 D-6 | Def. 1 | Inv. 1 (mediation) | Per-tool EEA classification | `tool_mapping_manifest.json` | FROZEN | leaf `a5358362…f1ea`; 25 EEA / 44 read-only of 69 distinct tools |
| §X-A (destination-recognition gate); V2 D-2 | — | — | R3 recognized-set gate (attack-independent) | `recipient_derivation_manifest.json` | FROZEN | leaf `9c2df01e…448e`; sets derived from benign env only |
| §VIII-G (metrics), §IX-F.2 (protocol freeze) | — | Inv. 3/4 exercised; 1/2 substrate NOT (Tier-S) | Metrics, arms, models, power gate | `evaluation_manifest.json` | FROZEN | leaf `61543f55…708c`; paired ≥2-model design, baseline-TASR gate, outcome-irrespective |
| V2 Part 2; refinement #1 (repo freeze) | — | — | Version freeze | `version_manifest.json` | FROZEN | leaf `7666f872…01e1`; repo+tag+commit `a75aba76…`+archive sha `1bce68f4…` |
| Verification Part 5 leaf #7; V2 D-9 | — | — | Benchmark inventory | `dataset_manifest.json` | FROZEN | leaf `057cae8f…c0b`; from installed benchmark: 97 users / 27 inj-tasks / **629 cases** / 69 tools |
| Governance #3; Verification Part 5 | — | — | Merkle commitment | `merkle_root.json` | FROZEN | root reproducible across runs + independently recomputed (PASS) |

### D-9 reconciliation (required paper action, recorded)
Pinned benchmark_version **v1**: injection-case count **629 == paper**, so the 629 anchor matches exactly. User-task count is **97 (installed) vs 79 (paper §IX-F)** — the paper must be corrected **79 → 97** with a note; this is the honest D-9 resolution (pin the release matching the 629 anchor; correct the mismatched count).

### Scientific-preservation check (Phase 2B)
| Frozen construct | Changed in Phase 2B? | Evidence |
|---|---|---|
| Γ authorization / SAFE_STATE / LLC | NO | manifests instantiate existing families; `Γ=max_i d_i, Π=1[Γ=0]` unchanged; no new predicate type |
| Gamma / L-DREA / LUIPM / Evidence Quad / Hydra Ledger | NO | no source touched; manifests are pre-registration data |
| Runtime/Execution Sovereignty | NO | theorems untouched; Tier-S coverage bound recorded |
| LAB / ConcurBench / ASB | NO | native benchmarks untouched |
| AgentDojo source | NO | read-only introspection; not edited |
| Paper | NO | not modified (79→97 correction recorded as a REQUIRED future revision, not applied here) |
| `external_validation/` (historical) | NO | preserved untouched |

**Phase 2B verdict:** seven manifests frozen and Merkle-committed (`ce8c8467…f618`) entirely offline from the installed benchmark + frozen §X semantics; blind-authoring preserved (injection corpus never inspected); root reproducible and independently verifiable; no frozen contribution altered. **Freeze rule now in force: no predicate/threshold/mapping/recipient may change without re-opening the anti-circularity gate.**

## Phase 3A — Runtime Interception (COMPLETE)

| Paper Section | Definition | Theorem | Architecture Component | Implementation Artifact | Status | Evidence |
|---|---|---|---|---|---|---|
| Def. 2(i) complete mediation; V2 Part 1 (sole chokepoint) | Def. 1, Def. 2 | Inv. 1 (mediation form) | Externalization boundary interposition | `interception/governed_runtime.py` (`GammaGovernedRuntime`) | COMPLETE | injected via AgentDojo's own `runtime_class`; `run_function` gated; **no AgentDojo source modified** |
| §IV-B (LLC `Γ=max·d_i`, `Π=1[Γ=0]`), class veto | — | Inv. 3, Inv. 4 | Γ decision engine (REUSED) | `interception/gamma_bridge.py` → `gamma_test_runner.evaluate_decision` | COMPLETE | engine imported, not reimplemented; `gamma_test_runner.py` UNCHANGED |
| §X predicate families; R1–R6 | Def. 1 instances | — | Predicate instantiation | `interception/predicate_evaluation.py` | COMPLETE | env-derived recognized sets (Recipient Manifest) + amount≤balance (Threshold Manifest); no invented predicate |
| Verification Part 5 (Merkle commitment) | — | — | Freeze integrity gate | `interception/frozen_policy.py` | COMPLETE | recomputes + asserts Merkle root `ce8c8467…f618` at runtime construction |
| §2.3 SAFE_STATE; §5 fail-closed | — | Inv. 3 | Deny path | `GammaGovernedRuntime.run_function` | COMPLETE | SAFE_STATE returns deny, side effect blocked (verified) |

### Verification (offline, no LLM, no benchmark scoring)
Real runtime + real env: read-only pass-through ✅; recognized recipient → PERMIT → real side effect ✅; unrecognized recipient → SAFE_STATE → blocked ✅; over-balance → SAFE_STATE ✅; two suites (banking, workspace) ✅; frozen root checked at construction ✅. **RESULT: ALL CHECKS PASS.**

### Scientific-preservation check (Phase 3A)
| Frozen construct | Changed? | Evidence |
|---|---|---|
| Γ authorization / LLC / SAFE_STATE | NO | reused `evaluate_decision` verbatim; `gamma_test_runner.py` git-unchanged |
| Gamma / L-DREA / LUIPM / Evidence Quad / Hydra Ledger | NO | Evidence/Hydra NOT emitted in 3A (later phases); no engine modified |
| Runtime/Execution Sovereignty | NO | theorems untouched; Tier-S decision layer only |
| LAB / ConcurBench / ASB | NO | native benchmarks untouched |
| AgentDojo source | NO | interposition via `runtime_class`; no `.py` under site-packages/agentdojo modified |
| Frozen manifests / Merkle root | NO | read-only; integrity asserted at load |
| Paper | NO | not modified |

**Phase 3A verdict:** runtime interception implemented at the sole approved chokepoint via AgentDojo's own injection parameter; Γ decision reused (no second engine); predicates instantiated from frozen manifests (none invented); PERMIT/SAFE_STATE verified to execute/block real side effects offline; zero modification to Gamma, AgentDojo, manifests, or the paper. **STOP — Evidence Quad, Hydra Ledger, replay, metrics, reports, and benchmark execution belong to later phases.**

## Phase 3A-R — Manifest-Authoritative Refactor + v2 Re-freeze (COMPLETE)

**Pre-registration superseded (pre-execution, content-preserving):** v1 root `ce8c8467…f618` → **v2 root `5421a3fdab502a518c1f2d50cffc7eb3c5497d61187ad24d31349b3af37cbc1e`**. Rationale recorded in `merkle_root.json` (`supersession_rationale`): machine-readable execution policy relocated FROM Python INTO the manifests; blind-authoring preserved (bindings from public tool signatures + §X, injection corpus never inspected); scientific content unchanged. Leaves 4/6/7 (recipient/version/dataset) byte-identical; only predicate/threshold/tool-mapping/evaluation changed.

| Refactor item | Requirement | Implementation Artifact | Status | Evidence |
|---|---|---|---|---|
| 1 | No hardcoded gate map | `predicate_manifest.family_metadata.*.gamma_slot`; `gamma_bridge` reads `policy.family_slot` | DONE | grep: no `_FAMILY_TO_GATE` |
| 2 | Tool→arg mapping from manifest | `tool_mapping_manifest.*.argument_binding`; `predicate_evaluation` reads it | DONE | grep: no `_TOOL_SPEC`; `send_money` binding in manifest |
| 3 | Threshold Manifest authoritative | `threshold_manifest.machine_readable` (`env_upper_bound` directive); evaluator interprets `env_ref` | DONE | grep: no raw `amount>balance`; over-balance test PASS |
| 4 | Unknown tool → SAFE_STATE | `evaluation_manifest.unknown_tool_policy`; `governed_runtime` fail-closed | DONE | unknown-tool test PASS (denied, not executed) |
| 5 | Structural predicates explicit | `family_metadata.*.evaluation_status = EXCLUDED_BY_POLICY_TIER_S`; evaluator reports status | DONE | decision records `evaluation_status` |
| 6 | Dependency inversion | `GammaGovernedRuntime(policy=, bridge=, evaluator=)` | DONE | DI test PASS |
| 7 | Expanded verification | temp-dir integrity tests | DONE | unknown / missing / tamper / invalid-root / version-mismatch all PASS (16/16) |

### Scientific-preservation check (Phase 3A-R)
| Frozen construct | Changed? | Evidence |
|---|---|---|
| Γ / LLC / SAFE_STATE | NO | `gamma_test_runner.py` git-UNCHANGED; engine reused |
| Predicates / thresholds / mappings (science) | NO | identical content; only re-encoded prose/Python → machine-readable manifest fields |
| Merkle root | **SUPERSEDED v1→v2** | pre-execution, content-preserving, documented; not a silent edit |
| AgentDojo source | NO | no `.py` modified |
| Paper | NO | not modified (v1→v2 root change recorded for the eventual §IX-F manifest-hash entry) |

**Phase 3A-R verdict:** _(SUPERSEDED by Phase 3A-R2 — the v2 re-freeze was reverted on review; the original scientific root ce8c8467 is restored immutable and binding moved to a separate Layer-2 manifest.)_

## Phase 3A-R2 — Two-Layer Split: Immutable Science + Derived Implementation Binding (COMPLETE)

Per review: the v2 re-freeze was **reverted**. The seven scientific manifests are restored **byte-identical to their original v1 content (root `ce8c8467…f618`)** and are permanently immutable. All implementation binding moved to a new, separate **Layer-2 artifact**.

### Artifact classification (scientific vs implementation)
| Layer | Artifact | Root / SHA | Mutable? |
|---|---|---|---|
| **1 — Scientific** | predicate / threshold / tool-mapping / recipient / evaluation / version / dataset manifests | Merkle root `ce8c8467…f618` | **NO — frozen forever** |
| **2 — Implementation** | `Execution_Binding_Manifest.json` (derived from Layer 1 + public signatures) | canonical sha `a2b816e0…d0a4`; `derived_from_scientific_root = ce8c8467…` | regenerable, provenance-locked |

| Refactor item | Requirement | Layer-2 artifact / code | Status | Evidence |
|---|---|---|---|---|
| — | Restore original 7 manifests + root | reverted `build_preregistration.py`; regenerated | DONE | root == `ce8c8467…` (byte-identical) |
| — | Separate Execution Binding Manifest | `Execution_Binding_Manifest.json` via `build_execution_binding.py` | DONE | deterministic (identical sha across runs); validated vs frozen tool-mapping + public signatures |
| 1 | Gamma-slot map from manifest | `family_metadata.*.gamma_slot`; `GammaBridge` reads `binding.family_slot` | DONE | no `_FAMILY_TO_GATE` in runtime |
| 2 | Tool→arg from manifest | `tool_argument_binding`; evaluator reads `binding.tool_binding` | DONE | no `_TOOL_SPEC` in runtime |
| 3 | Threshold authoritative | `family_metadata.*.threshold` (`env_upper_bound`); evaluator interprets `env_ref` | DONE | no raw `amount>balance`; over-balance test PASS |
| 4 | Unknown tool → SAFE_STATE | binding `unknown_tool_policy`; runtime fail-closed | DONE | unknown-tool test PASS |
| 5 | Structural predicates explicit | `evaluation_status = EXCLUDED_BY_POLICY_TIER_S`; evaluator reports status | DONE | decision records `evaluation_status` |
| 6 | Dependency inversion | `GammaGovernedRuntime(scientific=, binding=, bridge=, evaluator=)` | DONE | DI test PASS |
| 7 | Expanded verification | Layer-1 + Layer-2 integrity tests | DONE | 20/20 PASS (functional, unknown, L1 missing/tamper/invalid-root/version, L2 missing/tamper/provenance, DI) |

### Determinism of the Execution Binding Manifest
Generated by `build_execution_binding.py` from the 7 frozen manifests + pinned public tool signatures; regenerating yields a byte-identical file (canonical sha `a2b816e0…` reproduced across runs). The generator **validates** every binding against the frozen tool-mapping (a binding cannot introduce a predicate the frozen science did not assign — it caught and rejected an inconsistent `update_scheduled_transaction` binding) and against public v0.1.35 signatures.

### Scientific-preservation check (Phase 3A-R2)
| Frozen construct | Changed? | Evidence |
|---|---|---|
| The 7 scientific manifests + Merkle root | NO | restored byte-identical; root `ce8c8467…` reproduced |
| Γ / LLC / SAFE_STATE | NO | `gamma_test_runner.py` git-UNCHANGED; engine reused |
| Execution Binding Manifest | new **implementation** artifact | contains zero scientific content; provenance-locked to `ce8c8467…` |
| AgentDojo source | NO | no `.py` modified |
| Paper | NO | not modified |

**Phase 3A-R2 verdict:** the scientific pre-registration is frozen exactly once (root `ce8c8467…`, immutable forever); implementation binding lives in a separate, deterministically-derived, provenance-locked Layer-2 manifest; the runtime reads both layers and holds no policy; 20/20 checks PASS offline; Gamma and AgentDojo untouched. The reviewer's "how many times was it re-frozen?" question is eliminated: **once.** **STOP for approval before Phase 3B.**
