# Tool-Call Interface — Root Cause (Phase 5)

**Question:** does the failure to produce an EEA originate from (A) Ollama/OpenAI serialization,
(B) AgentDojo's parser, (C) the model, or (D) another interface layer?

## Evidence (all direct, no fabrication)

1. **Raw wire, actual benchmark request** (`toolcall_raw_response.json`): Ollama returned a
   **valid `tool_calls` array (2 entries)** with `finish_reason="tool_calls"` — captured via an httpx
   response event hook on the real request. → Ollama emits OpenAI-format tool calls.
2. **AgentDojo received** (`toolcall_agentdojo_received.json`): the SDK-parsed message had
   `tool_calls_is_None = false`, **2 tool calls received** — identical count to the wire. → parser did
   not drop anything.
3. **Determinism probe** (`toolcall_replay_summary.json`): the exact first-turn request replayed
   **32×** (8+24) → **32/32 returned valid `tool_calls`**, **32/32 called the EEA
   `create_calendar_event`**, **0 text-only**, **0 parser/serialization anomalies**.
4. **Schema comparison** (`toolcall_schema_comparison.md`): Ollama's envelope is OpenAI-conformant;
   the only deltas (extra `tool_calls[].index`, `content:""` vs `null`) are ignored by the SDK.
5. **Variance across live benchmark runs**: same first-turn input produced, on different executions,
   (a) the EEA `create_calendar_event` (32/32 isolated), (b) two `search_calendar_events` (wrong,
   read-only tool — `toolcall_raw_response.json`), and (c) — in an earlier run — assistant prose that
   *narrated* a call as text. In every captured case the **wire response faithfully reflected the
   model's own output**; no layer rewrote it.

## Elimination

- **Case A (Ollama/serialization failed):** REFUTED. 32/32 raw responses are valid OpenAI tool-call
  JSON; the schema conforms (Phase 4).
- **Case B (AgentDojo failed to parse valid tool_calls):** REFUTED. Wire count == parsed count (2==2);
  parser reads `message.tool_calls` 1:1 with no discard path (`openai_llm.py:126–131`, Phase 3).
- **Case C (Ollama converted tool calls into assistant content):** REFUTED. When tool calls exist they
  appear in `message.tool_calls` (not `content`); when prose appeared it was the model's own
  natural-language generation, faithfully returned as `content`. No evidence of a structured call being
  down-converted to text by Ollama.
- **Case D (another serialization layer altered the response):** REFUTED. Raw httpx-level bytes == SDK
  parse == what AgentDojo received; no intermediate mutation observed.

## Root cause

The interface (Ollama serialization + OpenAI schema + AgentDojo parser) is **correct and faithful**.
The variability in whether an EEA appears is **model-side (Case C = the model)**, specifically
**non-deterministic token generation by `llama3.1:8b`** (llama.cpp/Metal is not bit-deterministic even
at `temperature=0`): the same input yields, across runs, the correct EEA tool call, a wrong (read-only)
tool call, or occasional prose. The interface transports whatever the model emits, unaltered.

**Important correction to the prior report:** the earlier conclusion "the model is insufficiently
capable of producing EEAs" is **too strong**. Direct evidence shows the model **does** produce the
valid EEA tool call for this task — **32/32** in isolation. The accurate statement is: the model
*can* and *does* emit valid EEA tool calls, but its **multi-turn tool-selection is non-deterministic
and unreliable**, so a full benchmark episode sometimes lands on a non-EEA branch.

## Single evidence-supported conclusion

**Ollama produced valid `tool_calls`** (and AgentDojo parsed them correctly). The intermittent absence
of an EEA is model-generation non-determinism, not a serialization, parser, compatibility, or adapter
fault.
