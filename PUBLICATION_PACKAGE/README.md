# PUBLICATION_PACKAGE — L-DREA Combined Component Ablation (E5b)

Everything needed to drop straight into an IEEE Access manuscript. Every value in every artifact was produced by executing the runtime; nothing is estimated or hand-entered.

- Generated: `2026-07-11T14:13:45Z`
- Artifacts: **57/57** passed validation (0 missing, 0 invalid)
- Package complete: **True**

## Layout

| Directory | Contents |
|---|---|
| `latex/` | IEEE-ready `.tex` tables — `\input{}` them directly (needs `\usepackage{booktabs}`) |
| `figures/` | 7 publication figures, each as SVG + PDF + PNG (PDF is the vector master) |
| `tables/` | Human-readable Markdown tables |
| `json/` | Machine-readable evidence (the source of every number) |
| `csv/` | Flat data for re-analysis |
| `markdown/` | Analysis + interpretation reports |
| `threats/` | Threats to validity |
| `reviewer_mapping/` | Reviewer concern → experiment → evidence chain |
| `metadata/` | Provenance: git SHA, dataset SHA-256, seed, environment, per-artifact hashes |
| `dashboard/` | Self-contained interactive dashboard |

## Headline measured results

- **19 configurations** executed through the full runtime (n=6000/config).
- Baseline Runtime Integrity Score: **1.0**.
- Interaction effects measured, not assumed: the evidence→ledger→hash-chain cascade is a **Critical Dependency**; independent planes are **Additive**; **no** combination is synergistic on this workload.

## Required LaTeX preamble

```latex
\usepackage{booktabs}
```

## Reproduce everything

```bash
python3 run_publication_pipeline.py
```

