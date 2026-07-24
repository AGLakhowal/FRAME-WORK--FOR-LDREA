# PHASE 3A CERTIFICATION

**Purpose:** this document does not describe what was built. It **certifies what did NOT change** after the Phase 3A runtime-interception work. It is the pre-condition gate for Phase 3B.

**Scope of Phase 3A:** runtime interception + Γ decision only. No Evidence Quad emission, Hydra Ledger, replay, metrics, reports, dashboards, benchmark execution, or paper edits were performed.

**Verification basis:** git working-tree diff, SHA-256 digests, the Merkle commitment, and a 20/20 offline test suite. All facts below were captured on the environment recorded in §4.

---

## 1. Scientific Preservation

The following are certified **unchanged** — byte-identical where a file exists, or semantically untouched where the construct is a definition/theorem carried by the (unmodified) paper/spec.

| Construct | Where it lives | Certification | Evidence |
|---|---|---|---|
| **Gamma engine** | `gamma_test_runner.py` | **Byte-identical** | git: UNCHANGED; sha256 `20056c40b5805bf1107130f4fcd46460a831694b4c2ff0badfc93b10434485ab` |
| **Γ aggregation** (`Γ=max·d_i`, `Π=1[Γ=0]`, class veto) | `gamma_test_runner.evaluate_decision` | **Byte-identical; reused, not reimplemented** | interception imports the function; no second engine (grep: no `_FAMILY_TO_GATE`/`_TOOL_SPEC` in runtime) |
| **SAFE_STATE** | Gamma engine + FULL_SPEC §2.3 | **Semantically unchanged** | deny path returns SAFE_STATE via reused decision; definition not altered |
| **LUIPM** | frozen term | **Not engaged** | interception never references it; no file touched |
| **Evidence Quad** | `gamma_test_runner.py` (App./§3.3) | **Unchanged; NOT emitted in 3A** | out of Phase-3A scope; no code path emits it |
| **Hydra Ledger** | `gamma_test_runner.py` (§6.3) | **Unchanged; NOT emitted in 3A** | out of scope; untouched |
| **Runtime Sovereignty** (Inv. 6) | IEEE Paper §VI; FULL_SPEC | **Unchanged** | no theorem edited; paper not modified |
| **Execution Sovereignty** (Inv. 1) | IEEE Paper §VI; App. D (TLA⁺) | **Unchanged** | not modified; Tier-S coverage bound only (no new claim) |
| **LAB v1.0** | `gamma_test_runner.py`, benchmark logic | **Unchanged** | git: UNCHANGED |
| **ConcurBench** | `concurbench_full.py` | **Unchanged** | git: UNCHANGED |
| **ASB** | `concurbench_full.py` (ASB families) | **Unchanged** | git: UNCHANGED |
| **Definitions** (1, 2, 4; CTR; H1–H4) | IEEE Paper §IV/V | **Unchanged** | paper not modified |
| **Theorems / Invariants** (Prop. 1–2, Cor. 1–2, Inv. 1–6) | IEEE Paper §VI | **Unchanged** | paper not modified |
| **Metrics** (UER/FPR/FDR/FCR/RDR/…) | §VIII-G; `gamma_test_runner.py` | **Unchanged** | not computed in 3A; definitions untouched |
| **Formal assumptions** (A1–A4) | IEEE Paper §VI-A | **Unchanged** | paper not modified; Tier-S (A3 substrate) explicitly not exercised, not redefined |

**Supporting Gamma/benchmark files certified UNCHANGED (git):** `gamma_test_runner.py`, `concurbench_full.py`, `stress_test.py`, `fcr_test.py`, `full_spec_conformance.py`, `gamma_map_raw.py`, `gamma_replay_verify.py`, `concurbench_conformance_check.py`.

**Scientific pre-registration:** the seven frozen manifests are **byte-identical** to their original Phase-2B content; regeneration reproduces Merkle root `ce8c8467…f618` (§4). The earlier Phase-3A-R v2 re-freeze was fully reverted; the pre-registration was frozen **once**.

