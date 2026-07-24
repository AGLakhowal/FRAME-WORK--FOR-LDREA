#!/usr/bin/env python3
"""Class-blind Reported Artifact Emitter — deterministic serialization only.

A standalone engineering work package (flag-OFF / parallel; NOT Commit 5.2 activation). It
SERIALIZES the frozen pipeline's outputs into reported + replay artifacts to the conventions frozen
by ENGINEERING_SERIALIZATION_CONTRACT.md and ratified by ENGINEERING_OWNER_RATIFICATION_RECORD.md.

    (frozen) decision + sealed EEB evidence + injected envelope
              │   ReportedArtifactEmitter  (this module — serialize only)
              ▼
    reported artifact record  +  Hydra Ledger link (HASH_prev/HASH_current)

It performs NO decision work. It NEVER computes authorization, predicates, Gamma, or SAFE_STATE;
never interprets policy; never invents evidence; never reads `Class`. Every decision value is
CARRIED VERBATIM from the frozen `evaluate_decision` output; every observable is CARRIED from the
sealed EEB; every identifier/timestamp/ledger value is a deterministic function of Class-blind
inputs. The ledger HASH algorithm is the existing, independently-verified chain
(`gamma_replay_verify.py`); this module authors only a new Class-blind chain *instance* (its
adoption as the *reported* chain is the signed rebaseline scoped to Commit 5.2 — not done here).

Ratified conventions realized here (Contract §; Ratification §3):
  * C1 ProposalID / C2 PermitTokenID / C3 SubjectProfileID / C4 ERTuple_ID — index-derived (frozen verbatim)
  * C5 Timestamp — EPOCH_BASE + observable Time (frozen verbatim; NOT a wall-clock source)
  * C6 commit offset (+10ms) / C7 actuate offset (+25ms) — frozen verbatim
  * C7 actuate EMISSION GATE — driven by the FROZEN DECISION (actuated <=> PERMIT), never by `Class`
  * C8 EnvironmentContext — the `class=` token is REMOVED; the four Class-blind tokens are retained
  * C9 structural constants — PolicyHash from the frozen scientific Merkle root (caller-supplied);
        remaining constants from a single Class-independent origin (caller-injected); never a
        `Class`-selected template
  * C10 ledger canon composition (frozen verbatim; values decision-sourced) / C11 HASH generation (frozen algorithm)

Discipline (matching 2.1-2.5 / 4.1 / 5.1 / 5.1-B): standard library only; Python 3.9; NOT a time
source (all times injected/derived from the observable); imports NO engine (the decision is passed
in); imports the EEB type for typing only. UNCONSUMED scaffolding: nothing in the reported path
imports this module — it changes no metric and no benchmark.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional, Sequence

from .execution_evidence_bundle import ExecutionEvidenceBundle  # typing only

# --------------------------------------------------------------------------- #
# Frozen-verbatim engineering constants (Contract C5/C6/C7/C8; ratified).
# --------------------------------------------------------------------------- #
EPOCH_BASE = datetime(2013, 9, 1, tzinfo=timezone.utc)   # C5 (verbatim)
COMMIT_OFFSET_MS = 10                                     # C6 (verbatim)
ACTUATE_OFFSET_MS = 25                                    # C7 offset (verbatim)
GENESIS = "GENESIS"                                       # C11 genesis anchor
_PERMIT = "PERMIT"                                        # frozen engine decision vocabulary
# C8 Class-blind EnvironmentContext tokens (the `class=` token is REMOVED; these four are retained).
_ENV_DATASET_TAG = "ULB_2013_EU_CARD"
_ENV_SOURCE_TAG = "anonymized_PCA"


# --------------------------------------------------------------------------- #
# Shared primitives (Contract §0; frozen verbatim).
# --------------------------------------------------------------------------- #
def h12(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:12]


def h16(*parts: object) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:16]


def iso_ms(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (dt.microsecond // 1000)


def _num(value: Any) -> float:
    """Coerce a plane-A numeric observable to float, fail-closed to the EXISTING 0.0 fallback.

    H4 robustness fix: an ABSENT observable (None, from the ports/interpreter) or a DEGRADED one
    (a non-numeric value carried verbatim by the interpreter) must NOT raise during serialization;
    it maps to 0.0 — the SAME fail-closed fallback this module already used for NaN (via the
    `value == value` guard). Reuses the existing convention; adds no field, changes no schema, and
    is byte-identical for every well-formed numeric (float(value) is returned unchanged) and for
    NaN (still 0.0). Deterministic and Class-blind.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if v == v else 0.0   # NaN -> 0.0 (unchanged existing behaviour)


