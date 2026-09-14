# Product Requirements Document: The Lenny Growth Assistant

## 1. Overview and Problem Statement

Growth teams, product managers, and startup operators constantly make tactical decisions under pressure: setting up activation funnels, restructuring product teams, choosing between brand and performance marketing, or diagnosing why an onboarding flow fails. 

Lenny's Podcast has accumulated more than 300 in-depth interviews with operators like Brian Chesky, Elena Verna, Shreyas Doshi, and Marty Cagan. This archive contains concrete, real-world case studies and frameworks. However, the archive is largely inaccessible during day-to-day work:
1. Searching 300+ two-hour transcripts by keyword is clumsy and misses conceptual context.
2. Standard AI assistants give generic, watered-down advice that lacks the specific mechanics and caveats shared by guests.
3. Turning raw podcast insights into publishable team memos, executive updates, or thought leadership requires hours of manual synthesis.

The Lenny Growth Assistant solves this. It is a full-stack system that answers product and growth questions grounded exclusively in real episode transcripts, cites exact speakers and YouTube timestamps, and can turn those findings into structured Ship 30 for 30-style essays rendered directly in an isolated split-pane artifact viewer.

## 2. Target Users

### Primary: Growth Leads and Product Managers
They need answers to specific operational questions (for example, "What did Brian Chesky actually change about PM at Airbnb?" or "Why does Elena Verna argue against growth teams before product-market fit?"). They care about accuracy, attribution, and concrete tactical steps rather than generic summaries.

### Secondary: Founders and Content Creators
They want to distill podcast frameworks into structured essays and team playbooks using the Ship 30 for 30 methodology (compelling hook, skimmable structure, 1,200 to 1,500 words, clear takeaway).

### Evaluator / Hiring Team
A technical evaluator running this repository cold on a standard laptop. They will inspect architectural boundaries, model switching mechanics, retrieval precision, sandboxed security, code hygiene, and test coverage.

## 3. Success Metric

The single metric that defines whether this system works is:

**Grounded Retrieval Precision with Verifiable Attribution (Target: 100% of factual assertions backed by a clickable episode timestamp, with 0% unsupported hallucinations).**

If a user asks about an episode topic and the transcript corpus does not contain the answer, the assistant must state that the archive does not support an answer. Fabricating advice or quoting advice not present in the transcripts is considered a system failure.

Secondary operational metrics:
- Sub-200ms API retrieval latency over local pgvector embeddings.
- Full local execution capability on an 8GB to 16GB developer laptop using Ollama (`llama3.1:8b` or `qwen2.5:7b`).
- Deterministic word count adherence for the Ship 30 for 30 skill (target: 1,100 to 1,400 words, centering around 1,250 words).

## 4. What We Deliberately Cut and Why

To keep this project focused and defensible for an FDE take-home, several features were intentionally excluded:

1. **Full-Corpus Real-time Transcription / Whisper GPU Pipeline**  
   *What was cut:* Re-transcribing podcast audio from raw YouTube files.  
   *Why:* The ChatPRD repository already hosts 300+ cleaned transcripts with frontmatter and timestamps. Running Whisper on 450 hours of audio requires significant GPU compute and introduces cold-start latency. Using the existing transcript repository lets us focus on ingestion, chunking, retrieval, and synthesis.

2. **Cross-Encoder Reranking Model**  
   *What was cut:* A secondary cross-encoder reranker (such as `bge-reranker-large`) after initial vector retrieval.  
   *Why:* The transcript chunk size (around 300 to 500 tokens) combined with cosine similarity in pgvector and metadata pre-filtering yields strong relevance for this domain. Reranking adds 300ms to 800ms of CPU latency on a standard laptop without a GPU. For a corpus of several thousand chunks, vector retrieval with speaker-turn boundaries is sufficient. I would add reranking if the knowledge base expanded beyond 50,000 chunks.

