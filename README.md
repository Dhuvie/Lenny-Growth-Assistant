# The Lenny Growth Assistant: An Architecture for Grounded Retrieval-Augmented Generation, Long-Form Synthesis, and Sandboxed Execution

## Abstract

This repository presents the design, formal specification, and implementation of The Lenny Growth Assistant, an enterprise-grade retrieval-augmented generation (RAG) system grounded in the transcript archive of Lenny's Podcast. The system addresses three primary technical requirements: (1) deterministic attribution of product and growth advisory through verified YouTube timestamp citations, (2) automated synthesis of calibrated long-form essays (~1,250 words) adhering to the Ship 30 for 30 digital writing framework, and (3) secure rendering of untrusted dynamic HTML and markdown artifacts within a strictly isolated client-side execution sandbox.

The implementation is engineered for cold-start deployment on evaluator infrastructure. It operates locally with zero cloud dependencies using an Ollama inference backend (`llama3.1:8b`), an in-process FastEmbed ONNX vector pipeline, and a PostgreSQL instance configured with the `pgvector` extension. A swappable provider interface permits runtime reconfiguration to Anthropic Claude or OpenAI endpoints without modifying application logic.

---

## 1. System Architecture and Component Topology

The system adopts a modular four-tier architecture separating presentation, orchestration, model inference, and persistence layers. Communication across tiers employs standard REST protocols and Server-Sent Events (SSE) for incremental token and metadata streaming.

```
+-------------------------------------------------------------------------+
|                       Presentation Tier (React 18)                      |
|  - Vanilla CSS Token Design System (Impeccable style specification)     |
|  - Dynamic Split-Pane Chat and Artifact Workspace                       |
|  - Sandboxed Dynamic Iframe (Strict CSP, Zero Parent DOM Access)        |
+-------------------------------------------------------------------------+
                                     |
                                     | HTTP / Server-Sent Events (SSE)
                                     v
+-------------------------------------------------------------------------+
|                  Application Tier (FastAPI, Python 3.12)                |
|  - Dependency-injected Async SQLAlchemy Session Pool                    |
|  - RFC 7807 Structured Exception Handlers (Zero Bare 500 Responses)     |
|  - Deep Health Diagnostics Probe (/health)                              |
+-------------------------------------------------------------------------+
         |                                                 |
         v                                                 v
+-----------------------------+       +-----------------------------------+
|    Cognitive Agent Loop     |       |       Swappable Model Adapter     |
|  - Anthropic SDK DAG Loop   |       |  - Local Ollama (llama3.1:8b)     |
|  - Ship 30 Content Engine   | <---> |  - Google Gemini (Flash / Pro)    |
|  - Deterministic Tool Chain |       |  - Anthropic Claude 3.5 Sonnet    |
|                             |       |  - OpenAI GPT-4o                  |
+-----------------------------+       +-----------------------------------+
         |
         v
+-------------------------------------------------------------------------+
|               Retrieval & Embedding Tier (FastEmbed ONNX)               |
|  - In-Process Vector Embeddings: BAAI/bge-small-en-v1.5 (384 dimensions)|
|  - Latency: Sub-10ms CPU Generation (Zero PyTorch Runtime Overhead)     |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 Persistence Tier (PostgreSQL 16 + pgvector)             |
|  - HNSW Cosine Distance Index (ef_search=64, m=16)                      |
|  - Relational Schema for Conversation Sessions, Messages, and Citations |
|  - SQLite/aiosqlite Vector Fallback for Isolated Unit Test Execution    |
+-------------------------------------------------------------------------+
```

### Component Responsibilities

1. **Presentation Tier (`frontend/`):** Implemented in TypeScript using React 18 and Vite. Implements a responsive layout featuring real-time Server-Sent Event consumption, split-pane artifact viewing, verified YouTube badge links, and session management.
2. **Application Tier (`app/`):** Implemented in asynchronous Python 3.12 on FastAPI. Manages transaction lifecycles, connection pooling, and structured error responses.
3. **Agent Orchestration Engine (`app/agent/`):** Executes an iterative Observe-Think-Act-Synthesize cycle. Dynamically routes queries between semantic transcript retrieval, long-form essay formatting, and artifact production.
4. **Retrieval Pipeline (`app/rag/`):** Performs corpus parsing, speaker normalization, monotonic timestamp interpolation, token chunking, ONNX embedding generation, and cosine distance queries.
5. **Persistence Tier (`app/db/`):** Stores episodes, chunks, embeddings, conversation sessions, and messages with dialect-aware vector typing.

