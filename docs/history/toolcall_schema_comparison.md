# Tool-Call Schema Comparison (Phase 4) — OpenAI expected vs Ollama observed

Comparison of the schema AgentDojo/OpenAI-SDK expects against the raw JSON Ollama returned for the
exact benchmark request. No benchmark code changed; both captured at runtime.

## Expected (OpenAI ChatCompletion with tool calls)
```json
{
  "choices": [
    { "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          { "id": "call_...", "type": "function",
            "function": { "name": "<tool>", "arguments": "<json-string>" } }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

## Observed (Ollama `/v1/chat/completions`, raw off the wire — `toolcall_raw_sample_eea.json`)
```json
{
  "id": "chatcmpl-...", "object": "chat.completion", "created": 0000000000,
  "model": "llama3.1:8b", "system_fingerprint": "fp_ollama",
  "choices": [
    { "index": 0,
      "message": {
        "role": "assistant", "content": "",
        "tool_calls": [
          { "id": "call_gy31pvor", "index": 0, "type": "function",
            "function": { "name": "create_calendar_event",
                          "arguments": "{\"title\":\"Lunch\",\"start_time\":\"2024-05-19 12:00\", ...}" } }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": { "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ... }
}
```

## Field-by-field

| Path | Expected | Observed (Ollama) | Match? |
|---|---|---|---|
| `choices[0].finish_reason` | `"tool_calls"` | `"tool_calls"` | ✅ |
| `choices[0].message.role` | `"assistant"` | `"assistant"` | ✅ |
| `choices[0].message.content` | `null` | `""` (empty string) | ✅ compatible (SDK treats both as no text; `_assistant_message_to_content` returns `None` for `None`, `[""]` for `""`) |
| `message.tool_calls` | array | array | ✅ |
| `tool_calls[].id` | `str` | `str` | ✅ |
| `tool_calls[].type` | `"function"` | `"function"` | ✅ |
| `tool_calls[].function.name` | `str` | `str` | ✅ |
| `tool_calls[].function.arguments` | JSON **string** | JSON **string** | ✅ |
| `tool_calls[].index` | (absent in non-stream) | `0` present | ⚠️ **extra** field, harmless — SDK ignores unknown fields |
| top-level `system_fingerprint` | optional | `"fp_ollama"` | ✅ optional, ignored |
| top-level `usage` | present | present | ✅ |

## Structural differences highlighted
1. Ollama includes an **extra `index`** inside each `tool_calls[]` element (a streaming-style field).
   The OpenAI SDK `ChatCompletionMessageToolCall` model **ignores** it — Phase 2 confirmed both tool
   calls parsed cleanly (`n_parsed_tool_calls = 2`). **Not** a breaking difference.
2. `content` is `""` rather than `null`. Both map to "no assistant text". **Not** breaking.

**No breaking schema difference exists.** Ollama's tool-call envelope is OpenAI-schema-conformant for
AgentDojo's parser, which is why the SDK deserialized it and AgentDojo received every tool call intact.
