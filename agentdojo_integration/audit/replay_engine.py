"""Phase D --- ReplayEngine.

Consumes ONLY `execution_trace.jsonl` (no AgentDojo, no LLM, no frozen runtime). It:
  * reconstructs the per-step timeline, predicate evaluations, Gamma/Pi, decision, tool execution,
    and final state purely from recorded events; and
  * INDEPENDENTLY re-derives, from the recorded predicate deficits, the Law-of-Concurrence quantities
      Gamma_global = max_i deficit_i     (non-compensatory / OR over binary deficits)
      Pi           = 1 iff (Gamma_global == 0 AND Gamma_class == 0)
      decision     = PERMIT iff Pi == 1 else SAFE_STATE
    and checks they equal the values the runtime recorded.

A green replay proves the trace is internally consistent and the authorization decision is
reproducible from the trace alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ._util import read_jsonl, write_json


@dataclass
class StepReconstruction:
    step: int
    tool: str | None = None
    policy_class: str | None = None
    predicate_deficits: dict = field(default_factory=dict)
    predicate_status: dict = field(default_factory=dict)
    recorded_gamma_global: int | None = None
    recorded_gamma_class: int | None = None
    recorded_pi: int | None = None
    recorded_decision: str | None = None
    executed: bool | None = None
    env_delta: int | None = None
    # independent re-derivation
    derived_gamma_global: int | None = None
    derived_pi: int | None = None
    derived_decision: str | None = None
    consistent: bool | None = None


class ReplayEngine:
    def __init__(self, trace_jsonl: str | Path):
        self.path = Path(trace_jsonl)
        self.events = read_jsonl(self.path)
        self.steps: dict[int, StepReconstruction] = {}
        self.final: dict = {}

    # -- reconstruction ------------------------------------------------------
    def reconstruct(self) -> "ReplayEngine":
        for e in self.events:
            st = e.get("step_number")
            et = e.get("event_type")
            if et == "EPISODE_FINISHED":
                self.final = {"utility": e.get("utility"), "security": e.get("security")}
                continue
            if st is None:
                continue
            s = self.steps.setdefault(st, StepReconstruction(step=st))
            if et == "GAMMA_INTERCEPT":
                s.tool = e.get("tool_proposed"); s.policy_class = e.get("policy_class")
            elif et == "TOOL_CALL_PROPOSED" and s.tool is None:
                s.tool = e.get("tool_name")
            elif et == "PREDICATE_EVALUATION":
                s.predicate_deficits[e["predicate_name"]] = int(e.get("deficit", 0))
                s.predicate_status[e["predicate_name"]] = e.get("evaluation_status")
            elif et == "Γ COMPUTATION":
                s.recorded_gamma_global = e.get("gamma_global")
                s.recorded_gamma_class = e.get("gamma_class")
            elif et == "Π COMPUTATION":
                s.recorded_pi = e.get("final_pi")
            elif et in ("PERMIT_DECISION", "DENY_DECISION"):
                s.recorded_decision = e.get("decision")
            elif et == "TOOL_EXECUTION":
                s.executed = e.get("executed"); s.env_delta = e.get("env_effect_delta")
        return self

    # -- independent re-derivation + verification ----------------------------
    def verify(self) -> dict:
        checks = []
        for st in sorted(self.steps):
            s = self.steps[st]
            if s.recorded_gamma_global is None:  # a step with no Gamma adjudication (read-only / no EEA)
                continue
            # Gamma_global = OR over binary deficits (non-compensatory max)
            s.derived_gamma_global = 1 if any(v == 1 for v in s.predicate_deficits.values()) else 0
            gclass = s.recorded_gamma_class or 0
            s.derived_pi = 1 if (s.derived_gamma_global == 0 and gclass == 0) else 0
            s.derived_decision = "PERMIT" if s.derived_pi == 1 else "SAFE_STATE"
            s.consistent = (
                s.derived_gamma_global == s.recorded_gamma_global
                and s.derived_pi == s.recorded_pi
                and (s.recorded_decision is None or s.derived_decision == s.recorded_decision)
            )
            checks.append(s.consistent)
        all_ok = all(checks) if checks else True
        report = {
            "trace_file": str(self.path),
            "n_events": len(self.events),
            "n_steps": len(self.steps),
            "n_authorization_steps": len(checks),
            "all_steps_consistent": all_ok,
            "final_state": self.final,
            "steps": [self._step_view(self.steps[st]) for st in sorted(self.steps)],
        }
        return report

    @staticmethod
    def _step_view(s: StepReconstruction) -> dict:
        return {
            "step": s.step, "tool": s.tool, "policy_class": s.policy_class,
            "predicate_deficits": s.predicate_deficits,
            "recorded": {"gamma_global": s.recorded_gamma_global, "gamma_class": s.recorded_gamma_class,
                         "pi": s.recorded_pi, "decision": s.recorded_decision,
                         "executed": s.executed, "env_delta": s.env_delta},
            "derived": {"gamma_global": s.derived_gamma_global, "pi": s.derived_pi,
                        "decision": s.derived_decision},
            "consistent": s.consistent,
        }

    def run(self, out_json: str | Path | None = None) -> dict:
        self.reconstruct()
        report = self.verify()
        if out_json:
            write_json(out_json, report)
        return report


def replay_and_verify(trace_jsonl: str | Path, out_json: str | Path | None = None) -> dict:
    return ReplayEngine(trace_jsonl).run(out_json)