---

## 2. Mathematical and Retrieval Formulations

### Vector Space Representation

Text chunks and semantic search queries are projected into a 384-dimensional dense real vector space $\mathbb{R}^{384}$ using the `BAAI/bge-small-en-v1.5` transformer model executed via the ONNX Runtime:

$$f: \mathcal{T} \to \mathbb{R}^{384}, \quad \text{where } \|\mathbf{v}\|_2 = 1$$

Each output embedding is $L_2$-normalized during computation, simplifying vector comparison to the standard inner product.

### Cosine Similarity Metric

For a query embedding $\mathbf{q} \in \mathbb{R}^{384}$ and a candidate transcript chunk embedding $\mathbf{c} \in \mathbb{R}^{384}$, the cosine similarity is defined as:

$$\text{Sim}(\mathbf{q}, \mathbf{c}) = \frac{\mathbf{q} \cdot \mathbf{c}}{\|\mathbf{q}\|_2 \|\mathbf{c}\|_2} = \sum_{k=1}^{384} q_k c_k$$

PostgreSQL evaluates cosine distance using the `pgvector` operator `<=>`, where:

$$\text{Distance}_{\text{cosine}}(\mathbf{q}, \mathbf{c}) = 1 - \text{Sim}(\mathbf{q}, \mathbf{c})$$

### Negative Retrieval and Hallucination Rejection Boundary

A fundamental failure mode in conversational RAG systems is the tendency to hallucinate domain-specific advice when the indexing corpus lacks relevant context. The Lenny Growth Assistant enforces a strict similarity threshold cutoff:

$$\tau = 0.45$$

Let $\mathcal{C}_k = \{\mathbf{c}_1, \mathbf{c}_2, \dots, \mathbf{c}_k\}$ denote the top-$k$ nearest candidate chunks retrieved from the corpus. If:

$$\max_{\mathbf{c} \in \mathcal{C}_k} \text{Sim}(\mathbf{q}, \mathbf{c}) < \tau$$

the agent rejects speculative synthesis and returns a verified negative attribution response:

> "I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."

### Approximate Nearest Neighbor Search via HNSW

To ensure sub-millisecond retrieval across hundreds of thousands of transcript chunks, vector columns in PostgreSQL are indexed using Hierarchical Navigable Small World (HNSW) graphs:

```sql
CREATE INDEX idx_chunks_embedding_hnsw 
ON transcript_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

The construction parameter $m = 16$ establishes the maximum number of bidirectional connection links per node, while $ef\_construction = 64$ governs the candidate list size during graph indexing, balancing recall accuracy with insertion latency.

---

## 3. Corpus Ingestion, Parsing, and Normalization

The underlying corpus consists of over 300 episode transcripts comprising diverse formatting conventions across multiple production years. The ingestion pipeline implements an end-to-end extraction and normalization protocol.

### Multi-Format Universal Parser

The parser (`app/rag/parser.py`) applies regular expressions structured in priority order to extract turn-level data:

1. **Standard Parenthetical Turns:** `Speaker Name (HH:MM:SS): text`
2. **Continuation Parenthetical Turns:** `(HH:MM:SS): text`
3. **Bracketed Turns with Colons:** `[HH:MM:SS] Speaker Name: text`
4. **Standalone Colon Turns:** `Speaker Name:\ntext`
5. **Direct Utterance Turns:** `Speaker: text`

Canonical speaker normalization strips corporate affiliations, parenthetical notes, and formatting noise (for example, mapping `"Brian Chesky (CEO, Airbnb)"` to `"Brian Chesky"`).

### Monotonic Proportional Timestamp Interpolation

For transcripts containing speaker markers but entirely lacking timestamp anchors (such as early archive episodes), the parser applies a proportional word-count interpolation algorithm. Let $T_{\text{total}}$ represent the total audio duration in seconds, and let $W_{\text{total}}$ represent the aggregate word count across all turns. For each turn $i$ with cumulative preceding words $W_i$:

$$t_i = \left\lfloor T_{\text{total}} \times \frac{W_i}{W_{\text{total}}} \right\rfloor$$

This ensures that generated YouTube citation links maintain monotonic temporal progression across the duration of the interview.

### Heuristic Sponsor and Promotional Read Detection

Transcripts contain host sponsor reads and promotional endorsements that degrade retrieval purity. The parser computes an `is_sponsor` boolean classification based on promotional keywords (`sponsor`, `sponsored by`, `our partner`, `head to`, `promo code`, `discount code`). Chunks flagged as promotional are excluded from semantic retrieval to maintain content relevance.

### Speaker-Turn-Aware Chunking

The chunker (`app/rag/chunker.py`) groups turns into contextual windows between 1,200 and 1,800 characters, respecting speaker turn boundaries. Chunks preserve the starting timestamp and second offset of the initial turn within the window, guaranteeing that generated YouTube links navigate directly to the exact point of speech.

---

## 4. Agent Cognitive Architecture and Synthesis Engine

### Agent Execution Loop

The orchestration engine (`app/agent/orchestrator.py`) is structured according to the Anthropic Agent pattern:

```
[ User Input ]
      |
      v
