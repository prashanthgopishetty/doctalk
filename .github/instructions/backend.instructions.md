---
description: "Use when building, modifying, or debugging backend FastAPI routes, models, or middleware. Covers FastAPI + Pydantic v2 patterns, async conventions, dependency injection, and error handling for the DocTalk backend."
applyTo: "backend/**/*.py"
---

# Backend — FastAPI + Pydantic v2 Conventions

## FastAPI Patterns

### Router Setup
```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/v1", tags=["descriptive-tag"])
```

### Dependency Injection for Config & Store
```python
from app.config import Settings, get_settings
from app.store.vector_store import VectorStore, get_vector_store

@router.post("/endpoint")
async def my_endpoint(
    body: MyRequestModel,
    settings: Settings = Depends(get_settings),
    store: VectorStore = Depends(get_vector_store),
):
    ...
```

### Error Handling
- Always raise `HTTPException` with explicit `status_code` and meaningful `detail`
- Use `status.HTTP_*` constants — never raw integers
- Log exceptions before raising: `logger.exception("context: %s", exc)`

```python
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail=f"Failed to ingest codebase: {exc}",
)
```

### Streaming Routes
```python
from fastapi.responses import StreamingResponse

@router.post("/agent")
async def agent_endpoint(body: RunAgentInput):
    return StreamingResponse(
        event_generator(body),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
```

## Pydantic v2 Rules

- Use `model_config = ConfigDict(...)` — NOT `class Config:`
- Validators: use `@field_validator` and `@model_validator` — NOT `@validator`
- Optional fields: `field: str | None = None` — NOT `Optional[str]`
- `model_dump()` replaces `.dict()`, `model_validate()` replaces `.parse_obj()`

```python
from pydantic import BaseModel, ConfigDict, field_validator

class IngestRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str
    source_type: Literal["github", "local", "upload"]
    codebase_id: str | None = None

    @field_validator("source")
    @classmethod
    def source_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source must not be empty")
        return v
```

## Async Rules
- All database/IO operations must be `async`
- Never block the event loop — use `asyncio.to_thread()` for sync-only libraries
- Use `httpx.AsyncClient` — never `requests` in async context
- LangGraph `astream_events` must be consumed with `async for`

## Logging
```python
import logging
logger = logging.getLogger(__name__)
# Use structured calls:
logger.info("Ingesting codebase: id=%s source=%s", codebase_id, source)
```

## File Structure Rules
- Each file in `api/` defines ONE router and exports it
- `main.py` only assembles routers and middleware — no business logic
- Business logic lives in `agents/`, `tools/`, `graphs/`, `store/`
