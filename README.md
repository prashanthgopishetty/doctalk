# DocTalk — Multi-Agent Documentation Assistant

A conversational AI system that lets you ingest any codebase or document — GitHub URLs, local paths, or uploaded files (code, PDFs, Word docs, Markdown, etc.) — and ask natural-language questions about it. Answers are streamed back in real time via a multi-agent LangGraph pipeline.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Architecture Overview](#architecture-overview)
- [Key Design Decisions](#key-design-decisions)
- [Trade-offs & Known Limitations](#trade-offs--known-limitations)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [What I'd Improve Next](#what-id-improve-next)

---

## Problem Statement

**Option 2 — Documentation Assistant**

Large codebases and document collections are hard to navigate. Developers and knowledge workers waste time searching for where things are, what a function does, what a policy says, or whether something is tested. LLMs can answer those questions — but only if they are given the right context.

DocTalk solves this by:
1. **Ingesting** any codebase or document collection into a semantic vector index (ChromaDB)
2. **Routing** each question to a specialist agent that knows what tools to use
3. **Streaming** grounded answers token-by-token back to the user

Whether you're exploring code (Python, TypeScript, JavaScript, etc.), PDF technical manuals, Word documents, Markdown guides, or a mix of all of them, DocTalk understands the content and answers questions accurately.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Next.js 15)             │
│  IngestionPanel ──► POST /ingest                    │
│  ChatPanel      ──► POST /agent  (SSE stream)       │
└────────────────────────┬────────────────────────────┘
                         │ AG-UI Server-Sent Events
┌────────────────────────▼────────────────────────────┐
│              FastAPI Backend (Python 3.11)          │
│                                                     │
│  POST /ingest ─► Loader ─► AST Chunker ─► ChromaDB │
│                                                     │
│  POST /agent  ─► LangGraph StateGraph               │
│                      │                              │
│               ┌──────▼──────┐                       │
│               │  Supervisor │  (LLM intent router)  │
│               └──┬──┬──┬───┘                        │
│         ┌────────┘  │  └───────────┐                │
│         ▼           ▼             ▼  ...             │
│    Developer   Architecture   Testing               │
│     Agent        Agent         Agent                │
│         │           │             │                  │
│    code_search  code_search  code_search            │
│    find_symbol  list_files   find_symbol            │
│         │           │             │                  │
│         └───────────▼─────────────┘                 │
│                 ChromaDB                            │
└─────────────────────────────────────────────────────┘
```

### Ingestion Pipeline

```
Source Input
  │
  ├─ GitHub URL  ─► git clone --depth=1 ─► temp dir
  ├─ Local Path  ─►                         dir
  └─ File Upload ─► write bytes ──────────► temp dir
              │
              ▼
         walk_directory()
              │
     per file by extension:
       .py   ─► AST-level chunking (function/class nodes)
       .ts/js ─► regex heuristic chunking
       .pdf  ─► pypdf text extraction
       .docx ─► python-docx paragraph extraction
       other ─► character-split with 200-token overlap
              │
              ▼
      Document(page_content, metadata{
        file_path, language, symbol_name,
        start_line, end_line, codebase_id
      })
              │
              ▼
      OpenAIEmbeddings (Mistral-embed / any OpenAI-compatible)
              │
              ▼
      ChromaDB collection: doctalk_{codebase_id}
```

### Agent Routing

The LangGraph `supervisor` node sends the user's message to the LLM with a classification prompt. The LLM returns a single lowercase label (`developer`, `architecture`, `testing`, `self_improvement`, `documentation`). A conditional edge dispatches to the matching agent node. Each agent:

1. Prepends a role-specific system prompt
2. Calls `llm.bind_tools([code_search, find_symbol, list_files])`
3. Runs a tool-call loop until the LLM stops calling tools
4. Returns `{messages, agent_name}` to the graph state

### Streaming (AG-UI Protocol)

The `/agent` endpoint returns a `StreamingResponse` with `text/event-stream`. It translates LangGraph's `astream_events(version="v2")` into the AG-UI event schema the frontend understands:

| LangGraph event | AG-UI event emitted |
|---|---|
| stream start | `RunStarted` |
| `on_chain_start` (node name) | `StepStarted` |
| `on_chat_model_stream` | `TextMessageContent` |
| `on_tool_start` | `ToolCallStart` + `ToolCallArgs` |
| `on_tool_end` | `ToolCallEnd` + `ToolCallResult` |
| `on_chain_end` (agent node) | `StepFinished` |
| stream end / error | `RunFinished` / `RunError` |

---

## Key Design Decisions

### 1. Multi-agent specialisation over a single general-purpose agent

A single LLM with a "do everything" prompt produces shallow answers. A `developer` agent asked to explain authentication will search for auth-related symbols and trace call paths. An `architecture` agent asked the same question maps module dependencies. Specialisation lets each agent have a focused system prompt and a tailored tool set, giving better answers without increasing cost.

The LLM-based supervisor adds one cheap inference call per turn. The alternative (keyword regex routing) is brittle — "how do I test auth?" is clearly a `testing` question but regex would miss it.

### 2. AST-level chunking for Python, not fixed-size splitting

Splitting code at fixed character counts breaks functions mid-body and merges unrelated functions into one chunk — both hurt retrieval precision. Using Python's `ast` module, each function and class becomes its own Document, preserving semantic boundaries. TypeScript/JS gets a regex approximation of the same idea. For prose documents (PDF, DOCX) character splitting with overlap is fine because there are no syntactic boundaries to preserve.

### 3. ChromaDB in-process, not a separate service

ChromaDB can run embedded in the FastAPI process (no separate container, no network hop). For a single-user tool with codebases that fit in memory this is fast and operationally simple. The tradeoff is that it doesn't scale horizontally — but that's out of scope for this problem.

### 4. OpenAI-compatible embedding client with `check_embedding_ctx_length=False`

Mistral's embedding API is OpenAI-compatible but does not accept pre-tokenized integer arrays — it requires raw strings. `langchain_openai.OpenAIEmbeddings` by default pre-tokenizes input using tiktoken before sending, which causes a 422 error from Mistral. Setting `check_embedding_ctx_length=False` bypasses tokenization and sends plain strings. This is a one-line fix that keeps the dependency count low (no need for `langchain-mistralai`).

### 5. Shallow clone (`depth=1`) for GitHub ingestion

A full clone of a large repo can take tens of seconds and gigabytes of disk. Depth-1 gets the latest snapshot of every file in seconds. History is irrelevant for documentation questions.

### 6. Frontend calls FastAPI directly, not via CopilotKit's managed runtime

CopilotKit's `RemoteRuntime` is designed for its own agentic loop and adds middleware that conflicts with raw SSE streaming from LangGraph. Since we own both ends of the protocol, the frontend's `ChatPanel` establishes the SSE connection directly to `/agent` and parses AG-UI events manually. This gives full control over the streaming UX and removes the need for the CopilotKit backend package.

### 7. Graceful out-of-scope handling for non-content questions

The supervisor's prompt explicitly instructs the LLM to classify off-topic questions (general knowledge, recipes, jokes, weather, etc.) as `out_of_scope`. The system then routes those to a lightweight `out_of_scope_agent` which returns a polite, brief message:
- *No content ingested yet:* "Please ingest a codebase first..."
- *Off-topic query:* "I'm only able to answer questions about the ingested content..."

This prevents hallucinated answers to questions outside the system's expertise, improves user experience by redirecting intent clearly, and avoids wasting API calls on impossible questions. The supervisor's token output is also filtered out (via `on_chat_model_stream` guard) so only agent responses appear to the user, not routing decisions.

---

## Trade-offs & Known Limitations

| Area | Current approach | Limitation / What I'd do with more time |
|---|---|---|
| **Conversation memory** | No memory — each request is stateless | Add a Redis-backed thread store; pass prior messages in `RunAgentInput.messages` |
| **Agent tool loop depth** | Max iterations hard-coded to 5 | Expose as config; add cost guard |
| **Large file handling** | Files > 200 KB are skipped | Stream-chunk large files instead of skipping |
| **Multi-file upload** | All files chunked flat | Preserve relative paths to give agents folder context |
| **Supervisor accuracy** | Single LLM call, no confidence score | Add few-shot examples; fall back gracefully on ambiguous queries |
| **ChromaDB scaling** | Single in-process instance | Swap for Chroma server mode or Qdrant for multi-user deployment |
| **Auth / multi-tenancy** | None | Add JWT auth; scope collections per user |
| **Test coverage** | Backend unit tests scaffolded | Need integration tests for the full ingestion → query flow |
| **Docker Compose** | Works for Ollama; Mistral cloud key not passed through | Add `.env` passthrough in Compose for cloud keys |

---

## Project Structure

```
doctalk/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, CORS, lifespan
│   │   ├── config.py            # Pydantic Settings (env-backed)
│   │   ├── llm.py               # Cached ChatOpenAI factory
│   │   ├── api/
│   │   │   ├── chat.py          # POST /agent → AG-UI SSE stream
│   │   │   └── ingestion.py     # POST /ingest, /ingest/upload, GET, DELETE
│   │   ├── agents/
│   │   │   ├── developer_agent.py
│   │   │   ├── architecture_agent.py
│   │   │   ├── testing_agent.py
│   │   │   ├── self_improvement_agent.py
│   │   │   └── documentation_agent.py
│   │   ├── graphs/
│   │   │   ├── state.py         # AgentState TypedDict
│   │   │   ├── supervisor.py    # LLM-based intent router
│   │   │   └── main_graph.py    # StateGraph assembly (cached)
│   │   ├── tools/
│   │   │   ├── code_search.py   # ChromaDB similarity search tool
│   │   │   ├── file_tools.py    # find_symbol, list_files tools
│   │   │   ├── ast_parser.py    # AST/regex/PDF/DOCX chunkers
│   │   │   └── loaders.py       # GitHub clone, local walk, upload handler
│   │   └── store/
│   │       └── vector_store.py  # ChromaDB wrapper + embedding init
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout (no CopilotKit provider)
│   │   └── page.tsx             # Main page — sidebar + chat
│   ├── components/
│   │   ├── ChatPanel.tsx        # SSE client, message renderer
│   │   ├── IngestionPanel.tsx   # GitHub/local/upload ingestion form
│   │   ├── AgentSelector.tsx    # Manual agent hint override
│   │   ├── AgentThinking.tsx    # Step indicator during streaming
│   │   └── ToolCallDisplay.tsx  # Renders tool call/result blocks
│   ├── lib/
│   │   └── types.ts             # Shared TypeScript types
│   ├── .env.local.example
│   └── Dockerfile
├── docker-compose.yml
├── start.sh                     # One-command local dev startup
└── .github/
    ├── copilot-instructions.md  # Global Copilot context
    ├── agents/                  # Custom VS Code Copilot agents
    ├── instructions/            # File-pattern coding instructions
    └── prompts/                 # Reusable slash-command prompts
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Mistral AI API key — get one free at [console.mistral.ai](https://console.mistral.ai)
  - Or swap for any OpenAI-compatible endpoint (Ollama, OpenAI, Groq, etc.)

### Quickstart (local dev)

```bash
git clone https://github.com/your-username/doctalk
cd doctalk

# Backend env
cp backend/.env.example backend/.env
# Edit backend/.env — set LLM_API_KEY=your-mistral-key

# Frontend env
cp frontend/.env.local.example frontend/.env.local

# Start both servers (creates venv, installs deps, runs uvicorn + next dev)
chmod +x start.sh
./start.sh
```

Frontend: http://localhost:3000  
Backend API docs: http://localhost:8000/docs

### Docker Compose

```bash
# Create backend/.env with your keys first
docker compose up --build
```

### Manual setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Using the UI

1. **Ingest a codebase or documents** — paste a GitHub URL, enter a local path (or use Browse), or upload `.py`, `.ts`, `.js`, `.md`, `.pdf`, `.docx` files or any combination
2. **Ask questions** — type naturally in the chat box; the system routes your question automatically
3. **Watch the agent work** — the step indicator shows which agent is active and any tool calls it makes in real time
4. **Stay on-topic** — the system gracefully handles off-topic questions by politely redirecting you to questions about the ingested content (e.g. "summarize this", "how does X work?", "show me the architecture")

---

## Configuration Reference

All backend config is via environment variables (loaded from `backend/.env`):

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | *(required)* | API key for the LLM provider |
| `LLM_BASE_URL` | `https://api.mistral.ai/v1` | OpenAI-compatible chat endpoint |
| `LLM_MODEL` | `mistral-small-latest` | Model name to use |
| `EMBEDDING_MODEL` | `mistral-embed` | Embedding model name |
| `EMBEDDING_BASE_URL` | `https://api.mistral.ai/v1` | OpenAI-compatible embedding endpoint |
| `EMBEDDING_API_KEY` | *(falls back to `LLM_API_KEY`)* | Separate key if needed |
| `CHROMA_PATH` | `./chroma_db` | Directory for ChromaDB persistence |
| `GITHUB_TOKEN` | *(empty)* | Optional PAT for authenticated GitHub clones |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

**To use Ollama locally instead of Mistral:**

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5-coder:7b
LLM_API_KEY=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434/v1
```

---

## API Reference

### `POST /ingest`

Ingest a GitHub URL, local path, or directory of documents (code and/or files).

```json
{
  "source": "https://github.com/owner/repo",
  "source_type": "github",
  "codebase_id": "optional-custom-id"
}
```

Response:
```json
{
  "codebase_id": "abc123",
  "documents_indexed": 412,
  "message": "Successfully indexed 412 chunks from code and documents."
}
```

### `POST /ingest/upload`

Multipart form upload of one or more code or document files (`.py`, `.ts`, `.js`, `.md`, `.pdf`, `.docx`, etc.). Returns the same `IngestResponse` shape.

### `GET /ingest`

List all ingested codebase IDs currently in ChromaDB.

### `DELETE /ingest/{codebase_id}`

Delete a codebase collection from ChromaDB.

### `POST /agent`

AG-UI streaming endpoint. Accepts:

```json
{
  "threadId": "uuid",
  "runId": "uuid",
  "messages": [{"role": "user", "content": "how does auth work?"}],
  "state": {"codebaseId": "abc123"}
}
```

Returns a `text/event-stream` of AG-UI events.

---

## What I'd Improve Next

**Conversational memory** — the biggest missing piece. Right now every question is independent. Storing message history per `threadId` (e.g. in Redis or a simple SQLite store) would allow follow-up questions and context-aware answers.

**Smarter chunking** — the AST chunker handles Python well but the TypeScript chunker is a regex approximation. A proper tree-sitter based chunker would give accurate symbol extraction for TS, Go, Rust, etc.

**Re-ranking** — ChromaDB's cosine similarity retrieval is a good first pass but often returns noisy results. Adding a cross-encoder re-ranker (e.g. `flashrank`) over the top-20 candidates before passing to the LLM would improve answer quality measurably.

**Incremental re-ingestion** — today re-ingesting a source replaces the whole collection. File-level change detection (compare file hashes against stored metadata) would let the system update only changed files, making it practical for large repos and document sets under active development.

**Agent feedback loop** — if the LLM's initial tool call returns poor results, the agent currently just answers with what it has. Adding a self-critique step ("did these results answer the question? if not, reformulate the query") would reduce hallucination on difficult queries.

**Structured output for architecture queries** — the architecture agent currently returns prose. Returning a JSON dependency graph that the frontend renders as an interactive diagram would make it far more useful.

**Auth & multi-tenancy** — add JWT authentication and scope ChromaDB collections per user so multiple people can maintain their own code and document indexes without interference.
