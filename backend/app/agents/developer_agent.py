import json
import logging

from langchain_core.messages import AIMessage, ToolMessage

from app.graphs.state import AgentState
from app.llm import get_llm
from app.tools.code_search import code_search_tool
from app.tools.file_tools import find_symbol_tool, list_files_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Developer Agent — an expert at reading and explaining code and documents.

Your job: answer questions about how code works, where things are implemented, what specific functions/classes/modules do, and summarize or explain any ingested content (code, PDFs, DOCX, README files, or other documents).

Guidelines:
- Always search the codebase first using the available tools before answering
- For summarization requests, search broadly and synthesize what you find into a clear overview
- Show relevant code snippets with file paths in your response
- Trace call paths step by step when explaining flow
- Be concrete and reference specific files and line numbers
- If you cannot find an answer in the codebase, say so honestly

Codebase ID: {codebase_id}"""

_tools = [code_search_tool, find_symbol_tool, list_files_tool]


async def developer_agent_node(state: AgentState) -> dict:
    """LangGraph node: answers developer/implementation questions about the codebase."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(_tools)

    codebase_id = state.get("codebase_id", "")
    system_content = SYSTEM_PROMPT.format(codebase_id=codebase_id)

    from langchain_core.messages import SystemMessage
    messages = [SystemMessage(content=system_content), *state["messages"]]

    response = await llm_with_tools.ainvoke(messages)

    # Handle tool calls iteratively
    tool_messages: list[ToolMessage] = []
    while hasattr(response, "tool_calls") and response.tool_calls:
        tool_calls = response.tool_calls
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool = next((t for t in _tools if t.name == tool_name), None)
            if tool is None:
                result = f"Unknown tool: {tool_name}"
            else:
                try:
                    result = await tool.ainvoke(tool_args)
                except Exception as exc:
                    logger.exception("Tool %s failed", tool_name)
                    result = f"Tool error: {exc}"
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

        messages = [*messages, response, *tool_messages]
        tool_messages = []
        response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response], "agent_name": "developer"}
