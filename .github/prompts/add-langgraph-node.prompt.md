---
description: "Scaffold a new LangGraph agent node with a tool and register it in the supervisor graph. Provide the agent name and its purpose."
---

I need to add a new LangGraph agent node to the DocTalk system.

**Agent details:**
- Name: $AGENT_NAME
- Purpose: $AGENT_PURPOSE
- Tools it needs: $TOOLS_NEEDED

Please do the following:

1. **Create `backend/app/agents/${AGENT_NAME}_agent.py`** with:
   - A system prompt tailored to the agent's purpose
   - An async node function `${AGENT_NAME}_agent_node(state: AgentState) -> dict`
   - The agent bound to its tools via `llm.bind_tools([...])`
   - Tool call handling loop (check for tool calls, execute, append results)

2. **Create `backend/app/tools/${TOOLS_NEEDED}.py`** (if new tools are needed) with:
   - A `StructuredTool` using Pydantic v2 input schema
   - Async implementation
   - Docstring explaining what the tool does

3. **Update `backend/app/graphs/main_graph.py`**:
   - Import and add the new node: `builder.add_node("${AGENT_NAME}_agent", ${AGENT_NAME}_agent_node)`
   - Add edge back to END: `builder.add_edge("${AGENT_NAME}_agent", END)`

4. **Update `backend/app/graphs/supervisor.py`**:
   - Add the new agent to the routing classification options
   - Update the supervisor system prompt to include the new agent's name and description

Follow the conventions in `.github/instructions/langgraph.instructions.md`.