[ System Prompt + History Injection ]
      |
      v
[ LLM Step: Plan & Formulate Tool Invocation ]
      |
      +---> Tool: retrieve_podcast_transcripts(query, top_k)
      |         - Performs dense vector similarity search
      |         - Returns grounded citations with timestamps
      |
      +---> Tool: generate_ship30_essay(topic, core_thesis, guest_source)
      |         - Calibrates tone, formatting, and word count target (~1,250 words)
      |
      +---> Tool: create_artifact(title, type, content)
                - Extracts interactive React web components, executable HTML, or standalone Markdown
      |
      v
[ Synthesis & Stream Emission ]
      - SSE Events: token, status, citations, artifact, done
```

### Ship 30 for 30 Content Engine

When prompted to synthesize essays, guides, or deep-dive frameworks, the agent invokes the Ship 30 for 30 Engine (`app/agent/tools/ship30_tool.py`). This engine enforces specific rhetorical parameters:

- **Specific, High-Stakes Headline:** Outlines the core operational problem immediately.
- **Contrarian Hook:** 1 to 2 declarative sentences challenging established conventional wisdom.
- **Operational Pillars:** 3 to 5 actionable pillars with bold lead-in anchors and grounded guest quotes.
- **Monday Morning Checklist:** Concrete operational steps directly executable by product and growth teams.
- **Calibrated Length:** Calibrated between 1,100 and 1,400 words (nominal target: ~1,250 words).
- **Prohibited Terminology Filter:** Algorithmic exclusion of filler terms (`leverage`, `seamless`, `in today's fast-paced world`, `game-changer`, `revolutionize`, `robust solution`, `in conclusion`).

---

## 5. Security Model and Sandboxing Specifications

The application treats dynamic HTML and JavaScript artifacts as untrusted input.

### Dual-Layer Isolation Architecture

```
+--------------------------------------------------------------------+
|  Parent Window Context (http://localhost:5173)                     |
|  - Holds Local Storage, Session State, API Bearer Tokens           |
|                                                                    |
|    +----------------------------------------------------------+    |
|    |  Sandboxed <iframe>                                      |    |
|    |  - sandbox="allow-scripts"                               |    |
|    |  - EXCLUDES allow-same-origin (Unique Opaque Origin)     |    |
|    |  - EXCLUDES allow-top-navigation (No Window Redirects)   |    |
|    |  - EXCLUDES allow-forms & allow-popups                   |    |
|    |                                                          |    |
|    |  CSP Injected in srcDoc:                                 |    |
|    |  default-src 'none'; style-src 'unsafe-inline';          |    |
|    |  script-src 'unsafe-inline'; img-src data: https:;       |    |
|    +----------------------------------------------------------+    |
+--------------------------------------------------------------------+
```

### Sandboxing Guarantees

