#!/usr/bin/env python3
"""
generate_provenance_metadata.py — PART 6: provenance for every generated artifact.
==================================================================================

Every figure, table, JSON, CSV and Markdown artifact of the combined-ablation package gets a
provenance record containing:

    generation timestamp (UTC)   git commit SHA (+ dirty flag)   dataset SHA-256
    experiment seed              experiment version              generator script
    runtime version              Python version                  hostname / OS
    command executed             artifact SHA-256 + byte size

Outputs:
    metadata/provenance/<artifact>.json      one record per artifact
    metadata/PROVENANCE_MANIFEST.json        the index (every artifact, hash, generator, status)
    metadata/dataset_hashes.json             cached dataset SHA-256 (large files; recomputed on change)

Nothing is hardcoded: hashes are computed from the files on disk at generation time, the git SHA is
read from git, and a MISSING artifact is recorded as missing rather than silently skipped.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
META = ROOT / "metadata"
PROV = META / "provenance"
CA = ROOT / "experiments" / "combined_ablation"

EXPERIMENT_VERSION = "E5b/combined-ablation/2.0-publication"
SEED = 20260710

# artifact (repo-relative) -> the generator script that produced it
GENERATORS = {
    "experiments/combined_ablation/combined_ablation.json": "experiment_combined_ablation.py",
    "experiments/combined_ablation/combined_ablation.csv": "experiment_combined_ablation.py",
    "experiments/combined_ablation/combined_ablation_matrix.csv": "experiment_combined_ablation.py",
    "experiments/combined_ablation/combined_statistics.json": "experiment_combined_ablation.py",
    "experiments/combined_ablation/combined_statistics.csv": "experiment_combined_ablation.py",
    "experiments/combined_ablation/combined_statistics.md": "experiment_combined_ablation.py",
    "experiments/combined_ablation/threshold_sensitivity.json": "experiment_threshold_sensitivity.py",
    "experiments/combined_ablation/threshold_sensitivity.csv": "experiment_threshold_sensitivity.py",
    "experiments/combined_ablation/threshold_sensitivity.md": "experiment_threshold_sensitivity.py",
    "experiments/combined_ablation/cross_dataset_ablation.json": "experiment_cross_dataset_ablation.py",
    "experiments/combined_ablation/cross_dataset_summary.csv": "experiment_cross_dataset_ablation.py",
    "experiments/combined_ablation/cross_dataset_summary.md": "experiment_cross_dataset_ablation.py",
    "experiments/combined_ablation/cross_dataset_summary.tex": "experiment_cross_dataset_ablation.py",
    "COMPONENT_REGISTRY.json": "combined_ablation_discovery.py",
    "COMPONENT_DEPENDENCY_GRAPH.md": "combined_ablation_discovery.py",
    "component_dependency_graph.svg": "combined_ablation_discovery.py",
    "COMBINED_ABLATION_ANALYSIS.md": "experiment_combined_ablation.py",
    "GRACEFUL_DEGRADATION_ANALYSIS.md": "experiment_combined_ablation.py",
    "COMBINED_ABLATION_IMPLEMENTATION_REPORT.md": "experiment_combined_ablation.py",
    # The E5b combined-ablation threats live in their OWN file. `THREATS_TO_VALIDITY.md` is tracked,
    # pre-existing reviewer evidence (E1-E8) owned by experiments/generate_publication_docs.py — it is
    # recorded here for provenance but is NOT produced by this package and is never overwritten.
    "COMBINED_ABLATION_THREATS_TO_VALIDITY.md": "generate_threats_to_validity.py",
    "THREATS_TO_VALIDITY.md": "experiments/generate_publication_docs.py (pre-existing, not owned by E5b)",
    "dashboard/combined_runtime_ablation.html": "experiment_combined_ablation.py",
    "README/COMBINED_ABLATION.md": "experiment_combined_ablation.py",
    "metadata/combined_ablation_run_metadata.json": "experiment_combined_ablation.py",
}
for _t in ["table_combined_ablation", "table_statistics", "table_interactions",
           "table_threshold_sensitivity", "table_cross_dataset"]:
    GENERATORS[f"paper_tables/{_t}.tex"] = "generate_paper_tables.py"
for _t in ["table_combined_ablation_A", "table_combined_ablation_B", "table_combined_ablation_C"]:
    for _e in ("md", "csv", "tex"):
        GENERATORS[f"paper_tables/{_t}.{_e}"] = "experiment_combined_ablation.py"
for _f in ["combined_ablation_matrix", "interaction_graph", "threshold_heatmap", "dataset_comparison",
           "runtime_integrity", "graceful_degradation", "dependency_graph"]:
    for _e in ("svg", "pdf", "png"):
        GENERATORS[f"paper_figures/{_f}.{_e}"] = "generate_paper_figures.py"


def sha256_file(p: Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def git_info() -> dict:
    def g(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except Exception:
            return None
    sha = g("rev-parse", "HEAD")
    return {"commit_sha": sha, "commit_sha_short": (sha or "")[:12] or None,
            "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(g("status", "--porcelain")),
            "dirty_note": ("working tree has uncommitted changes at generation time — the artifact "
                           "corresponds to the tree, not to the commit alone")}


def dataset_hashes() -> dict:
    """SHA-256 of every discovered dataset. Cached (files are hundreds of MB); the cache is keyed by
    (size, mtime) so a changed dataset is re-hashed rather than trusted."""
    cache_p = META / "dataset_hashes.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    out = {}
    try:
        sys.path.insert(0, str(ROOT / "experiments"))
        import dataset_adapters as DA
        recs = DA.discover()
    except Exception as ex:
        return {"error": f"dataset discovery failed: {type(ex).__name__}: {ex}"}
    for r in recs:
        p = Path(r["path"])
        if not p.exists():
            out[r["adapter"]] = {"status": "NOT_FOUND", "path": r["relpath"]}
            continue
        st = p.stat()
        key = r["relpath"]
        prev = cache.get(key)
        if prev and prev.get("size_bytes") == st.st_size and prev.get("mtime_ns") == st.st_mtime_ns:
            out[r["adapter"]] = prev                       # unchanged -> reuse cached digest
            continue
        t0 = time.time()
        rec = {"path": r["relpath"], "sha256": sha256_file(p), "size_bytes": st.st_size,
               "mtime_ns": st.st_mtime_ns, "hash_seconds": round(time.time() - t0, 2)}
        out[r["adapter"]] = rec
        cache[key] = rec
    META.mkdir(exist_ok=True)
    cache_p.write_text(json.dumps(cache, indent=2) + "\n")
    return out


def env_block() -> dict:
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "runtime_version": f"CPython {platform.python_version()}",
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "cpu_count": os.cpu_count(),
    }


def main() -> int:
    META.mkdir(exist_ok=True)
    PROV.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    git = git_info()
    env = env_block()
    ds = dataset_hashes()
    command = " ".join([Path(sys.executable).name] + sys.argv)

    records, missing = [], []
    for rel, gen in sorted(GENERATORS.items()):
        p = ROOT / rel
        base = {
            "artifact": rel,
            "generation_timestamp_utc": ts,
            "git": git,
            "dataset_sha256": ds,
            "experiment_seed": SEED,
            "experiment_version": EXPERIMENT_VERSION,
            "generator_script": gen,
            "generator_script_sha256": (sha256_file(ROOT / gen) if (ROOT / gen).exists() else None),
            "environment": env,
            "command_executed": command,
            "reproduce_with": f"python3 {gen}",
        }
        if p.exists():
            base.update({"status": "PRESENT", "sha256": sha256_file(p),
                         "size_bytes": p.stat().st_size,
                         "modified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                       time.gmtime(p.stat().st_mtime))})
        else:
            base.update({"status": "MISSING", "sha256": None, "size_bytes": None,
                         "note": "artifact not present at provenance-generation time; "
                                 "run its generator (see reproduce_with)"})
            missing.append(rel)
        flat = rel.replace("/", "__")
        (PROV / f"{flat}.json").write_text(json.dumps(base, indent=2) + "\n")
        records.append({k: base[k] for k in
                        ("artifact", "status", "sha256", "size_bytes", "generator_script")})

    manifest = {
        "manifest": "L-DREA combined-ablation publication provenance",
        "experiment_version": EXPERIMENT_VERSION,
        "generation_timestamp_utc": ts,
        "git": git, "environment": env, "experiment_seed": SEED,
        "dataset_sha256": ds,
        "command_executed": command,
        "n_artifacts": len(records),
        "n_present": sum(1 for r in records if r["status"] == "PRESENT"),
        "n_missing": len(missing),
        "missing": missing,
        "artifacts": records,
        "note": ("Every record is computed from the file on disk at generation time. A MISSING "
                 "artifact is recorded as missing — it is never silently omitted."),
    }
    (META / "PROVENANCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[provenance] {manifest['n_present']}/{manifest['n_artifacts']} artifacts present; "
          f"{manifest['n_missing']} missing")
    print(f"[provenance] git {git['commit_sha_short']} (dirty={git['dirty']}); "
          f"datasets hashed: {[k for k in ds if isinstance(ds[k], dict) and ds[k].get('sha256')]}")
    if missing:
        print(f"[provenance] missing: {', '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}")
    print(f"[provenance] wrote metadata/PROVENANCE_MANIFEST.json + metadata/provenance/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
