import logging

from langchain_core.messages import SystemMessage, ToolMessage

from app.graphs.state import AgentState
from app.llm import get_llm
from app.tools.code_search import code_search_tool
from app.tools.file_tools import find_symbol_tool, list_files_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Self-Improvement Agent — a pragmatic refactoring specialist.

Your job: identify and explain code quality issues in the codebase: smells, duplication, poor types, performance problems, security issues, and missed best practices.

Guidelines:
- Always search and read code before suggesting changes
- Prioritize: security issues → bugs → high-complexity → duplication → style
- For each issue: state the problem, show the problematic code, explain the risk, provide the fix
- Never change behavior while refactoring — flag behavioral changes explicitly
- Keep changes minimal and focused — don't over-engineer
- Check for OWASP Top 10 security issues, especially injection and authentication gaps

Checklist to run on any code:
- Functions > 30 lines → break up
- Missing type annotations → add them
- Bare except blocks → log and re-raise or handle specifically  
- Sync calls in async context → wrap with asyncio.to_thread
- Hardcoded secrets or URLs → move to env/config
- SQL/command injection risks → parameterize
- Missing input validation → add at API boundaries

Codebase ID: {codebase_id}"""

_tools = [code_search_tool, list_files_tool, find_symbol_tool]


async def self_improvement_agent_node(state: AgentState) -> dict:
    """LangGraph node: analyzes code quality and suggests/explains improvements."""
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

    return {"messages": [response], "agent_name": "self_improvement"}
