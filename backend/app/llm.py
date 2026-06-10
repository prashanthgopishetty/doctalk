from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """Return a cached LLM instance configured from environment settings.

    Defaults to Qwen via Ollama's OpenAI-compatible endpoint.
    Swap to any OpenAI-compatible provider by changing env vars:
      LLM_BASE_URL, LLM_MODEL, LLM_API_KEY
    """
    settings = get_settings()
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,  # type: ignore[arg-type]
        temperature=0,
        streaming=True,
    )
