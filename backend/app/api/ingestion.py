import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, field_validator

from app.config import Settings, get_settings
from app.store.vector_store import VectorStore, get_vector_store
from app.tools.loaders import load_github_repo, load_local_path, load_uploaded_files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str
    source_type: Literal["github", "local"]
    codebase_id: str | None = None  # if None, a new UUID is generated

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source must not be empty")
        return v


class IngestResponse(BaseModel):
    codebase_id: str
    documents_indexed: int
    message: str


class ListCodebasesResponse(BaseModel):
    codebases: list[str]


class DeleteResponse(BaseModel):
    message: str


@router.post(
    "",
    summary="Ingest a codebase",
    description="Accepts a GitHub URL or local path, chunks and embeds all source files into ChromaDB.",
    response_model=IngestResponse,
)
async def ingest_codebase(
    body: IngestRequest,
    settings: Settings = Depends(get_settings),
    store: VectorStore = Depends(get_vector_store),
) -> IngestResponse:
    codebase_id = body.codebase_id or uuid.uuid4().hex

    logger.info("Ingesting codebase: id=%s type=%s source=%s", codebase_id, body.source_type, body.source)

    try:
        if body.source_type == "github":
            docs = await load_github_repo(body.source, codebase_id, settings.github_token)
        else:
            docs = await load_local_path(body.source, codebase_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Ingestion failed for %s", body.source)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        )

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No supported source files found at the given location.",
        )

    try:
        indexed = await store.add_documents(docs, codebase_id)
    except RuntimeError as exc:
        # Raised when Ollama is unreachable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    logger.info("Indexed %d documents for codebase: %s", indexed, codebase_id)

    return IngestResponse(
        codebase_id=codebase_id,
        documents_indexed=indexed,
        message=f"Successfully indexed {indexed} code chunks.",
    )


@router.post(
    "/upload",
    summary="Ingest uploaded files",
    description="Upload one or more source files directly; they are chunked and indexed into ChromaDB.",
    response_model=IngestResponse,
)
async def ingest_upload(
    files: list[UploadFile],
    store: VectorStore = Depends(get_vector_store),
) -> IngestResponse:
    if not files:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No files provided.")

    codebase_id = uuid.uuid4().hex
    file_contents: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        file_contents.append((f.filename or "unknown", content))

    try:
        docs = await load_uploaded_files(file_contents, codebase_id)
    except Exception as exc:
        logger.exception("Upload ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload ingestion failed: {exc}",
        )

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No supported source files found in uploaded content.",
        )

    try:
        indexed = await store.add_documents(docs, codebase_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return IngestResponse(
        codebase_id=codebase_id,
        documents_indexed=indexed,
        message=f"Successfully indexed {indexed} code chunks from {len(files)} file(s).",
    )


@router.get(
    "",
    summary="List all ingested codebases",
    response_model=ListCodebasesResponse,
)
async def list_codebases(store: VectorStore = Depends(get_vector_store)) -> ListCodebasesResponse:
    return ListCodebasesResponse(codebases=store.list_codebases())


@router.delete(
    "/{codebase_id}",
    summary="Delete an ingested codebase",
    response_model=DeleteResponse,
)
async def delete_codebase(
    codebase_id: str,
    store: VectorStore = Depends(get_vector_store),
) -> DeleteResponse:
    if not store.collection_exists(codebase_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Codebase '{codebase_id}' not found.")
    store.delete_collection(codebase_id)
    return DeleteResponse(message=f"Codebase '{codebase_id}' deleted.")
