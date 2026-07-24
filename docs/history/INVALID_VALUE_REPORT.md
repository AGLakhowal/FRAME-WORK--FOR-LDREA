# INVALID_VALUE_REPORT

Search for values that are manually entered, estimated, hand-copied, duplicated, stale, overwritten,
cached, inconsistent, or non-reproducible — across Tables 10/11/13, their JSON/CSV, figures, and the
raw traces.

## Result: NO INVALID VALUES FOUND

All 26 independent recomputation/consistency checks PASS (`verify_provenance.py`). Specifically:
- No **manually entered** statistic: every Table 10/11/13 number resolves to a JSON key produced by a
  named function over raw traces (see VALUE_TRACEABILITY.md).
- No **estimated / hand-copied**: recomputation from raw == stored (counts, Wilson, entropy, latency).
- No **duplicated / stale / overwritten**: JSON == CSV == traces; re-running `stats_engine.analyze`
  reproduces stored scalars; figures == statistics.
- No **inconsistent**: Γ_global=OR(deficits), Π, decision re-derive correctly for all 14 decisions;
  replay re-run == stored.
- No **non-reproducible**: every value has a documented reproduce command.

## Items requiring an explicit note (valid, not invalid)

| Item | Location | Nature | Why NOT invalid |
|---|---|---|---|
| FPR = "undefined (n=0)" | Table 11 | no denominator | Honestly reported n=0 (the agent proposed 0 attacker-targeted actions), NOT a fabricated 0. |
| FDR = 0.000 [0,0.434] | Table 11 | near-tautological | Explicitly caveated (legit class = recognized set the monitor uses); reported for completeness. |
| security 1/33 "0 via EEA" | Table 11 | needs interpretation | Verified: the 1 success was a read-only action (no EEA) → Group III / Property-v, out of scope by construction. |
| Rounding | Tables 10/11 | display precision | Both raw and rounded shown in VALUE_TRACEABILITY / TABLE_VERIFICATION (e.g., 0.021593→0.0216, 0.78571→0.786). |
| Two latency contexts (T10) | Table 10 | different n | build/bind/emit (n=2000) vs Runtime Context/Replay (n=5000) — each cited to its own run; not mixed within a cell. |
| GIL-bound throughput (T13) | Table 13 | design fact | Real measurement; the decline is honestly reported with the GIL explanation, not hidden. |

## Correction actions required: NONE.

No value was altered by this audit (verification-only). No recompute produced a different number than
the stored artifact, so no correction is warranted.