# --------------------------------------------------------------------------- #
# Identifier serialization (C1-C4; index-derived, Class-blind).
# --------------------------------------------------------------------------- #
def proposal_id(index: int) -> str:
    return "TXN_%06d" % index


def permit_token_id(index: int) -> str:
    return "PERMIT_%s" % h16("permit", index)


def ertuple_id(index: int) -> str:
    return "ERT_%s" % h16("ertuple", index)


def subject_profile_id(index: int) -> str:
    return "CARDPROFILE_SYN_%s" % h12("profile", index)


# --------------------------------------------------------------------------- #
# Timestamp serialization (C5/C6/C7; derived from the observable Time — NOT a wall clock).
# --------------------------------------------------------------------------- #
def _base_ts(time_observable: Any) -> datetime:
    # Fail-closed read of the plane-A `Time` observable (seconds): ABSENT/malformed/NaN -> 0.0
    # (existing fallback). No `Class`, no wall clock.
    return EPOCH_BASE + timedelta(seconds=_num(time_observable))


def environment_context(time_observable: Any, amount_observable: Any) -> str:
    """C8 ratified Class-blind EnvironmentContext: the four admissible tokens; NO `class=` token."""
    t = _num(time_observable)      # ABSENT/malformed/NaN -> 0.0 (existing fail-closed fallback)
    amt = _num(amount_observable)
    return "%s;source_time_sec=%d;amount=%g;source=%s" % (
        _ENV_DATASET_TAG, int(t), amt, _ENV_SOURCE_TAG)


def _ledger_canon(pid: str, status: str, gamma: Any, harm: float, ptid: str, ts_utc: str) -> str:
    """C10 canon composition (frozen verbatim); values are decision-sourced (Class-blind)."""
    return "%s|%s|%s|%.6f|%s|%s" % (pid, status, gamma, float(harm), ptid, ts_utc)


