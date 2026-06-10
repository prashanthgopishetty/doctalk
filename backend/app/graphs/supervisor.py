import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.graphs.state import AgentState
from app.llm import get_llm

logger = logging.getLogger(__name__)

AGENT_NAMES = ["developer", "architecture", "testing", "self_improvement", "documentation", "out_of_scope"]

SUPERVISOR_SYSTEM_PROMPT = """You are a routing supervisor for a multi-agent documentation assistant.

CRITICAL RULE: If the user has ingested ANY content (code, documents, resumes, PDFs, etc.), assume their question is about that content UNLESS it is clearly asking for unrelated general knowledge.

Your job is to classify the user's question into the most appropriate specialist agent category:

- **developer**: Questions asking to analyze, understand, summarize, explain, describe, or extract information from ANY ingested content. This includes:
  - Code: "how does X work?", "what does this function do?", "explain the authentication"
  - Documents/Resumes/PDFs: "what are the strong points?", "summarize this", "what skills does the candidate have?", "extract key information", "what is in this document?"
  - ANY content: explain, describe, analyze, summarize, show me, tell me about, what is, find, extract, list, identify, highlight
  
- **architecture**: Questions about overall structure, organization, dependencies, relationships, or layout of the ingested content. Examples: "show me the structure", "how is this organized?", "what depends on what?", "architecture overview"

- **testing**: Questions specifically about tests, test coverage, or testing strategies. Examples: "what tests exist?", "test coverage", "how is this tested?"

- **self_improvement**: Requests to improve, refactor, optimize, or review the ingested content for quality. Examples: "improve this code", "refactor the logic", "security review"

- **documentation**: Requests to generate or improve documentation, docstrings, comments, or API docs for the ingested content.

- **out_of_scope**: ONLY use this if the question is clearly asking for information UNRELATED to the ingested content. Examples:
  - General world knowledge: "what is the capital of France?", "tell me about history"
  - Unrelated advice: "how to cook pasta?", "write me a poem", "tell me a joke"
  - Math/trivia: "what is 2+2?", "who won the 2020 Olympics?"
  - DO NOT mark as out_of_scope if it could relate to the document. Example: "strong areas" about a resume → developer, NOT out_of_scope

KEY: Prioritize understanding CONTEXT over exact keywords. When in doubt, route to "developer" to analyze/explain the content.

Respond with ONLY the single lowercase category name. No punctuation, no explanation.

Examples:
- "what are the strong areas of the candidate?" (resume ingested) → developer
- "summarize the resume" → developer
- "how does the authentication work?" (code ingested) → developer
- "what skills does this person have?" (resume ingested) → developer
- "extract the experience section" (resume ingested) → developer
- "tell me about the architecture" → architecture
- "what is the tech stack?" → developer
- "improve this code" → self_improvement
- "what is the capital of France?" → out_of_scope
- "write me a poem" → out_of_scope"""


async def supervisor_node(state: AgentState) -> dict:
    """Route the user's query to the most appropriate specialist agent."""

    # Fast-path: no codebase ingested yet
    if not state.get("codebase_id", "").strip():
        return {"next": "out_of_scope", "agent_name": "out_of_scope"}

    llm = get_llm()

    # Get the last human message for classification
    last_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_message = str(msg.content)
            break

    if not last_message:
        return {"next": "developer"}

    response = await llm.ainvoke([
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=last_message),
    ])

    route = str(response.content).strip().lower()

    # Validate — fall back to developer if unrecognized
    if route not in AGENT_NAMES:
        logger.warning("Supervisor returned unknown route '%s', defaulting to developer", route)
        route = "developer"

    logger.info("Supervisor routed '%s...' → %s", last_message[:60], route)
    return {"next": route}


def route_to_agent(state: AgentState) -> str:
    """Conditional edge function: returns the agent name to route to."""
    return state.get("next", "developer")


async def out_of_scope_node(state: AgentState) -> dict:
    """Return a polite refusal for questions outside the ingested codebase."""
    codebase_id = state.get("codebase_id", "").strip()

    if not codebase_id:
        message = "Please ingest a codebase first (GitHub URL, local path, or file upload) and I'll be ready to help you explore it."
    else:
        message = "I'm only able to answer questions about the ingested source data. Try asking about how the code works, its structure, tests, or improvements."

    return {
        "messages": [AIMessage(content=message)],
        "agent_name": "out_of_scope",
    }