3. **User Authentication and Multi-Tenant RBAC**  
   *What was cut:* Auth0, Clerk, or JWT login screens.  
   *Why:* This is an internal tool demo designed to run via Docker Compose on an evaluator's machine. Forcing an evaluator to sign up or mock authentication credentials adds friction without proving architectural capability. Sessions are isolated by persistent session IDs stored in PostgreSQL instead.

4. **Multi-Agent Swarm / LangGraph Graph Cyclic Loops**  
   *What was cut:* Orchestration graphs with multiple autonomous agents debating each other.  
   *Why:* Multi-agent loops are notoriously prone to infinite loops and timeout failures when running on local 8B parameter models. An FDE prioritizes reliability over novelty. A single deterministic orchestrator with structured tool dispatch delivers faster, more reliable results on local hardware.

## 5. Key Assumptions

1. **Host Environment:** The host system has Docker and Docker Compose installed, with at least 8GB of free system memory.
2. **Local LLM Execution:** If using the local provider, Ollama is pre-installed on the host system (`ollama serve`) with `llama3.1:8b` pulled.
3. **Cloud LLM Execution:** If using cloud providers, valid API keys for Google Gemini (`gemini-3.5-flash-lite`), Anthropic Claude, or OpenAI are supplied in `.env`.
4. **Knowledge Base Integrity:** Transcripts in the `data/` directory or pre-indexed bundles contain YAML frontmatter and speaker timestamps adhering to universal podcast conventions.
5. **Browser Security Sandboxing:** Evaluator browsers respect standard HTML5 `iframe[sandbox]` constraints and Content Security Policy directives.

## 6. Scope and Core Requirements

### In Scope (Hard Requirements)
- **FastAPI Backend:** Strict Pydantic v2 schemas for all payloads, typed error envelopes (no unhandled 500s), and a `/health` endpoint validating database and LLM provider connectivity.
- **Multi-Model Provider Switcher:** Runtime toggle supporting local Ollama (`llama3.1:8b`) and cloud providers (Google Gemini with `gemini-3.5-flash-lite`, Anthropic Claude 3.5 Sonnet, OpenAI GPT-4o) controlled via environment variable or the frontend header selector.
- **Knowledge Base and RAG Pipeline:** Universal ingestion parser handling parenthetical timestamps, square brackets, continuation turns, un-timestamped interpolation, and sponsor read filtering. Vector search via PostgreSQL `pgvector` with HNSW indexing and FastEmbed ONNX embeddings. Citations include guest, episode title, and clickable YouTube URL with `&t=` timestamp.
- **Grounded Chat Surface:** Preserves session history across turns, streams tokens via Server-Sent Events (SSE), and explicitly declines questions outside the transcript knowledge base ($\tau = 0.45$).
- **Claude-Style Clean Conversation:** Raw artifact code (`html`, `react`, `markdown`) is extracted cleanly from chat message bubbles, leaving the chat conversation scannable while rendering artifacts exclusively in the side viewer.
- **Interactive Prompt Controls:** Inline editing, "Edit in Box", resend, and copy buttons below user prompts.
- **Ship 30 for 30 Content Skill:** Dedicated agent skill applying Nicolas Cole and Dickie Bush writing mechanics (headline, hook, problem, skimmable list body, actionable takeaway) and Impeccable tone principles. Produces essays near 1,250 words.
- **Sandboxed Multi-Modal Artifact Viewer:** Split-pane rendering for:
  - Markdown essays & documents (rendered vs raw).
  - Executable HTML5/CSS components.
  - Interactive React web components (compiled live via React 18 UMD + Babel Standalone + Tailwind CSS CDN).
  - Sandboxed iframe with locked-down attributes (`sandbox="allow-scripts"`) and strict Content Security Policy (CSP) blocking parent window access and network exfiltration.
