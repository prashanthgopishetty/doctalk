import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document


@pytest.fixture
def mock_agent_state():
    return {
        "messages": [HumanMessage(content="How does authentication work?")],
        "codebase_id": "test_codebase",
        "agent_name": "",
        "next": "",
    }


@pytest.fixture
def mock_docs():
    return [
        Document(
            page_content="def authenticate(token: str) -> User: ...",
            metadata={"file_path": "auth.py", "start_line": 1, "end_line": 5, "language": "python"},
        )
    ]


@pytest.mark.asyncio
async def test_developer_agent_returns_message(mock_agent_state, mock_docs):
    mock_response = AIMessage(content="Authentication is handled in auth.py")
    mock_llm = AsyncMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.agents.developer_agent.get_llm", return_value=mock_llm):
        from app.agents.developer_agent import developer_agent_node
        result = await developer_agent_node(mock_agent_state)

    assert "messages" in result
    assert result["agent_name"] == "developer"
    assert result["messages"][0].content == "Authentication is handled in auth.py"


@pytest.mark.asyncio
async def test_architecture_agent_returns_message(mock_agent_state):
    mock_response = AIMessage(content="The project follows a layered architecture...")
    mock_llm = AsyncMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.agents.architecture_agent.get_llm", return_value=mock_llm):
        from app.agents.architecture_agent import architecture_agent_node
        result = await architecture_agent_node(mock_agent_state)

    assert result["agent_name"] == "architecture"


@pytest.mark.asyncio
async def test_supervisor_routes_to_developer(mock_agent_state):
    mock_response = MagicMock()
    mock_response.content = "developer"
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graphs.supervisor.get_llm", return_value=mock_llm):
        from app.graphs.supervisor import supervisor_node
        result = await supervisor_node(mock_agent_state)

    assert result["next"] == "developer"


@pytest.mark.asyncio
async def test_supervisor_routes_to_testing():
    state = {
        "messages": [HumanMessage(content="What test files exist?")],
        "codebase_id": "test",
        "agent_name": "",
        "next": "",
    }
    mock_response = MagicMock()
    mock_response.content = "testing"
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graphs.supervisor.get_llm", return_value=mock_llm):
        from app.graphs.supervisor import supervisor_node
        result = await supervisor_node(state)

    assert result["next"] == "testing"


@pytest.mark.asyncio
async def test_supervisor_fallback_on_unknown_route():
    state = {
        "messages": [HumanMessage(content="hello")],
        "codebase_id": "test",
        "agent_name": "",
        "next": "",
    }
    mock_response = MagicMock()
    mock_response.content = "unknown_agent_xyz"
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.graphs.supervisor.get_llm", return_value=mock_llm):
        from app.graphs.supervisor import supervisor_node
        result = await supervisor_node(state)

    assert result["next"] == "developer"
