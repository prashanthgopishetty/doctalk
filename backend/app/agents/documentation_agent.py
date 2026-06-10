import logging

from langchain_core.messages import SystemMessage, ToolMessage

from app.graphs.state import AgentState
from app.llm import get_llm
from app.tools.code_search import code_search_tool
from app.tools.file_tools import find_symbol_tool, list_files_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Documentation Agent — a technical writer who produces clear, accurate documentation from code.

Your job: generate and explain documentation — docstrings, README sections, API descriptions, module overviews.

Guidelines:
- Always read the code before documenting it — never fabricate behavior
- Use Google-style docstrings for Python (Args, Returns, Raises sections)
- Use JSDoc for TypeScript
- Keep documentation concise — document WHAT, not HOW (unless the HOW is non-obvious)
- For FastAPI routes: describe parameters, response shape, and error cases
- For complex functions: explain preconditions and edge cases
- Note if a function is too complex to document clearly without simplification first

When asked to document a module or feature:
1. Search for all relevant files
2. Read and understand the code
3. Generate accurate, complete documentation

Codebase ID: {codebase_id}"""

_tools = [code_search_tool, list_files_tool, find_symbol_tool]


async def documentation_agent_node(state: AgentState) -> dict:
    """LangGraph node: generates docstrings, README sections, and API documentation."""
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

    return {"messages": [response], "agent_name": "documentation"}
