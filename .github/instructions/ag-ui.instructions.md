---
description: "Use when implementing or modifying the AG-UI SSE endpoint, translating LangGraph events to AG-UI protocol events, or debugging streaming responses. Covers RunStarted, StepStarted, TextMessageContent, ToolCallStart/End, RunFinished event formats."
applyTo: "backend/**/api/**"
---

# AG-UI SSE Protocol Conventions

## Event Format
All AG-UI events are emitted as Server-Sent Events:
```
data: {"type": "EVENT_TYPE", ...fields}\n\n
```

## Required Event Sequence
```
RunStarted
  StepStarted(stepName=<agent_node_name>)
    [TextMessageStart(messageId, role="assistant")]
    [TextMessageContent(messageId, delta=<chunk>)]  ← repeat
    [TextMessageEnd(messageId)]
    [ToolCallStart(toolCallId, toolCallName)]
    [ToolCallArgs(toolCallId, delta=<json_fragment>)]
    [ToolCallEnd(toolCallId)]
    [ToolCallResult(messageId, toolCallId, content)]
  StepFinished(stepName=<agent_node_name>)
RunFinished
```

## Event Builder Helper
```python
import json
import uuid

def ag_ui_event(event_type: str, payload: dict) -> str:
    """Format a single AG-UI event as an SSE data line."""
    data = {"type": event_type, **payload}
    return f"data: {json.dumps(data)}\n\n"

# Usage:
yield ag_ui_event("RunStarted", {"threadId": thread_id, "runId": run_id})
yield ag_ui_event("StepStarted", {"stepName": "developer_agent"})
yield ag_ui_event("TextMessageStart", {"messageId": msg_id, "role": "assistant"})
yield ag_ui_event("TextMessageContent", {"messageId": msg_id, "delta": chunk})
yield ag_ui_event("TextMessageEnd", {"messageId": msg_id})
yield ag_ui_event("StepFinished", {"stepName": "developer_agent"})
yield ag_ui_event("RunFinished", {"threadId": thread_id, "runId": run_id})
```

## LangGraph Event → AG-UI Mapping
| LangGraph Event | AG-UI Event |
|-----------------|-------------|
| `on_chain_start` (node name) | `StepStarted` |
| `on_chain_end` (final node) | `StepFinished` |
| `on_chat_model_stream` | `TextMessageContent` |
| `on_tool_start` | `ToolCallStart` + `ToolCallArgs` (first chunk) |
| `on_tool_end` | `ToolCallEnd` + `ToolCallResult` |
| graph completion | `RunFinished` |
| exception | `RunError` |

## RunInput Schema (from CopilotKit)
```python
class Message(BaseModel):
    role: str
    content: str

class RunAgentInput(BaseModel):
    threadId: str
    runId: str
    messages: list[Message]
    state: dict | None = None   # carries codebase_id, agent_hint
```

## StreamingResponse Setup
```python
from fastapi.responses import StreamingResponse

return StreamingResponse(
    generate_ag_ui_events(body),
    media_type="text/event-stream",
    headers={
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    },
)
```

## Error Handling in Stream
```python
try:
    async for event in graph.astream_events(...):
        ...
except Exception as exc:
    logger.exception("Agent run failed")
    yield ag_ui_event("RunError", {"message": str(exc), "code": "AGENT_ERROR"})
```

## Rules
- `threadId` and `runId` must be echoed back on `RunStarted` and `RunFinished`
- `messageId` must be consistent across `TextMessageStart`, `TextMessageContent`, `TextMessageEnd`
- `toolCallId` must be consistent across `ToolCallStart`, `ToolCallArgs`, `ToolCallEnd`
- Never close the stream without emitting `RunFinished` or `RunError`
- Use `uuid.uuid4().hex` for new IDs
