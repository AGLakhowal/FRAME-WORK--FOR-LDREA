"""ScientificPolicy --- Layer 1 loader for the SEVEN IMMUTABLE scientific manifests.

These seven manifests are the scientific pre-registration. They are frozen ONCE, forever, at the
canonical Merkle root ce8c8467...; this loader only reads them and enforces their integrity. It
provides tool classification (mediated / EEA class / predicate families) from the frozen Tool
Mapping Manifest. It contains NO implementation binding --- that lives in Layer 2 (ExecutionBinding).

Integrity failures raised as PolicyError:
  * Missing Manifest    (a required leaf absent)
  * Invalid Merkle Root (recomputed != recorded: tampering)
  * Version Mismatch    (recorded != expected_root)

Spec: Verification Part 5 (Merkle commitment). The seven manifests are NEVER modified.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path

DEFAULT_MANIFEST_DIR = Path(__file__).resolve().parent.parent / "manifests"
# The canonical, immutable scientific pre-registration root (frozen once, in Phase 2B).
SCIENTIFIC_ROOT = "ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618"

_LEAF_FILES = [
    "predicate_manifest.json", "threshold_manifest.json", "tool_mapping_manifest.json",
    "recipient_derivation_manifest.json", "evaluation_manifest.json",
    "version_manifest.json", "dataset_manifest.json",
]
_UNKNOWN_CLASS = "UNKNOWN_TOOL_NOT_IN_FROZEN_MAP"


class PolicyError(RuntimeError):
    """Raised on any frozen-artifact integrity / version / availability failure."""


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class ScientificPolicy:
    def __init__(self, manifest_dir=None, expected_root: str | None = SCIENTIFIC_ROOT):
        self.manifest_dir = Path(manifest_dir) if manifest_dir else DEFAULT_MANIFEST_DIR
        self.expected_root = expected_root
        self._m: dict = {}
        self.root = self._verify()
        self._tool_map = {r["tool"]: r for r in self._m["tool_mapping_manifest.json"]["tools"]}

    def _load(self, name: str) -> dict:
        p = self.manifest_dir / name
        if not p.exists():
            raise PolicyError(f"Missing Manifest: required frozen leaf '{name}' not found in {self.manifest_dir}.")
        return json.loads(p.read_text())

    def _verify(self) -> str:
        for f in _LEAF_FILES:
            self._m[f] = self._load(f)
        cur = [_sha(_canon(self._m[f])) for f in _LEAF_FILES]
        while len(cur) > 1:
            if len(cur) % 2:
                cur = cur + [cur[-1]]
            cur = [_sha((cur[i] + cur[i + 1]).encode()) for i in range(0, len(cur), 2)]
        recomputed = cur[0]
        recorded = self._load("merkle_root.json")["merkle_root"]
        if recomputed != recorded:
            raise PolicyError(f"Invalid Merkle Root: recomputed {recomputed} != recorded {recorded} (tampering).")
        if self.expected_root is not None and recorded != self.expected_root:
            raise PolicyError(f"Version Mismatch: manifest root {recorded} != expected {self.expected_root}.")
        return recorded

    def classify(self, tool: str):
        """(mediated, eea_class, families, conditional). Unknown -> flagged for fail-closed handling."""
        row = self._tool_map.get(tool)
        if row is None:
            return (True, _UNKNOWN_CLASS, [], False)
        return (bool(row["mediated"]), row["eea_class"], list(row["predicate_families"]), bool(row["conditional"]))

    @property
    def is_unknown_class(self):
        return _UNKNOWN_CLASS


def default_scientific_policy() -> ScientificPolicy:
    return ScientificPolicy(expected_root=SCIENTIFIC_ROOT)
