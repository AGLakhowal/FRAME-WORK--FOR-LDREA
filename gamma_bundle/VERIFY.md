# Verifying this audit bundle

Bundle id: `30159125bfcf43e1dc2a06aa7325748cccebdb1dceb7f0394eac9d5c090c3416`
Created:   2026-07-11T17:45:12Z
Method:    `gamma_test_runner/LAB-v1.0/2.0`
Ledger:    DIGEST_REFERENCE · sha256 `1ce2a9e8d4330a0583a9d20a398de43297ea59c404e006e7f1161208481931da`

## 1. Verify every member checksum

```bash
cd gamma_bundle
shasum -a 256 -c CHECKSUMS.sha256
```

Every line must report `OK`. 30 files are covered.

## 2. Verify the bundle programmatically

```bash
python tools/export_audit_bundle.py --verify
```

This re-reads `MANIFEST.json`, re-hashes every member from its bytes, and confirms the recorded
ledger digest still matches the live `gamma_replay_manifest.jsonl`. Exit code 0 means the bundle is
internally consistent and bound to the ledger it claims.

## 3. Re-verify the ledger independently

```bash
python replay_package/gamma_replay_verify.py gamma_replay_manifest.jsonl
```

The verifier shares no code with the authorization engine and never reads the dataset. Exit 0 = PASS.

## What is NOT in this bundle

* The 430 MB source dataset. It is identified by SHA-256 in
  `reproducibility/dataset_fingerprint.json`.
* The full 192 MB ledger. It is referenced by SHA-256; the GENESIS anchor and chain terminus are embedded in `replay_package/ledger_anchor_slice.jsonl`. Re-export with `--full` to embed it.
