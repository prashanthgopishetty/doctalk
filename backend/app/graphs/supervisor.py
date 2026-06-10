import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.graphs.state import AgentState
from app.llm import get_llm

logger = logging.getLogger(__name__)

AGENT_NAMES = ["developer", "architecture", "testing", "self_improvement", "documentation"]

SUPERVISOR_SYSTEM_PROMPT = """You are a routing supervisor for a multi-agent code documentation assistant.

Given the user's latest message, classify it into exactly ONE of these agent categories:

- **developer**: Questions about how specific code works, how to use an API, what a function does, tracing call paths, understanding implementations. Keywords: how does, what does, explain, show me, find, where is, how to use.

- **architecture**: Questions about system structure, module organization, dependencies, design patterns, project layout, what depends on what. Keywords: architecture, structure, dependencies, modules, packages, design, overview, layers, organization.

- **testing**: Questions about tests, test coverage, how to test something, generating test cases, unit tests, integration tests. Keywords: test, tests, testing, coverage, spec, unit, mock, assert, pytest, jest.

- **self_improvement**: Requests to improve, refactor, or review code quality, find code smells, optimize, security review. Keywords: refactor, improve, optimize, code smell, review, quality, security, performance, clean up.

- **documentation**: Requests to generate or explain documentation, docstrings, README, API docs, comments. Keywords: document, docstring, readme, api docs, comment, describe, explain the api.

Respond with ONLY the single lowercase agent name. No punctuation, no explanation.
Examples:
- "how does authentication work?" → developer
- "what are the test files?" → testing
- "show me the project structure" → architecture
- "refactor the user service" → self_improvement
- "write docstrings for the models" → documentation"""


async def supervisor_node(state: AgentState) -> dict:
    """Route the user's query to the most appropriate specialist agent."""
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
