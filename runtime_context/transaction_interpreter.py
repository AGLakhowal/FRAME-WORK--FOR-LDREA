#!/usr/bin/env python3
"""Transaction Interpreter — plane-A producer (Commit 2.4).

Reads the OBSERVABLE TRANSACTION REQUEST and converts each observable field into an atomic,
immutable Commit 2.1 EvidenceField with plane-A provenance, per
EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md §2.2/§4/§5 and RUNTIME_CONTEXT_LAYER_SPECIFICATION.md
§5/§8. Plane B (Runtime Context, Commit 2.3) is an INDEPENDENT, parallel producer; this module
does not read it. Commit 2.5 alone assembles all planes into a sealed bundle.

Class-blindness BY CONSTRUCTION: the interpreter reads ONLY a fixed plane-A allowlist —
`Amount`, `Time`, an optional action reference, and `V1..V28` as a single OPAQUE feature
reference. Every other request key — INCLUDING `Class` — is neither read nor copied. `Class`
has no place on the allowlist, so it cannot leak (EEB §Principles Class-blind; RCL §8).

This interpreter EXPOSES observations; it NEVER decides. It does not authorize, evaluate
predicates / Gamma / SAFE_STATE, invoke evaluate_decision, evaluate policy or governance,
interpret plane-B runtime context, assemble a bundle, or serialize. It owns SHAPE and
OBSERVATION, never MEANING.

Malformed values are recorded, NOT fixed: a present-but-wrong-type observation yields
`EvidenceQuality = DEGRADED` with the value carried VERBATIM. The interpreter never infers,
repairs, normalizes, coerces, or interprets a value; the frozen engine's fail-closed policy
decides what DEGRADED means. Opaque features are carried as-is and never type-judged.

Discipline (matching Commits 2.1/2.2/2.3):
  * Standard library only; Python 3.9 compatible; no pandas / no file I/O / no engine import.
  * NOT a time source — `observed_at` is an injected label (no datetime.now()/time()).
  * Readings are the immutable Commit 2.1 EvidenceField (origin_plane = A); no new type.
  * Commit 2.4 is UNCONSUMED scaffolding: nothing imports this module.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from .execution_evidence_bundle import (
    EvidenceField, ProvenanceDescriptor, OriginPlane, EvidenceQuality,
    TrustLevel, VerificationMethod,
)

# Producer identity recorded in every plane-A reading's provenance.
_PRODUCER = "transaction.interpreter"

# The interpreter is not a time source; provenance observed_at is an injected label. When the
# caller supplies none, this non-empty sentinel keeps the EEB provenance-completeness check (2.1)
# satisfied without reading a wall clock.
_OBSERVED_AT = "unobserved"

# ---- fixed plane-A allowlist (the ONLY keys ever read; Class is deliberately absent) ------ #
AMOUNT_KEY = "Amount"
TIME_KEY = "Time"
ACTION_REF_KEY = "TxnActionRef"                                  # optional
FEATURE_KEYS = tuple("V%d" % i for i in range(1, 29))           # V1..V28, opaque embedding

#: Exactly the request keys the interpreter is permitted to read. Anything not here — including
#: ``Class`` — is ignored. Exposed so a test can assert the boundary.
ALLOWLIST = (AMOUNT_KEY, TIME_KEY, ACTION_REF_KEY) + FEATURE_KEYS

# EEB payload field names this producer populates (plane A).
FIELD_AMOUNT = "txn_amount"
FIELD_TIME = "txn_time"
FIELD_ACTION_REF = "txn_action_ref"
FIELD_FEATURE_REF = "txn_feature_ref"


def _is_number(value: Any) -> bool:
    """True for a real numeric scalar. bool is excluded (it is not a transaction amount/time)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _field(value: Any, quality: EvidenceQuality, observed_at: str) -> EvidenceField:
    """Build an immutable plane-A EvidenceField (Commit 2.1 type). Value carried verbatim.

    Plane-A evidence is a direct read of the request payload: field-presence + type verified,
    self-reported trust. Quality is PRESENT for a well-formed value or DEGRADED for a malformed
    one — a recorded fact, never a decision.
    """
    return EvidenceField(
        value=value,
        provenance=ProvenanceDescriptor(
            origin_plane=OriginPlane.A,
            producer_id=_PRODUCER,
            evidence_quality=quality,
            observed_at=observed_at,
            verification_method=VerificationMethod.FIELD_PRESENCE,
            trust_level=TrustLevel.SELF_REPORTED,
        ),
    )


class TransactionInterpreter:
    """Plane-A producer: request → atomic plane-A EvidenceField objects. Stateless.

    Reads only the fixed plane-A allowlist; drops every other key (Class included). Produces a
    field ONLY for an allowlisted key that is present; absent keys yield no field (the assembler
    in Commit 2.5 handles absence). It STOPS at atomic EvidenceField objects — no bundle, no
    plane B/C/D, no predicate, no decision.
    """

    def interpret(self, request: Mapping[str, Any],
                  observed_at: Optional[str] = None) -> Dict[str, EvidenceField]:
        """Interpret one transaction request into plane-A EvidenceField objects.

        Returns a mapping of EEB payload field name -> immutable EvidenceField, containing only
        the fields observable in this request. `Class` and all non-allowlisted keys are ignored.
        """
        obs = observed_at if observed_at is not None else _OBSERVED_AT
        out: Dict[str, EvidenceField] = {}

        # Amount / Time — numeric plane-A facts; wrong type -> DEGRADED (carried verbatim).
        if AMOUNT_KEY in request:
            v = request[AMOUNT_KEY]
            q = EvidenceQuality.PRESENT if _is_number(v) else EvidenceQuality.DEGRADED
            out[FIELD_AMOUNT] = _field(v, q, obs)
        if TIME_KEY in request:
            v = request[TIME_KEY]
            q = EvidenceQuality.PRESENT if _is_number(v) else EvidenceQuality.DEGRADED
            out[FIELD_TIME] = _field(v, q, obs)

        # Optional action / externalization-target reference — opaque non-empty string.
        if ACTION_REF_KEY in request:
            v = request[ACTION_REF_KEY]
            q = EvidenceQuality.PRESENT if (isinstance(v, str) and v) else EvidenceQuality.DEGRADED
            out[FIELD_ACTION_REF] = _field(v, q, obs)

        # V1..V28 — a SINGLE opaque feature reference (governance-service input only; NEVER a
        # predicate; never decomposed or type-judged). Carried as an immutable tuple, verbatim,
        # in canonical V1..V28 order; produced only if at least one feature is present.
        features = tuple(request[k] for k in FEATURE_KEYS if k in request)
        if features:
            out[FIELD_FEATURE_REF] = _field(features, EvidenceQuality.PRESENT, obs)

        return out
