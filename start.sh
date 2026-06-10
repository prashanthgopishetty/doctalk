#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[doctalk]${NC} $1"; }
warn() { echo -e "${YELLOW}[doctalk]${NC} $1"; }
err()  { echo -e "${RED}[doctalk]${NC} $1"; }

cleanup() {
  log "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── Check Ollama ──────────────────────────────────────────────────────────────
if ! curl -s http://localhost:11434 > /dev/null 2>&1; then
  warn "Ollama is not running at http://localhost:11434"
  warn "Start it with: ollama serve"
  warn "Then pull models: ollama pull qwen2.5-coder:7b && ollama pull nomic-embed-text"
  warn "Continuing anyway — you can still ingest if Ollama starts later."
fi

# ── Backend setup ─────────────────────────────────────────────────────────────
log "Setting up backend..."
cd "$BACKEND_DIR"

if [[ ! -d ".venv" ]]; then
  log "Creating Python virtual environment..."
  python311 -m venv .venv 2>/dev/null || python3 -m venv .venv
fi

source .venv/bin/activate

log "Installing backend dependencies..."
pip install -r requirements.txt -q

if [[ ! -f ".env" ]]; then
  log "Creating .env from .env.example..."
  cp .env.example .env
fi

log "Starting backend on http://localhost:8000 ..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend setup ────────────────────────────────────────────────────────────
log "Setting up frontend..."
cd "$FRONTEND_DIR"

if [[ ! -d "node_modules" ]]; then
  log "Installing frontend dependencies..."
  npm install -q
fi

if [[ ! -f ".env.local" ]]; then
  log "Creating .env.local from .env.local.example..."
  cp .env.local.example .env.local
fi

log "Starting frontend on http://localhost:3000 ..."
npm run dev &
FRONTEND_PID=$!

# ── Wait for both ─────────────────────────────────────────────────────────────
log ""
log "DocTalk is starting up:"
log "  Frontend → http://localhost:3000"
log "  Backend  → http://localhost:8000"
log "  API docs → http://localhost:8000/docs"
log ""
log "Press Ctrl+C to stop both servers."

wait
