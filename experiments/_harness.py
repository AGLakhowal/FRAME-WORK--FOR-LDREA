#!/usr/bin/env python3
"""
experiments/_harness.py — shared, dependency-free execution harness for the L-DREA
Tier-S reference-implementation evaluation.
==================================================================================

This module does NOT implement or modify any authorization logic. It only:
  * captures host / software / git / seed / timestamp execution metadata,
  * runs each stable experiment entrypoint (subprocess or in-process callable),
  * copies the artifacts that entrypoint emits into experiments/<name>/,
  * records a per-run metadata.json, a REPRODUCE.md, and the captured stdout log,
  * computes sha256 for every collected artifact (provenance).

Every number in the evaluation is produced by executing the stable engine code; this
harness never fabricates, estimates, or hardcodes a metric value.

Timestamp policy: the ONE wall-clock read happens here (recorded per run). It is
execution metadata, never an input to any authorization decision.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repo root
EXP = ROOT / "experiments"
PY = sys.executable                                     # ./.venv python that invoked RUN_ALL
ADI_PY = ROOT / "agentdojo_integration" / ".venv" / "bin" / "python"

# A fixed evaluation seed. The stable experiments are deterministic (index-driven
# workloads or seeded RNG); this is recorded for provenance and passed where honored.
EVAL_SEED = 20260709


def sha256_file(p: Path) -> str | None:
    if not p.exists() or p.is_dir():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def host_info() -> dict:
    info = {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_version": sys.version.split()[0],
        "python_executable": str(PY),
        "cpu_count": os.cpu_count(),
        "eval_seed": EVAL_SEED,
    }
    for key, sysctl in (("cpu_brand", "machdep.cpu.brand_string"), ("mem_bytes", "hw.memsize")):
        try:
            out = subprocess.check_output(["sysctl", "-n", sysctl], stderr=subprocess.DEVNULL).decode().strip()
            info[key] = int(out) if out.isdigit() else out
        except Exception:
            info[key] = None
    try:
        info["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                    stderr=subprocess.DEVNULL).decode().strip()
        info["git_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT,
                                                         stderr=subprocess.DEVNULL).decode().strip())
    except Exception:
        info["git_head"] = None
        info["git_dirty"] = None
    return info


@dataclass
class RunResult:
    exp_id: str
    title: str
    outdir: str
    reproduction_command: str
    status: str                      # EXECUTED | BLOCKED | FAILED
    started_utc: str
    duration_s: float
    return_code: int | None
    log_path: str
    artifacts: dict = field(default_factory=dict)      # name -> {path, sha256, bytes}
    blocked_reason: str | None = None
    missing_dependency: str | None = None
    rerun_when_available: str | None = None
    notes: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


class Experiment:
    """One experiment: a stable entrypoint + the artifacts it produces.

    kind = 'subprocess'  -> argv run with the repo python
         = 'callable'    -> 'module:function' imported and called (in-process)
         = 'adi'         -> argv run with the agentdojo_integration venv python
    """

    def __init__(self, exp_id, title, dirname, kind, target, *,
                 reproduction_command, produces, collect, requires=None,
                 seed_env=None, notes=None):
        self.exp_id = exp_id
        self.title = title
        self.dir = EXP / dirname
        self.kind = kind
        self.target = target
        self.reproduction_command = reproduction_command
        self.produces = produces                # list[Path] the entrypoint writes at repo root/elsewhere
        self.collect = collect                  # dict artifact_name -> source Path to copy into self.dir
        self.requires = requires or []          # external deps for FRESH raw data (e.g. ollama)
        self.seed_env = seed_env or {}
        self.notes = notes

    # -- dependency probing (only blocks FRESH raw-data generation) ----------------
    def check_requirements(self) -> tuple[bool, str | None, str | None]:
        for req in self.requires:
            if req.startswith("ollama"):
                # Probe the SERVER, not just the binary: `ollama` can sit on PATH with no server
                # running and no model pulled, which is not a usable backend.
                import sys as _sys
                if str(ROOT) not in _sys.path:
                    _sys.path.insert(0, str(ROOT))
                try:
                    from agentdojo_integration import ollama_probe
                    info = ollama_probe.probe()
                except Exception:  # probe unavailable -> fall back to a PATH check
                    info = {"available": shutil.which("ollama") is not None,
                            "detail": "ollama binary not on PATH"}
                if not info["available"]:
                    return (False, info["detail"],
                            "brew install ollama && ollama serve & ollama pull llama3.1:8b")
        return (True, None, None)

    def run(self) -> RunResult:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "logs").mkdir(exist_ok=True)
        log_path = self.dir / "logs" / f"{self.exp_id}.log"
        started = time.gmtime()
        started_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", started)
        t0 = time.time()

        ok, reason, rerun = self.check_requirements()
        if not ok:
            log_path.write_text(f"BLOCKED: {reason}\nrerun when available: {rerun}\n")
            return RunResult(self.exp_id, self.title, str(self.dir.relative_to(ROOT)),
                             self.reproduction_command, "BLOCKED", started_iso, 0.0, None,
                             str(log_path.relative_to(ROOT)), blocked_reason=reason,
                             missing_dependency=", ".join(self.requires),
                             rerun_when_available=rerun, notes=self.notes)

        rc, status = 0, "EXECUTED"
        env = dict(os.environ, **{k: str(v) for k, v in self.seed_env.items()})
        try:
            if self.kind in ("subprocess", "adi"):
                interp = str(ADI_PY) if self.kind == "adi" else str(PY)
                argv = [interp] + self.target
                with log_path.open("w") as lf:
                    proc = subprocess.run(argv, cwd=ROOT, env=env, stdout=lf,
                                          stderr=subprocess.STDOUT)
                    rc = proc.returncode
                if rc != 0:
                    status = "FAILED"
            elif self.kind == "callable":
                mod_name, fn_name = self.target.split(":")
                import importlib
                sys.path.insert(0, str(ROOT))
                mod = importlib.import_module(mod_name)
                fn = getattr(mod, fn_name)
                # capture stdout
                import contextlib, io
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    self._callable_return = fn(**self._callable_kwargs()) if self._callable_kwargs() else fn()
                log_path.write_text(buf.getvalue() or "(callable produced no stdout)\n")
            else:
                raise ValueError(f"unknown kind {self.kind}")
        except Exception as e:  # noqa: BLE001
            import traceback
            log_path.write_text((log_path.read_text() if log_path.exists() else "") +
                                f"\nHARNESS EXCEPTION:\n{traceback.format_exc()}")
            status, rc = "FAILED", 1

        duration = time.time() - t0

        # collect artifacts into the experiment dir
        artifacts = {}
        for name, src in self.collect.items():
            src = Path(src)
            if src.exists():
                dst = self.dir / src.name
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
                artifacts[name] = {"path": str(dst.relative_to(ROOT)),
                                   "sha256": sha256_file(dst), "bytes": dst.stat().st_size}
            else:
                artifacts[name] = {"path": None, "sha256": None, "bytes": None,
                                   "note": "expected artifact not produced"}

        res = RunResult(self.exp_id, self.title, str(self.dir.relative_to(ROOT)),
                        self.reproduction_command, status, started_iso, round(duration, 3), rc,
                        str(log_path.relative_to(ROOT)), artifacts=artifacts, notes=self.notes)

        # per-run metadata.json + REPRODUCE.md
        meta = {"experiment": self.exp_id, "title": self.title,
                "host": host_info(), "run": res.to_json()}
        (self.dir / "metadata.json").write_text(json.dumps(meta, indent=2))
        (self.dir / "REPRODUCE.md").write_text(
            f"# Reproduce {self.exp_id} — {self.title}\n\n"
            f"```bash\n{self.reproduction_command}\n```\n\n"
            f"- Interpreter: `{PY if self.kind!='adi' else ADI_PY}`\n"
            f"- Working dir: repo root\n- Seed: {EVAL_SEED}\n"
            f"- Deterministic: index-driven / seeded workloads (see summary.md)\n")
        return res

    # subclasses / registration can override to pass kwargs to a callable
    _kwargs: dict = {}

    def with_kwargs(self, **kw):
        self._kwargs = kw
        return self

    def _callable_kwargs(self):
        return getattr(self, "_kwargs", {}) or {}


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))
