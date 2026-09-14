# Architecture Document: The Lenny Growth Assistant

## 1. System Topology and Component Boundaries

The Lenny Growth Assistant is designed as a modular, three-tier architecture containerized via Docker Compose:

```
+--------------------------------------------------------------------------------+
|                               Browser / Client                                 |
|  React 18 + Vite (TypeScript, Vanilla CSS tokens following Impeccable.style)   |
|  - Split-pane layout (Chat Stream + Sandboxed Artifact Viewer)                 |
|  - Server-Sent Events (SSE) consumer for streaming completions                |
+---------------------------------------+----------------------------------------+
                                        | HTTP / SSE
                                        v
+--------------------------------------------------------------------------------+
|                           Backend Application (FastAPI)                        |
|                                                                                |
|  [ API Layer ]                                                                 |
|  - Pydantic v2 Request/Response Validation & Structured Error Envelopes        |
|  - Health Probe (/health) checking DB + LLM reachability                       |
|                                                                                |
|  [ Agent & Skills Layer ] (Anthropic Agent Architecture)                       |
|  - Deterministic Intent Router (Grounded Q&A vs Ship 30 Essay vs Artifact)     |
|  - Grounded RAG Tool (`retrieve_transcript_chunks`)                            |
|  - Ship 30 for 30 Content Tool (`generate_ship30_essay`)                       |
|  - Artifact Generation Tool (`create_artifact`)                                |
|                                                                                |
|  [ LLM Provider Abstraction ]                                                 |
|  - Swappable Engine: Local Ollama (llama3.1:8b) | Google Gemini | Claude | OpenAI|
|                                                                                |
|  [ Ingestion & Retrieval Engine ]                                              |
|  - Universal Frontmatter Parser & Monotonic Timestamp Interpolator             |
|  - FastEmbed ONNX Runtime (BAAI/bge-small-en-v1.5, 384 dim, <10ms CPU)         |
+---------------------------------------+----------------------------------------+
                                        | SQLAlchemy Async / psycopg3
                                        v
+--------------------------------------------------------------------------------+
|                        Data Persistence (PostgreSQL 16)                        |
|                                                                                |
|  - pgvector extension for dense embedding storage & HNSW cosine index         |
|  - Relational tables: sessions, messages, episodes, transcript_chunks          |
+--------------------------------------------------------------------------------+
```

## 2. Agent Layer Justification: Anthropic Agent SDK Architecture vs Pi Coding Agent

The assignment requires selecting either the **Anthropic Claude Agent SDK** or **Pi Coding Agent**, and justifying the choice plainly.

### Decision: Anthropic Claude Agent SDK Architecture

I chose the **Anthropic Claude Agent SDK pattern** and deliberately rejected Pi Coding Agent. Here is the technical justification:

1. **Runtime and Language Homogeneity:**  
   Pi Coding Agent (`earendil-works/pi`) is a TypeScript/Node.js minimalist harness. Because our backend requires FastAPI, SQLAlchemy, and pgvector for high-performance Python data ingestion and vector math, choosing Pi would create a fragmented dual-runtime architecture (Python FastAPI + Node.js Pi agent subprocess). Managing subprocess IPC over standard I/O or JSON-RPC introduces process supervision overhead, potential zombie processes inside Docker containers, and complex cross-language error propagation.
2. **Provider-Agnostic Tool-Calling Loop:**  
   The Anthropic Agent SDK pattern formalizes the agent loop around explicit tool definitions (`input_schema`), tool execution, and message history accumulation (`Think -> Act -> Observe -> Respond`). We implement this pattern natively in Python. By writing a unified provider adapter, the identical agent loop runs against Anthropic Claude (`claude-3-5-sonnet`) when cloud credentials are provided, or against local Ollama (`llama3.1:8b`) via Ollama's OpenAI-compatible tool-calling endpoint.
3. **Determinism over Unconstrained Autonomy:**  
   Pi Coding Agent is designed as an open-ended terminal coding agent with general shell tools (`bash`, `write`, `edit`). For an enterprise growth assistant, general shell access is both an unnecessary security risk and prone to looping on local 8B parameter models. The Anthropic Agent pattern restricts the agent to strictly bounded, domain-specific tools (`retrieve_transcript_chunks`, `generate_ship30_essay`, `create_artifact`), guaranteeing reliable execution on consumer hardware.

## 3. Database Schema

The database runs on PostgreSQL 16 with the `pgvector` extension enabled.

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb NOT NULL,
    artifacts JSONB DEFAULT '[]'::jsonb NOT NULL,
    model_provider VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_messages_session_id ON messages(session_id);

