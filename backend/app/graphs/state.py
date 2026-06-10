from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    codebase_id: str
    agent_name: str   # which specialist was routed to (set by supervisor)
    next: str         # routing target chosen by supervisor
