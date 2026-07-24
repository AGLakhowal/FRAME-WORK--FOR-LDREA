# HARDCODED_CONSTANT_AUDIT

Every constant used in a calculation feeding a paper value. No constant lacks justification.

| Constant | Value | File | Purpose | Scientific Justification | Hardcoded? | Replaceable? |
|---|---|---|---|---|---|---|
| `Z95` | 1.959963984540054 | audit/_util.py:16 | Wilson/normal 95% CI z-score | Φ⁻¹(0.975), the exact 0.975 quantile of the standard normal → 95% two-sided CI | Yes | Yes — `wilson_ci(..., z=)` parameter |
| bootstrap `n_boot` | 2000 | audit/_util.py:73 | # resamples for percentile bootstrap CI | 2000 resamples give stable 2.5/97.5 percentiles for these sample sizes; standard practice | Yes | Yes — function arg |
| bootstrap `seed` | 12345 | audit/_util.py:74 | RNG seed for deterministic bootstrap | Fixed seed ⇒ reproducible CI (required by reproducibility mandate) | Yes | Yes — function arg; any fixed seed valid |
| `alpha` | 0.05 | audit/_util.py:74 | CI tail mass (→95%) | Standard 95% confidence level | Yes | Yes — function arg |
| entropy `base` | 2 | audit/_util.py (shannon_entropy) | log base → bits | Decision entropy reported in **bits** | Yes | Yes — arg (base=) |
| histogram bin edges | [-0.5, 0.5, 1.5] | audit/stats_engine.py:134,136 | bin Γ/Π (binary 0/1) | Γ_global, Π ∈ {0,1}; edges center integer bins | Yes | Yes — the variable is binary by construction |
| deficit-count bin edges | [-0.5,0.5,1.5,2.5,3.5,10.5] | audit/stats_engine.py:138 | bin small integer deficit counts | integer counts 0..N; edges center integers | Yes | Yes |
| `harm_threshold` | 0.5 | interception/gamma_bridge.py:30 | frozen Gamma HARM_RISK gate threshold | **FROZEN paper parameter** (Law-of-Concurrence); reused engine default, not introduced by the audit | Yes (frozen) | No — frozen component; must not change |
| Gamma row defaults | HARM_RISK 0.0, TelemetryFresh True, … | interception/gamma_bridge.py:32-36 | neutral row seed for the reused engine | **FROZEN** — part of the reused `evaluate_decision` contract | Yes (frozen) | No — frozen |
| concurrency workload `n_decisions` | 200000 | audit/concurrency_scaling.py:100 | # decisions per thread level | large enough for stable throughput/latency timing; experiment size, not a paper statistic | Yes | Yes — arg |
| concurrency thread counts | [1,2,4,8,16,32] | audit/concurrency_scaling.py:31 | scaling levels | powers-of-two sweep spanning ≤ and > cpu_count(10) | Yes | Yes — arg |
| runtime-profile `n_rows` | 5000 | audit/runtime_profile.py | rows for RCL/Replay timing | large enough for stable per-row latency | Yes | Yes — arg |

## Findings
- **No constant lacks scientific justification.** No `SCIENTIFIC JUSTIFICATION REQUIRED` flags.
- The two **frozen** constants (`harm_threshold=0.5`, Gamma row defaults) belong to the reused,
  paper-specified engine — they are *not* introduced by the audit framework and must not be altered.
- All audit-side constants (z, n_boot, seed, alpha, base, bin edges, workload sizes) are standard and
  exposed as function parameters (replaceable), used with documented, conventional values.

**HARDCODED CONSTANT AUDIT: PASS (all justified).**
