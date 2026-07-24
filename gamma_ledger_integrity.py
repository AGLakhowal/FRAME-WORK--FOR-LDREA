#!/usr/bin/env python3
"""Gamma Hardening v1 — ledger record authenticity.

The legacy replay manifest was an UNSIGNED linear hash chain. Because the
verifier never recomputed hashes from content and there was no keyed MAC, an
attacker could (E-7) fabricate a fully self-consistent chain from scratch or
(E-8) edit a real record in place and still pass verification.

This module adds a keyed integrity tag (`sig`) over the canonical bytes of the
ENTIRE decision record (every field except `sig` itself). Any edit to any field
— decision, gamma_g, gamma_class, pi, the evidence quad, or the chain hashes —
changes the canonical bytes and invalidates `sig`. Fabrication is infeasible
without the key.

Algorithm: HMAC-SHA256 (stdlib, deterministic, dependency-free). This blocks the
executed exploits (external forgery + in-place tampering). It is symmetric, so it
does NOT by itself give third-party non-repudiation — the documented upgrade path
is Ed25519 detached signatures with the private key held in an HSM/TPM, verified
against a published public key. The record/verifier interfaces here are
signature-scheme agnostic so that swap is localized to `_mac()`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

DEFAULT_KEY_PATH = Path(__file__).with_name("runtime_keys") / "ledger_hmac.key"
SIG_FIELD = "sig"
SIG_ALG = "HMAC-SHA256"


def generate_key(path: Path = DEFAULT_KEY_PATH) -> bytes:
    """Create a fresh 32-byte key (hex-encoded on disk) if one does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = os.urandom(32)
        path.write_text(key.hex())
        os.chmod(path, 0o600)
    return load_key(path)


def load_key(path: Path = DEFAULT_KEY_PATH) -> bytes:
    return bytes.fromhex(Path(path).read_text().strip())


def canonical_record_bytes(rec: dict) -> bytes:
    """Deterministic serialization of a decision record, excluding `sig`."""
    payload = {k: v for k, v in rec.items() if k != SIG_FIELD}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _mac(key: bytes, msg: bytes) -> str:
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def sign_record(rec: dict, key: bytes) -> dict:
    rec = dict(rec)
    rec.pop(SIG_FIELD, None)
    rec[SIG_FIELD] = {"alg": SIG_ALG, "mac": _mac(key, canonical_record_bytes(rec))}
    return rec


def verify_record(rec: dict, key: bytes) -> bool:
    sig = rec.get(SIG_FIELD)
    if not isinstance(sig, dict) or sig.get("alg") != SIG_ALG or "mac" not in sig:
        return False
    expected = _mac(key, canonical_record_bytes(rec))
    return hmac.compare_digest(str(sig["mac"]), expected)
