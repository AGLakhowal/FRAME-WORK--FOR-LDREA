# PROJECT GUIDE — Understand L-DREA End-to-End

> **Read this first.** It explains what the project *is*, why it exists, what every big piece does,
> and which commands you actually need. The other files in `docs/` go deeper on specific topics.
> You do **not** need to read any source code to understand this guide.

Documentation set (all in `docs/`):
- **PROJECT_GUIDE.md** ← you are here (the big picture + who-runs-what)
- **ARCHITECTURE.md** — diagrams of how the pieces connect
- **COMMAND_REFERENCE.md** — every command, what it does, what it outputs
- **FLOWCHARTS.md** — what happens step-by-step when you run a command
- **EXPERIMENT_GUIDE.md** — every experiment (E1–E8) in detail
- **PAPER_TRACEABILITY.md** — where every paper number comes from + one full worked example
- **BEGINNER_GUIDE.md** — the whole thing explained with a bank analogy (ELI10)
- **CHEATSHEET.md** — "if I want to do X, run Y" + common mistakes

---

## 1. What is L-DREA? (in one paragraph)

**L-DREA** = *Lakhowal Deterministic Runtime Enforcement Architecture*. It is a **security guard that
sits between an AI agent and the real world.** When an AI wants to *do* something with real
consequences — move money, send an email, delete a file, change a password — L-DREA checks the action
**before** it happens and either says **PERMIT** (allow it) or **SAFE_STATE** (block it, safely). It is
built to be *deterministic* (same input → same decision, every time), *fail-closed* (when in doubt,
block), and *auditable* (every decision leaves tamper-evident evidence you can replay later).

**Analogy.** Think of an AI agent as a very fast, very capable new employee who can wire money and send
company-wide emails. Training that employee to "be careful" is not enough — you also want a **rule at
the door**: nothing leaves the building unless a guard checks the paperwork. L-DREA is that guard. The
AI can *propose* anything; L-DREA decides what actually *executes*.

## 2. Why was it created? What problem does it solve?

Modern AI agents don't just chat — they **take actions**. Today's AI-safety tools mostly work by:
- **Filtering the words** the AI produces (content moderation), or
- **Writing down what happened afterward** (logging).

Neither of those is a **reference monitor** — a gate that mediates *every* action *before* it executes.
If an attacker tricks the agent (a "prompt injection"), a word-filter can be bypassed and a log only
tells you about the damage *after* it's done. L-DREA solves this by being a **pre-action authorization
boundary**: the action does not happen unless the gate approves it.

Two ideas make it different from "normal AI safety":
1. **Capability ≠ Authority.** Being *able* to propose an action is separate from being *allowed* to
   execute it. The AI has capability; only L-DREA has authority.
2. **Non-compensatory decisions.** A single serious problem cannot be "averaged away" by other things
   looking fine. One red flag = block. (More on this below.)

## 3. The key vocabulary (plain English)

| Term | Plain-English meaning |
|------|----------------------|
| **Gamma (Γ)** | The **decision function** — the actual brain of the guard. It looks at all the checks and outputs a single verdict. There are two parts: **Γ_G** (did any individual check fail?) and **Γ_class** (did a "class-level" rule get violated?). If either is non-zero → block. |
| **Predicate** | One individual **check** ("is the recipient a known account?", "is the amount within limits?", "is the security token valid?"). Each predicate returns pass/fail. |
| **PERMIT** | The verdict "**allow this action to execute**." Only happens when *every* check passes. |
| **SAFE_STATE** | The verdict "**block this action**" and stay safe. This is the default when anything is wrong or uncertain (fail-closed). |
| **Class-level veto** | A rule that blocks an action even if each individual check looks clean, because the *pattern* is bad (stops an attacker from gaming the individual checks — "Goodhart's law" protection). |
| **Replay** | The ability to **re-run the exact decision later** from a saved record and get the identical result — proving the decision was deterministic and untampered. |
| **Evidence Quad / Hydra Ledger** | The **tamper-evident record** of each decision, chained together like a blockchain so any change is detectable. |
| **LAB v1.0** | The **benchmark / test protocol** — the standardized way of measuring whether L-DREA authorizes correctly. |
| **ConcurBench** | A **conformance test suite** that checks L-DREA under concurrency, adversarial, and distributed conditions. |
| **AgentDojo** | An **external, third-party benchmark** of AI agents under prompt-injection attack. We plug L-DREA in as the authorization layer to test it on *someone else's* adversarial tasks (not our own). |
| **Tier-S / Tier-T / Tier-H** | Three "strengths" of the guard's foundation: **S** = software-only (this repository), **T** = trusted-hardware enclave, **H** = dedicated hardware (FPGA+HSM). **This project is Tier-S: software is the reference implementation.** |

## 4. How the pieces fit together (one sentence each)

- The **AI agent** proposes actions.
- The **Runtime Interceptor** catches every action before it executes.
- **Gamma** evaluates all the **predicates** (checks) and produces **PERMIT** or **SAFE_STATE**.
- Every decision is written to the **Hydra Ledger** as tamper-evident **evidence**.
- The **Replay verifier** can re-check every decision from that evidence alone.
- **LAB / ConcurBench / AgentDojo** are the **test harnesses** that push many actions through the guard
  to measure how well it behaves.