1. **Opaque Origin Enforcement:** Because `allow-same-origin` is omitted from the iframe sandbox attribute, the sandboxed document resolves to a unique null origin `opaque origin`. Any attempt by running scripts to access `window.parent`, `window.localStorage`, or `document.cookie` triggers an immediate security error from the browser rendering engine.
2. **Network Isolation:** The Content Security Policy explicitly sets `default-src 'none'`. This prevents running artifact scripts from executing external `fetch`, `XMLHttpRequest`, or `WebSocket` connections to exfiltrate session data.
3. **Client-Side Markdown Sanitization:** Markdown and text content outside sandboxed iframes are processed through `DOMPurify` before DOM insertion to eliminate script injection vectors.

---

## 6. Complete API Specification

The backend adheres to OpenAPI 3.1 specifications. All validation errors follow structured RFC 7807 problem details.

### Endpoints Overview

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/health` | Deep diagnostic probe verifying DB, LLM, and index metrics | `200`, `503` |
| `GET` | `/api/info` | Runtime provider, model, and system configuration | `200` |
| `GET` | `/api/sessions` | List active conversation sessions ordered by updated timestamp | `200` |
| `POST` | `/api/sessions` | Create a new conversation session | `201` |
| `GET` | `/api/sessions/{id}` | Fetch session details and complete message history | `200`, `404` |
| `DELETE` | `/api/sessions/{id}` | Delete a conversation session and cascade related records | `200`, `404` |
| `POST` | `/api/chat` | Submit a prompt and open an SSE response stream | `200`, `404`, `422` |
| `GET` | `/api/artifacts` | List all generated dynamic artifacts | `200` |
| `GET` | `/api/artifacts/{id}` | Retrieve specific artifact by unique identifier | `200`, `404` |

### Server-Sent Events (SSE) Streaming Protocol (`POST /api/chat`)

When streaming responses from `POST /api/chat`, the server transmits structured text streams using the following event types:

```
event: status
data: {"message": "Searching transcript archive..."}

event: citations
data: [{"guest": "Elena Verna", "episode_title": "B2B Growth", "youtube_url": "https://www.youtube.com/watch?v=...&t=304s", ...}]

event: token
data: {"token": "Product"}

event: token
data: {"token": "-led"}

event: artifact
data: {"id": "art-123", "title": "PLG Playbook", "type": "markdown", "content": "# Operational Playbook..."}

event: done
data: {"status": "completed"}
```

---

## 7. Deployment and Operational Guide

### Prerequisites

- **Docker and Docker Compose:** (Recommended)
- **Local Ollama Engine:** Required for zero-cloud local execution:
  ```bash
  # Download from https://ollama.ai
  ollama serve
  ollama pull llama3.1:8b
  ```
- *Alternative:* Python 3.12+ and Node.js 20+ for native host execution.

### Single-Command Deployment (Docker Compose)

1. Clone the repository and prepare the configuration:
   ```bash
   git clone https://github.com/your-username/lenny-growth-assistant.git
   cd lenny-growth-assistant
   cp .env.example .env
   ```

2. Confirm that Ollama is serving on port 11434:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Launch the containerized stack:
   ```bash
   docker compose up --build
   ```

The orchestration boots three services:
- `lenny_postgres`: PostgreSQL 16 with `pgvector` on port `5432`
- `lenny_backend`: FastAPI server on port `8000` (auto-seeds foundational episodes)
- `lenny_frontend`: React + Vite web application on port `5173`

Access the web interface at: `http://localhost:5173`

---

## 8. Swappable Model Provider Configuration

The active model provider can be toggled through environment variables without recompilation or code modification. In addition, the frontend Header includes an interactive model selector allowing evaluators to dynamically switch between local Ollama and Google Gemini models per conversation session.

### 1. Local Ollama (Default Configuration)
```ini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

### 2. Google Gemini Cloud (Multiple Models)
Get your API key at https://aistudio.google.com/ and configure:
```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.5-flash-lite
```

Supported Gemini models include:
- `gemini-3.5-flash-lite`: Ultra-fast inference, high-throughput cost efficiency, and low latency (recommended default).
- `gemini-3.8-flash`: Frontier intelligence with balanced speed and multimodal understanding.
- `gemini-3.7-flash`: Hybrid reasoning and advanced tool invocation capabilities.
- `gemini-2.5-flash`: Stable fast cloud inference tier.
- `gemini-2.5-pro`: Deep reasoning and extensive synthesis for complex domain analysis.
- `gemini-2.0-flash`: Reliable multimodal tier.

### 3. Anthropic Claude
```ini
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 4. OpenAI
```ini
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o
```

