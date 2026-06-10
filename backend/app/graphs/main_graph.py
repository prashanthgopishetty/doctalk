from functools import lru_cache
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.architecture_agent import architecture_agent_node
from app.agents.developer_agent import developer_agent_node
from app.agents.documentation_agent import documentation_agent_node
from app.agents.self_improvement_agent import self_improvement_agent_node
from app.agents.testing_agent import testing_agent_node
from app.graphs.state import AgentState
from app.graphs.supervisor import out_of_scope_node, route_to_agent, supervisor_node


@lru_cache
def build_graph() -> Any:
    """Build and compile the DocTalk multi-agent StateGraph.

    Graph topology:
        supervisor → (developer | architecture | testing | self_improvement | documentation | out_of_scope) → END
    """
    builder: StateGraph = StateGraph(AgentState)

    # Nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("developer_agent", developer_agent_node)
    builder.add_node("architecture_agent", architecture_agent_node)
    builder.add_node("testing_agent", testing_agent_node)
    builder.add_node("self_improvement_agent", self_improvement_agent_node)
    builder.add_node("documentation_agent", documentation_agent_node)
    builder.add_node("out_of_scope_agent", out_of_scope_node)

    # Entry point
    builder.set_entry_point("supervisor")

    # Supervisor → agent (conditional routing)
    builder.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "developer": "developer_agent",
            "architecture": "architecture_agent",
            "testing": "testing_agent",
            "self_improvement": "self_improvement_agent",
            "documentation": "documentation_agent",
            "out_of_scope": "out_of_scope_agent",
        },
    )

    # All agent nodes → END
    for node in [
        "developer_agent",
        "architecture_agent",
        "testing_agent",
        "self_improvement_agent",
        "documentation_agent",
        "out_of_scope_agent",
    ]:
        builder.add_edge(node, END)

    return builder.compile()
