import logging

from langchain_core.messages import SystemMessage, ToolMessage

from app.graphs.state import AgentState
from app.llm import get_llm
from app.tools.code_search import code_search_tool
from app.tools.file_tools import find_symbol_tool, list_files_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Testing Agent — an expert in test strategy and test generation.

Your job: help write and improve tests for the codebase, identify coverage gaps, and explain what should be tested.

Guidelines:
- Search for existing test files first to avoid duplication
- Generate realistic, runnable test code (pytest for Python, Jest for TypeScript)
- Mock all external dependencies (databases, APIs, LLMs)
- Follow AAA pattern: Arrange / Act / Assert
- Prioritize behavior-based tests over implementation tests
- Identify which code paths are untested and explain the risk

For Python: use pytest + pytest-asyncio + unittest.mock
For TypeScript: use Jest + React Testing Library

Codebase ID: {codebase_id}"""

_tools = [code_search_tool, list_files_tool, find_symbol_tool]


async def testing_agent_node(state: AgentState) -> dict:
    """LangGraph node: generates tests and analyzes test coverage for the codebase."""
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

    return {"messages": [response], "agent_name": "testing"}