-- Episodes table
CREATE TABLE episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(512) NOT NULL,
    guest VARCHAR(255) NOT NULL,
    youtube_url VARCHAR(512) NOT NULL,
    video_id VARCHAR(64) NOT NULL,
    publish_date DATE,
    duration_seconds FLOAT,
    view_count INTEGER,
    channel VARCHAR(128),
    keywords JSONB DEFAULT '[]'::jsonb NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_episodes_slug ON episodes(slug);
CREATE INDEX idx_episodes_guest ON episodes(guest);

-- Transcript chunks table
CREATE TABLE transcript_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    speaker VARCHAR(255) NOT NULL,
    start_timestamp VARCHAR(32) NOT NULL, -- e.g. "00:05:04"
    start_seconds INTEGER NOT NULL,       -- e.g. 304 (used for &t=304s link)
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding vector(384) NOT NULL,       -- MiniLM-L6-v2 produces 384 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX idx_chunks_episode_id ON transcript_chunks(episode_id);
-- HNSW index for fast approximate nearest neighbor cosine search
CREATE INDEX idx_chunks_embedding_hnsw ON transcript_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## 4. Ingestion and Retrieval Pipeline

```
[ Transcript Archive: ChatPRD/lennys-podcast-transcripts ]
                     |
                     v
   [ 1. Ingestion Loader (app/ingest.py) ]
   - Parse YAML frontmatter (guest, title, youtube_url, duration, keywords)
   - Parse speaker turns and timestamps (e.g. "Brian Chesky (00:05:04):")
                     |
                     v
   [ 2. Chunking Engine ]
   - Group speaker turns into coherent semantic windows (~250-400 words / 1,200-1,800 chars)
   - Preserve exact starting timestamp and calculate second offset
   - Deduplicate consecutive speaker turns while maintaining overlap
                     |
                     v
   [ 3. Local Embedding Generator ]
   - Model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
   - Fast, CPU-friendly (runs under 10ms per chunk on normal CPU, zero API cost)
                     |
                     v
   [ 4. Upsert to pgvector ]
   - Store episode metadata in `episodes`
   - Bulk upsert chunks and vectors into `transcript_chunks`
                     |
                     v
   [ 5. Query-Time Retrieval ]
   - Embed user query with identical embedding model
   - Cosine distance search: `1 - (embedding <=> query_vec)`
   - Filter threshold: similarity > 0.45 (reject below threshold to prevent hallucination)
   - Top-K selection (k = 5 chunks) formatted with speaker, episode, and YouTube URL
```

### Citation Linking Mechanics
When chunk metadata contains `video_id="4ef0juAMqoE"` and `start_seconds=304`, the retrieval tool formats the citation as:
`[Brian Chesky - Brian Chesky's new playbook (00:05:04)](https://www.youtube.com/watch?v=4ef0juAMqoE&t=304s)`.
This gives the user instant one-click playback at the exact second the statement occurred.

## 5. Model Configuration and Toggle Mechanism

The model provider is swappable at runtime without touching application code. In addition, the frontend header provides a dropdown selector enabling dynamic model switching per conversation session.

### Configuration Layer
The configuration is driven by `app/core/config.py` using `pydantic-settings`:

```python
class Settings(BaseSettings):
    LLM_PROVIDER: str = "ollama"  # "ollama", "gemini", "claude", or "openai"
    
    # Local Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lenny_assistant"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
```

### Provider Fallback and Health Verification
When the backend boots or serves requests:
1. It validates whether the configured provider is reachable.
2. If `LLM_PROVIDER=ollama`, it queries `GET /api/tags` on `OLLAMA_BASE_URL` to verify Ollama is running and that the model is loaded.
3. If `LLM_PROVIDER=gemini`, it queries Google's OpenAI-compatible models endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/models`) and measures latency.
4. If `LLM_PROVIDER=claude`, it validates that `ANTHROPIC_API_KEY` is present and well-formed.
5. **Fallback Behavior:** If the active provider fails (e.g., Ollama is not running), the API does not throw a raw 500. It returns an HTTP 503 error with an explicit JSON payload:
   ```json
   {
     "error": "PROVIDER_UNAVAILABLE",
     "message": "Ollama is not running at http://localhost:11434. Start Ollama with 'ollama serve' or set LLM_PROVIDER=gemini in .env",
     "active_provider": "ollama",
     "available_providers": ["ollama", "gemini", "claude", "openai"]
   }
   ```

## 6. Agent Skills and Routing Logic

The agent orchestrator inspects user intent to determine which skill and tool to dispatch:

