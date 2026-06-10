---
description: "Create a new LangChain StructuredTool for a DocTalk agent. Provide the tool name, what it does, and its input parameters."
---

Create a new LangChain `StructuredTool` for the DocTalk backend.

**Tool details:**
- Tool name: $TOOL_NAME
- Description: $TOOL_DESCRIPTION
- Input parameters: $INPUT_PARAMS
- Which agent(s) will use it: $AGENT_NAMES

Create `backend/app/tools/${TOOL_NAME}.py` with:

1. **Pydantic v2 input schema**:
   ```python
   class ${ToolName}Input(BaseModel):
       model_config = ConfigDict(str_strip_whitespace=True)
       # fields based on $INPUT_PARAMS
   ```

2. **Async implementation function** `_${tool_name}(...)`:
   - Use `async def`
   - Access `VectorStore` or other dependencies via module-level singleton (not function args, since StructuredTool doesn't support DI)
   - Include proper error handling with informative messages
   - Return a string (tools must return strings for LangChain tool protocol)

3. **StructuredTool instance**:
   ```python
   ${tool_name}_tool = StructuredTool.from_function(
       coroutine=_${tool_name},
       name="${TOOL_NAME}",
       description="${TOOL_DESCRIPTION}",
       args_schema=${ToolName}Input,
   )
   ```

4. **Export** the tool instance at module level

Follow the conventions in `.github/instructions/backend.instructions.md`.
Include a docstring on the implementation function explaining parameters and return value.