**Honest disclosure (files modified BEFORE Phase 3A, not by this work):** git shows five pre-existing modifications from the prior (rejected) synthetic attempt: `.DS_Store`, `concurbench_full_report.json`, `gamma_report.html`, `gamma_report_page.py`, `run_all.py`. These are report **outputs** and reporting/orchestration glue — **not scientific logic and not the LAB/ConcurBench/ASB benchmark definitions**. None were touched during Phases 2A–3A; they remain flagged for revert/quarantine in a later phase.

---

## 2. Engineering Preservation — AgentDojo

**AgentDojo was never modified.** The integration is interposition-only.

| AgentDojo aspect | Certification | Evidence |
|---|---|---|
| Benchmark **prompts** | Unchanged | no file under `site-packages/agentdojo` modified |
| Benchmark **tasks** (user + injection) | Unchanged | task suites loaded read-only; 97 user / 27 injection / 629 cases enumerated, not altered |
| Benchmark **scoring** (utility/security checkers) | Unchanged | not touched; used read-only as ground truth |
| Benchmark **tools** | Unchanged | 69 tools enumerated read-only; none edited |
| Benchmark **evaluation** methodology | Unchanged | no benchmark run performed; harness untouched |
| AgentDojo **source (`.py`)** | Unchanged | `find site-packages/agentdojo -name '*.py' -newer <freeze>` → empty |

AgentDojo `0.1.35` is consumed as an installed, pinned dependency. No fork, no edit, no vendored copy.

---

## 3. Runtime Certification

**Interception mechanism.** L-DREA is interposed at the sole approved chokepoint — `FunctionsRuntime.run_function` (AgentDojo `agent_pipeline/tool_execution.py:103`) — by a subclass:

```
class GammaGovernedRuntime(FunctionsRuntime):   # governed_runtime.py:31
    def run_function(self, env, function, kwargs, raise_on_error=False):
        # classify (Layer 1) → unknown: SAFE_STATE | read-only: super() | EEA: reused Γ → PERMIT/SAFE_STATE
```

**`runtime_class` injection is the ONLY integration mechanism.** AgentDojo's `TaskSuite.run_task_with_pipeline` exposes `runtime_class: type[FunctionsRuntime] = FunctionsRuntime` (`task_suite.py:345`) and constructs `runtime = runtime_class(self.tools)` (`task_suite.py:380`). Passing `GammaGovernedRuntime` there is a first-class, documented extension point — not a modification.

**No monkey-patching.** Certified by inspection: the interception layer contains **no** `setattr`, `unittest.mock`, `.patch`, `__dict__` mutation, or reassignment of any `agentdojo.*` attribute (grep over `interception/` → none). The only `agentdojo` reference is `from agentdojo.functions_runtime import FunctionsRuntime` for subclassing. AgentDojo classes, functions, and instances are never mutated at runtime.

**On SAFE_STATE the real function is never called:** the override returns `("", deny_error)` without invoking `super().run_function`, so no side effect occurs (verified: transaction/email counts unchanged on denial).

---

## 4. Reproducibility

| Field | Value |
|---|---|
| **Scientific Merkle root** (immutable, 7 manifests) | `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618` |
| **Execution Binding SHA** (Layer-2, canonical) | `a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1` |
| Execution Binding provenance | `derived_from_scientific_root = ce8c8467…`; public-signature snapshot `746c3ef5…` |
| **L-DREA repository commit** | `763008a32e9225f5086eb8c6794625c88da0bf1b` (branch `main`) |
| **AgentDojo version** | `0.1.35`, commit `a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` (tag `v0.1.35`), MIT, benchmark_version `v1` |
| **Python** | CPython `3.11.15` (uv-managed standalone) |
| **Package manager** | uv `0.11.13` (venv is pip-less; hashed lock `agentdojo_requirements.lock`) |
| **Platform** | Darwin arm64 / macOS `26.5.1` (Apple silicon) |
| **Gamma engine sha256** | `20056c40b5805bf1107130f4fcd46460a831694b4c2ff0badfc93b10434485ab` (UNCHANGED) |

