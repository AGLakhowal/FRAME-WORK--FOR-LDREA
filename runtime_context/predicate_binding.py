#!/usr/bin/env python3
"""Runtime Predicate Binding `B` — evidence -> engine-input schema (Commit 5.1-B).

The single missing link of the L-DREA pipeline, implemented EXACTLY as the frozen scientific
specification defines it:

    Execution Evidence Bundle (evidence-only)
              │   B  (this module)
              ▼
    Execution Evidence Bundle (bound decision schema)
              │   eeb_to_engine (Commit 4.1, FROZEN, pure remap)
              ▼
    evaluate_decision (FROZEN)  ->  Gamma  ->  Decision

`B : E -> S` is a PURE, PROVENANCE-PRESERVING map with exactly the three admissible per-field
outcomes fixed by PREDICATE_BINDING_SCIENTIFIC_SPECIFICATION.md §3 and the classification in
PREDICATE_BINDING_FINAL_SPECIFICATION.md / DEPLOYMENT_POLICY_SPECIFICATION.md:

  (1) CARRY               — a plane-native PRESENT value is transported VERBATIM into its schema
                            slot (no transform).
  (2) ABSENT -> FAIL-CLOSED — an ABSENT/DEGRADED value is mapped to the schema representation the
                            FROZEN non-default-permit policy treats as a deficit (EEB §6;
                            FULL_SPEC 2.3/0.10). `B` does NOT decide what absence means; it marks
                            the availability fact in the deficit-direction the frozen engine
                            already reads, and the frozen engine converts it to SAFE_STATE.
  (3) UNSUPPORTED -> OUT-OF-SLICE — a predicate whose plane is not produced in this arm is not
                            fabricated (RUNTIME_EVIDENCE_ARCH §6; P7 "do not invent").

Admissibility constraints (spec §3, binding): `B` (a) reads each field only from its native
plane; (b) applies NO threshold, comparison, or numeric transform — thresholds live in
policy/engine, never here; (c) NEVER reads `Class`; (d) is deterministic over persisted evidence.

What `B` NEVER does: authorize, compute Gamma / SAFE_STATE / a decision, call evaluate_decision,
threshold a raw delta into a boolean, derive or invent a policy value (`L_amt`, θ_fresh), admit a
`V1..V28` HARM proxy (governance-rejected — PREDICATE_BINDING_FINAL_SPECIFICATION.md §3 (4a)),
read `Class`, or fabricate evidence. It is a TRANSFORMATION LAYER ONLY.

Credit-card arm (this deployment): no risk service (plane D absent), no authority service (plane
C absent), and no operator-declared observable gate-set / SLA. Under the deployment contract's
missing-policy behaviour (DEPLOYMENT_POLICY_SPECIFICATION.md P12) and Gap-3(a) full-vector
fail-closed, every decision predicate input therefore resolves to its fail-closed representation
and the FROZEN engine yields SAFE_STATE for every row — the degenerate, zero-parameter, all-deny
result the corpus blesses as "demonstrating fail-closed safety." No SLA is invented to avoid it.

Discipline (matching 2.1-2.5 / 4.1 / 5.1): standard library only; Python 3.9 compatible; NOT a
time source (envelope carried from the source bundle / injected); reuses the Commit 2.1
EvidenceField + the Commit 2.5 assembler (no new bundle model); imports NO engine
(gamma_test_runner) — the engine's NODE_GATE_COLS ordering is supplied by the caller, exactly as
Commit 4.1 does, so there is no import cycle. Commit 5.1-B is UNCONSUMED scaffolding: nothing in
the reported benchmark path imports this module; it changes no metric and no benchmark.
"""
from __future__ import annotations

from typing import Sequence

from .execution_evidence_bundle import (
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod, ExecutionEvidenceBundle,
)
from .assembler import ExecutionEvidenceBundleAssembler

_PRODUCER = "rcl.predicate_binding"

