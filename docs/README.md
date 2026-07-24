# L-DREA Documentation Set — Start Here

A no-code, plain-English guide to the whole project. Written so a new PhD student (or the paper's author
returning after a break) can understand it end-to-end **without reading source code**. All diagrams are
Mermaid and render on GitHub.

## Reading order

1. **[PROJECT_GUIDE.md](PROJECT_GUIDE.md)** — the big picture: what L-DREA is, why it exists, the key
   words (Gamma, predicates, PERMIT, SAFE_STATE, LAB, ConcurBench, AgentDojo), and which commands you
   need for your role. **Start here.**
2. **[BEGINNER_GUIDE.md](BEGINNER_GUIDE.md)** — the same ideas as a bank-security story (ELI10). Read
   this if any term felt abstract.
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** — how every piece connects, with full diagrams and the folder
   map.
4. **[FLOWCHARTS.md](FLOWCHARTS.md)** — what happens step-by-step when you run a command, and how a
   dataset row becomes a paper number.
5. **[EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md)** — all 8 experiments (E1–E8) and every file they
   produce.
6. **[PAPER_TRACEABILITY.md](PAPER_TRACEABILITY.md)** — where each paper number comes from, plus one
   complete authorization walked end-to-end.
7. **[COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)** — every command: purpose, runtime, requirements,
   outputs.
8. **[CHEATSHEET.md](CHEATSHEET.md)** — "if I want X, run Y" + the errors you'll hit and how to fix them.

## The 10-second summary

L-DREA is a **safety gate for AI actions**: an AI can propose anything, but a deterministic, fail-closed
guard ("Gamma") checks every action against many pass/fail predicates and only says **PERMIT** if all
pass — otherwise **SAFE_STATE** (block). Every decision is written to a tamper-evident ledger that can be
replayed to prove it was honest. Eight experiments push realistic transactions and real adversarial agent
tasks through the gate, and one command turns the results into the paper's figures, tables, and
reviewer-facing evidence — all automatically, all reproducible.

## The one command that does everything

```bash
./.venv/bin/python RUN_ALL_EXPERIMENTS.py
```
Then read `FINAL_EVIDENCE_REPORT.md`.