- **Deployment and Testing:** Docker Compose setup, `.env.example`, structured JSON logging, 23 passing automated pytest tests, and a comprehensive manual UI test plan.

### Out of Scope
- Automatic YouTube audio downloading and transcription.
- Social media auto-posting (X/Twitter, LinkedIn API integration).
- User billing, subscription tiers, and paid seats.

## 7. User Journeys

### Journey 1: Grounded Research with Timestamp Verification
1. User enters: "What does Brian Chesky say about managing by influence vs micromanagement?"
2. System retrieves relevant chunks from Brian Chesky's episode (`episodes/brian-chesky/transcript.md`).
3. Assistant returns a synthesized answer detailing Chesky's view on "being in the details" vs "telling people what to do."
4. Response includes footnote citations: `[Brian Chesky - Brian Chesky's new playbook (00:00:00)](https://www.youtube.com/watch?v=4ef0juAMqoE&t=0s)`.
5. User clicks the citation and jumps directly to the exact moment in the YouTube video.

### Journey 2: Producing a Ship 30 for 30 Essay Artifact
1. User enters: "Draft a Ship 30 essay based on Elena Verna's advice on why early-stage startups should not hire a growth team."
2. Assistant detects the essay creation intent and activates the `generate_ship30_essay` skill.
3. System retrieves Elena Verna's transcript segments on product-market fit, distribution, and growth team anti-patterns.
4. Assistant generates a structured essay (~1,250 words) with:
   - Hook: Short, contrarian assertion.
   - Core premise: Why distribution cannot be outsourced before product-market fit.
   - Three actionable pillars with examples from Amplitude and Dropbox.
   - Specific takeaway checklist for early-stage founders.
5. System emits the essay as an artifact payload.
6. The Artifact Viewer slides open on the right pane, rendering the essay with clear typographic hierarchy.
7. User can toggle between rendered view and raw Markdown, or copy with one click.

### Journey 3: Generating an Interactive React Web Component
1. User enters: "Create an interactive React calculator for CAC payback and user retention based on Elena Verna's growth model."
2. Assistant retrieves Elena Verna's retention metrics and formulates a complete, self-contained React component with stateful sliders, inputs, and Tailwind CSS.
3. The main chat displays an introductory summary and an Artifact Callout Card ("React Component: CAC Payback Calculator"); raw code is kept out of the main chat feed.
4. The Artifact Viewer automatically opens in the right pane, compiling the TSX live via Babel Standalone and mounting the component.
5. The user can interact with the calculator (adjusting CAC, ARPU, and churn) and switch to the **Raw** tab to copy the code.

### Journey 4: Graceful Handling of Unsupported Queries
1. User enters: "What is Lenny's favorite recipe for sourdough bread?"
2. Vector retrieval returns chunks below the similarity threshold ($\tau = 0.45$).
3. Assistant responds: "I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."
4. No hallucinated recipes or speculative answers are returned.

## 8. Acceptance Criteria

| Feature | Acceptance Criteria |
| :--- | :--- |
| **Model Toggle** | Switching `LLM_PROVIDER=ollama` to `LLM_PROVIDER=gemini` switches provider without code edits. UI header allows dynamic per-session switching. |
| **Health Check** | `GET /health` returns status code 200 with JSON payload reporting DB status (`connected`), LLM status (`reachable`), and index metrics. Returns 503 if DB or active LLM is down. |
| **Retrieval Accuracy** | Every factual claim references a verified episode slug, guest, and timestamp. Citation URLs include valid `&t=` offsets. |
| **Negative Retrieval** | Questions on topics outside the corpus trigger an explicit rejection rather than hallucination. |
| **Ship 30 Skill** | Output includes hook, problem, numbered headers, explanation, and takeaway. Total length is within 1,100 to 1,400 words. |
| **React & HTML Artifacts** | Interactive React and HTML components render live in the side viewer. Raw code is excluded from the main chat feed. |
| **Artifact Security** | Artifacts render in an iframe with `sandbox="allow-scripts"` without `allow-same-origin`. Script attempting `window.parent.location` or `fetch('https://evil.com')` is blocked by CSP. |
| **Prompt Controls** | User prompts include inline editing, "Edit in Box", resending, and copying actions. |
| **Persistence** | Reloading the browser preserves chat sessions, message history, and associated artifacts in PostgreSQL. |
| **Docker Compose** | Running `docker compose up -d --build` launches PostgreSQL with pgvector, FastAPI backend, and React frontend without manual intervention. |

