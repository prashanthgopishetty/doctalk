---
description: "Use when writing or modifying LangGraph state graphs, agent nodes, supervisor logic, or graph edges in the DocTalk backend. Covers StateGraph patterns, AgentState TypedDict, node functions, streaming, and conditional routing."
applyTo: ["backend/**/graphs/**", "backend/**/agents/**"]
---

# LangGraph Conventions

## AgentState
All nodes receive and return `AgentState`. Always type it as a `TypedDict` with `Annotated` for reducers.

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    agent_name: str          # which agent was routed to
    codebase_id: str         # active codebase collection
    next: str                # supervisor routing target
```

## Node Functions
- Must be `async def`
- Accept `AgentState`, return `dict` (partial state update)
- Do NOT mutate state in-place

```python
async def developer_agent_node(state: AgentState) -> dict:
    # ... build response
    return {"messages": [AIMessage(content=response)], "agent_name": "developer"}
```

## StateGraph Assembly
```python
from langgraph.graph import StateGraph, END

def build_graph() -> CompiledGraph:
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("developer_agent", developer_agent_node)
    # ...
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {"developer": "developer_agent", "architecture": "architecture_agent", ...},
    )
    for agent in AGENT_NAMES:
        builder.add_edge(agent, END)
    return builder.compile()
```

## Supervisor Routing
```python
async def supervisor_node(state: AgentState) -> dict:
    # Use LLM to classify intent
    classification = await llm.ainvoke(SUPERVISOR_PROMPT + last_message)
    return {"next": classification.strip().lower()}

def route_to_agent(state: AgentState) -> str:
    return state["next"]
```

## Streaming with astream_events
```python
async for event in graph.astream_events(input_state, version="v2"):
    kind = event["event"]
    if kind == "on_chain_start":
        yield format_ag_ui_event("StepStarted", {"stepName": event["name"]})
    elif kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"].content
        if chunk:
            yield format_ag_ui_event("TextMessageContent", {"delta": chunk})
    elif kind == "on_tool_start":
        yield format_ag_ui_event("ToolCallStart", {"toolCallName": event["name"]})
    elif kind == "on_tool_end":
        yield format_ag_ui_event("ToolCallEnd", {})
        yield format_ag_ui_event("ToolCallResult", {"content": str(event["data"]["output"])})
```

## Tool Binding
```python
from langchain_core.tools import StructuredTool

llm_with_tools = llm.bind_tools([code_search_tool, file_reader_tool])
response = await llm_with_tools.ainvoke(state["messages"])
```

## Rules
- Never use `graph.invoke()` in streaming contexts — always `astream_events`
- Always handle `on_chain_error` events and emit `RunError` AG-UI event
- Keep supervisor prompt concise — classify into exactly one of the 5 agent names
- Agent nodes should NOT call each other — only supervisor routes between agents
