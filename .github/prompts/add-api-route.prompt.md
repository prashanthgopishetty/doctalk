---
description: "Add a new FastAPI route to the DocTalk backend with proper Pydantic request/response models, dependency injection, and error handling."
---

Add a new FastAPI route to the DocTalk backend.

**Route details:**
- HTTP method: $HTTP_METHOD
- Path: $ROUTE_PATH
- Purpose: $ROUTE_PURPOSE
- Router file: $ROUTER_FILE (e.g., `backend/app/api/ingestion.py`)

Please:

1. **Add Pydantic v2 request model** (if POST/PUT):
   ```python
   class ${Name}Request(BaseModel):
       model_config = ConfigDict(str_strip_whitespace=True)
       # fields...
   ```

2. **Add Pydantic v2 response model**:
   ```python
   class ${Name}Response(BaseModel):
       # fields...
   ```

3. **Add the route function** to `$ROUTER_FILE`:
   - Use `async def`
   - Inject `Settings` and `VectorStore` via `Depends`
   - Use `HTTPException` with `status.HTTP_*` constants for errors
   - Add OpenAPI `summary` and `description` to the decorator
   - Log the operation with `logger.info`

4. **Register the router** in `backend/app/main.py` if it's a new router file

Follow `.github/instructions/backend.instructions.md` for all conventions.
