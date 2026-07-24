# Stage 10 — Audit Bundle Export

Status: **EXECUTED** · 16.0s

- Bundle verification: **PASS**
- Bundle id: `30159125bfcf43e1dc2a06aa7325748cccebdb1dceb7f0394eac9d5c090c3416`
- Members verified: 30
- Ledger digest bound to live ledger: True

The criterion is not directory existence. Every member is re-hashed from its bytes and the recorded ledger digest must match the live ledger; an empty or tampered bundle FAILS.

Reproduce: `./.venv/bin/python tools/export_audit_bundle.py && ./.venv/bin/python concurbench_full.py`