- The **experiments** run those harnesses and write **JSON → CSV → tables → figures**, which become the
  **paper's evidence**.

See **ARCHITECTURE.md** for the full picture as diagrams.

## 5. The dataset (and what it is NOT)

The project uses the **ULB Credit-Card dataset** (`GAMMA_G0_CREDITCARD_FULL_mapped.csv`, ~451 MB,
284,807 rows). **Important:** this is **not** used to "detect fraud." It is used only as a **realistic
stream of transactions** to push through the authorization guard. The question we answer is *"does
L-DREA authorize or deny each runtime action correctly?"* — never *"can L-DREA catch fraudsters?"*

## 6. Two "run everything" commands — don't confuse them

This is the **single most important thing to understand** about the repo layout:

| Command | What it is | What it produces |
|---------|-----------|------------------|
| `python run_all.py` | The **older Gamma/ConcurBench suite** — runs the LAB benchmark + ConcurBench + stress + fail-closed + full-spec and builds an **HTML dashboard**. | `gamma_report.html` + several `*_report.json` at the repo root |
| `python RUN_ALL_EXPERIMENTS.py` | The **newer Tier-S reproducible evaluation** — runs **8 experiments (E1–E8)**, packages everything under `experiments/`, and auto-generates figures, tables, provenance, claim matrix, and validators. | The whole `experiments/` tree + `CLAIM_EVIDENCE_MATRIX.md`, `FINAL_EVIDENCE_REPORT.md`, etc. |

**If you want the publication evidence package, use `RUN_ALL_EXPERIMENTS.py`.** The older `run_all.py`
is still valid and useful for the interactive dashboard, but the reproducible, reviewer-facing package
is the new one.

## 7. Which commands do YOU need? (by role)

### Beginner ("I just want to see it work")
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py --fast     # ~30s, runs a lighter version of everything
```
Then open `experiments/figures/` (pictures) and `FINAL_EVIDENCE_REPORT.md` (the summary).

### Research workflow ("I'm running experiments")
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py            # full run, all 8 experiments (~45s)
# inspect: experiments/<name>/summary.md  and  experiments/statistics/statistics_report.md
```

### Paper workflow ("I'm writing / updating the paper")
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py            # regenerates tables + figures from fresh data
# use: experiments/tables/*.md (+ *.tex) and experiments/figures/*.svg directly in the manuscript
```

### Reviewer workflow ("I need to defend / audit the claims")
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py            # produce all evidence
./.venv/bin/python validate_paper_claims.py          # every number: JSON = table = figure = manifest?
./.venv/bin/python scientific_consistency.py         # 9 integrity checks (provenance, CIs, no stale files)
# read: CLAIM_EVIDENCE_MATRIX.md, reviewer_mapping.md, THREATS_TO_VALIDITY.md
```

### Developer workflow ("I'm changing something / debugging")
```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py --only formal replay      # run just a couple experiments
./.venv/bin/python experiment_robustness.py                         # run one experiment directly
./.venv/bin/python -m pytest tests/ -q                             # unit tests (if present)
```

See **CHEATSHEET.md** for the full "if I want X, run Y" table.

## 8. Learning summary

### Beginner version (2 minutes)
L-DREA is a **safety gate for AI actions**. An AI can propose anything; L-DREA checks each action with a
list of pass/fail tests and only says **PERMIT** if *everything* passes — otherwise **SAFE_STATE**
(block). Every decision is recorded so it can be re-checked later. We push a big stream of realistic
transactions (and adversarial agent tasks) through the gate, measure how well it decides, and turn those
measurements into the tables and figures in the paper. One command (`RUN_ALL_EXPERIMENTS.py`) runs
everything and produces the whole evidence package automatically.

### Researcher version (5 minutes)
The contribution is a **substrate-neutral runtime reference monitor for the action boundary** — a
deterministic, fail-closed, evidence-bearing authorization layer that generalizes Anderson's 1972
reference-monitor concept from *data access* to *externally-effective action*. The decision core
("Gamma") uses **non-compensatory aggregation** (Γ_G = max of per-check deficits, so one failure cannot
be offset) plus a **class-level veto** (prevents Goodhart-style gaming). Correctness is validated four
ways: (1) an exhaustive check that an independent re-implementation matches the engine over the entire
2¹⁶ input space; (2) a TLA⁺/TLC model-check of the Execution-Sovereignty invariant; (3) a full-corpus
run on 284,807 transactions (0 false permits, 100% replay determinism); (4) a fault-injection suite (16
failure modes, 0 false permits). External validity comes from **AgentDojo** (0 false permits on
genuinely-foreign attacker targets, measured without an LLM). Performance is characterized under
concurrency (safety holds at 1–64 threads; throughput is honestly reported as GIL-bound and *not*
scaling). The whole evaluation is **reproducible by one command** and **auto-audited**: a claims
registry maps each paper claim to an artifact + JSON pointer, and two validators confirm every number is
consistent across JSON → table → figure → manifest and that provenance is unbroken. The framing is
**Tier-S**: the software implementation is the reference; hardware deployment is explicitly *not
claimed*. The one dependency-blocked item (fresh AgentDojo LLM episodes → needs Ollama) is documented
with its exact rerun command.

**You can now explain this project to another researcher.** For the deep dives, continue to the other
`docs/` files.