# --------------------------------------------------------------------------- #
# Fail-closed schema representations.
#
# These are NOT invented policy values. Each is the deficit-direction the FROZEN engine
# (gamma_test_runner.py:133-178, evaluate_decision) already reads; `B` only encodes the
# availability fact "evidence ABSENT" into that frozen direction so the frozen engine converts
# it to a deficit (EEB §6 fail-closed; FULL_SPEC 2.3/0.10 non-default-permit):
#
#   * gate boolean   — engine deficits on `not row[g]`      -> fail-closed = False (not satisfied)
#   * StaleContext   — engine deficits on `row["StaleContext"]` -> fail-closed = True  (assume stale)
#   * TelemetryFresh — engine deficits on `not row["TelemetryFresh"]` -> fail-closed = False (not fresh)
#   * class veto     — no non-Class veto producer in this arm; Class is NEVER read     -> "" (no veto)
#   * HARM_RISK      — governance service ABSENT and the V1..V28 proxy is REJECTED, so the HARM
#                      predicate is OUT-OF-SLICE. The engine unconditionally evaluates
#                      `HARM_RISK > theta`, so a numeric placeholder is required; 0.0 asserts NO
#                      positive hazard (B fabricates none). The arm's fail-closed is delivered by
#                      the absent authority gates above, not by HARM; 0.0 is immaterial to Gamma/Pi.
# --------------------------------------------------------------------------- #
_FAILCLOSED_GATE = False        # gate not satisfied
_FAILCLOSED_STALE = True        # context assumed stale
_FAILCLOSED_FRESH = False       # telemetry assumed not-fresh
_NO_VETO = ""                   # no non-Class veto evidence (Class never read)
_HARM_ABSENT_PLACEHOLDER = 0.0  # no positive hazard asserted (proxy rejected; out-of-slice)


def _bool_value(ef) -> bool:
    """True iff `ef` is a PRESENT boolean carriable verbatim (outcome 1 for a boolean slot).

    A raw numeric delta or an ABSENT/DEGRADED field is NOT boolean-carriable: converting it would
    require a threshold, which `B` must never apply (spec §3(b)). Such a field falls to
    fail-closed (outcome 2)."""
    return (ef is not None
            and ef.provenance.evidence_quality == EvidenceQuality.PRESENT
            and isinstance(ef.value, bool))


def _failclosed_field(value, plane: OriginPlane, observed_at: str) -> EvidenceField:
    """Fail-closed schema field: the deficit-direction `value` tagged as the availability fact
    ABSENT on its native `plane`. Provenance is preserved (native plane recorded); the ABSENT
    quality states honestly that this is a fail-closed projection of missing evidence, not a
    produced value."""
    return EvidenceField(
        value=value,
        provenance=ProvenanceDescriptor(
            origin_plane=plane,
            producer_id=_PRODUCER,
            evidence_quality=EvidenceQuality.ABSENT,
            observed_at=observed_at,
            verification_method=VerificationMethod.FIELD_PRESENCE,
            trust_level=TrustLevel.DERIVED,
        ),
    )