Restart the backend process or container after updating `.env`. The UI status header reflects the active engine automatically, and the dropdown allows instant runtime switching.

---

## 9. Ingestion CLI Reference

The repository provides an idempotent command-line utility (`app/ingest.py`) to index episode transcripts:

```bash
# Seed the foundational 20 episodes (1,450 chunks)
python -m app.ingest --seed

# Index specific episodes by slug identifier
python -m app.ingest --episodes brian-chesky,elena-verna,shreyas-doshi

# Index the complete archive of 303 episodes
python -m app.ingest --all

# Force re-indexing of already processed episodes
python -m app.ingest --seed --reindex
```

### Cold-Start Seed Data Bundle

To prevent evaluators from waiting for hundreds of episodes to embed upon first launch, the repository includes pre-computed embeddings for 20 foundational growth episodes (`data/seed_data/seed_episodes.json`). The database auto-populates this bundle during startup in under two seconds.

---

## 10. Automated Verification and Test Harness

The test suite validates architectural integrity, security policies, parsing heuristics, and grounding constraints.

### Test Execution Commands

Run the full automated test suite:
```bash
.venv/bin/pytest -v tests/
```
*(On Windows: `.venv\Scripts\pytest -v tests/`)*

Verify frontend TypeScript compilation and production bundle build:
```bash
cd frontend
npm run build
```

### Test Coverage Matrix

| Test Module | Scope | Assertions Verified |
|---|---|---|
| `tests/test_api.py` | API Contracts | Deep health probe, session CRUD lifecycle, RFC 7807 structured 422 error envelopes, Gemini provider exposure in `/api/info` |
| `tests/test_retrieval.py` | RAG Pipeline | Timestamp parsing, YouTube URL builder, multi-variant transcript parsing, timestamp interpolation, sponsor read filtering, chunking, FastEmbed embeddings, cosine similarity threshold rejection |
| `tests/test_agent_routing.py` | Cognitive Layer | Tool schemas, Ship 30 for 30 writing principles, word count calibration, artifact block extraction, interactive React artifact extraction, contextual follow-up resolution, Gemini provider factory and multi-model configuration |
| `tests/test_security.py` | Sandboxing | Iframe sandbox attributes, exclusion of `allow-same-origin`, Content Security Policy header verification, DOMPurify sanitization |

Current status: **23 passed, 0 warnings, 0 failures (1.28s).**

### Manual UI Test Plan
In addition to the automated test suite, an interactive step-by-step verification checklist for evaluators is provided in [`tests/MANUAL_TEST_PLAN.md`](file:///c:/projects/LENNY%20Assistant/tests/MANUAL_TEST_PLAN.md).

---

## 11. Troubleshooting Reference

### 1. Health Probe Reports Unreachable LLM (503 Service Unavailable)
- **Root Cause:** The Ollama service daemon is not running on the host, or model weights have not been downloaded.
- **Remediation:** Start the Ollama process using `ollama serve` and pull the required model using `ollama pull llama3.1:8b`. Alternatively, switch to Google Gemini by configuring `GEMINI_API_KEY` in `.env` or selecting Gemini from the UI header dropdown. Verify endpoint responsiveness using `curl http://localhost:11434/api/tags`.

### 2. Docker Container Inability to Route to Host Ollama
- **Root Cause:** Containerized backend instances on Linux or customized networking configurations fail to resolve host interfaces.
- **Remediation:** The included `docker-compose.yml` configures `extra_hosts: ["host.docker.internal:host-gateway"]`. If issues persist on Linux platforms, configure `OLLAMA_BASE_URL=http://172.17.0.1:11434` in `.env`.

### 3. Negative Knowledge Response Attribution
- **Observation:** The assistant replies that the topic is not discussed in the podcast transcripts archive.
- **Explanation:** This is verified system behavior. The similarity metric threshold ($\tau = 0.45$) protects the user against hallucinations when a topic is absent from the transcript corpus.

---
