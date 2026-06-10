from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "mistral"
    llm_base_url: str = "https://api.mistral.ai/v1"
    llm_model: str = "mistral-small-latest"
    llm_api_key: str = ""

    # Embeddings
    embedding_provider: str = "mistral"
    embedding_model: str = "mistral-embed"
    embedding_base_url: str = "https://api.mistral.ai/v1"
    embedding_api_key: str = ""  # defaults to llm_api_key if empty

    @property
    def resolved_embedding_api_key(self) -> str:
        return self.embedding_api_key or self.llm_api_key

    # ChromaDB
    chroma_path: str = "./chroma_db"
    chroma_collection_prefix: str = "doctalk"

    # GitHub (optional, for authenticated clone)
    github_token: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
