import json
import logging
import uuid
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.graphs.main_graph import build_graph

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])


class InputMessage(BaseModel):
    role: str
    content: str


class RunAgentInput(BaseModel):
    threadId: str
    runId: str
    messages: list[InputMessage]
    state: dict | None = None  # carries codebase_id, agent_hint from frontend


def _ag_ui_event(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **payload})}\n\n"


async def _generate_events(body: RunAgentInput) -> AsyncIterator[str]:
    thread_id = body.threadId
    run_id = body.runId
    codebase_id = (body.state or {}).get("codebaseId", "")

    yield _ag_ui_event("RunStarted", {"threadId": thread_id, "runId": run_id})

    # Build LangGraph input state
    lc_messages = [
        HumanMessage(content=m.content) if m.role == "user" else
        __import__("langchain_core.messages", fromlist=["AIMessage"]).AIMessage(content=m.content)
        for m in body.messages
    ]
    graph_input = {
        "messages": lc_messages,
        "codebase_id": codebase_id,
        "agent_name": "",
        "next": "",
    }

    graph = build_graph()

    current_step: str = ""
    current_msg_id: str = ""
    tool_call_ids: dict[str, bool] = {}  # toolCallId → started

    try:
        async for event in graph.astream_events(graph_input, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_chain_start" and name not in ("LangGraph", "__start__", "supervisor"):
                step_name = "DocTalk" if name == "out_of_scope_agent" else (
                    name.replace("_agent", "").replace("_", " ").title() + " Agent"
                )
                current_step = name
                yield _ag_ui_event("StepStarted", {"stepName": step_name})

            elif kind == "on_chain_end" and name == current_step:
                step_name = "DocTalk" if name == "out_of_scope_agent" else (
                    name.replace("_agent", "").replace("_", " ").title() + " Agent"
                )

                # out_of_scope_agent returns an AIMessage directly (no LLM stream),
                # so we must forward its content here as text events.
                if name == "out_of_scope_agent":
                    output = event.get("data", {}).get("output", {})
                    oos_messages = output.get("messages", []) if isinstance(output, dict) else []
                    for oos_msg in oos_messages:
                        content = getattr(oos_msg, "content", "") or ""
                        if content:
                            if not current_msg_id:
                                current_msg_id = uuid.uuid4().hex
                                yield _ag_ui_event("TextMessageStart", {
                                    "messageId": current_msg_id,
                                    "role": "assistant",
                                })
                            yield _ag_ui_event("TextMessageContent", {
                                "messageId": current_msg_id,
                                "delta": content,
                            })

                yield _ag_ui_event("StepFinished", {"stepName": step_name})

            elif kind == "on_chat_model_stream" and current_step:
                # Guard: only forward tokens when inside an agent node.
                # Without this, the supervisor's own LLM response (e.g. "out_of_scope")
                # leaks into the chat as visible text.
                chunk = event["data"]["chunk"]
                delta = chunk.content if hasattr(chunk, "content") else ""
                if delta:
                    if not current_msg_id:
                        current_msg_id = uuid.uuid4().hex
                        yield _ag_ui_event("TextMessageStart", {
                            "messageId": current_msg_id,
                            "role": "assistant",
                        })
                    yield _ag_ui_event("TextMessageContent", {
                        "messageId": current_msg_id,
                        "delta": delta,
                    })

            elif kind == "on_tool_start":
                tool_call_id = event.get("run_id", uuid.uuid4().hex)
                tool_name = name
                tool_call_ids[tool_call_id] = True
                args_str = json.dumps(event["data"].get("input", {}))
                yield _ag_ui_event("ToolCallStart", {
                    "toolCallId": tool_call_id,
                    "toolCallName": tool_name,
                    "parentMessageId": current_msg_id or None,
                })
                yield _ag_ui_event("ToolCallArgs", {
                    "toolCallId": tool_call_id,
                    "delta": args_str,
                })
                yield _ag_ui_event("ToolCallEnd", {"toolCallId": tool_call_id})

            elif kind == "on_tool_end":
                tool_call_id = event.get("run_id", "")
                result = event["data"].get("output", "")
                yield _ag_ui_event("ToolCallResult", {
                    "messageId": current_msg_id or uuid.uuid4().hex,
                    "toolCallId": tool_call_id,
                    "content": str(result)[:4000],  # truncate very long results
                    "role": "tool",
                })

        if current_msg_id:
            yield _ag_ui_event("TextMessageEnd", {"messageId": current_msg_id})

    except Exception as exc:
        logger.exception("Agent run failed: thread=%s run=%s", thread_id, run_id)
        
        # Provide user-friendly error messages for common API issues
        error_message = str(exc)
        user_message = error_message
        
        if "429" in error_message or "rate_limit" in error_message.lower():
            user_message = "⏱️ API rate limit exceeded. Please wait a moment and try again. If this persists, check your API plan or consider using local Ollama."
        elif "401" in error_message or "unauthorized" in error_message.lower():
            user_message = "🔑 API authentication failed. Check your API key in backend/.env"
        elif "timeout" in error_message.lower():
            user_message = "⏳ Request timed out. The API is taking too long to respond. Please try again."
        elif "connection" in error_message.lower():
            user_message = "🌐 Connection error. Check your internet connection and API endpoint URL."
        
        yield _ag_ui_event("RunError", {"message": user_message, "code": "AGENT_ERROR"})
        return

    yield _ag_ui_event("RunFinished", {"threadId": thread_id, "runId": run_id})


@router.post(
    "/agent",
    summary="Run the DocTalk multi-agent system",
    description=(
        "Accepts an AG-UI RunAgentInput payload and streams AG-UI SSE events back. "
        "Automatically routes to the appropriate specialist agent based on the query."
    ),
)
async def run_agent(body: RunAgentInput) -> StreamingResponse:
    return StreamingResponse(
        _generate_events(body),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