```
                                  User Message
                                       |
                                       v
                          [ Agent Orchestrator Loop ]
                          (Observe -> Think -> Act)
                                       |
                 +---------------------+---------------------+
                 |                                           |
                 v                                           v
    [ Grounded Retrieval Tool ]                 [ Ship 30 Content Tool ]
    - `retrieve_podcast_transcripts`            - `generate_ship30_essay`
    - FastEmbed ONNX embedding (<10ms)          - Enforces Cole/Bush principles
    - pgvector cosine distance search           - Calibrated ~1,250 words
    - Negative cutoff (tau = 0.45)              - Prohibited buzzword filter
    - Emits citations with &t=...s              - Emits structured essay
                 |                                           |
                 +---------------------+---------------------+
                                       |
                                       v
                        [ Artifact Generation Tool ]
                        - `create_artifact(title, type, content)`
                        - `type: "markdown"` (essays, guides)
                        - `type: "html"` (HTML5/CSS widgets)
                        - `type: "react"` (Interactive React applications)
                                       |
                                       v
                        [ Claude-Style Clean Chat Stream ]
                        - Strips raw code fences from message bubble
                        - Renders inline Artifact Callout Card
                        - Streams artifact payload to side viewer
                                       |
                                       v
                        [ Sandboxed Artifact Viewer ]
                        - Markdown: High-contrast typography
                        - HTML: Sandboxed iframe with CSP
                        - React: React 18 UMD + Babel Standalone
                          + Tailwind CSS CDN runtime mounting
```

### The Ship 30 for 30 Skill Architecture
Rather than relying on an unstructured monolithic prompt, the Ship 30 for 30 skill is built as a structured two-stage pipeline:
1. **Fact Extraction Stage:** Extracts the core thesis, specific quotes, and tactical steps from the retrieved podcast transcripts.
2. **Essay Formulation Stage:** Enforces the Cole/Bush rules:
   - Strong contrarian hook.
   - Elimination of passive voice and buzzwords.
   - Skimmable rhythm (short sentences, bold keywords, bullet points).
   - Word count calibration targeting ~1,250 words.

### Interactive React Artifact Architecture
When an interactive tool, calculator, or dashboard is requested:
1. **Extraction:** The orchestrator identifies `type="react"` or ````tsx / ````jsx blocks.
2. **Module Import Normalization:** `ArtifactViewer.tsx` parses ES module imports (such as `import React, { useState } from 'react'`) into UMD variable bindings (`const { useState } = React;`).
3. **In-Browser Compilation:** Babel Standalone transpiles JSX/TSX syntax to standard JavaScript in real-time.
4. **Isolated Mounting:** The compiled component renders into `#root` inside the sandboxed iframe, providing full access to React hooks and interactive state without exposing the parent DOM or tokens.

## 7. API Endpoints Contract

All endpoints follow strict Pydantic request/response validation.

### `GET /health`
Validates end-to-end service readiness.
- Response (200 OK):
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "llm_provider": {
      "provider": "ollama",
      "model": "llama3.1:8b",
      "status": "reachable"
    },
    "indexed_episodes": 25,
    "indexed_chunks": 1840
  }
  ```
- If database or LLM is unreachable, returns status `503 Service Unavailable` with diagnostic details.

### `POST /api/sessions`
Creates a new conversation session.
- Request: `{ "title": "Elena Verna Growth Strategy" }`
- Response: `{ "id": "uuid", "title": "...", "created_at": "..." }`

### `GET /api/sessions`
Lists persisted chat sessions ordered by `updated_at DESC`.

### `GET /api/sessions/{session_id}/messages`
Retrieves all historical messages, citations, and artifacts for a session.

### `POST /api/chat`
Submits a message and streams back the assistant's grounded response.
- Request:
  ```json
  {
    "session_id": "uuid",
    "content": "Why shouldn't early startups hire a growth team according to Elena Verna?",
    "stream": true
  }
  ```
- Response: Server-Sent Events (SSE) streaming data tokens, closing with `[DONE]` and emitting citation objects and artifact metadata.

### `POST /api/artifacts`
Explicitly saves or updates an artifact attached to a session.

## 8. Security Architecture

1. **Untrusted Code Execution Isolation:** As documented in `design.md`, all HTML artifacts are isolated inside a sandboxed iframe with `sandbox="allow-scripts"` and a strict Content Security Policy disabling network calls and parent window access.
2. **SQL Injection Defense:** All database interactions use SQLAlchemy ORM with parameterized SQL queries. Vector cosine distance queries use pgvector operators via parameterized query builders.
3. **CORS Configuration:** Restricted to the frontend host (`http://localhost:5173` or Docker network origin).
4. **Environment Isolation:** Secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`) are read from environment variables; `.env` is ignored in `.gitignore`, and `.env.example` contains only placeholder values.

## 9. Deployment Topology

The entire application runs via Docker Compose (`docker-compose.yml`):
- `postgres`: PostgreSQL 16 with `pgvector` pre-installed (`pgvector/pgvector:pg16`), volume mounted for persistent storage.
- `backend`: Python 3.11 with FastAPI, running under Uvicorn. Connects to `postgres:5432` and host Ollama (`host.docker.internal:11434`).
- `frontend`: Node 20 / Nginx serving the compiled React application on port 5173 / 80.
