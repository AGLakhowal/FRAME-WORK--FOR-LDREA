# Statistical Analysis — computed from executed outputs

> **Determinism note.** The authorization engine is deterministic. For its outputs, a confidence interval quantifies coverage of the sampled input space (sampling uncertainty of the proportion), NOT run-to-run stochastic variability. Frequentist p-values are not computed for deterministic equalities. Bootstrap CIs are applied only to measured latency, which is genuinely variable.

## Proportion metrics (Wilson 95%)
| Metric | Events/N | Point | Wilson95 low | Wilson95 high | Exp |
|--------|----------|-------|--------------|---------------|-----|
| False Permit Rate (ULB, should-deny pop.) | 0/492 | 0 | 0.000e+00 | 7.747e-03 | E1 |
| Unauthorized Execution Rate (ULB, all rows) | 0/284807 | 0 | 8.470e-22 | 1.349e-05 | E1 |
| Boundary FPR (AgentDojo foreign targets) | 0/62 | 0 | 0.000e+00 | 5.834e-02 | E7 |
| Robustness false-permit rate (all decision-path faults) | 0/51 | 0 | 0.000e+00 | 7.005e-02 | E8 |
| Single-deficit false-permit rate (E9 predicate isolation) | 0/13 | 0 | 0.000e+00 | 2.281e-01 | E9 |

## Zero-event upper bounds (Wilson vs rule-of-three 3/n)
| Metric | N | Wilson95 upper | Rule-of-three upper | Exp |
|--------|---|----------------|---------------------|-----|
| False Permit Rate (ULB, should-deny pop.) | 492 | 7.747e-03 | 6.098e-03 | E1 |
| Unauthorized Execution Rate (ULB, all rows) | 284,807 | 1.349e-05 | 1.053e-05 | E1 |
| Boundary FPR (AgentDojo foreign targets) | 62 | 5.834e-02 | 4.839e-02 | E7 |
| Robustness false-permit rate (all decision-path faults) | 51 | 7.005e-02 | 5.882e-02 | E8 |
| Single-deficit false-permit rate (E9 predicate isolation) | 13 | 2.281e-01 | 2.308e-01 | E9 |

## Ablation effect sizes (risk difference + Cohen's h vs full L-DREA)
| Contrast | Baseline leak | Ablated leak | Risk diff | Cohen's h | N/arm |
|----------|--------------|-------------|-----------|-----------|-------|
| remove_class_veto vs baseline | 0.000 | 0.250 | +0.250 | 1.047 | 60,000 |
| remove_noncompensatory_gamma vs baseline | 0.000 | 0.250 | +0.250 | 1.047 | 60,000 |
| remove_authorization_layer vs baseline | 0.000 | 0.750 | +0.750 | 2.094 | 60,000 |

## Latency
```json
[
  {
    "metric": "ULB decision latency (ms) \u2014 summary (no raw samples persisted)",
    "experiment": "E1",
    "mean": 0.025917,
    "p95": 0.032333,
    "p99": 0.03775,
    "note": "raw per-row latency samples are not persisted by the stable runner; bootstrap requires the sample vector. Summary reported instead."
  }
]
```

## Sensitivity across thread levels
```json
{
  "concurrency_threads": {
    "levels": [
      1,
      2,
      4,
      8,
      16,
      32,
      64
    ],
    "throughput_decisions_per_s": [
      355150.6,
      408922.3,
      318722.5,
      95098.4,
      75342.0,
      71116.3,
      69796.5
    ],
    "p99_ms": [
      0.0019159999986584353,
      0.0015409999996052193,
      0.003000000003083869,
      0.003792000001112683,
      0.0040000000041118255,
      0.004166000003635872,
      0.004167000000165899
    ],
    "false_permits": [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "false_denials": [
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "observation": "safety metrics (FP/FD) are invariant to thread count; throughput is monotone-degrading (GIL-bound) \u2014 a genuine sensitivity of performance, not of correctness."
  },
  "design_effect_on_FPR_bound": {
    "events": 0,
    "n": 492,
    "sweep": [
      {
        "design_effect": 1.0,
        "n_eff": 492.0,
        "wilson95_upper": 0.007747353014470844
      },
      {
        "design_effect": 1.7,
        "n_eff": 289.4,
        "wilson95_upper": 0.013117878992148575
      },
      {
        "design_effect": 2.0,
        "n_eff": 246.0,
        "wilson95_upper": 0.015375585936884312
      },
      {
        "design_effect": 3.0,
        "n_eff": 164.0,
        "wilson95_upper": 0.022887425119427582
      }
    ],
    "observation": "The FPR upper bound scales with the assumed design effect. DE = 1.7 is the value the engine reports; DE = 1.0 (independent rows) is optimistic and DE = 3.0 pessimistic. The qualitative conclusion \u2014 zero observed false permits with a bound of order 1e-2 on n = 492 \u2014 is stable across the sweep."
  },
  "ablation_workload": {
    "workload_n_per_config": 60000,
    "leak_rates": {
      "baseline_full_LDREA": 0.0,
      "remove_class_veto": 0.25,
      "remove_noncompensatory_gamma": 0.25,
      "remove_authorization_layer": 0.75
    },
    "observation": "The engine is deterministic and the workload is index-driven, so each leak rate is an exact proportion of a constructed population, not an estimate. Increasing n narrows the Wilson interval but cannot move the point value."
  }
}
```