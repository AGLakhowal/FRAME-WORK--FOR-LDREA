"""ExecutionBinding --- Layer 2 loader for the Execution Binding Manifest (IMPLEMENTATION only).

This reads Execution_Binding_Manifest.json --- a deterministically generated, NON-scientific
translation of the frozen Layer-1 manifests into runtime lookup structures. It provides the
runtime bindings (gamma-slot routing, tool argument bindings, threshold directives, evaluation
status, unknown-tool policy). It introduces NO scientific content.

Integrity (raised as PolicyError):
  * Missing binding manifest
  * Binding integrity failure (canonical sha != expected)
  * Provenance failure (derived_from_scientific_root != the frozen scientific root)

Spec: refactor items 1-6 (manifest-driven, no Python policy); Layer-2 separation.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path

from .frozen_policy import PolicyError, DEFAULT_MANIFEST_DIR, SCIENTIFIC_ROOT

_BINDING_FILE = "Execution_Binding_Manifest.json"
# Canonical sha256 of the deterministically generated binding manifest (build_execution_binding.py).
BINDING_SHA = "a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1"


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class ExecutionBinding:
    def __init__(self, manifest_dir=None, expected_sha: str | None = BINDING_SHA,
                 scientific_root: str = SCIENTIFIC_ROOT):
        self.manifest_dir = Path(manifest_dir) if manifest_dir else DEFAULT_MANIFEST_DIR
        p = self.manifest_dir / _BINDING_FILE
        if not p.exists():
            raise PolicyError(f"Missing binding manifest: {_BINDING_FILE} not found in {self.manifest_dir}.")
        self._b = json.loads(p.read_text())
        self.sha = _sha(_canon(self._b))
        if expected_sha is not None and self.sha != expected_sha:
            raise PolicyError(f"Binding Integrity Failure: canonical sha {self.sha} != expected {expected_sha}.")
        if self._b.get("derived_from_scientific_root") != scientific_root:
            raise PolicyError(
                f"Binding Provenance Failure: derived_from_scientific_root "
                f"{self._b.get('derived_from_scientific_root')} != frozen scientific root {scientific_root}."
            )
        self._family = self._b["family_metadata"]
        self._tools = self._b["tool_argument_binding"]

    def family_slot(self, family: str) -> str:
        return self._family[family]["gamma_slot"]

    def family_status(self, family: str) -> str:
        return self._family[family]["evaluation_status"]

    def family_threshold(self, family: str) -> dict:
        return dict(self._family.get(family, {}).get("threshold", {"kind": "structural", "deficit": 0}))

    def tool_binding(self, tool: str) -> dict:
        return dict(self._tools.get(tool, {"recognition": None, "structural_only": True}))

    def unknown_tool_handling(self) -> dict:
        """Runtime fail-closed HANDLING for tools absent from the frozen map.

        Not a new scientific policy: it is the runtime consequence of Definition 2(i) (complete
        mediation) resolved to SAFE_STATE (FULL_SPEC 2.3 / 0.10 non-default-permit)."""
        return dict(self._b["unknown_tool_handling"])


def default_execution_binding() -> ExecutionBinding:
    return ExecutionBinding(expected_sha=BINDING_SHA, scientific_root=SCIENTIFIC_ROOT)
