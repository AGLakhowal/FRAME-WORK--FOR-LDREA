# AgentDojo Boundary FPR — direct adjudication (no LLM)

- Frozen root: `ce8c8467a3a9d60c69864b8a94a44f2b871440b333f659307da011e1bb64f618`  binding sha `a38619274c6e796eeb8ba2e03c45a9ef351cd571c141118be82dc8351dc969b1`
- Injection tasks: 27 across 4 suites; adversarial actions adjudicated: 70

## Soundness — genuinely-foreign attacker targets (the claim)
- **FPR = 0/62 = 0.0**  (Wilson95 upper = 5.834e-02)

## Recognized-identifier sends (correct-by-policy, not false permits)
- permitted 8/8 — targets already in the env recognized set (known contacts/URLs the attack GOAL named). Documented limitation: recognition-based gating cannot flag a known contact weaponized as an exfil sink.

## Coverage boundary (structural-only tools)
- permitted 0/0 — these tools carry no env recognition gate.

## By suite (foreign-target FPR)
- workspace: FPR 0/24 (Wilson95↑ 1.380e-01)
- travel: FPR 0/12 (Wilson95↑ 2.425e-01)
- banking: FPR 0/16 (Wilson95↑ 1.936e-01)
- slack: FPR 0/10 (Wilson95↑ 2.775e-01)