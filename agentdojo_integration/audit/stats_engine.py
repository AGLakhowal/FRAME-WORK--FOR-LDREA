"""Phase B --- multi-episode statistical analysis.

Consumes per-episode `execution_trace.jsonl` files, extracts every authorization decision and
predicate evaluation, and computes benchmark-wide statistics with Wilson + bootstrap confidence
intervals and full descriptive statistics. Emits CSV / JSON / Markdown + publication-ready tables.

No fabricated values: every number is derived from recorded events. Metrics that require external
ground-truth labels (false-permit / false-deny rate) are reported as null with an explicit reason,
never invented.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from ._util import (read_jsonl, write_json, write_text, wilson_ci, bootstrap_ci,
                    describe, shannon_entropy, histogram)

_EEA_DECISION_EVENTS = {"PERMIT_DECISION", "DENY_DECISION"}


def _episode_traces(root: str | Path) -> list[Path]:
    return sorted(Path(root).rglob("execution_trace.jsonl"))


def collect(root: str | Path) -> dict:
    """Flatten all episodes into per-decision, per-predicate, per-event record tables."""
    decisions, predicates, tool_calls, latencies = [], [], [], []
    episodes = []
    for tf in _episode_traces(root):
        events = read_jsonl(tf)
        epi = tf.parent.name
        by_step: dict = defaultdict(dict)
        util = sec = None
        for e in events:
            et = e.get("event_type")
            if e.get("processing_time_ms") is not None:
                latencies.append({"episode": epi, "event_type": et, "ms": e["processing_time_ms"]})
            st = e.get("step_number")
            if et == "GAMMA_INTERCEPT":
                by_step[st]["tool"] = e.get("tool_proposed"); by_step[st]["class"] = e.get("policy_class")
            elif et == "TOOL_CALL_PROPOSED":
                tool_calls.append({"episode": epi, "step": st, "tool": e.get("tool_name")})
            elif et == "PREDICATE_EVALUATION":
                predicates.append({"episode": epi, "step": st, "predicate": e["predicate_name"],
                                   "deficit": int(e.get("deficit", 0)), "status": e.get("evaluation_status")})
            elif et == "Γ COMPUTATION":
                by_step[st]["gamma_global"] = e.get("gamma_global"); by_step[st]["gamma_class"] = e.get("gamma_class")
                by_step[st]["deficit_count"] = e.get("deficit_count")
            elif et == "Π COMPUTATION":
                by_step[st]["pi"] = e.get("final_pi")
            elif et == "GLOBAL_POLICY_EVALUATION":
                by_step[st]["harm_threshold"] = e.get("harm_threshold")
            elif et in _EEA_DECISION_EVENTS:
                by_step[st]["decision"] = e.get("decision")
                by_step[st]["blocking_predicate"] = e.get("blocking_predicate")
            elif et == "TOOL_EXECUTION":
                by_step[st]["executed"] = e.get("executed")
            elif et == "EPISODE_FINISHED":
                util, sec = e.get("utility"), e.get("security")
        for st, d in by_step.items():
            if "decision" in d:  # a genuine Gamma adjudication happened at this step
                decisions.append({"episode": epi, "step": st, **d})
        episodes.append({"episode": epi, "trace": str(tf), "utility": util, "security": sec,
                         "n_events": len(events)})
    return {"episodes": episodes, "decisions": decisions, "predicates": predicates,
            "tool_calls": tool_calls, "latencies": latencies}


def analyze(root: str | Path) -> dict:
    data = collect(root)
    dec = data["decisions"]
    preds = data["predicates"]
    n_dec = len(dec)
    permits = [d for d in dec if d.get("decision") == "PERMIT"]
    denials = [d for d in dec if d.get("decision") == "SAFE_STATE"]
    n_perm, n_deny = len(permits), len(denials)

    gamma_vals = [d.get("gamma_global") for d in dec if d.get("gamma_global") is not None]
    pi_vals = [d.get("pi") for d in dec if d.get("pi") is not None]
    deficit_counts = [d.get("deficit_count") for d in dec if d.get("deficit_count") is not None]
    class_veto = [1 if d.get("gamma_class") == 1 else 0 for d in dec]
    harm_thresholds = [d.get("harm_threshold") for d in dec if d.get("harm_threshold") is not None]

    # predicate activation (evaluated) & failure (deficit==1) frequency
    pred_activation = Counter(p["predicate"] for p in preds)
    pred_failure = Counter(p["predicate"] for p in preds if p["deficit"] == 1)
    pred_table = {}
    for name, act in pred_activation.items():
        fail = pred_failure.get(name, 0)
        pred_table[name] = {"activations": act, "failures": fail,
                            "failure_rate": wilson_ci(fail, act)}

    # per-tool authorization / denial frequency
    tool_dec = defaultdict(lambda: {"permit": 0, "deny": 0})
    for d in dec:
        tool_dec[d.get("tool")]["permit" if d.get("decision") == "PERMIT" else "deny"] += 1
    tool_table = {t: {**v, "n": v["permit"] + v["deny"],
                      "permit_rate": wilson_ci(v["permit"], v["permit"] + v["deny"])}
                  for t, v in tool_dec.items()}

    # policy-class utilization
    policy_util = Counter(d.get("class") for d in dec)

    # latency by event type + overall + Gamma-decision overhead
    lat_all = [x["ms"] for x in data["latencies"]]
    gamma_lat = [x["ms"] for x in data["latencies"] if x["event_type"] in ("Γ COMPUTATION", "GLOBAL_POLICY_EVALUATION")]
    lat_by_type = defaultdict(list)
    for x in data["latencies"]:
        lat_by_type[x["event_type"]].append(x["ms"])

    # decision entropy + authorization stability
    dec_entropy = shannon_entropy([n_perm, n_deny])
    # stability: within each (tool,class) group, fraction that agrees with the group's majority decision
    grp = defaultdict(list)
    for d in dec:
        grp[(d.get("tool"), d.get("class"))].append(d.get("decision"))
    stab = []
    for _k, ds in grp.items():
        if ds:
            maj = Counter(ds).most_common(1)[0][1]
            stab.append(maj / len(ds))
    stability = sum(stab) / len(stab) if stab else None

    return {
        "n_episodes": len(data["episodes"]),
        "n_decisions": n_dec,
        "n_authorizations_permit": n_perm,
        "n_denials": n_deny,
        "permit_rate_wilson": wilson_ci(n_perm, n_dec),
        "denial_rate_wilson": wilson_ci(n_deny, n_dec),
        "class_veto_frequency": {"count": sum(class_veto), "rate_wilson": wilson_ci(sum(class_veto), n_dec)},
        "gamma_global": {"distribution": histogram(gamma_vals, [-0.5, 0.5, 1.5]),
                         "describe": describe(gamma_vals)},
        "pi": {"distribution": histogram(pi_vals, [-0.5, 0.5, 1.5]), "describe": describe(pi_vals)},
        "deficit_count": {"describe": describe(deficit_counts),
                          "distribution": histogram(deficit_counts, [-0.5, 0.5, 1.5, 2.5, 3.5, 10.5])},
        "harm_threshold": {"describe": describe(harm_thresholds),
                           "unique_values": sorted(set(harm_thresholds))},
        "predicate_frequency": pred_table,
        "tool_frequency": tool_table,
        "policy_utilization": dict(policy_util),
        "latency_ms": {"overall": describe(lat_all),
                       "overall_mean_bootstrap": bootstrap_ci(lat_all),
                       "gamma_decision_overhead": describe(gamma_lat),
                       "by_event_type": {k: describe(v) for k, v in lat_by_type.items()}},
        "decision_entropy_bits": dec_entropy,
        "authorization_stability": stability,
        "false_permit_rate": None,
        "false_deny_rate": None,
        "_labels_note": ("false_permit_rate / false_deny_rate require external ground-truth labels of "
                         "the CORRECT authorization for each action; these are not present in the traces, "
                         "so they are reported as null rather than fabricated. AgentDojo utility/security "
                         "are episode-level task/attack outcomes, not per-action authorization ground truth."),
        "episode_outcomes": {"utility_true": sum(1 for e in data["episodes"] if e["utility"] is True),
                             "security_true": sum(1 for e in data["episodes"] if e["security"] is True),
                             "total": len(data["episodes"])},
    }


# ------------------------------------------------------------------ writers
def write_reports(root: str | Path, outdir: str | Path) -> dict:
    data = collect(root)
    stats = analyze(root)
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    write_json(out / "statistics.json", stats)

    # decisions.csv (one row per Gamma adjudication)
    with open(out / "decisions.csv", "w", newline="") as f:
        cols = ["episode", "step", "tool", "class", "gamma_global", "gamma_class", "pi",
                "deficit_count", "decision", "blocking_predicate", "executed", "harm_threshold"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for d in data["decisions"]:
            w.writerow(d)
    # predicates.csv
    with open(out / "predicates.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["episode", "step", "predicate", "deficit", "status"])
        w.writeheader()
        for p in data["predicates"]:
            w.writerow(p)

    write_text(out / "statistics_tables.md", _markdown_tables(stats))
    return stats


def _fmt_ci(ci: dict) -> str:
    if not ci or ci.get("p") is None:
        return "n/a"
    return f"{ci['p']:.3f} [{ci['low']:.3f}, {ci['high']:.3f}]"


def _markdown_tables(s: dict) -> str:
    L = ["# Statistical Analysis — publication tables", "",
         f"- Episodes: {s['n_episodes']} · Gamma decisions: {s['n_decisions']} "
         f"(PERMIT {s['n_authorizations_permit']}, SAFE_STATE {s['n_denials']})",
         f"- Permit rate (Wilson 95%): {_fmt_ci(s['permit_rate_wilson'])}",
         f"- Denial rate (Wilson 95%): {_fmt_ci(s['denial_rate_wilson'])}",
         f"- Class-veto rate (Wilson 95%): {_fmt_ci(s['class_veto_frequency']['rate_wilson'])}",
         f"- Decision entropy: {s['decision_entropy_bits']:.4f} bits · Authorization stability: {s['authorization_stability']}",
         "",
         "## Table I — Γ / Π / deficit-count descriptive statistics", "",
         "| metric | count | mean | median | std | min | max | IQR |", "|---|---|---|---|---|---|---|---|"]
    for name, key in [("Γ_global", "gamma_global"), ("Π", "pi"), ("deficit_count", "deficit_count")]:
        d = s[key]["describe"]
        L.append(f"| {name} | {d['count']} | {_n(d['mean'])} | {_n(d['median'])} | {_n(d['std'])} | "
                 f"{_n(d['min'])} | {_n(d['max'])} | {_n(d['iqr'])} |")
    L += ["", "## Table II — Predicate activation & failure (Wilson 95%)", "",
          "| predicate | activations | failures | failure rate [95% CI] |", "|---|---|---|---|"]
    for name, v in sorted(s["predicate_frequency"].items(), key=lambda kv: -kv[1]["activations"]):
        L.append(f"| {name} | {v['activations']} | {v['failures']} | {_fmt_ci(v['failure_rate'])} |")
    L += ["", "## Table III — Per-tool authorization (Wilson 95%)", "",
          "| tool | n | permit | deny | permit rate [95% CI] |", "|---|---|---|---|---|"]
    for t, v in sorted(s["tool_frequency"].items(), key=lambda kv: -kv[1]["n"]):
        L.append(f"| {t} | {v['n']} | {v['permit']} | {v['deny']} | {_fmt_ci(v['permit_rate'])} |")
    L += ["", "## Table IV — Latency (ms)", "",
          "| scope | count | mean | median | std | max |", "|---|---|---|---|---|---|"]
    lo = s["latency_ms"]["overall"]; go = s["latency_ms"]["gamma_decision_overhead"]
    bc = s["latency_ms"]["overall_mean_bootstrap"]
    L.append(f"| all events | {lo['count']} | {_n(lo['mean'])} | {_n(lo['median'])} | {_n(lo['std'])} | {_n(lo['max'])} |")
    L.append(f"| Gamma decision overhead | {go['count']} | {_n(go['mean'])} | {_n(go['median'])} | {_n(go['std'])} | {_n(go['max'])} |")
    L.append("")
    L.append(f"Bootstrap 95% CI for mean event latency: {_n(bc['stat'])} [{_n(bc['low'])}, {_n(bc['high'])}] "
             f"(n={bc['n']}, {bc['n_boot']} resamples, seed {bc['seed']}).")
    L += ["", f"> {s['_labels_note']}"]
    return "\n".join(L)


def _n(x) -> str:
    return "n/a" if x is None else f"{x:.4f}" if isinstance(x, float) else str(x)
