# Ollama Environment Setup Report (for AgentDojo local execution)

**Date:** 2026-07-09
**Scope:** environment setup only — install + validate Ollama and assess compatibility with the
existing AgentDojo integration. **No repository code modified. Benchmark NOT run. No results fabricated.**

---

## 1. Installation report

| Step | Action | Result |
|---|---|---|
| Pre-check | `which ollama`, `/Applications/Ollama.app` | not installed |
| Method | Homebrew absent → official macOS build `Ollama-darwin.zip` (GitHub release) | downloaded 156 MB |
| Install | `Ollama.app` → `/Applications/` (standard location) | installed |
| Binary | `/Applications/Ollama.app/Contents/Resources/ollama` | **v0.31.1** |
| CLI symlink | `/usr/local/bin` not writable without sudo | use full path or `export PATH`; non-blocking |
| Server | `ollama serve` (background) on `127.0.0.1:11434` | reachable (`/api/version → 0.31.1`) |

`/usr/local/bin/ollama` was not symlinked (no write permission without sudo). Add to PATH if desired:
```bash
export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
```
The Ollama menubar app also auto-starts the server on login; for headless use, `ollama serve`.

---

## 2. Hardware summary

| Property | Value |
|---|---|
| Architecture | **Apple Silicon (arm64)** |
| Chip | Apple **M5** |
| macOS | **26.5.1** (build 25F80) |
| RAM | **16 GB** unified memory |
| Free disk | 367 GB |
| Metal GPU accel | yes (Apple Silicon) |

---

## 3. Installed model

**`llama3.1:8b`** (4.92 GB, Q4_K_M) — pulled and verified.

**Why this model:** on **16 GB** unified memory, an 8B model at 4-bit (~5–6 GB resident + KV cache)
runs reliably with headroom for the OS and the Python/AgentDojo process. `llama3.1:70b` (~40 GB)
**cannot** fit in 16 GB and would either fail to load or thrash — so it was correctly excluded.
`llama3.1:8b` is the largest reliable choice on this hardware and natively supports tool/function
calling, which AgentDojo requires.

---

## 4. Ollama verification output

- **Simple prompt** (`ollama run llama3.1:8b "Reply with exactly: OLLAMA_OK"`) → produced `OLLAMA_OK`.
- **OpenAI-compat models** (`GET /v1/models`) → `{"data":[{"id":"llama3.1:8b", ...}]}`.
- **OpenAI-compat tool calling** (`POST /v1/chat/completions` with a `tools` payload) →
  `finish_reason: "tool_calls"`, returned a well-formed call:
  ```json
  {"type":"function","function":{"name":"get_balance","arguments":"{\"account\":\"A\"}"}}
  ```
  This is exactly the structure AgentDojo's `OpenAILLM` consumes.

---

## 5. Compatibility assessment with AgentDojo

Inspected `agentdojo.agent_pipeline.agent_pipeline.get_llm` (installed `agentdojo==0.1.35`). Findings:

- **Does it already support Ollama?** Not by name, but **functionally yes**. AgentDojo's `local` and
  `vllm_parsed` providers target a generic **OpenAI-compatible** localhost endpoint
  (`openai.OpenAI(api_key="EMPTY", base_url="http://localhost:{LOCAL_LLM_PORT}/v1")`). Ollama serves
  exactly that at `:11434/v1`.
- **Does it expect an OpenAI-compatible endpoint?** **Yes** — both local providers use the OpenAI
  client against `/v1`. Confirmed live: with `LOCAL_LLM_PORT=11434`,
  - `_get_local_model_id(11434)` → `"llama3.1:8b"` (AgentDojo auto-detects the Ollama model),
  - `get_llm("vllm_parsed", …)` → `OpenAILLM` bound to `http://localhost:11434/v1/`,
  - `get_llm("local", …)` → `LocalLLM` bound to `http://localhost:11434/v1/`.
- **Does it expect vLLM?** The naming (`vllm_parsed`, default port 8000) reflects vLLM as the
  reference server, but the code is **not vLLM-specific** — it is plain OpenAI-compatible HTTP.
  Ollama substitutes cleanly.
- **Is an adapter required?** **No.** No code change is needed to point AgentDojo at Ollama.
  Native tool calling was verified working end-to-end. Configuration alone suffices.

**Recommended provider:** `vllm_parsed` → `OpenAILLM` (native `tool_calls`, which Ollama + llama3.1
support, as verified). `local` → `LocalLLM` uses prompt-delimiter tool parsing and also points at
Ollama, but native tool calling is the cleaner match for AgentDojo's tool-heavy tasks.

*Caveat (quality, not compatibility):* an 8B local model will score lower on utility/attack-success
than frontier hosted models — a benchmark-quality consideration, not a code/wiring issue.

---

## 6. Required environment variables

Configuration only — **no code change**:

```bash
export LOCAL_LLM_PORT=11434     # point AgentDojo's local provider at Ollama (default was 8000)
export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"   # optional: ollama on PATH
# ensure the server is up:  ollama serve   (or the Ollama.app menubar)
```

No API key is required for `local` / `vllm_parsed` (the runner already treats them as key-free).
The model id is auto-detected from `/v1/models`; `MODEL_NAME` is not needed (leave `model_id=None`).

---

## 7. Recommended next step

When you choose to execute the genuine benchmark (a separate, already-approved step — **not run here**):

```bash
export LOCAL_LLM_PORT=11434
agentdojo_integration/.venv/bin/python agentdojo_integration/run_benchmark.py \
    --model vllm_parsed --suites banking --limit 1 --limit-injections 1 \
    --logdir agentdojo_integration/runs --out agentdojo_results.json     # smoke first
```
Then drop `--limit` flags and add all four suites for the full corpus. `run_benchmark.py` already
maps `vllm_parsed`/`local` to key-free execution, so no `RUN_PENDING_PROVIDER` gate applies.

---

## Verdict

Ollama is installed (v0.31.1), the server is reachable on `127.0.0.1:11434`, `llama3.1:8b` is pulled
and produces output including native tool calls, and AgentDojo's existing `local`/`vllm_parsed`
providers resolve against Ollama with configuration alone. No adapter, no code change.

**READY TO RUN AGENTDOJO WITH OLLAMA**
