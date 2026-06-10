import logging

from langchain_core.messages import SystemMessage, ToolMessage

from app.graphs.state import AgentState
from app.llm import get_llm
from app.tools.code_search import code_search_tool
from app.tools.file_tools import find_symbol_tool, list_files_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Architecture Agent — a systems-thinking specialist.

Your job: reveal how a codebase is organized — its layers, module boundaries, dependency relationships, and design patterns.

Guidelines:
- Start by listing the top-level structure with list_files
- Identify architectural layers (e.g., API → Service → Domain → Store)
- Trace import dependencies to show coupling
- Use Mermaid diagrams (```mermaid) to illustrate structure when helpful
- Describe what each major component does and why it exists
- Note any architectural concerns (tight coupling, circular deps, missing layers)

Codebase ID: {codebase_id}"""

_tools = [list_files_tool, code_search_tool, find_symbol_tool]


async def architecture_agent_node(state: AgentState) -> dict:
    """LangGraph node: answers architecture and structure questions about the codebase."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(_tools)

    codebase_id = state.get("codebase_id", "")
    messages = [SystemMessage(content=SYSTEM_PROMPT.format(codebase_id=codebase_id)), *state["messages"]]

    response = await llm_with_tools.ainvoke(messages)

    while hasattr(response, "tool_calls") and response.tool_calls:
        tool_messages: list[ToolMessage] = []
        for tc in response.tool_calls:
            tool = next((t for t in _tools if t.name == tc["name"]), None)
            try:
                result = await tool.ainvoke(tc["args"]) if tool else f"Unknown tool: {tc['name']}"
            except Exception as exc:
                logger.exception("Tool %s failed", tc["name"])
                result = f"Tool error: {exc}"
            tool_messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        messages = [*messages, response, *tool_messages]
        response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response], "agent_name": "architecture"}