class ReportedArtifactEmitter:
    """Pure serializer: (frozen decision + sealed EEB + injected envelope) -> reported record.

    Stateless. It reads no `Class`, computes no decision, and thresholds nothing. Every value it
    writes is either a Class-blind deterministic function of its inputs, a verbatim carry of the
    frozen decision, or a caller-supplied Class-independent constant.
    """

    def emit(self, index: int, *,
             decision: Mapping[str, Any],
             harm: Any,
             amount: Any,
             time: Any,
             run_id: str,
             prior_ledger_hash: str = GENESIS,
             policy_hash: str = "",
             method_version: str = "",
             structural_constants: Optional[Mapping[str, Any]] = None,
             evidence_bundle: Optional[ExecutionEvidenceBundle] = None) -> Dict[str, Any]:
        """Serialize one reported artifact record + its ledger link.

        `decision`  — the FROZEN `evaluate_decision` output (carried verbatim; keys `decision`,
                      `gamma_g`). `harm` — the bound EEB `harm_risk_score` value (carried).
        `amount`/`time` — plane-A observables (from the sealed EEB). `policy_hash` — the frozen
        scientific Merkle root (C9; caller-sourced, Class-independent). `structural_constants` —
        a single Class-independent origin's constants (C9; caller-injected). `evidence_bundle` —
        the sealed EEB, for provenance linkage (ref/digest/method_version). Nothing here is
        computed from `Class`; the emitter is not a time source.
        """
        status = str(decision["decision"])                 # carried verbatim from the frozen engine
        gamma = decision["gamma_g"]                         # carried verbatim
        actuated = (status == _PERMIT)                      # C7 gate: driven by the DECISION, not Class

        base = _base_ts(time)
        ts_utc = iso_ms(base)
        commit_ts = iso_ms(base + timedelta(milliseconds=COMMIT_OFFSET_MS))
        actuate_ts = iso_ms(base + timedelta(milliseconds=ACTUATE_OFFSET_MS)) if actuated else ""

        pid = proposal_id(index)
        ptid = permit_token_id(index)

        canon = _ledger_canon(pid, status, gamma, harm, ptid, ts_utc)
        hash_current = hashlib.sha256((str(prior_ledger_hash) + "||" + canon).encode()).hexdigest()

        record: Dict[str, Any] = {
            # -- identity / envelope (C1-C4) -- #
            "RunID": run_id,
            "ProposalID": pid,
            "BenchmarkRowID": "%s_ROW_%06d" % (run_id, index),
            "Step": index,
            "SubjectProfileID": subject_profile_id(index),
            "PermitTokenID": ptid,
            "ERTuple_ID": ertuple_id(index),
            # -- timestamps (C5/C6/C7) -- #
            "TimestampUTC": ts_utc,
            "CommitTimestamp": commit_ts,
            "ActuateTimestamp": actuate_ts,                # "" iff not actuated (decision-gated)
            # -- provenance-faithful Class-blind environment (C8) -- #
            "EnvironmentContext": environment_context(time, amount),
            # -- decision carried verbatim (serialization, not computation) -- #
            "Status": status,
            "Gamma": gamma,
            "HARM_RISK": float(harm),
            "Actuated": actuated,
            "ACT_PERMIT": actuated,
            # -- structural constants (C9): PolicyHash from the frozen Merkle root; the rest from a
            #    single Class-independent injected origin. No `Class`-selected template. -- #
            "PolicyHash": policy_hash,
            "MethodVersion": method_version,
            # -- ledger (C10/C11): new Class-blind chain instance; frozen hashing algorithm -- #
            "LedgerCanon": canon,
            "HASH_prev": str(prior_ledger_hash),
            "HASH_current": hash_current,
        }
        if structural_constants:
            for k, v in structural_constants.items():       # merged verbatim; caller guarantees Class-independence
                record.setdefault(k, v)
        # -- provenance linkage to the sealed EEB (preserve chain-of-custody) -- #
        if evidence_bundle is not None:
            record["EvidenceBundleID"] = evidence_bundle.bundle_id
            record["EvidenceBundleDigest"] = evidence_bundle.integrity_digest
            record.setdefault("MethodVersion", evidence_bundle.method_version)
        return record

    def emit_chain(self, items: Sequence[Mapping[str, Any]], *,
                   run_id: str, genesis: str = GENESIS) -> list:
        """Serialize an ordered sequence into a genesis-anchored ledger chain.

        Each item is a mapping of the per-row `emit(...)` kwargs (minus `index`/`run_id`/
        `prior_ledger_hash`, which are threaded here). Returns the ordered records with a valid
        adjacency chain (`HASH_prev[i] == HASH_current[i-1]`), deterministic over the inputs.
        """
        out = []
        prev = genesis
        for i, item in enumerate(items, start=1):
            rec = self.emit(i, run_id=run_id, prior_ledger_hash=prev, **dict(item))
            out.append(rec)
            prev = rec["HASH_current"]
        return out


def emit_reported_record(index: int, **kwargs: Any) -> Dict[str, Any]:
    """Module-level convenience wrapper over ``ReportedArtifactEmitter().emit(...)``."""
    return ReportedArtifactEmitter().emit(index, **kwargs)
