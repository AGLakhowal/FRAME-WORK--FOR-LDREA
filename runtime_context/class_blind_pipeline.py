#!/usr/bin/env python3
"""Class-blind runtime pipeline — end-to-end ACTIVATION orchestrator (Commit 5.2 Phase A).

NEUTRAL runtime activation only. This module WIRES the already-implemented, frozen components into
one runnable end-to-end path; it redesigns nothing, introduces no methodology, and does NOT touch
the reported credit-card arm (`gamma_map_raw` remains the reported default). It is a NEW, parallel
module: nothing in the reported benchmark path imports it, so it changes no metric, no benchmark,
no baseline, and no reported artifact.

    Runtime Observation (request + injected runtime clocks)
        │  build_evidence_bundle (5.1, FROZEN)      -> Execution Context -> sealed EEB
        ▼
    Execution Evidence Bundle
        │  PredicateBinding.bind (5.1-B, FROZEN)    -> bound EEB
        ▼
    EEB -> Engine Adapter
        │  decision_inputs_from_eeb (4.1, FROZEN)   -> decision schema
        ▼
    Frozen evaluate_decision (FROZEN)               -> Gamma / Pi / Decision
        │
        ▼
    Reported Artifact Emitter (FROZEN)              -> reported record + Hydra Ledger link
        │
        ▼
    Replay Manifest (FROZEN write_replay_manifest)  -> Evidence Quad + genesis-anchored chain

This orchestrator ONLY calls the public APIs of the frozen components; it computes no decision,
predicate, Gamma, or SAFE_STATE itself, reads no `Class`, introduces no threshold or heuristic, and
is not a wall-clock time source (all envelope labels are injected or deterministically derived from
`run_id` + row index). `harm_threshold` is the frozen engine's EXISTING default parameter (0.5,
the value used at every existing call site); it is not a new threshold and is moot in this arm
(HARM is absent). Phase B (retire `gamma_map_raw`; flip the reported arm; rebaseline) is a separate,
explicitly-non-neutral future commit and is NOT begun here.

Discipline (matching 2.1-2.5 / 4.1 / 5.1 / 5.1-B / emitter): standard library + pandas (only to
feed the frozen replay-manifest emitter) + the frozen project components; Python 3.9. Importing the
frozen engine here is correct (this is the top-level wiring, not a leaf) and creates no cycle
(`gamma_test_runner` does not import this module).
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .evidence_trace_builder import build_evidence_bundle
from .predicate_binding import PredicateBinding
from .eeb_to_engine import decision_inputs_from_eeb
from .reported_artifact_emitter import ReportedArtifactEmitter, GENESIS
from .transaction_interpreter import FIELD_AMOUNT, FIELD_TIME
# Top-level wiring legitimately consumes the frozen engine + frozen replay emitter (no cycle).
from gamma_test_runner import evaluate_decision, write_replay_manifest, NODE_GATE_COLS

# The frozen engine's EXISTING default threshold parameter (used verbatim at every call site, e.g.
# `evaluate_decision(row, 0.5)`). NOT a new threshold; moot in the credit-card arm (HARM absent).
ENGINE_HARM_THRESHOLD = 0.5


def _observable(eeb, field: str, default: Any = None) -> Any:
    """Read a plane-A observable value out of the sealed EEB (verbatim; no `Class`)."""
    ef = getattr(eeb.payload, field, None)
    return default if ef is None else ef.value


def run_pipeline(requests: Sequence[Mapping[str, Any]], *,
                 run_id: str,
                 runtimes: Optional[Sequence[Optional[Mapping[str, Any]]]] = None,
                 harm_threshold: float = ENGINE_HARM_THRESHOLD,
                 policy_hash: str = "",
                 method_version: str = "",
                 structural_constants: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Run the complete Class-blind pipeline over `requests`; return records + decisions + ledger head.

    `requests`  — observable transaction requests (the plane-A interpreter drops `Class`).
    `runtimes`  — optional per-request injected runtime observations (clocks) for plane B; where
                  absent, plane-B fields are honestly evidence-absent.
    Envelope labels are deterministic functions of `run_id` + row index (this module is NOT a time
    source). Every stage is a frozen component; this function only threads their outputs.
    """
    binder = PredicateBinding()
    emitter = ReportedArtifactEmitter()
    records: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    prev = GENESIS

    for i, req in enumerate(requests, start=1):
        rt = runtimes[i - 1] if runtimes else None
        created_at = "%s:created:%06d" % (run_id, i)
        observed_at = "%s:observed:%06d" % (run_id, i)

        # 1. Runtime Observation -> Execution Context -> sealed EEB  (5.1, frozen)
        eeb = build_evidence_bundle(
            dict(req), bundle_id="%s-EEB-%06d" % (run_id, i), created_at=created_at,
            runtime=rt, observed_at=observed_at)
        # 2. EEB -> Predicate Binding -> bound EEB  (5.1-B, frozen)
        bound = binder.bind(eeb, NODE_GATE_COLS, observed_at=observed_at)
        # 3. bound EEB -> EEB->Engine Adapter -> decision schema  (4.1, frozen)
        schema = decision_inputs_from_eeb(bound, NODE_GATE_COLS)
        # actuation is a post-observation fact (Gap 1), absent here; non-material to Gamma/Pi.
        schema.setdefault("Actuated", False)
        schema.setdefault("ACT_PERMIT", False)
        # 4. decision schema -> Frozen evaluate_decision -> Gamma / Pi / Decision  (frozen)
        dec = evaluate_decision(schema, harm_threshold)
        # 5. decision -> Reported Artifact Emitter -> reported record + ledger link  (frozen)
        rec = emitter.emit(
            i, decision=dec, harm=schema["HARM_RISK"],
            amount=_observable(eeb, FIELD_AMOUNT), time=_observable(eeb, FIELD_TIME),
            run_id=run_id, prior_ledger_hash=prev, policy_hash=policy_hash,
            method_version=method_version, structural_constants=structural_constants,
            evidence_bundle=eeb)
        records.append(rec)
        decisions.append(dec)
        prev = rec["HASH_current"]

    return {"records": records, "decisions": decisions, "ledger_head": prev, "n": len(records)}


