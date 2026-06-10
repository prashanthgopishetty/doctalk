import logging
from pydantic import BaseModel, ConfigDict
from langchain_core.tools import StructuredTool

from app.store.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class ListFilesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    codebase_id: str
    language: str = ""


class FindSymbolInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    symbol_name: str
    codebase_id: str


async def _list_files(codebase_id: str, language: str = "") -> str:
    """List all indexed files in a codebase, optionally filtered by language."""
    store = get_vector_store()
    if not store.collection_exists(codebase_id):
        return f"No codebase found with id: {codebase_id}"

    collection = store._client.get_collection(store._collection_name(codebase_id))
    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas") or []

    seen: set[str] = set()
    files: list[str] = []
    for meta in metadatas:
        if not meta:
            continue
        fp = meta.get("file_path", "")
        lang = meta.get("language", "")
        if language and lang != language:
            continue
        if fp and fp not in seen:
            seen.add(fp)
            files.append(f"`{fp}` ({lang})")

    if not files:
        filter_msg = f" with language={language}" if language else ""
        return f"No files found{filter_msg} in codebase: {codebase_id}"
    return f"Files in `{codebase_id}`:\n" + "\n".join(sorted(files))


async def _find_symbol(symbol_name: str, codebase_id: str) -> str:
    """Find all indexed chunks that define or reference a specific symbol name."""
    store = get_vector_store()
    if not store.collection_exists(codebase_id):
        return f"No codebase found with id: {codebase_id}"

    collection = store._client.get_collection(store._collection_name(codebase_id))
    results = collection.get(
        where={"symbol_name": {"$eq": symbol_name}},
        include=["documents", "metadatas"],
    )

    docs = results.get("documents") or []
    metas = results.get("metadatas") or []

    if not docs:
        return f"No symbol `{symbol_name}` found in codebase: {codebase_id}"

    parts: list[str] = [f"Found `{symbol_name}` in {len(docs)} location(s):\n"]
    for doc, meta in zip(docs, metas):
        fp = (meta or {}).get("file_path", "?")
        sl = (meta or {}).get("start_line", "")
        el = (meta or {}).get("end_line", "")
        lang = (meta or {}).get("language", "")
        loc = f"`{fp}:{sl}-{el}`" if sl else f"`{fp}`"
        parts.append(f"### {loc}\n```{lang}\n{doc}\n```")
    return "\n\n".join(parts)


list_files_tool = StructuredTool.from_function(
    coroutine=_list_files,
    name="list_files",
    description=(
        "List all source files indexed in a codebase. "
        "Optionally filter by programming language. "
        "Use to understand what files exist before searching."
    ),
    args_schema=ListFilesInput,
)

find_symbol_tool = StructuredTool.from_function(
    coroutine=_find_symbol,
    name="find_symbol",
    description=(
        "Find all code chunks that define a specific function, class, or variable by exact name. "
        "Use when you know the symbol name and want to find its definition."
    ),
    args_schema=FindSymbolInput,
)
