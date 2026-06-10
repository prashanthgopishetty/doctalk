# DocTalk — Copilot Instructions

## Project Overview
DocTalk is a multi-agent Code Documentation Assistant. Users ingest a codebase (GitHub URL, local path, or file upload) and ask questions about it in natural language. The system routes queries to specialized AI agents and streams answers back via the AG-UI protocol.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, LangGraph, LangChain, ChromaDB, Pydantic v2
- **Frontend**: Next.js 15 (App Router), TypeScript, CopilotKit, Tailwind CSS
- **Protocol**: AG-UI (Server-Sent Events, event-based streaming)
- **LLM**: Configurable — default Qwen via Ollama (`qwen2.5-coder:7b`); swap via env vars
- **Embeddings**: `nomic-embed-text` via Ollama (configurable)

## Monorepo Layout
```
doctalk/
├── backend/           # FastAPI + LangGraph application
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/       # HTTP routes (chat.py, ingestion.py)
│   │   ├── agents/    # 5 specialized LangGraph agent nodes
│   │   ├── graphs/    # StateGraph assembly (state, supervisor, main_graph)
│   │   ├── tools/     # LangChain StructuredTools (code_search, loaders, ast_parser)
│   │   └── store/     # ChromaDB vector store wrapper
│   └── tests/
├── frontend/          # Next.js + CopilotKit application
│   ├── app/
│   │   ├── api/copilotkit/  # AG-UI bridge (RemoteRuntime → FastAPI)
│   │   └── page.tsx
│   └── components/
└── .github/
    ├── agents/        # Copilot custom agents for development
    ├── instructions/  # File-specific coding instructions
    └── prompts/       # Reusable slash-command prompts
```

## Agent Routing (Backend)
The LangGraph supervisor uses LLM-based intent classification to route queries:
- Keywords: test/coverage/spec/unit → `TestingAgent`
- Keywords: architecture/structure/dependency/module → `ArchitectureAgent`
- Keywords: refactor/improve/optimize/code smell → `SelfImprovementAgent`
- Keywords: document/docstring/readme/api docs → `DocumentationAgent`
- Default → `DeveloperAgent`

## AG-UI Event Flow
Backend emits SSE events translating LangGraph `astream_events`:
```
RunStarted → StepStarted (node name) → TextMessageContent (chunks) → StepFinished → RunFinished
ToolCallStart → ToolCallArgs → ToolCallEnd → ToolCallResult
```

## Coding Conventions
- All Python async functions must use `async def`
- Pydantic v2: use `model_validator`, `field_validator` — NOT v1 `validator`
- LangGraph nodes are plain `async def` functions that take and return `AgentState`
- AG-UI events are emitted as JSON via `data: {json}\n\n` SSE format
- FastAPI routes use dependency injection for config/store
- TypeScript: strict mode, no `any`, use `unknown` for externals
- React components: functional only, no class components
- CopilotKit state updates go through `useCoAgent` or `useCopilotReadable`

## Commit Conventions
Format: `<type>(<scope>): <description>`
Types: feat, fix, refactor, test, docs, chore
Scopes: backend, frontend, agents, tools, graphs, api, store

Examples:
- `feat(agents): add documentation agent with docstring tool`
- `fix(graphs): handle supervisor routing fallback correctly`
- `feat(frontend): add AgentSelector component with auto-routing`
