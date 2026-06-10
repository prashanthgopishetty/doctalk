---
description: "Analyze a DocTalk agent file for code quality issues and apply improvements: type safety, complexity, duplication, missing error handling, performance."
---

Analyze and improve the following agent file: $AGENT_FILE_PATH

Please:

1. **Read `$AGENT_FILE_PATH`** completely

2. **Run through this checklist**:
   - [ ] Are all async functions using `async def`?
   - [ ] Are all return types annotated?
   - [ ] Is the system prompt clear and concise (< 500 chars ideally)?
   - [ ] Is the tool call loop handling errors gracefully?
   - [ ] Are there any bare `except:` blocks?
   - [ ] Is there any duplicated logic shared with other agents?
   - [ ] Does the agent correctly return a state dict (not mutate in place)?
   - [ ] Are tools imported from `backend/app/tools/` (not hardcoded)?
   - [ ] Is the LLM binding done once at module level (not inside the node function)?

3. **List all issues found** before making changes:
   ```
   Issue 1: [description] — Line X
   Issue 2: [description] — Line X
   ```

4. **Apply fixes** for all issues found

5. **Summarize changes made** after editing

Follow `.github/instructions/langgraph.instructions.md` and `.github/agents/self-improvement.agent.md`.
Do not change the agent's behavior or routing — only improve the code quality.
