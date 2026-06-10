import logging
from pydantic import BaseModel, ConfigDict
from langchain_core.tools import StructuredTool
from langchain_core.documents import Document

from app.store.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class CodeSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str
    codebase_id: str
    k: int = 8


async def _code_search(query: str, codebase_id: str, k: int = 8) -> str:
    """Search the ChromaDB vector store for code chunks relevant to the query.

    Args:
        query: Natural language or code query.
        codebase_id: The identifier of the ingested codebase collection.
        k: Maximum number of results to return.

    Returns:
        Formatted string of matching code chunks with file paths and line numbers.
    """
    store = get_vector_store()
    docs: list[Document] = await store.similarity_search(query, codebase_id, k=k)
    if not docs:
        return "No relevant code found in the codebase for this query."

    parts: list[str] = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        location = meta.get("file_path", "unknown")
        start = meta.get("start_line", "")
        end = meta.get("end_line", "")
        lang = meta.get("language", "")
        symbol = meta.get("symbol_name", "")
        line_ref = f":{start}-{end}" if start and end else ""
        symbol_ref = f" ({symbol})" if symbol else ""
        parts.append(
            f"### Result {i}: `{location}{line_ref}`{symbol_ref}\n"
            f"```{lang}\n{doc.page_content}\n```"
        )
    return "\n\n".join(parts)


code_search_tool = StructuredTool.from_function(
    coroutine=_code_search,
    name="code_search",
    description=(
        "Search the ingested codebase for code relevant to a query. "
        "Returns matching code chunks with file paths and line numbers. "
        "Use this to find implementations, understand how things work, "
        "or locate where specific functionality lives."
    ),
    args_schema=CodeSearchInput,
)
