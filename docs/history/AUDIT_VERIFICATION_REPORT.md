# AUDIT VERIFICATION REPORT

**Role:** Independent IEEE Artifact-Evaluation reviewer.
**Mandate:** Treat the prior `IMPLEMENTATION_AUDIT_REPORT.md` as a *hypothesis*, not fact. Verify or refute each CRITICAL finding using direct code evidence only. No inference, no speculation, no code changes.
**Method:** Direct reads of the actual source files + the actually-emitted JSON reports + the actually-mapped CSV. Every conclusion below cites `file:line` and, where the claim is about a *value*, the emitted report that carries it.

**Bottom line up front:** All five audit findings are **VERIFIED (TRUE)** on direct code evidence. Finding 3 requires a precision correction — the audit's own wording ("adjacency only / copied") is right, but the nuance (what *is* genuinely recomputed vs. what is copied) is spelled out below so it is not overstated in either direction.

---

## FINDING 1 — Label Leakage / Tautological Evaluation

### 1. Finding (as stated by prior audit)
"The Gamma runtime appears to re-derive decisions from predicate columns that were themselves generated directly from the fraud `Class` label." → Every headline safety figure is structurally guaranteed by construction, not empirically earned.

### 2. Evidence (direct code)

**Stage A — the predicate columns are written directly from the `Class` label.**
`gamma_map_raw.py`:
- L122–123: `is_fraud = classes[i] == 1` where `classes = raw["Class"].astype(int).tolist()` (L118). The single branch variable is the raw ground-truth label.
- L132: `harm = HARM_FRAUD if is_fraud else derive_harm_risk(...)` → `HARM_FRAUD = 0.8` (L48).
- L150–164 (`if is_fraud:`): `Gate_A3=False`, `Gate_A7=False`, `Lambda_G=False`, `Gamma=1`, `GammaZero=False`, `ACT_PERMIT=False`, `SAFE_STATE=True`, `Actuated=False`, `Status="SAFE_STATE"`, `ReasonCodes="CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL;SAFE_STATE_DENIAL"`, `FirstFailingGate="Gate_A3"`.
- L166–181 (`else:`): all `Gate_A1..A7=True`, `Lambda_G=True`, `Gamma=0`, `Status="PERMITTED"`, `ReasonCodes="CLASS_0_LEGITIMATE;ALL_GATES_PASS;PERMITTED_ACTUATED"`.
- The module docstring states this openly (L14, L25–28): *"GROUND TRUTH is the real `Class` column … The authorization outcome is driven by that real label."*

**Stage B — the runtime re-derives the decision from exactly those columns.**
`gamma_test_runner.py`, vectorized decision path (the one that produces the reported metrics), L868–892:
- L869–870: deficit for each `NODE_GATE_COLS` = `(~df[c])` — reads `Gate_A1..A7, Lambda_G, TOKEN_VALID, AuthoritySignatureValid` (the mapper-written gates).
- L871: `HARM_RISK > harm_threshold` — reads the mapper-written `HARM_RISK` (0.8 vs ≤0.049 against θ=0.5).
- L883–886: `DerivedGammaClass = ReasonCodes contains "CLASS_1"` — reads the mapper-written `ReasonCodes` string, whose "CLASS_1" token was written from `is_fraud`.
- L889–892: `DerivedPi = (DerivedGammaG==0) & (DerivedGammaClass==0)`; `DerivedDecision = PERMIT/SAFE_STATE`.