class PredicateBinding:
    """The binding `B`: sealed evidence-only EEB -> sealed bound EEB (engine-input schema).

    Stateless and pure. It CONSUMES only the sealed EEB (plus the engine's gate-column ordering,
    supplied by the caller to avoid an engine import cycle), CARRIES plane-native PRESENT values
    verbatim, maps ABSENT/DEGRADED evidence to the frozen fail-closed direction, and seals the
    result via the frozen Commit 2.5 assembler. It never reads `Class`, never thresholds, never
    computes a decision, and invents no value.
    """

    def bind(self, evidence_eeb: ExecutionEvidenceBundle,
             node_gate_cols: Sequence[str], *,
             observed_at: str = "unobserved") -> ExecutionEvidenceBundle:
        """Bind a sealed evidence-only EEB into a sealed bound EEB.

        `node_gate_cols` is the FROZEN engine's `NODE_GATE_COLS` ordering, supplied by the caller
        (as Commit 4.1 does) so this module imports no engine. Returns a new sealed EEB whose
        decision-consumed fields are ready for the frozen `eeb_to_engine` adapter and
        `evaluate_decision`, without ever calling them.
        """
        src = evidence_eeb.payload
        obs = observed_at

        # -- node predicate vector (the engine gate booleans) ----------------------------------- #
        # CARRY (outcome 1) only if the source already provides a per-gate PRESENT boolean vector
        # aligned to the engine ordering (a deployment whose upstream policy produced bound gates).
        # Otherwise (the credit-card arm: authority plane C ABSENT, no observable gate declared)
        # every gate is ABSENT -> fail-closed (outcome 2). No gate->plane binding is invented.
        carriable = (len(src.node_predicate_vector) == len(node_gate_cols)
                     and all(_bool_value(ef) for ef in src.node_predicate_vector))
        if carriable:
            node_vector = tuple(src.node_predicate_vector)                      # carry verbatim
        else:
            node_vector = tuple(
                _failclosed_field(_FAILCLOSED_GATE, OriginPlane.C, obs)         # authority-plane absent
                for _ in node_gate_cols
            )

        # -- HARM_RISK (plane D) ---------------------------------------------------------------- #
        # CARRY a real PRESENT governance score; otherwise ABSENT (proxy rejected) -> out-of-slice
        # numeric placeholder (no hazard asserted). Never derive a V1..V28 proxy.
        if (src.harm_risk_score is not None
                and src.harm_risk_score.provenance.evidence_quality == EvidenceQuality.PRESENT
                and isinstance(src.harm_risk_score.value, (int, float))
                and not isinstance(src.harm_risk_score.value, bool)):
            harm = src.harm_risk_score                                          # carry verbatim
        else:
            harm = _failclosed_field(_HARM_ABSENT_PLACEHOLDER, OriginPlane.D, obs)

        # -- StaleContext / TelemetryFresh (plane B) -------------------------------------------- #
        # CARRY an already-boolean predicate verbatim; a raw delta (number) or ABSENT field is NOT
        # thresholded here (spec §3(b)) -> fail-closed.
        stale = (src.stale_context if _bool_value(src.stale_context)
                 else _failclosed_field(_FAILCLOSED_STALE, OriginPlane.B, obs))
        fresh = (src.telemetry_fresh if _bool_value(src.telemetry_fresh)
                 else _failclosed_field(_FAILCLOSED_FRESH, OriginPlane.B, obs))

        # -- class-veto (plane D) --------------------------------------------------------------- #
        # CARRY a PRESENT non-Class veto string; otherwise no veto ("" ). `Class` is NEVER read.
        cv = src.class_veto_evidence
        if (cv is not None and cv.provenance.evidence_quality == EvidenceQuality.PRESENT
                and isinstance(cv.value, str)):
            class_veto = cv                                                     # carry verbatim
        else:
            class_veto = _failclosed_field(_NO_VETO, OriginPlane.D, obs)

        # -- plane-A observables + E-cached ledger link: carry VERBATIM (provenance preserved) --- #
        return ExecutionEvidenceBundleAssembler().assemble(
            bundle_id="%s:bound" % evidence_eeb.bundle_id,
            created_at=evidence_eeb.created_at,
            subject_ref=evidence_eeb.subject_ref,
            method_version=evidence_eeb.method_version,
            txn_amount=src.txn_amount,
            txn_time=src.txn_time,
            txn_action_ref=src.txn_action_ref,
            txn_feature_ref=src.txn_feature_ref,
            node_predicate_vector=node_vector,
            harm_risk_score=harm,
            stale_context=stale,
            telemetry_fresh=fresh,
            class_veto_evidence=class_veto,
            prior_ledger_link=src.prior_ledger_link,
        )


def bind_evidence_to_schema(evidence_eeb: ExecutionEvidenceBundle,
                            node_gate_cols: Sequence[str], *,
                            observed_at: str = "unobserved") -> ExecutionEvidenceBundle:
    """Module-level convenience wrapper over ``PredicateBinding().bind(...)``."""
    return PredicateBinding().bind(evidence_eeb, node_gate_cols, observed_at=observed_at)
