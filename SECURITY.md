# Security Policy

## Scope

This repository is a **research reproducibility artifact**, not a production security product.
L-DREA is a deterministic reference monitor evaluated under the conditions described in the paper;
nothing here should be deployed as a safety control without an independent assessment.

The threat model, the evaluated boundary, and the known gaps are documented in:

- [`LIMITATIONS_AND_NEGATIVE_RESULTS.md`](LIMITATIONS_AND_NEGATIVE_RESULTS.md)
- [`THREATS_TO_VALIDITY.md`](THREATS_TO_VALIDITY.md)
- §19 · Limitations, in [`README.md`](README.md)

Known and disclosed limitations (e.g. recognition-based authorization cannot distinguish a legitimate
contact weaponized as an exfiltration sink) are **documented findings, not vulnerabilities**. Please
read the limitations first — a report that restates a disclosed limitation will be closed as such.

## Reporting a vulnerability

If you believe you have found a genuine security issue — for example a way to bypass the action
boundary that the evaluation does not disclose, or a flaw in the evidence/hash-chain verification that
would let a tampered ledger verify as intact — please report it **privately**.

- Preferred: GitHub's **Report a vulnerability** (Security → Advisories) on this repository.
- Do **not** open a public issue for an undisclosed bypass.

Please include: what you attacked, the exact command or input, what you expected, what happened, and
the artifact (ledger / evidence / log) that demonstrates it.

## What to expect

- Acknowledgement of the report.
- An assessment of whether the finding is in scope (a bypass of a claimed property) or a restatement
  of an already-disclosed limitation.
- If in scope: the finding will be reproduced against the frozen engine and, where it affects a claim
  made in the paper, disclosed rather than quietly patched. **The scientific record takes precedence
  over the repository's appearance.**

## Supported versions

| Version | Supported |
|---|---|
| `v1.0-paper` (frozen artifact accompanying the IEEE Access submission) | Security reports accepted |
| Anything earlier | Not supported |

The `v1.0-paper` tag is **frozen** to match the published paper. A security fix that would change a
reported value will not be applied to that tag; it will be documented and shipped separately, so the
artifact continues to reproduce the paper exactly.
