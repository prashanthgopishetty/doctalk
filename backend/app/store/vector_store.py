import logging
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.config import Settings

logger = logging.getLogger(__name__)

_chroma_client: chromadb.ClientAPI | None = None
_embeddings: Embeddings | None = None


def _build_embeddings(settings: Settings) -> Embeddings:
    """Build an Embeddings instance from config. Supports any OpenAI-compatible endpoint.

    check_embedding_ctx_length=False is required for Mistral (and other non-OpenAI
    providers) — it prevents langchain from tokenizing and sending integer token IDs,
    which Mistral rejects with 422. Raw strings are sent instead.
    """
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        api_key=settings.resolved_embedding_api_key,  # type: ignore[arg-type]
        check_embedding_ctx_length=False,
    )


def init_vector_store(settings: Settings) -> None:
    global _chroma_client, _embeddings
    _chroma_client = chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    _embeddings = _build_embeddings(settings)
    logger.info("ChromaDB initialized at: %s | embeddings: %s", settings.chroma_path, settings.embedding_model)


def get_vector_store() -> "VectorStore":
    if _chroma_client is None or _embeddings is None:
        raise RuntimeError("VectorStore not initialized. Call init_vector_store() first.")
    return VectorStore(_chroma_client, _embeddings)


class VectorStore:
    def __init__(self, client: chromadb.ClientAPI, embeddings: Embeddings) -> None:
        self._client = client
        self._embeddings = embeddings

    def _collection_name(self, codebase_id: str) -> str:
        return f"doctalk_{codebase_id}"

    def collection_exists(self, codebase_id: str) -> bool:
        try:
            self._client.get_collection(self._collection_name(codebase_id))
            return True
        except Exception:
            return False

    def delete_collection(self, codebase_id: str) -> None:
        name = self._collection_name(codebase_id)
        self._client.delete_collection(name)
        logger.info("Deleted collection: %s", name)

    def list_codebases(self) -> list[str]:
        prefix = "doctalk_"
        return [
            c.name[len(prefix):]
            for c in self._client.list_collections()
            if c.name.startswith(prefix)
        ]

    async def add_documents(
        self,
        documents: list[Document],
        codebase_id: str,
        batch_size: int = 50,
    ) -> int:
        collection = self._client.get_or_create_collection(
            name=self._collection_name(codebase_id),
            metadata={"hnsw:space": "cosine"},
        )
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            texts = [doc.page_content for doc in batch]
            metadatas: list[dict[str, Any]] = [
                {k: v for k, v in doc.metadata.items() if v is not None}
                for doc in batch
            ]
            ids = [f"{codebase_id}_{i + j}" for j, _ in enumerate(batch)]
            try:
                embeddings = await self._embeddings.aembed_documents(texts)
            except ConnectionError as exc:
                raise RuntimeError(
                    "Cannot reach Ollama at the configured embedding URL. "
                    "Make sure Ollama is running (`ollama serve`) and the model is pulled "
                    f"(`ollama pull {self._embeddings.model}`). Error: {exc}"
                ) from exc
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total += len(batch)
            logger.info("Embedded batch %d/%d (%d docs)", i // batch_size + 1, -(-len(documents) // batch_size), total)
        return total

    async def similarity_search(
        self,
        query: str,
        codebase_id: str,
        k: int = 8,
    ) -> list[Document]:
        if not self.collection_exists(codebase_id):
            return []
        collection = self._client.get_collection(self._collection_name(codebase_id))
        query_embedding = await self._embeddings.aembed_query(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        docs: list[Document] = []
        if results["documents"] and results["documents"][0]:
            for text, meta in zip(results["documents"][0], results["metadatas"][0]):  # type: ignore[index]
                docs.append(Document(page_content=text, metadata=meta or {}))
        return docs
