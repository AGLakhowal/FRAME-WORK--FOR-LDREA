# CONFIDENCE_INTERVAL_VERIFICATION

Every CI in Tables 10/11/13 is a **Wilson score interval** (closed-form) except the bootstrap CI for
mean event latency. Each is recomputed independently in `verify_provenance.py` (pure-Python Wilson,
no reuse of `_util`). All match to <1e-9.

## Method — Wilson score interval (95%)
```
z      = 1.959963984540054            # Φ⁻¹(0.975), 95% two-sided
p̂      = k / n
denom  = 1 + z²/n
center = (p̂ + z²/(2n)) / denom
half   = z·√( (p̂(1−p̂) + z²/(4n)) / n ) / denom
CI     = [center − half, center + half]   (clamped to [0,1])
```

## Table 11 — permit rate (k=11, n=14)
- p̂ = 11/14 = 0.785714285714…
- z² = 3.841458820694…; z²/n = 0.274389915764; denom = 1.274389915764
- center = (0.785714 + 0.137194957882)/1.274389916 = 0.724197…
- half = 1.959963985·√((0.785714·0.214286 + 0.960364705/56)/14)/1.274389916 = 0.200089…
- **CI = [0.524107694, 0.924286132]** → paper **0.786 [0.524, 0.924]** (round to 3 dp)
- Independent recompute == stored `permit_rate_wilson` (PASS).

## Table 11 — denial rate (k=3, n=14)
- p̂ = 3/14 = 0.214285714
- **CI = [0.075713867, 0.475892306]** → paper **0.214 [0.076, 0.476]** (PASS)

## Table 11 — FDR (k=0, n=5)
- p̂ = 0; Wilson lower = 0.0; upper = z²/(4n)-driven = **0.434482465**
- → paper **0.000 [0.000, 0.434]** (PASS). FPR: k/n with n=0 → **undefined**, reported as such (not a CI).

## Table 11 — class-veto rate (k=0, n=14)
- **[0.0, 0.215]** from `class_veto_frequency.rate_wilson` (count=0). Consistent.

## Bootstrap CI (mean event latency) — method audit
- `_util.bootstrap_ci`: percentile bootstrap, **n_boot=2000**, **seed=12345** (deterministic),
  **alpha=0.05** → [2.5th, 97.5th] percentile of 2000 resampled means. Deterministic across runs
  (unit test `bootstrap deterministic (fixed seed)` PASS). Only used for the descriptive latency
  table, not a headline Table 11 cell.

## Verdict
All confidence intervals are Wilson (closed-form) or fixed-seed percentile bootstrap; every reported
interval reproduces from its raw counts using the documented formula and the single constant
z = 1.959963984540054. **CI VERIFICATION: PASS.**
