#!/usr/bin/env python
"""Live probe for a local Ollama server.

E7's core measurements (predicate evaluation, authorization, evidence quad, hash chain,
ledger, replay) are guard-side properties of L-DREA and run with NO model in the loop.
Ollama is required only by the OPTIONAL live-episode arm, which generates fresh agent
trajectories to measure agent-side task utility and attack-success rate.

`shutil.which("ollama")` is not a sufficient check: the binary can be installed while the
server is down, in which case AgentDojo's local provider fails deep inside an HTTP call.
This module probes the server itself.

AgentDojo reaches a local model through provider `vllm_parsed`, which builds
`base_url=f"http://localhost:{LOCAL_LLM_PORT}/v1"`. Ollama serves an OpenAI-compatible API
on port 11434, so `LOCAL_LLM_PORT=11434` wires the two together with no external credential.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_PORT = 11434
TAGS_PATH = "/api/tags"


def endpoint(port: int | None = None) -> str:
    """OpenAI-compatible base URL that AgentDojo's `vllm_parsed` provider will construct."""
    return f"http://localhost:{port or _port()}/v1"


def _port() -> int:
    return int(os.getenv("LOCAL_LLM_PORT", DEFAULT_PORT))


def probe(port: int | None = None, timeout: float = 2.0) -> dict:
    """Ask the local Ollama server which models it has loaded.

    Never raises. Returns a dict that is safe to embed verbatim in a run manifest:
        {available: bool, endpoint: str, port: int, models: [str], detail: str}
    """
    p = port or _port()
    url = f"http://localhost:{p}{TAGS_PATH}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"available": False, "endpoint": endpoint(p), "port": p, "models": [],
                "detail": f"no Ollama server at {url}: {e.reason}"}
    except (OSError, ValueError, KeyError) as e:
        return {"available": False, "endpoint": endpoint(p), "port": p, "models": [],
                "detail": f"Ollama server at {url} returned an unusable response: {e}"}

    models = [m["name"] for m in payload.get("models", []) if "name" in m]
    if not models:
        return {"available": False, "endpoint": endpoint(p), "port": p, "models": [],
                "detail": f"Ollama is running at {url} but has no models pulled"}
    return {"available": True, "endpoint": endpoint(p), "port": p, "models": models,
            "detail": f"Ollama reachable at {url} with {len(models)} model(s)"}


REMEDIATION = (
    "Start Ollama and pull a model, then re-run:\n"
    "    brew install ollama\n"
    "    ollama serve &\n"
    "    ollama pull llama3.1:8b\n"
    f"    export LOCAL_LLM_PORT={DEFAULT_PORT}\n"
    "The E7 core (guard-side) measurements do not need this; only the optional live-episode arm does."
)


def require(port: int | None = None, timeout: float = 2.0) -> dict:
    """Return probe info, or raise with actionable remediation.

    Use at the entry point of code that genuinely cannot proceed without a model. Callers that
    merely *prefer* a model should call `probe()` and branch on `available`.
    """
    info = probe(port, timeout)
    if not info["available"]:
        raise RuntimeError(f"Ollama unavailable — {info['detail']}\n\n{REMEDIATION}")
    return info


def selected_model(info: dict, preferred: str = "llama3.1:8b") -> str:
    """Pick the preferred model if the server has it, else the first one it does have."""
    return preferred if preferred in info["models"] else info["models"][0]


if __name__ == "__main__":
    import sys
    i = probe()
    print(json.dumps(i, indent=2))
    sys.exit(0 if i["available"] else 1)
