#!/usr/bin/env python3
"""
e5b_metric_note.py — the SINGLE source of the E5b metric-disambiguation note.
=============================================================================

The Combined Runtime Ablation (E5b) evaluates the runtime on a BLIND stream, so its detection
metrics are a different scientific construct from the authorization-soundness metrics reported by
the main benchmark and by AgentDojo. The two must never share a displayed name.

This module is the ONE place that note is written. Every E5b table, figure caption, dashboard
section, README and report imports it, so the wording cannot drift between surfaces.

SCOPE: these names exist ONLY inside E5b (Combined Ablation, Threshold Sensitivity, Cross-Dataset
Ablation, Master Ablation Table, E5b dashboard section, E5b JSON/figures/README). No metric outside
E5b is renamed — the Gamma LAB benchmark, the main authorization benchmark, AgentDojo, the runtime
evaluation and all production evidence keep their original, already-correct names.
"""
from __future__ import annotations

# The four E5b-local renames (old displayed name -> new displayed name).
RENAMES = [
    ("false_permit_rate", "undetected_risk_rate", "Undetected Risk Rate (URR)",
     "FN / (TP + FN) = 1 - Blind Detection Recall",
     "fraction of malicious events left UNDETECTED during blind runtime evaluation"),
    ("false_denial_rate", "benign_flag_rate", "Benign Flag Rate (BFR)",
     "FP / (TN + FP) = 1 - specificity",
     "fraction of benign events incorrectly flagged during blind runtime evaluation"),
    ("authorization_accuracy", "blind_decision_accuracy", "Blind Decision Accuracy",
     "(TP + TN) / N", "agreement of the runtime decision with the WITHHELD label"),
    ("runtime_risk_detection_rate", "blind_risk_detection_recall", "Blind Detection Recall",
     "TP / (TP + FN)", "recall of the blind, unsupervised anomaly-bound predicates"),
]

# ---------------------------------------------------------------- plain text (canonical wording)
NOTE_TEXT = (
    "URR (Undetected Risk Rate) = FN / (TP + FN) = 1 - Blind Detection Recall. "
    "This metric measures the fraction of malicious events that remain undetected during blind "
    "runtime evaluation. It is NOT the False Permit Rate reported in the main authorization "
    "benchmark. The paper's False Permit Rate (0/492 and 0/62) measures authorization soundness "
    "and remains unchanged."
)

# ---------------------------------------------------------------- Markdown
NOTE_MD = (
    "> **NOTE — URR is not the False Permit Rate.**\n"
    "> `URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall`\n"
    ">\n"
    "> This metric measures the fraction of malicious events that remain **undetected during blind "
    "runtime evaluation**. It is **NOT** the False Permit Rate reported in the main authorization "
    "benchmark. The paper's False Permit Rate (**0/492** and **0/62**) measures **authorization "
    "soundness** and remains unchanged."
)

# ---------------------------------------------------------------- LaTeX (IEEE table note)
NOTE_TEX = (
    "\\textbf{Note --- URR is not the False Permit Rate.} "
    "$\\mathrm{URR}\\;(\\text{Undetected Risk Rate}) = \\mathrm{FN}/(\\mathrm{TP}+\\mathrm{FN}) "
    "= 1 - \\text{Blind Detection Recall}$. "
    "This metric measures the fraction of malicious events that remain undetected during blind "
    "runtime evaluation. It is \\emph{not} the False Permit Rate reported in the main authorization "
    "benchmark. The paper's False Permit Rate ($0/492$ and $0/62$) measures authorization soundness "
    "and remains unchanged."
)

# ---------------------------------------------------------------- HTML (dashboard note)
NOTE_HTML = (
    "<p class='note'><b>NOTE — URR is not the False Permit Rate.</b> "
    "<code>URR (Undetected Risk Rate) = FN / (TP + FN) = 1 − Blind Detection Recall</code>. "
    "This metric measures the fraction of malicious events that remain undetected during blind "
    "runtime evaluation. It is <b>NOT</b> the False Permit Rate reported in the main authorization "
    "benchmark. The paper's False Permit Rate (0/492 and 0/62) measures authorization soundness and "
    "remains unchanged.</p>"
)


def note(fmt: str = "md") -> str:
    return {"md": NOTE_MD, "tex": NOTE_TEX, "html": NOTE_HTML, "text": NOTE_TEXT}[fmt]


if __name__ == "__main__":
    print(NOTE_TEXT)
    print()
    for old, new, disp, formula, means in RENAMES:
        print(f"  {old:28s} -> {new:28s}  '{disp}'  = {formula}")