Both the scientific Merkle root and the Execution Binding SHA are reproducible: regenerating from `build_preregistration.py` and `build_execution_binding.py` yields byte-identical output (verified across runs).

---

## 5. Dataset Inventory Note — 97 vs 79 (REQUIRES VERIFICATION)

**Discrepancy.** The regenerated inventory from the installed, pinned AgentDojo `v0.1.35` (benchmark_version `v1`) reports **97 user tasks**; the manuscript (§IX-F) states **79 tasks**.

**What is corroborated.** The **629 injection-case** anchor matches `v1` *exactly*: banking 16×9=144, slack 21×5=105, travel 20×7=140, workspace 40×6=240 → **629**. This strongly indicates `v1` is the release the paper's 629 figure refers to, and that **97** is the true user-task count of that release.

**Plausible explanations (none assumed correct):**
1. The paper's **79** referenced an earlier AgentDojo pre-release/snapshot whose user-task count differed, while the 629 figure was carried from a later count — an internal inconsistency in the manuscript draft.
2. **79** counted a **filtered subset** of user tasks (e.g., excluding a category, or only tasks reachable by a particular agent) rather than the full 97.
3. **79** is a transcription/typo error for a nearby figure.
4. The paper mixed counts from two AgentDojo versions (user tasks from one, injection cases from another).

**Disposition (mandatory before manuscript revision):**
- **Do not change the paper** in Phase 3A.
- **Do not assume** either 79 or 97 is correct.
- Recorded as a required reconciliation item: before §IX-F is revised, confirm which AgentDojo release/subset the "79" referred to, then either (a) correct 79→97 with a note pinning `v0.1.35`/`v1`, or (b) document the subset definition that yields 79. The Evaluation Manifest already flags this (`N_reconciliation.REQUIRED_PAPER_ACTION`).

---

## 6. Unknown-Tool Handling (renamed; not a new policy)

Prior wording "Unknown Tool **Policy**" is renamed to **"Unknown-Tool Handling / Fail-Closed Runtime Handling"** to reflect that this is **implementation behavior, not scientific policy**.

- **Behavior:** a tool absent from the frozen Tool Mapping Manifest is denied (SAFE_STATE) and never executed.
- **It introduces no new policy, predicate, threshold, or authorization rule.** It is the **runtime consequence of Definition 2(i) (complete mediation)** — every candidate action must be mediated — applied to an unclassified tool, **resolved to SAFE_STATE** (FULL_SPEC §2.3, §0.10 non-default-permit).
- **Where recorded:** the Layer-2 `Execution_Binding_Manifest.json` key is now `unknown_tool_handling` (`handling: SAFE_STATE_FAIL_CLOSED`, with a `not_a_new_policy` note and `derived_from: Definition 2(i) + SAFE_STATE`). The runtime method is `ExecutionBinding.unknown_tool_handling()`. (This changed the Layer-2 binding SHA to `a3861927…`; the immutable scientific root `ce8c8467…` is unaffected.)

---

## Verification Summary

Offline suite (no LLM, no benchmark scoring): **20/20 PASS** — functional interception (banking + workspace: pass-through, recognized→PERMIT+executed, unrecognized→SAFE_STATE+blocked, over-balance→SAFE_STATE); unknown-tool fail-closed (denied, not executed); Layer-1 integrity (missing / tamper / corrupt-root / version-mismatch all raise); Layer-2 integrity (missing / tampered-sha / provenance-break all raise); dependency injection (both layers).

## Certification Statement

Phase 3A added a runtime-interception layer that adjudicates AgentDojo tool calls through the **reused** Gamma engine, driven entirely by frozen manifests. It changed **none** of the scientific contributions (§1), **none** of AgentDojo (§2), used **only** `runtime_class` injection with **no** monkey-patching (§3), and is fully reproducible (§4). The one open item is the documented, unresolved **97 vs 79** dataset-inventory discrepancy (§5), which must be reconciled before any manuscript revision and is **not** actioned here.

**STOP.** Phase 3B not started. No benchmark executed. Gamma, AgentDojo, and the paper unmodified.
