# Tool-Call Parser Trace (Phase 3) — AgentDojo OpenAI path

**Objective:** trace exactly how AgentDojo extracts tool calls from the provider response, with
file/function/line references, and determine whether it discards tool calls or whether none existed.

**File:** `agentdojo/agent_pipeline/llms/openai_llm.py` (installed `agentdojo==0.1.35`, py3.11 venv).

## Request construction (what is sent)
- `OpenAILLM.query` @ **line 188** builds:
  - `openai_messages = [_message_to_openai(m, model) for m in messages]`
  - `openai_tools = [_function_to_openai(tool) for tool in runtime.functions.values()]`
- `chat_completion_request(...)` @ **line 143** issues the HTTP call @ **line 159**:
  ```python
  client.chat.completions.create(
      model=model, messages=messages,
      tools=tools or NOT_GIVEN,
      tool_choice="auto" if tools else NOT_GIVEN,   # tools present -> "auto"
      temperature=temperature or NOT_GIVEN, ...)
  ```
  Observed at runtime: `n_tools_sent = 24`, `tool_choice = "auto"`, `temperature = 0.0`.

## Response parsing (how tool calls are extracted)
- `OpenAILLM.query` @ **line 201**: `output = _openai_to_assistant_message(completion.choices[0].message)`
- `_openai_to_assistant_message` @ **line 126**:
  ```python
  def _openai_to_assistant_message(message: ChatCompletionMessage) -> ChatAssistantMessage:
      if message.tool_calls is not None:                                    # line 127
          tool_calls = [_openai_to_tool_call(tc) for tc in message.tool_calls]   # line 128
      else:
          tool_calls = None                                                # line 130
      return ChatAssistantMessage(role="assistant",
                 content=_assistant_message_to_content(message), tool_calls=tool_calls)
  ```
- `_openai_to_tool_call` @ **line 112**: maps each `ChatCompletionMessageToolCall` →
  `FunctionCall(function=tc.function.name, args=json.loads(tc.function.arguments), id=tc.id)`.

The parser reads the **SDK-parsed** `ChatCompletionMessage.tool_calls`. The OpenAI Python SDK has
already deserialized the raw HTTP JSON into that object before AgentDojo sees it. There is **no
custom text parsing** and **no place where a present `tool_calls` array is dropped**: if
`message.tool_calls` is non-None, every element is converted 1:1.

## input → parsed representation → runtime object (observed, benchmark request)

| Stage | Evidence file | Content |
|---|---|---|
| **input** (raw HTTP JSON off the wire) | `toolcall_raw_response.json` | `choices[0].message.tool_calls` = **2 entries**, `finish_reason="tool_calls"`, `content=""` |
| **parsed representation** (SDK `ChatCompletionMessage`, exactly what AgentDojo received) | `toolcall_agentdojo_received.json` | `message.tool_calls_is_None = false`, `n_parsed_tool_calls = 2` |
| **runtime object** (`_openai_to_assistant_message` output) | — | `ChatAssistantMessage.tool_calls` = 2 `FunctionCall`s, forwarded into the tools loop → `GammaGovernedRuntime.run_function` |

## Verdict for Phase 3
AgentDojo **did not discard** any tool calls. Every `tool_calls` element present in the wire response
was received (Phase 2: 2 present → 2 parsed) and converted to a runtime `FunctionCall`. When a run
produced **no** actionable EEA, it was because the provider response contained **no EEA tool call**
(either read-only/wrong-tool calls, or — in one earlier run — model prose), **not** because the
parser dropped a valid one. Parser is exonerated.