## 9. Risk Analysis and Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| Local Ollama model runs slowly or runs out of RAM on 8GB laptops. | High | Medium | Default to `llama3.1:8b` or `qwen2.5:7b` with 4-bit quantization. Include explicit instructions in README on how to configure Ollama memory limits or fallback to Google Gemini (`gemini-3.5-flash-lite`). |
| Full ingestion of 303 episodes takes too long during an initial demo run. | High | High | Seed the database with a pre-indexed vector bundle of 20 core growth episodes (Brian Chesky, Elena Verna, Shreyas Doshi, Casey Winters, Marty Cagan, etc.). Provide an asynchronous CLI command (`python -m app.ingest --all`) for background indexing of the remainder. |
| LLM generates malicious HTML/JavaScript inside an artifact. | Critical | Low | Isolate iframe execution: set `sandbox="allow-scripts"` without `allow-same-origin` or `allow-top-navigation`, and enforce a strict CSP (`default-src 'none'; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' 'unsafe-eval' https:;`). |
| Database connection drops during long streaming responses. | Medium | Low | Use SQLAlchemy connection pooling with health pings (`pool_pre_ping=True`) and structured error recovery in FastAPI. |

## 10. Implementation Plan & Milestones

The project was executed across five structured implementation phases:

- **Milestone 1: Data Ingestion & RAG Foundation**
  - Built universal YAML frontmatter and multi-pattern transcript parser (`app/rag/parser.py`).
  - Integrated FastEmbed ONNX embeddings (`BAAI/bge-small-en-v1.5`) and PostgreSQL pgvector HNSW indexing.
  - Implemented cosine distance retrieval with negative similarity rejection threshold ($\tau = 0.45$).
  - Pre-computed seed bundle for instant (<2s) cold boot.

- **Milestone 2: Multi-Model Agent Orchestrator & Skills**
  - Implemented Anthropic Agent tool-calling pattern (`Observe -> Think -> Act -> Synthesize`).
  - Implemented multi-provider abstraction: Local Ollama, Google Gemini (`gemini-3.5-flash-lite`), Anthropic Claude, OpenAI.
  - Built dedicated Ship 30 for 30 Content Skill enforcing rhetorical principles and word count calibration (~1,250 words).

- **Milestone 3: Split-Screen Frontend & Sandboxed Artifact Viewer**
  - Developed React 18 + Vite frontend with bespoke high-contrast dark theme (following Impeccable principles).
  - Built Claude-style split-pane Artifact Viewer with Rendered vs Raw toggle.
  - Enforced dual-layer security: `iframe[sandbox="allow-scripts"]` with null origin isolation and CSP headers.

- **Milestone 4: Interactive React Component Generation & Clean Chat**
  - Integrated React 18 UMD, Babel Standalone, and Tailwind CSS CDN for client-side live compilation of interactive React pages and widgets.
  - Cleaned main chat feed to strip code dumps, leaving only conversational narratives and Artifact Callouts.
  - Added prompt editing, resending, and clipboard controls.

- **Milestone 5: Production Readiness & Verification**
  - Created 23 automated pytest tests covering API contracts, RAG precision, negative rejection, security policies, and agent routing.
  - Docker Compose orchestration for single-command deployment.
  - Authored comprehensive documentation: PRD, Architecture, Design, Manual Test Plan, and Video Script.