**Stage C — ground truth for FPR/FDR is the *same* mapper column.**
L946–959: `NormalizedStatus = Status` (mapper's `Status`, PERMITTED→PERMIT); `truth_permit = NormalizedStatus == PERMIT`; `FalsePermit = derived_permit & ~truth_permit`; `FalseDenial = ~derived_permit & truth_permit`. Both operands trace to `Class`.

**Stage D — the emitted numbers confirm it.**
`gamma_summary.json`: `rows=284807`, `derived_safe_state=492`, `derived_permit=284315`, `match_status_rate=1.0`, `false_permit_count=0`, `false_denial_count=0`, `unauthorized_execution_count=0`. `top_rule_failures`: `Gate_A3=492, Gate_A7=492, Lambda_G=492, HARM_RISK_THETA=492` — the exact four columns the mapper flips for `is_fraud`, and exactly 492 = the fraud count. `sample_fail_rows[].ReasonCodes = "CLASS_1_FRAUD;GATE_A3_HARM_RISK_FAIL;SAFE_STATE_DENIAL"` — verbatim the mapper's hardcoded string (`gamma_map_raw.py:163`).

**Stage E — no independent (feature-based) arm exists.**
A repository grep for any predicate computed from `V1..V28`/`Amount` *without* `Class` returns nothing in the runtime (`gamma_test_runner.py`, `concurbench_full.py`): the only `V1..V28` uses are the mapper's `v_anom = raw[v_cols].abs().sum()` feeding the *legit-row* harm proxy (`gamma_map_raw.py:120,132`), which by construction stays ≤0.049 < θ (`derive_harm_risk` clamps to 0.049, L89) and therefore cannot change any decision. `Amount` never reaches a gate. Detection is never attempted from features.

### 3. Execution Trace

```
raw creditcard.csv  ──►  Class ∈ {0,1}                       (gamma_map_raw.py:118)
                          │
                          ▼  is_fraud = (Class==1)            (:123)
        ┌─────────────────┴──────────────────────────────────┐
   is_fraud = True                                     is_fraud = False
   Gate_A3/A7/Lambda_G = False   (:151-153)            Gate_A1..A7/Lambda_G = True  (:167-169)
   HARM_RISK = 0.80              (:132,146)            HARM_RISK ≤ 0.049           (:88-89,132)
   Status = "SAFE_STATE"         (:161)                Status = "PERMITTED"        (:177)
   ReasonCodes ⊃ "CLASS_1"       (:163)                ReasonCodes ⊃ "CLASS_0"     (:179)
        └─────────────────┬──────────────────────────────────┘
                          ▼  mapped CSV (GAMMA_G0_CREDITCARD_FULL_mapped.csv)
                          ▼
   gamma_test_runner.evaluate_decision()/vectorized path
     DerivedGammaG      = max(¬gates, HARM_RISK>θ, StaleContext, ¬TelemetryFresh)   (:868-876)
     DerivedGammaClass  = ("CLASS_1" ∈ ReasonCodes)                                 (:883-886)
     DerivedPi          = (GammaG==0 ∧ GammaClass==0)                               (:889)
     DerivedDecision    = PERMIT | SAFE_STATE                                       (:892)
                          ▼
     truth_permit       = (Status == PERMIT)      ← SAME mapper column              (:954)
     FalsePermit/FalseDenial = Derived vs truth   ← Class vs Class                  (:957-959)
                          ▼
   Final metrics: agreement 1.0, FPR 0/492, FDR 0, UER 0, 6/6 invariants   (gamma_summary.json / gamma_lab_v1_report.json)
```

### 4. Dependency Graph (per synthesized predicate)

| Predicate (mapper output) | Formula / source | Depends on `Class`? | Amount? | Time? | Derived-risk? | Multi-feature? | External calc? |
|---|---|---|---|---|---|---|---|
| `Gate_A3`,`Gate_A7`,`Lambda_G` | `False if is_fraud else True` (:151-169) | **YES (direct)** | no | no | no | no | no |
| `Gate_A1,A2,A4,A5,A6` | `True` for legit; inherited-template for fraud (:124,167) | via `is_fraud` branch | no | no | no | no | no |
| `Gamma`,`GammaZero`,`ACT_PERMIT`,`ExecutionLegitimacy`,`SAFE_STATE`,`Actuated` | set per branch (:154-176) | **YES (direct)** | no | no | no | no | no |
| `HARM_RISK`,`DomainHazardScore`,`SeverityScore` | `0.8 if is_fraud else derive_harm_risk(amount,v_anom)` (:132,146-148) | **YES (branch selects)** | legit only | no | legit only | legit only (∑\|Vi\|, inert) | no |
| `Status`,`DecisionOutcome` | `"SAFE_STATE"/"PERMITTED"` per branch (:161-178) | **YES (direct)** | no | no | no | no | no |
| `ReasonCodes` (`CLASS_1`/`CLASS_0` token) | literal string per branch (:163,179) | **YES (direct)** | no | no | no | no | no |
| `FirstFailingGate` | `"Gate_A3"/"NONE"` per branch (:164,180) | **YES (direct)** | no | no | no | no | no |
| `TOKEN_VALID`,`AuthoritySignatureValid` | `True` for **all** rows (:184-185) | no (constant) | no | no | no | no | no |
| `HASH_prev`,`HASH_current` | SHA-256(prev‖canon) (:196-203) | indirectly (canon includes Status/Gamma/harm) | no | no | no | no | genuine SHA-256 |
| `TimestampUTC`,`Commit/ActuateTimestamp` | `EPOCH_BASE + Time` (:127-129) | no | no | **YES** | no | no | no |

### 5. Verified: **YES** — audit finding CONFIRMED.
`evaluate_decision()` / the vectorized path is **not** making an independent authorization decision; it is **reconstructing the `Class` label** that `gamma_map_raw.py:150-181` already encoded into the gate/harm/reason/status columns, then comparing that reconstruction against the *same* label (`Status`). Leakage begins at `gamma_map_raw.py:123` (`is_fraud`) and is fully baked by L164/L181. The 100% agreement / 0-FPR / 0-UER / 6-of-6-invariant headlines are tautological by construction.

### 6. Scientific Impact: **HIGH.**
Every credit-card *correctness/detection* headline is a wiring-consistency check, not evidence of detection. An IEEE evaluator cannot read FPR 0/492 or "6/6 invariants hold" as a measured property of the mechanism on this dataset.

### 7. Recommendation (identification only — nothing fixed)
Label every credit-card correctness figure as a *non-compensatory wiring/consistency* check, not detection. A genuine claim would require a second arm whose predicates are computed from `V1..V28`/`Amount` **without reading `Class`**, then scored against `Class`. (No modification performed.)

---

## FINDING 2 — TLC "Verification"

### 1. Finding
Prior audit: TLC is **not executed** during runtime; state counts are attested/hardcoded constants, checked only for internal consistency.

### 2. Evidence
- `gamma_test_runner.py:498-508` (docstring of `verify_tlc`): *"We **cannot re-run TLC here** without the .tla/.cfg sources + tla2tools.jar"*; enumerates escalating tiers 0–3, with *"tier 3 fully-reproduced re-run TLC from source (**out of scope here**)."*
- L521–540: the "verification" reads four **CSV columns** (`TLCSpecHash, TLCCfgHash, TLCTotalStates, TLCViolationCount`). `total_states = int(states.iloc[0])` — read from the trace, not model-checked. V1–V5 are internal-consistency predicates (all hashes equal across rows, states>0, Σviolations==0).
- L545–565: V6/V7 (source-hash binding) run **only if** `spec_path`/`cfg_path` supplied; V8/V9 **only if** `log_path` supplied — else `None`.
- L595–596: with no artifacts, `tier = "tier0_attestation_consistency_only"`.
- **Default invocation supplies none:** `run_all.py:55` → `cmd = [sys.executable, "gamma_test_runner.py", "--no-open"]` (+ optional `--input`). No `--tla-spec`, `--tla-cfg`, or `--tlc-log`. Confirmed in the emitted report: `gamma_lab_v1_report.json` → `tlc_verification.checks.V8_log_states_match = None` (and V6/V7 likewise unsupplied).
- `full_spec_conformance.py:314-327` (`tlc()`): `"distinct_reachable_states": 40192,  # Paper A Appendix A (attested)` and `"max_clock_skew": 1` are **hardcoded literals**; `note` states they *"are attested from Paper A; supply --tlc-log … to machine-verify them here."*
- No `tla2tools.jar` / TLC subprocess exists anywhere: a repo grep for `tla2tools`/`subprocess.*tlc` returns only the argparse help text and docstrings.

### 3. Execution Trace
```
Dashboard (gamma_report_page.py:726-735)  reads  L.tlc_verification.*
        ▲
gamma_lab_v1_report.json  ← verify_tlc()  (runner:1211)
        ▲                        │ reads CSV cols TLCTotalStates/TLCViolationCount (:521-540)
        │                        │ V6/V7/V8/V9 = None  (no --tla-spec/--tla-cfg/--tlc-log; run_all.py:55)
        │                        ▼
        │                   tier0_attestation_consistency_only  (:596)
TLC engine (tla2tools.jar)  ── NEVER INVOKED ──  no subprocess, no .tla/.cfg read
full_spec tlc(): distinct_reachable_states = 40192  ← HARDCODED literal (full_spec_conformance.py:318)
```

### 4. Dependency Graph
`total_states` / `violation_count` (runner) ← `TLCTotalStates`/`TLCViolationCount` CSV columns (constant across rows) ← copied from the golden-trace template (`gamma_map_raw.py:23` "Structural constants … TLC* hashes … are copied from the sample template"). `distinct_reachable_states` (full_spec) ← integer literal `40192`. Neither depends on any execution of a model checker.

### 5. Verified: **YES** — audit finding CONFIRMED.
TLC is **loaded/attested/cached**, not **executed** and not **machine-verified** in the default run. Precisely: at runtime it is **cached** (state counts read from CSV) and **internally attested** (V1–V5 consistency of those cached values). It is **not** executed, and (default run) **not** cross-checked against a real TLC log. The code is honest about this internally (tier labels, docstrings); the concern is presentation as "formal verification."

### 6. Scientific Impact: **HIGH** (as a verification claim) / **LOW** (as engineering).
The mechanism to escalate to a real check exists and is correctly gated; but nothing in the shipped run reaches tier ≥1, so "Execution Sovereignty verified by TLC" overstates what happened.

### 7. Recommendation
Surface the internal tier label (`tier0_attestation_consistency_only`) in the dashboard; rename the field to "attestation" unless `tla2tools.jar` is actually run. (No modification performed.)

---

## FINDING 3 — Replay Hash Chain

### 1. Finding
Prior audit: the hash chain is **copied** from the trace and only its **adjacency** is checked; not fully re-derived.

### 2. Evidence — traced stage by stage

**Stage 1 — Original record → hash generation (GENUINE compute).**
`gamma_map_raw.py:196-203`: `canon = ProposalID|Status|Gamma|harm|PermitTokenID|TimestampUTC`; `cur_hash = sha256(prev_hash + "||" + canon)`; GENESIS-anchored (L116). This is a real SHA-256 chain.

**Stage 2 — Mapped dataset → replay manifest (COPIED, not recomputed).**
`gamma_test_runner.py:646-647`: `hp = df["HASH_prev"]; hc = df["HASH_current"]` — taken verbatim from the CSV. L683–684 write those same strings into each record; L696 sets `evidence_quad.ledger_hash = hc[i]` (a *copy* of `HASH_current`). **No SHA-256 is recomputed from record content here.** The only computation is `adj = (hp[i] == hc[i-1])` (L675) — an adjacency relation over the copied values — and a running `manifest_hash = sha256(bytes of every line)` (L659,672,700).

**Stage 3 — Runner's in-line chain check (ADJACENCY only).**
L908-911: `chain_ok = HASH_prev == HASH_current.shift(1)`. Verifies linkage, **not** that `HASH_current == sha256(prev‖content)`.

**Stage 4 — Independent verifier (`gamma_replay_verify.py`).**
- Genuine: recomputes the **manifest file's** SHA-256 over exact bytes (L48,59,107) and can assert it equals `--expect-sha256` (L129-134).
- Genuine: re-checks **adjacency** `hp == prev_current` with GENESIS anchoring (L74-86).
- **Trivial-by-construction:** `ledger_hash == hash_current` (L90) always holds because Stage 2 *set* `ledger_hash = hc[i]`.
- **Not performed:** nowhere does the verifier (or runner) recompute `sha256(prev ‖ canonical_record)` and compare to `HASH_current`. The content→hash binding is never re-derived; only the *chain topology* and the *file integrity* are.

**Stage 5 — Dashboard.** `gamma_report_page.py:742-779` reads `L.replay_manifest.*` summary values (`manifest_sha256`, `adjacency_all_ok`, `n_records`). Emitted: `hash_chain_links_ok = 284807`, `replay_divergence_count = 0` (`gamma_summary.json`).

### 3. Execution Trace
```
Original record ──► sha256(prev‖canon) ─► HASH_current        GENUINE   (gamma_map_raw.py:200)
                                            │ (written into CSV)
Mapped CSV ─────────► HASH_prev/HASH_current  COPIED verbatim  (runner:646-647)
                                            │
Replay manifest ────► ledger_hash := HASH_current  COPIED      (runner:696)
                      adjacency_ok := hp==prev_hc  RECOMPUTED   (runner:675)
                      manifest_sha256 := sha256(bytes) GENUINE  (runner:659-700)
                                            │
Independent verify ─► file sha256           RECOMPUTED/verified (verify:107,129)
                      adjacency             RECOMPUTED/verified (verify:74-86)
                      ledger_hash==hash_cur  TRIVIAL (set equal) (verify:90)
                      content→hash binding   ✗ NEVER re-derived
                                            │
Dashboard ──────────► reads summary          COPIED             (report_page:742-779)
```

### 4. Dependency Graph
`manifest_sha256` (recomputed) ⟵ raw bytes of manifest. `adjacency_all_ok` (recomputed) ⟵ copied `HASH_prev/current`. `ledger_hash` check (trivial) ⟵ self-reference. `HASH_current` correctness ⟵ **only** trusted from the mapper; no downstream re-derivation.

### 5. Verified: **YES** — audit finding CONFIRMED (with precision).
- **Recomputed & genuinely verified:** the manifest file's SHA-256 (tamper-evidence) and the hash-chain **adjacency** (284,807 links).
- **Copied:** the per-record `HASH_prev/HASH_current` and `ledger_hash`.
- **Never re-derived:** the content→hash binding (`HASH_current ?= sha256(prev‖record)`).
So the audit's "adjacency only / copied, not re-derived" is correct. Its label of the manifest SHA-256 as genuine (its §8.1) is also correct. The two are not in conflict: file-integrity and topology are real; content-integrity re-derivation is absent.

### 6. Scientific Impact: **MEDIUM.**
Tamper-evidence and chain topology are genuinely independently checkable — a real, non-trivial property. But "replay determinism verified" should not be read as "every decision's hash was recomputed from its inputs," which does not happen.

### 7. Recommendation
State precisely what the verifier proves (file integrity + adjacency) vs. what it does not (content re-hash). Adding a content re-derivation step would close the gap. (No modification performed.)

---

## FINDING 4 — Stress Test Values (HIGH / MEDIUM / STRONG FIT / 92–95% / 75–85%)

### 1. Finding
Prior audit: `confidence`, `tackled`, `verdict` and the "78.4% effectively tackled" aggregate are **authored/hardcoded**, not measured.

### 2. Evidence
`stress_test.py`, literal keyword arguments passed into `_scenario(...)`:
- P1 (L90-91): `confidence="HIGH", tackled="92-95%", verdict="STRONG FIT"`.
- P2 (L137): `confidence="MEDIUM", tackled="60-70%", verdict="PARTIAL FIT"`.
- P3 (L189): `confidence="HIGH", tackled="75-85%", verdict="STRONG FIT"`.
- P4 (L226): `confidence="MEDIUM-HIGH", tackled="70-80%", verdict="DEFENSIBLE"`.
- The scenario **predicate booleans** are likewise authored literals, e.g. `P("amount_within_daily_limit", False, "$28M > $5M …")` (L62), `P("integrity_flux_I_phi", False, "0.78 vs threshold 0.30")` (L70).
- Aggregate (L274-279): `lo,hi = tackled.split("-"); mids.append((lo+hi)/2); agg = round(sum(mids)/len(mids),1)` → midpoint of the four hardcoded ranges. Numerically: (93.5+65+80+75)/4 = 78.375 → **78.4** (matches `stress_test_report.json.aggregate.weighted_effectively_tackled_pct` and `range:"74-81%"`, itself a literal string L290).

What **is** genuinely computed: `gamma_decision()` (L34-45) really counts failed in-scope predicates and yields PERMIT/SAFE_STATE; `fail_closed_ok` (L256,265) and `in_scope_pass_rate` (L248) are computed from those results. But those inputs (the `passed` booleans) are authored, and `confidence/tackled/verdict/78.4%` are authored/derived-from-authored.

### 3. Execution Trace
```
Author writes P(name, passed, …) booleans + confidence/tackled/verdict strings   (stress_test.py:60-231)
        │
gamma_decision(preds) ─► counts failed in-scope ─► PERMIT/SAFE_STATE  (COMPUTED, real logic :34-45)
        │                                                   │
_scenario(...) attaches confidence/tackled/verdict LITERALS │ + computes in_scope_pass_rate/fail_closed_ok
        ▼                                                   ▼
run(): agg = mean(midpoint(tackled range strings)) = 78.4   (:274-279, DERIVED FROM LITERALS)
        ▼
stress_test_report.json → dashboard "weighted ~78.4% (74-81%)"  (gamma_report_page.py:146-147)
```

### 4. Classification Table

| Value | Source (file:line) | Measured | Computed | Estimated | Expert judgement | Hardcoded |
|---|---|---|---|---|---|---|
| `confidence` HIGH/MEDIUM/MEDIUM-HIGH | :90,137,189,226 | | | | ✓ | ✓ (literal) |
| `tackled` 92-95% / 60-70% / 75-85% / 70-80% | :91,137,189,226 | | | ✓ | ✓ | ✓ (literal) |
| `verdict` STRONG FIT / PARTIAL FIT / DEFENSIBLE | :91,137,189,226 | | | | ✓ | ✓ (literal) |
| `weighted_effectively_tackled_pct` 78.4 | :274-279 | | ✓ (arithmetic) | | | ← of hardcoded inputs |
| `range` "74-81%" | :290 | | | ✓ | ✓ | ✓ (literal) |
| predicate `passed` booleans | :62-231 | | | | ✓ | ✓ (literal) |
| `decision` PERMIT/SAFE_STATE | gamma_decision :34-45 | | ✓ (real logic) | | | |
| `fail_closed_ok`, `in_scope_pass_rate` | :248,256,265 | | ✓ | | | |

### 5. Verified: **YES** — audit finding CONFIRMED.
The five flagged values are hardcoded authored/expert-judgement strings; the 78.4% headline is a deterministic mean **of hardcoded ranges** (computed-of-hardcoded). The fail-closed decisions themselves are real computations over authored inputs.

### 6. Scientific Impact: **MEDIUM.**
"78.4% effectively tackled" reads as a benchmark metric but is author-assessed coverage. The genuine, defensible outputs are `fail_closed_ok` / `in_scope_pass_rate`.

### 7. Recommendation
Relabel `confidence/tackled/verdict/78.4%` as "author-assessed (non-empirical)"; keep the computed `fail_closed_ok`/`in_scope_pass_rate` as the actual results. (No modification performed.)

---

## FINDING 5 — Static Policy References

### 1. Finding
Prior audit (P3): `spec_policy_reference_band_7_1` is a static block — paper thresholds *displayed but not checked* this run.

### 2. Evidence
`gamma_test_runner.py:1396-1409` — `spec_policy_reference_band_7_1` is a dict of **string thresholds**: `ICS_integrity_confidence ">= 0.90"`, `PR_LCB_robustness_lower_bound ">= 0.80"`, `CI_WIDTH "<= 0.03"`, `DeltaV_stability_residual "<= 0"`, `C_coherence ">= C_STAR (default 0.85)"`, `PTP_skew "<= 1 ms"`, `cycle_latency "<= 100 ms (P95)"`, `ER_LOCAL_evidence_commit "= 1.0"`, plus a `hard_stops` list. These are text, not comparisons.
- Its own `note` (L1397-1399) states: *"Listed as normative reference; **this dataset run enforces the gate/harm/token/hash/ordering rules above**"* — i.e., the run enforces a *different* set, not these bands.
- Consumed for **display only**: `gamma_report_page.py:648`: `const bands = GR.spec_policy_reference_band_7_1 || {};` — rendered, never compared against any computed `ICS`/`PR_LCB`/`CI_WIDTH`/`DeltaV`/`C`/`PTP`/latency value.
- No code path evaluates any run value against these strings: a grep for `ICS_integrity_confidence`, `PR_LCB`, `DeltaV_stability`, `C_STAR` outside this literal block and the JS render returns nothing that performs a `>=`/`<=` test.
- Related: `PolicyHash` (`gamma_report_page.py:761`, runner:1103) is displayed per-row provenance; it is not an executed policy check either.

### 3. Execution Trace
```
gamma_test_runner.py:1396-1409  spec_policy_reference_band_7_1 = { "...>=0.90", "...<=0.03", ... }  LITERAL
        │  (written into gamma_lab_v1_report.json)
        ▼
gamma_report_page.py:648  bands = GR.spec_policy_reference_band_7_1  ──►  rendered as reference text
        │
        ✗ no branch compares any run-computed ICS / PR_LCB / CI_WIDTH / DeltaV / C / PTP / latency to these bands
```

### 4. Dependency Graph
`spec_policy_reference_band_7_1` ⟵ string literals only. Out-edges: → JSON report → dashboard render. In-edges from runtime computation: **none**. It is a leaf display node with no enforcement wiring.

### 5. Verified: **YES** — audit finding CONFIRMED.
Every displayed FULL_SPEC §7.1 band is **Documentation / Display-only / Never executed** this run. The code self-documents this (the `note`). It is *normative reference text*, not a runtime result.

### 6. Scientific Impact: **LOW** (correctly disclosed) → **MEDIUM** if a reader mistakes the bands for checks that passed.
The `note` mitigates, but the bands sit adjacent to genuinely-checked rules and could be misread as enforced.

### 7. Recommendation
Visually separate "normative reference (not checked this run)" from computed results, or compute and compare the bands. (No modification performed.)

---

## SUMMARY TABLE

| # | Finding | Verified? | Where leakage/gap begins | Scientific Impact |
|---|---|---|---|---|
| 1 | Label leakage / tautological evaluation | **YES (TRUE)** | `gamma_map_raw.py:123` → gates/status/reason from `Class`; re-read at `gamma_test_runner.py:868-892,954` | **HIGH** |
| 2 | TLC not executed (attested/cached) | **YES (TRUE)** | `verify_tlc` tier0 default; `full_spec_conformance.py:318` literal `40192`; no `tla2tools.jar` | **HIGH** (as verification claim) |
| 3 | Replay hash chain copied; adjacency-only | **YES (TRUE)** | manifest copies `HASH_*` (`:646-647,696`); content→hash never re-derived. File-SHA & adjacency ARE genuine | **MEDIUM** |
| 4 | Stress values authored/hardcoded | **YES (TRUE)** | `stress_test.py:90-91,137,189,226`; 78.4% = mean of literals `:274-279` | **MEDIUM** |
| 5 | Static policy references display-only | **YES (TRUE)** | `gamma_test_runner.py:1396-1409` literals; rendered `gamma_report_page.py:648`, never compared | **LOW→MEDIUM** |

### Reviewer's determination
All five CRITICAL findings of the prior audit are **objectively true on direct code evidence**. The prior audit is **not refuted on any of the five points**. The only refinement is to Finding 3: the audit is right that hashes are copied and only adjacency is re-checked, and equally right (its §8.1) that the manifest's own SHA-256 and the adjacency traversal are genuinely, independently recomputable — these are consistent, not contradictory, and this report states exactly which bytes are re-derived and which are trusted.

Separately corroborated in passing (not among the five, but load-bearing for Finding 1's blast radius): the reported `derived_safe_state = 492` equals the fraud count exactly, and `top_rule_failures` are precisely the four columns the mapper flips for `is_fraud` — direct numeric confirmation that the decision reconstructs the label rather than detecting from features.

**No code was modified. No refactor, redesign, or improvement was applied. Forensic verification only.**
