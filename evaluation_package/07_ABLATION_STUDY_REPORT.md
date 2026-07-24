# Category E — Ablation Study Report

**Purpose.** Demonstrate *why every architectural component exists* by removing each control
individually and measuring the safety regression it causes.
**Host.** Apple M5 / Python 3.9.6. **Date.** 2026-07-09. **All numbers fresh.**

## E1 — Component ablation

- **Command:** `./.venv/bin/python experiment_ablation.py`
- **Workload:** 60,000 deterministic decisions per config (θ = 0.5, compensatory τ = 0.15), controlled
  deficit mix. Each config swaps only the *decision function*; the baseline calls the frozen
  `evaluate_decision`.
- **Metric:** **leaked permits** = decisions the removed control converts from SAFE_STATE to PERMIT vs.
  the full-L-DREA baseline stream. This is the causal, measurable safety-regression signal on the
  software stack (Wilson 95% CI reported).

| Config (control removed) | permits | leaked permits | leaked rate (Wilson95 CI) | throughput (dec/s) | replay |
|---|---:|---:|---|---:|:--:|
| **baseline (full L-DREA)** | 15,000 | **0** | 0.0 [—, 6.4×10⁻⁵] | 665,111 | ✓ |
| − class-level veto | 30,000 | **15,000** | 0.250 [0.2466, 0.2535] | 664,015 | ✓ |
| − non-compensatory Γ (→ weighted-sum τ=0.15) | 30,000 | **15,000** | 0.250 [0.2466, 0.2535] | 820,357 | ✓ |
| − authorization layer (permit-all) | 60,000 | **45,000** | 0.750 [0.7465, 0.7534] | 3,724,501 | ✓ |

**Interpretation (honest, causal).**
- **Class-level veto** causally accounts for **15,000 / 60,000** denials (25%) that a veto-free rule
  leaks — direct evidence that the veto is not redundant with node-level predicates.
- **Non-compensatory Γ** causally accounts for another **15,000 / 60,000** (25%): a compensatory
  weighted-sum (τ = 0.15) permits deficit rows that `max`-aggregation denies. This is the concrete
  demonstration of the paper's central structural claim — compensation leaks.
- **Removing the authorization layer** leaks everything (45,000 = the entire deniable population, 75%).
- Note the **throughput inversion**: weaker configs are *faster* (permit-all reaches 3.7 M dec/s) —
  the safety controls have a real, if small, cost, and removing them trades safety for speed. Replay
  determinism holds in **every** config (the ledger stays consistent even when the policy is wrong),
  confirming determinism is orthogonal to policy correctness.

**Limitations (stated plainly).** This is a **leak-count on a synthetic deficit workload** — the
**Tier-S software analogue** of the paper's Table 4 FPR ablation. It is **not** the paper's
hardware-measured FPR (Tier-S 0.63%, −Γ 1.72%, −class-veto 3.11%) on the 360,000-item LAB
adversarial subset, because that generator and the Tier-H substrate are absent from this repository
(BLOCKED — see `08_THREATS_TO_VALIDITY.md` B3). The *direction and ranking* of the effects match the
paper (class-veto and Γ are the dominant safety contributors; removing authorization is catastrophic);
the *absolute FPR percentages* are not reproducible here.

## Category E verdict

Each structural component is shown to **causally prevent leaked permits** — class-veto (25%),
non-compensatory Γ (25%), authorization layer (75%) — with determinism preserved throughout. The
component-contribution claim is **CLOSED at Tier-S** as a leak-count; the paper's exact FPR deltas
remain **OPEN** on the missing LAB generator + Tier-H hardware.
