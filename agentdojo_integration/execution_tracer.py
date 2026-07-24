"""Execution Tracer --- PURE OBSERVABILITY for the AgentDojo x L-DREA x Gamma episode.

Reconstructs the entire episode after a run. It records; it never decides. Non-invasiveness is
structural:

  * The tracing runtime is a SUBCLASS of the frozen GammaGovernedRuntime. It injects FRESH but
    byte-identical frozen dependencies (same manifests, same roots ce8c8467.../a38619274c...) and
    wraps their bound methods with record-then-delegate observers. Every wrapper calls the original
    and returns its unchanged value, so classify / predicate-evaluation / Gamma / Pi / PERMIT-DENY
    are computed by the frozen code exactly as without the tracer.
  * The LLM observer wraps client.chat.completions.create, returning the exact original completion
    object. No prompt, tool, message, temperature, or response is altered.

Nothing in AgentDojo, the frozen interception package, gamma_test_runner.evaluate_decision, the
runner, prompts, attacks, or scoring is modified. The only cost is minimal logging overhead.

Every event carries: event_id, episode_id, timestamp, step_number, event_type, runtime_component,
processing_time_ms. Event-type-specific fields are attached per the trace specification.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from agentdojo.functions_runtime import FunctionsRuntime  # noqa: F401  (type context only)

from agentdojo_integration.interception.governed_runtime import GammaGovernedRuntime
from agentdojo_integration.interception.frozen_policy import ScientificPolicy, SCIENTIFIC_ROOT
from agentdojo_integration.interception.execution_binding import ExecutionBinding, BINDING_SHA
from agentdojo_integration.interception.gamma_bridge import GammaBridge, METHOD_VERSION
from agentdojo_integration.interception.predicate_evaluation import PredicateEvaluator


def _sha(obj) -> str:
    if not isinstance(obj, (str, bytes)):
        obj = json.dumps(obj, sort_keys=True, default=str)
    if isinstance(obj, str):
        obj = obj.encode("utf-8")
    return "sha256:" + hashlib.sha256(obj).hexdigest()


# ============================================================================================
# Tracer: append-only event log with monotonic ids/steps + deterministic clock offset
# ============================================================================================
class ExecutionTracer:
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.events: list[dict] = []
        self._eid = 0
        self.step = 0
        self.current_tool_step = 0

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def emit(self, event_type: str, runtime_component: str, payload: dict | None = None,
             step: int | None = None, processing_time_ms: float | None = None) -> dict:
        self._eid += 1
        ev = {
            "event_id": f"evt-{self._eid:06d}",
            "episode_id": self.episode_id,
            "timestamp": self._now(),
            "step_number": self.step if step is None else step,
            "event_type": event_type,
            "runtime_component": runtime_component,
            "processing_time_ms": round(processing_time_ms, 4) if processing_time_ms is not None else None,
        }
        if payload:
            ev.update(payload)
        self.events.append(ev)
        return ev

    def next_step(self) -> int:
        self.step += 1
        return self.step


# ============================================================================================
# Tracing runtime: frozen GammaGovernedRuntime subclass with observation-only wrappers
# ============================================================================================
def make_tracing_runtime(tracer: ExecutionTracer):
    class TracingRuntime(GammaGovernedRuntime):
        def __init__(self, functions=None, **kw):
            # Fresh, isolated, byte-identical frozen deps (re-verify to the same frozen roots),
            # so wrapping their methods cannot leak into any global singleton.
            sci = ScientificPolicy()
            binding = ExecutionBinding()
            bridge = GammaBridge(binding)
            evaluator = PredicateEvaluator(binding)
            super().__init__(functions, scientific=sci, binding=binding, bridge=bridge, evaluator=evaluator)
            self._tracer = tracer
            self.candidate_trace: list[dict] = []
            if not hasattr(tracer, "_runtimes"):
                tracer._runtimes = []
            tracer._runtimes.append(self)
            self._wrap_observers()

        # ---- record-then-delegate wrappers on the frozen collaborators ----
        def _wrap_observers(self):
            sci, ev, br = self.scientific, self.evaluator, self.bridge
            _classify, _evaluate, _decide = sci.classify, ev.evaluate, br.decide
            t = self._tracer

            def classify(function):
                s = time.perf_counter()
                res = _classify(function)
                dt = (time.perf_counter() - s) * 1000
                mediated, eea_class, families, conditional = res
                t.emit("GAMMA_INTERCEPT", "GammaGovernedRuntime", {
                    "tool_proposed": function,
                    "normalized_action": eea_class,
                    "subject": "agent",
                    "action": eea_class,
                    "object": function,
                    "resource": function,
                    "policy_class": eea_class,
                    "mediated": bool(mediated),
                    "predicate_families": list(families),
                    "is_unknown": eea_class == sci.is_unknown_class,
                }, step=t.current_tool_step, processing_time_ms=dt)
                return res

            def evaluate(env, tool, args, families, binding):
                s = time.perf_counter()
                res = _evaluate(env, tool, args, families, binding)
                dt = (time.perf_counter() - s) * 1000
                deficits, status = res.get("deficits", {}), res.get("status", {})
                recog = (binding or {}).get("recognition")
                amt = (binding or {}).get("amount")
                for fam in families:
                    src = ("recognition" if (recog and recog.get("family") == fam)
                           else "amount" if (amt and amt.get("family") == fam) else "structural/aggregator")
                    raw = None
                    if src == "recognition":
                        raw = {"args_checked": recog["args"], "recognized_set": recog["recognized_set"],
                               "normalizer": recog["normalizer"],
                               "targets": [args.get(a) for a in recog["args"]]}
                    elif src == "amount":
                        raw = {"arg": amt["arg"], "value": args.get(amt["arg"])}
                    t.emit("PREDICATE_EXTRACTION", "PredicateEvaluator", {
                        "predicate_name": fam, "source": src, "raw_evidence": raw,
                        "normalized_value": json.dumps(args, sort_keys=True, default=str),
                        "confidence": 1.0,
                    }, step=t.current_tool_step)
                for fam in families:
                    t.emit("PREDICATE_EVALUATION", "PredicateEvaluator", {
                        "predicate_name": fam,
                        "deficit": int(deficits.get(fam, 0)),
                        "satisfied": deficits.get(fam, 0) == 0,
                        "evaluation_status": status.get(fam),
                        "confidence": 1.0,
                        "policy_used": "ExecutionBinding.family_threshold",
                        "policy_version": METHOD_VERSION,
                    }, step=t.current_tool_step, processing_time_ms=dt / max(1, len(families)))
                self._last_eval = res
                return res

            def decide(deficits, harm_threshold: float = 0.5):
                s = time.perf_counter()
                res = _decide(deficits, harm_threshold)
                dt = (time.perf_counter() - s) * 1000
                active = sorted(k for k, v in deficits.items() if v == 1)
                # global (node-gate / max-aggregation deficit) vs class (veto) policy layers
                t.emit("GLOBAL_POLICY_EVALUATION", "GammaBridge", {
                    "deficit_families_active": active, "gamma_g": res["gamma_g"],
                    "deficit_count": res["deficit_count"], "aggregation": "non_compensatory_max",
                    "harm_threshold": harm_threshold,
                }, step=t.current_tool_step)
                t.emit("CLASS_POLICY_EVALUATION", "GammaBridge", {
                    "gamma_class": res["gamma_class"], "class_veto": res["gamma_class"] == 1,
                }, step=t.current_tool_step)
                t.emit("Γ COMPUTATION", "gamma_test_runner.evaluate_decision", {
                    "gamma_global": res["gamma_g"], "gamma_class": res["gamma_class"],
                    "deficit_count": res["deficit_count"], "isb": res["isb"],
                    "equation": "Gamma_G = max_i d_i (non-compensatory) ; class veto if ReasonCodes in {CLASS_1,GOODHART}",
                    "final_gamma": res["gamma_g"],
                }, step=t.current_tool_step, processing_time_ms=dt)
                t.emit("Π COMPUTATION", "gamma_test_runner.evaluate_decision", {
                    "equation": "Pi = 1 iff (Gamma_G == 0 AND Gamma_class == 0) else 0",
                    "inputs": {"gamma_g": res["gamma_g"], "gamma_class": res["gamma_class"]},
                    "final_pi": res["pi"],
                }, step=t.current_tool_step)
                self._last_decision = res
                return res

            sci.classify, ev.evaluate, br.decide = classify, evaluate, decide

        # ---- observe run_function: proposal, execution, result, observation ----
        def run_function(self, env, function, kwargs, raise_on_error: bool = False):
            t = self._tracer
            t.current_tool_step = t.next_step()
            self._last_eval = None
            self._last_decision = None
            t.emit("TOOL_CALL_PROPOSED", "AgentDojo.ToolsExecutor", {
                "tool_name": function, "arguments": dict(kwargs),
                "normalized_arguments": json.dumps(dict(kwargs), sort_keys=True, default=str),
                "tool_id": function, "call_id": f"{t.episode_id}-s{t.current_tool_step}",
            }, step=t.current_tool_step)
            self.candidate_trace.append({"function": function, "kwargs": dict(kwargs)})

            n_tx_before = self._env_action_count(env)
            s = time.perf_counter()
            content, error = self.run_function_split(env, function, kwargs, raise_on_error)
            dt = (time.perf_counter() - s) * 1000
            n_tx_after = self._env_action_count(env)

            dec = getattr(self, "_last_decision", None)
            decisions = self.gamma_decisions[-1] if self.gamma_decisions else None
            decision_str = (decisions or {}).get("decision") if decisions else ("PASS_THROUGH" if error is None and dec is None else None)

            if dec is not None:  # a mediated EEA reached Gamma
                if dec["decision"] == "PERMIT":
                    t.emit("PERMIT_DECISION", "GammaGovernedRuntime", {
                        "decision": "PERMIT", "reason": "Gamma_G==0 and Gamma_class==0 (Pi==1)",
                        "policy_triggered": None, "blocking_predicate": None,
                        "gamma_g": dec["gamma_g"], "gamma_class": dec["gamma_class"], "pi": dec["pi"],
                    }, step=t.current_tool_step)
                else:
                    ev = getattr(self, "_last_eval", {}) or {}
                    blocking = sorted(k for k, v in ev.get("deficits", {}).items() if v == 1) or ["(class-veto)"]
                    t.emit("DENY_DECISION", "GammaGovernedRuntime", {
                        "decision": "SAFE_STATE", "reason": f"deficit(s): {blocking}",
                        "policy_triggered": "Law-of-Concurrence", "blocking_predicate": blocking[0],
                        "gamma_g": dec["gamma_g"], "gamma_class": dec["gamma_class"], "pi": dec["pi"],
                    }, step=t.current_tool_step)

            executed = (error is None)
            t.emit("TOOL_EXECUTION", "AgentDojo.FunctionsRuntime", {
                "tool_invoked": function, "arguments": dict(kwargs),
                "executed": executed, "blocked": not executed,
                "decision_context": decision_str,
                "env_effect_delta": n_tx_after - n_tx_before,
            }, step=t.current_tool_step, processing_time_ms=dt)
            obs = content if content is not None else (error or "")
            obs_str = obs if isinstance(obs, str) else json.dumps(obs, default=str)
            t.emit("TOOL_RESULT", "AgentDojo.FunctionsRuntime", {
                "success": executed, "error": error,
                "returned_value_preview": obs_str[:500],
            }, step=t.current_tool_step)
            t.emit("OBSERVATION_RETURNED", "AgentDojo.ToolsExecutor", {
                "observation_preview": obs_str[:500], "observation_hash": _sha(obs_str),
                "observation_size_bytes": len(obs_str.encode("utf-8")),
            }, step=t.current_tool_step)
            return content, error

        # split so we can call the frozen super().run_function once and time it
        def run_function_split(self, env, function, kwargs, raise_on_error):
            return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)

        @staticmethod
        def _env_action_count(env) -> int:
            for path in (("bank_account", "transactions"), ("inbox", "emails"), ("calendar", "events")):
                obj = env
                for p in path:
                    obj = getattr(obj, p, None)
                    if obj is None:
                        break
                if obj is not None:
                    try:
                        return len(obj)
                    except TypeError:
                        pass
            return -1

    return TracingRuntime


# ============================================================================================
# LLM observer: wrap client.chat.completions.create (record-then-delegate, unchanged return)
# ============================================================================================
def instrument_pipeline_llm(pipeline, tracer: ExecutionTracer):
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM

    def _find(els):
        for e in els:
            if isinstance(e, OpenAILLM):
                return e
            sub = getattr(e, "elements", None)
            if sub:
                r = _find(sub)
                if r:
                    return r
        return None

    llm = _find(pipeline.elements)
    if llm is None:
        return None
    client = llm.client
    _orig = client.chat.completions.create
    tracer._llm_messages = []

    def wrapped(*a, **k):
        messages = k.get("messages", [])
        tools = k.get("tools", []) or []
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        user_msgs = [m for m in messages if m.get("role") == "user"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        step = tracer.next_step()
        if len([e for e in tracer.events if e["event_type"] == "LLM_REQUEST"]) >= 1:
            tracer.emit("LLM_NEXT_CONTEXT", "AgentDojo.pipeline", {
                "conversation_length": len(messages),
                "tool_outputs_appended": len(tool_msgs),
            }, step=step)
        tracer.emit("LLM_REQUEST", "AgentDojo.OpenAILLM", {
            "model": k.get("model"),
            "temperature": k.get("temperature") if not _is_notgiven(k.get("temperature")) else None,
            "seed": k.get("seed") if k.get("seed") is not None else "not_provided",
            "n_available_tools": len(tools),
            "system_prompt_hash": _sha(sys_msgs),
            "conversation_hash": _sha(messages),
            "user_message_hash": _sha(user_msgs[-1] if user_msgs else None),
            "tool_schema_hash": _sha(tools),
        }, step=step)
        s = time.perf_counter()
        completion = _orig(*a, **k)
        dt = (time.perf_counter() - s) * 1000
        try:
            msg = completion.choices[0].message
            fr = completion.choices[0].finish_reason
            tcs = msg.tool_calls or []
            usage = getattr(completion, "usage", None)
            tracer.emit("LLM_RESPONSE", "AgentDojo.OpenAILLM", {
                "finish_reason": fr,
                "assistant_text": msg.content,
                "n_tool_calls": len(tcs),
                "tool_names": [tc.function.name for tc in tcs],
                "tool_arguments": [tc.function.arguments for tc in tcs],
                "tool_calls": [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in tcs],
                "reasoning_metadata": getattr(msg, "reasoning", None),
                "response_hash": _sha({"content": msg.content, "tool_calls": [(tc.function.name, tc.function.arguments) for tc in tcs]}),
                "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            }, step=step, processing_time_ms=dt)
            tracer._llm_messages.append({"step": step, "request_messages": messages, "response": {
                "finish_reason": fr, "content": msg.content,
                "tool_calls": [{"id": tc.id, "name": tc.function.name, "arguments": tc.function.arguments} for tc in tcs]}})
        except Exception as e:  # never break the run on a logging error
            tracer.emit("LLM_RESPONSE", "AgentDojo.OpenAILLM", {"log_error": str(e)}, step=step, processing_time_ms=dt)
        return completion

    client.chat.completions.create = wrapped
    return llm


def _is_notgiven(v) -> bool:
    return type(v).__name__ == "NotGiven"


# ============================================================================================
# Output writers
# ============================================================================================
_TRACE_COMPONENTS = ["User", "LLM", "ToolsExecutor", "GammaGovernedRuntime", "PredicateEvaluator",
                     "GammaBridge", "DecisionEngine", "FunctionsRuntime"]


def write_all(outdir: str, tracer: ExecutionTracer, meta: dict):
    d = Path(outdir)
    d.mkdir(parents=True, exist_ok=True)
    ev = tracer.events

    # execution_trace.jsonl
    with open(d / "execution_trace.jsonl", "w") as f:
        for e in ev:
            f.write(json.dumps(e, default=str) + "\n")

    # execution_trace.csv (flat core columns)
    cols = ["event_id", "episode_id", "timestamp", "step_number", "event_type",
            "runtime_component", "processing_time_ms"]
    with open(d / "execution_trace.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["detail"])
        w.writeheader()
        for e in ev:
            row = {c: e.get(c) for c in cols}
            row["detail"] = json.dumps({k: v for k, v in e.items() if k not in cols}, default=str)
            w.writerow(row)

    def _of(types):
        return [e for e in ev if e["event_type"] in types]

    # per-domain logs
    json.dump(_of({"PREDICATE_EXTRACTION", "PREDICATE_EVALUATION"}),
              open(d / "predicate_log.json", "w"), indent=2, default=str)
    json.dump(_of({"GLOBAL_POLICY_EVALUATION", "CLASS_POLICY_EVALUATION", "Γ COMPUTATION", "Π COMPUTATION"}),
              open(d / "gamma_log.json", "w"), indent=2, default=str)
    json.dump(_of({"PERMIT_DECISION", "DENY_DECISION", "GAMMA_INTERCEPT"}),
              open(d / "authorization_log.json", "w"), indent=2, default=str)
    json.dump(_of({"TOOL_CALL_PROPOSED", "TOOL_EXECUTION", "TOOL_RESULT", "OBSERVATION_RETURNED"}),
              open(d / "tool_execution_log.json", "w"), indent=2, default=str)
    json.dump(getattr(tracer, "_llm_messages", []), open(d / "llm_messages.json", "w"), indent=2, default=str)

    # execution_graph.json (nodes = events, edges = sequential + step grouping)
    nodes = [{"id": e["event_id"], "type": e["event_type"], "component": e["runtime_component"],
              "step": e["step_number"]} for e in ev]
    edges = [{"from": ev[i]["event_id"], "to": ev[i + 1]["event_id"]} for i in range(len(ev) - 1)]
    json.dump({"nodes": nodes, "edges": edges}, open(d / "execution_graph.json", "w"), indent=2)

    # decision_tree.json (per tool step: proposal -> intercept -> predicates -> gamma -> decision)
    tree = {}
    for e in ev:
        st = e["step_number"]
        tree.setdefault(st, {"step": st, "events": []})
        if e["event_type"] in {"TOOL_CALL_PROPOSED", "GAMMA_INTERCEPT", "PREDICATE_EVALUATION",
                               "Γ COMPUTATION", "Π COMPUTATION", "PERMIT_DECISION", "DENY_DECISION",
                               "TOOL_EXECUTION"}:
            tree[st]["events"].append({k: v for k, v in e.items()
                                       if k in ("event_type", "tool_name", "policy_class", "predicate_name",
                                                "deficit", "gamma_global", "final_pi", "decision", "executed")})
    json.dump(list(tree.values()), open(d / "decision_tree.json", "w"), indent=2, default=str)

    # summary
    perm = _of({"PERMIT_DECISION"})
    deny = _of({"DENY_DECISION"})
    gammas = [e["gamma_global"] for e in _of({"Γ COMPUTATION"})]
    pis = [e["final_pi"] for e in _of({"Π COMPUTATION"})]
    lat = [e["processing_time_ms"] for e in ev if e.get("processing_time_ms") is not None]
    summary = {
        "episode_id": tracer.episode_id,
        "meta": meta,
        "total_events": len(ev),
        "total_steps": tracer.step,
        "n_llm_calls": len(_of({"LLM_REQUEST"})),
        "n_tool_calls_proposed": len(_of({"TOOL_CALL_PROPOSED"})),
        "n_permitted": len(perm),
        "n_denied": len(deny),
        "gamma_statistics": _stats(gammas),
        "pi_statistics": _stats(pis),
        "total_logged_latency_ms": round(sum(lat), 4),
        "final_utility_score": meta.get("utility"),
        "final_security_score": meta.get("security"),
        "frozen_roots": {"scientific_root": SCIENTIFIC_ROOT, "binding_sha": BINDING_SHA,
                         "method_version": METHOD_VERSION},
    }
    json.dump(summary, open(d / "execution_summary.json", "w"), indent=2, default=str)

    # episode_timeline.md + mermaid
    _write_timeline(d / "episode_timeline.md", tracer, summary)
    return summary


def _stats(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {"count": len(xs), "min": min(xs), "max": max(xs), "mean": round(sum(xs) / len(xs), 6)}


def _mermaid(tracer: ExecutionTracer) -> str:
    lines = ["sequenceDiagram", "    autonumber",
             "    participant U as User", "    participant L as LLM",
             "    participant T as ToolsExecutor", "    participant G as GammaGovernedRuntime",
             "    participant P as PredicateEngine", "    participant D as DecisionEngine(Γ,Π)",
             "    participant F as ToolRuntime"]
    for e in tracer.events:
        et = e["event_type"]
        if et == "LLM_REQUEST":
            lines.append("    U->>L: LLM_REQUEST (step %s)" % e["step_number"])
        elif et == "LLM_RESPONSE":
            n = e.get("n_tool_calls", 0)
            lines.append("    L-->>T: LLM_RESPONSE finish=%s, tool_calls=%s" % (e.get("finish_reason"), n))
        elif et == "TOOL_CALL_PROPOSED":
            lines.append("    T->>G: TOOL_CALL_PROPOSED %s" % e.get("tool_name"))
        elif et == "GAMMA_INTERCEPT":
            lines.append("    G->>P: GAMMA_INTERCEPT class=%s" % e.get("policy_class"))
        elif et == "PREDICATE_EVALUATION":
            lines.append("    P->>P: PREDICATE %s deficit=%s" % (e.get("predicate_name"), e.get("deficit")))
        elif et == "Γ COMPUTATION":
            lines.append("    P->>D: Γ=%s (class=%s)" % (e.get("gamma_global"), e.get("gamma_class")))
        elif et == "Π COMPUTATION":
            lines.append("    D->>D: Π=%s" % e.get("final_pi"))
        elif et == "PERMIT_DECISION":
            lines.append("    D-->>F: PERMIT")
        elif et == "DENY_DECISION":
            lines.append("    D-->>G: SAFE_STATE (deny)")
        elif et == "TOOL_EXECUTION":
            lines.append("    F->>F: TOOL_EXECUTION executed=%s" % e.get("executed"))
        elif et == "OBSERVATION_RETURNED":
            lines.append("    F-->>L: OBSERVATION_RETURNED")
        elif et == "EPISODE_FINISHED":
            lines.append("    Note over U,F: EPISODE_FINISHED utility=%s security=%s" % (e.get("utility"), e.get("security")))
    return "\n".join(lines)


def _write_timeline(path: Path, tracer: ExecutionTracer, summary: dict):
    lines = [f"# Episode Timeline — {tracer.episode_id}", "",
             f"- total events: {summary['total_events']} | steps: {summary['total_steps']}",
             f"- LLM calls: {summary['n_llm_calls']} | tool calls: {summary['n_tool_calls_proposed']}",
             f"- permitted: {summary['n_permitted']} | denied: {summary['n_denied']}",
             f"- Γ stats: {summary['gamma_statistics']}",
             f"- Π stats: {summary['pi_statistics']}",
             f"- utility: {summary['final_utility_score']} | security: {summary['final_security_score']}",
             "", "## Sequence diagram (Mermaid)", "", "```mermaid", _mermaid(tracer), "```", "",
             "## Event stream", "", "| step | event | component | ms |", "|---|---|---|---|"]
    for e in tracer.events:
        lines.append(f"| {e['step_number']} | {e['event_type']} | {e['runtime_component']} | "
                     f"{e['processing_time_ms'] if e['processing_time_ms'] is not None else ''} |")
    path.write_text("\n".join(lines))
    # also emit a standalone .mmd
    (path.parent / "episode_sequence.mmd").write_text(_mermaid(tracer))