def _manifest_dataframe(records: Sequence[Mapping[str, Any]], decisions: Sequence[Mapping[str, Any]]):
    """Assemble the exact columns the FROZEN `write_replay_manifest` reads: chain/ids/policy from the
    emitter records; decision-derived columns from the frozen engine output. (Imports pandas lazily.)"""
    import pandas as pd
    return pd.DataFrame({
        "HASH_prev": [r["HASH_prev"] for r in records],
        "HASH_current": [r["HASH_current"] for r in records],
        "ProposalID": [r["ProposalID"] for r in records],
        "ERTuple_ID": [r["ERTuple_ID"] for r in records],
        "PolicyHash": [r["PolicyHash"] for r in records],
        "DerivedDecision": [d["decision"] for d in decisions],
        "DerivedGammaG": [d["gamma_g"] for d in decisions],
        "DerivedGammaClass": [d["gamma_class"] for d in decisions],
        "DerivedPi": [d["pi"] for d in decisions],
        "DerivedChainLinked": [True] * len(records),
        "DerivedUnauthorized": [d["unauthorized"] for d in decisions],
    })


def write_pipeline_manifest(result: Mapping[str, Any], path) -> Dict[str, Any]:
    """Serialize a pipeline result into a replay manifest via the FROZEN `write_replay_manifest`.

    `path` is caller-chosen; this NEVER writes a reported artifact. Returns the frozen emitter's
    summary (path, n_records, genesis_anchored, adjacency_all_ok, manifest_sha256, verify_with).
    """
    df = _manifest_dataframe(result["records"], result["decisions"])
    return write_replay_manifest(df, path)


def _demo() -> int:
    """Tiny in-memory activation demo (no file writes): prove the wired path runs end-to-end."""
    reqs = [{"Amount": 149.62, "Time": 406, "V1": 0.1}, {"Amount": 12.0, "Time": 10, "V2": 0.3}]
    res = run_pipeline(reqs, run_id="CLASS_BLIND_PIPELINE_DEMO")
    dist: Dict[str, int] = {}
    for d in res["decisions"]:
        dist[d["decision"]] = dist.get(d["decision"], 0) + 1
    print("class-blind pipeline demo: n=%d decision_distribution=%s ledger_head=%s..."
          % (res["n"], dist, res["ledger_head"][:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
