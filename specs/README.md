# Normative specifications

These documents are **cited by name from production source code** as the specification that
code implements. They are not archival. Moving or renaming one leaves a dangling citation in
the docstring of the module that implements it.

No spec is read at runtime — every citation is a docstring or comment reference — so nothing
breaks functionally if one is absent. They are kept because the code's provenance depends on
them.

| Specification | Size | Cited by |
|---|--:|---|
| [AGENTDOJO_LDREA_EXTERNAL_VALIDATION_DESIGN_V2.md](AGENTDOJO_LDREA_EXTERNAL_VALIDATION_DESIGN_V2.md) | 37 KB | `agentdojo_integration/manifests/agentdojo_freeze_manifest.json` |
| [AUTHORIZATION_ENGINE_CLASSIFICATION.md](AUTHORIZATION_ENGINE_CLASSIFICATION.md) | 11 KB | `tools/authorization_registry.json` |
| [DEPLOYMENT_POLICY_SPECIFICATION.md](DEPLOYMENT_POLICY_SPECIFICATION.md) | 37 KB | `runtime_context/predicate_binding.py` |
| [ENGINEERING_OWNER_RATIFICATION_RECORD.md](ENGINEERING_OWNER_RATIFICATION_RECORD.md) | 11 KB | `runtime_context/reported_artifact_emitter.py`<br>`tests/test_reported_artifact_emitter.py` |
| [ENGINEERING_SERIALIZATION_CONTRACT.md](ENGINEERING_SERIALIZATION_CONTRACT.md) | 16 KB | `runtime_context/reported_artifact_emitter.py`<br>`tests/test_reported_artifact_emitter.py` |
| [EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md](EXECUTION_EVIDENCE_BUNDLE_SPECIFICATION.md) | 32 KB | `runtime_context/assembler.py`<br>`runtime_context/execution_evidence_bundle.py`<br>`runtime_context/ports.py`<br>`runtime_context/transaction_interpreter.py` |
| [FINAL_FORENSIC_AUTHORIZATION_AUDIT.md](FINAL_FORENSIC_AUTHORIZATION_AUDIT.md) | 18 KB | `tools/authorization_registry.json` |
| [PREDICATE_BINDING_FINAL_SPECIFICATION.md](PREDICATE_BINDING_FINAL_SPECIFICATION.md) | 13 KB | `runtime_context/predicate_binding.py` |
| [PREDICATE_BINDING_SCIENTIFIC_SPECIFICATION.md](PREDICATE_BINDING_SCIENTIFIC_SPECIFICATION.md) | 20 KB | `runtime_context/predicate_binding.py`<br>`tests/test_predicate_binding.py` |
| [RUNTIME_CONTEXT_LAYER_SPECIFICATION.md](RUNTIME_CONTEXT_LAYER_SPECIFICATION.md) | 26 KB | `runtime_context/context_objects.py`<br>`runtime_context/transaction_interpreter.py`<br>`tests/test_context_objects.py` |
| [RUNTIME_EVIDENCE_ARCHITECTURE.md](RUNTIME_EVIDENCE_ARCHITECTURE.md) | 24 KB | `runtime_context/assembler.py` |

Superseded working documents live in [`docs/history/`](../docs/history/).
