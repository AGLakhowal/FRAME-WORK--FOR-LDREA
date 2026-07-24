"""GammaGovernedRuntime --- L-DREA interposition at the AgentDojo execution boundary.

The ONLY interception point (FunctionsRuntime.run_function), injected via AgentDojo's own
`runtime_class` parameter --- no AgentDojo source modified. The runtime reads from TWO layers:

  Layer 1 (ScientificPolicy)   -- 7 immutable frozen manifests (root ce8c8467...): tool -> mediated /
                                   EEA class / predicate families; unknown-tool detection.
  Layer 2 (ExecutionBinding)   -- Execution Binding Manifest (derived from Layer 1): argument bindings,
                                   family -> gamma slot, threshold directives, evaluation status,
                                   unknown-tool fail-closed policy.

Both layers, plus the GammaBridge and PredicateEvaluator, are INJECTED (dependency inversion). This
class holds no scientific mapping and no implementation binding of its own.

Behavior: unknown tool -> SAFE_STATE (fail closed); read-only -> pass through; EEA -> reused Gamma
decision -> PERMIT (execute) / SAFE_STATE (block). Phase 3A: decision + interception ONLY.

Spec: Definition 1/2/4; FULL_SPEC 2.3 / 0.10; refactor items 4 (fail-closed) and 6 (dependency inversion).
"""
from __future__ import annotations
import threading
from typing import Mapping

from agentdojo.functions_runtime import FunctionsRuntime

from .frozen_policy import ScientificPolicy, default_scientific_policy
from .execution_binding import ExecutionBinding, default_execution_binding
from .gamma_bridge import GammaBridge, METHOD_VERSION
from .predicate_evaluation import PredicateEvaluator


class GammaGovernedRuntime(FunctionsRuntime):
    def __init__(self, functions=None, *, scientific=None, binding=None, bridge=None, evaluator=None):
        super().__init__(functions or [])
        # Injected dependencies (default to the real, frozen/derived ones).
        self.scientific: ScientificPolicy = scientific or default_scientific_policy()
        self.binding: ExecutionBinding = binding or default_execution_binding()
        self.bridge = bridge or GammaBridge(self.binding)
        self.evaluator = evaluator or PredicateEvaluator(self.binding)
        self.frozen_merkle_root = self.scientific.root      # immutable scientific root ce8c8467...
        self.binding_sha = self.binding.sha                 # Layer-2 provenance sha
        self.method_version = METHOD_VERSION
        self.gamma_decisions: list[dict] = []
        # (F-5) Guard the shared decision log against concurrent run_function calls.
        self._lock = threading.Lock()

    def _record(self, entry: dict) -> None:
        with self._lock:
            self.gamma_decisions.append(entry)

    def _deny(self, function, eea_class, detail, raise_on_error):
        error = f"GammaSafeState: action '{function}' ({eea_class}) denied by L-DREA authorization boundary — {detail}."
        if raise_on_error:
            raise PermissionError(error)
        return "", error

    def run_function(self, env, function, kwargs: Mapping, raise_on_error: bool = False):
        mediated, eea_class, families, conditional = self.scientific.classify(function)

        # (4) Unknown-tool fail-closed HANDLING (not a new policy; the runtime consequence of
        # Definition 2(i) complete mediation + SAFE_STATE). Protects future AgentDojo releases.
        if eea_class == self.scientific.is_unknown_class:
            h = self.binding.unknown_tool_handling()
            self._record({"function": function, "eea_class": "UNKNOWN",
                          "decision": "SAFE_STATE", "reason": "unknown_tool_fail_closed_handling"})
            return self._deny(function, "UNKNOWN_TOOL", f"not in frozen Tool Mapping Manifest ({h['handling']}); not executed", raise_on_error)

        # Read-only tools: outside the externalization boundary (Definition 1).
        if not mediated:
            return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)

        # Externally effective action: adjudicate with the REUSED Gamma engine.
        # (F-3) TOCTOU narrowing: hold the lock across adjudicate -> execute and
        # re-adjudicate immediately before executing. If any intervening mutation
        # of `env` flips the decision away from PERMIT, we fail closed rather than
        # acting on a stale authorization. Full atomicity additionally requires the
        # host to snapshot env at decide-time (documented residual).
        tool_binding = self.binding.tool_binding(function)
        with self._lock:
            ev = self.evaluator.evaluate(env, function, kwargs, families, tool_binding)
            result = self.bridge.decide(ev["deficits"])
            self.gamma_decisions.append({
                "function": function, "eea_class": eea_class,
                "decision": result["decision"], "gamma_g": result["gamma_g"], "gamma_class": result["gamma_class"],
                "deficits": {k: v for k, v in ev["deficits"].items() if v},
                "evaluation_status": ev["status"],
            })

            if result["decision"] == "PERMIT":
                # Re-check against the current env state right before executing.
                ev2 = self.evaluator.evaluate(env, function, kwargs, families, tool_binding)
                result2 = self.bridge.decide(ev2["deficits"])
                if result2["decision"] != "PERMIT":
                    first_failing = sorted(k for k, v in ev2["deficits"].items() if v) or ["(class-veto)"]
                    return self._deny(function, eea_class,
                                      f"state changed after authorization (TOCTOU); re-check denied, first_failing={first_failing}",
                                      raise_on_error)
                return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)
        first_failing = sorted(k for k, v in ev["deficits"].items() if v) or ["(class-veto)"]
        return self._deny(function, eea_class,
                          f"Gamma_G={result['gamma_g']}, Gamma_class={result['gamma_class']}, first_failing={first_failing}",
                          raise_on_error)
