---
description: "Generate pytest unit tests for a DocTalk backend module. Provide the file path to the module you want tests for."
---

Generate pytest unit tests for the following module: $MODULE_PATH

Please:

1. **Read `$MODULE_PATH`** to understand all functions, classes, and behaviors

2. **Create `backend/tests/test_${module_name}.py`** with:
   - `conftest.py` fixtures if needed (or add to existing `conftest.py`)
   - One test class per function/class being tested
   - Tests for: happy path, validation errors, edge cases, async behavior

3. **Mock all external dependencies**:
   - ChromaDB calls → `MagicMock`
   - LLM calls → `AsyncMock` returning realistic fake responses
   - File system / GitHub → `AsyncMock` or `pytest.MonkeyPatch`
   - HTTP calls → `respx` or `httpx` mock

4. **Follow these patterns**:
   ```python
   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch

   @pytest.mark.asyncio
   async def test_${function_name}_${scenario}():
       # Arrange
       ...
       # Act
       result = await function_under_test(...)
       # Assert
       assert result == expected
   ```

5. **Target**: at least one test per code path (success + each error branch)

Follow `.github/instructions/backend.instructions.md` and `.github/agents/testing.agent.md` for all conventions.
