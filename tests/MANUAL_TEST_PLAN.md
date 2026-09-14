# Manual UI Verification & Test Plan

This manual test plan provides step-by-step verification instructions for evaluators inspecting **The Lenny Growth Assistant** web application (`http://localhost:5173`).

---

## Prerequisites
1. Stack running via Docker Compose (`docker compose up -d --build`) or local dev server.
2. Open browser to `http://localhost:5173`.
3. Verify the Header shows `GEMINI (gemini-3.5-flash-lite)` or `OLLAMA (llama3.1:8b)` with a green operational status indicator.

---

## Test Scenario 1: System Readiness & Health Diagnostics

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 1.1 | Open `http://localhost:8000/health` in a browser or curl | HTTP 200 OK with JSON response: `status: "healthy"`, `database: "connected"`, `indexed_episodes: 20`, `indexed_chunks: 1441`. | [ ] |
| 1.2 | Inspect the Header engine pill on `http://localhost:5173` | Shows active model and provider with green status indicator. | [ ] |

---

## Test Scenario 2: Grounded Q&A with Clickable YouTube Citations

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 2.1 | Click the starter prompt: *"What are Elena Verna's 10 growth tactics that never work?"* (or type it into the composer) | Tokens stream into the assistant bubble via Server-Sent Events (SSE). | [ ] |
| 2.2 | Inspect the synthesized response | The assistant enumerates Elena Verna's specific tactical growth caveats directly from the podcast transcript. | [ ] |
| 2.3 | Inspect the citation badges beneath the message | Footnote badges appear, e.g. `[Elena Verna 00:00:26]`. | [ ] |
| 2.4 | Click any citation badge | Opens the exact YouTube episode in a new tab with the start parameter pre-populated (e.g., `&t=26s`). Playback starts at that exact second. | [ ] |

---

## Test Scenario 3: Negative Retrieval Guardrail (Anti-Hallucination)

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 3.1 | In the composer, ask an ungrounded question: *"What is Lenny's favorite sourdough bread recipe?"* | Assistant performs vector search and identifies that cosine similarity is below threshold ($\tau = 0.45$). | [ ] |
| 3.2 | Verify assistant response | Assistant explicitly states: *"I searched the podcast transcripts archive, but this topic is not discussed in the available episodes. I cannot answer based on Lenny's Podcast transcripts."* Zero hallucinated recipes are returned. | [ ] |

---

## Test Scenario 4: Ship 30 for 30 Content Skill & Split-Pane Artifact Viewer

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 4.1 | Click the starter prompt: *"Draft a Ship 30 for 30 essay on why performance marketing fails to create accumulating advantages."* | The agent dispatches the `generate_ship30_essay` skill tool. | [ ] |
| 4.2 | Inspect the main chat feed | Main chat displays an introductory summary and an inline Artifact Callout card ("Ship 30 Essay: ~1,250 words") with an "Open in Viewer" button. Raw essay code does NOT clutter the main chat. | [ ] |
| 4.3 | Inspect the right-hand Artifact Viewer | The side panel slides open beside the chat: includes Contrarian Hook, Core Problem, Numbered Pillars with bold anchors, and a Monday Morning Checklist. | [ ] |
| 4.4 | Inspect the word count badge | Badge shows word count close to ~1,250 words (within 1,100 to 1,400 words). | [ ] |
| 4.5 | Toggle between "Preview" and "Raw" tabs | "Preview" renders formatted Markdown; "Raw" displays monospace Markdown syntax. | [ ] |
| 4.6 | Click the "Copy" button | Button icon briefly confirms copied state; clipboard contains raw markdown. | [ ] |

---

## Test Scenario 5: Interactive React Web Component Generation & Live Sandbox Execution

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 5.1 | Enter prompt: *"Create an interactive React retention and CAC payback calculator based on Elena Verna's metrics."* | The agent generates an interactive React component (`type="react"`). | [ ] |
| 5.2 | Inspect the main chat feed | The chat message displays only the conversational intro and an Artifact Callout Card ("React Component: CAC Payback Calculator"). Raw TSX code is stripped from chat. | [ ] |
| 5.3 | Inspect the Artifact Viewer | The component compiles live in-browser via Babel Standalone + React 18 + Tailwind CSS. | [ ] |
| 5.4 | Interact with the component | Sliders, inputs, and state buttons respond dynamically to user interaction inside the sandboxed iframe. | [ ] |
| 5.5 | Switch to "Raw" view | Raw React/TSX source code is visible with one-click copy. | [ ] |

---

## Test Scenario 6: User Prompt Controls (Inline Edit, Edit in Box, Resend, Copy)

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 6.1 | Hover cursor below any user message | An action bar appears with **Edit**, **Edit in Box**, **Resend**, and **Copy**. | [ ] |
| 6.2 | Click **Edit** | The user bubble transforms into an inline textarea with Save/Send and Cancel buttons. | [ ] |
| 6.3 | Modify text and press Enter (or click Send) | The updated query is sent immediately as a new message. | [ ] |
| 6.4 | Click **Edit in Box** | The prompt text is loaded directly into the bottom composer input for editing. | [ ] |
| 6.5 | Click **Resend** | Re-sends the exact prompt to test alternate model responses. | [ ] |
| 6.6 | Click **Copy** | Copies prompt text to clipboard with a checkmark badge. | [ ] |

---

## Test Scenario 7: Dynamic Model Switching

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 7.1 | In the Header, click the model dropdown selector | Dropdown lists Local Ollama (`llama3.1:8b`) and Google Gemini tiers (`gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`). | [ ] |
| 7.2 | Select a different model (e.g., `gemini-2.5-flash`) | Header badge updates immediately. Subsequent chat queries execute against the newly selected model. | [ ] |

---

## Test Scenario 8: Security Sandbox Enforcement (CSP & Origin Isolation)

| Step | Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 8.1 | Inspect the Artifact Viewer iframe in Chrome DevTools Elements tab | `sandbox="allow-scripts"` is present. `allow-same-origin` and `allow-top-navigation` are strictly absent. | [ ] |
| 8.2 | Check the Console tab inside the iframe context | The document origin is `null` (unique opaque origin). Any attempt to access `window.parent.localStorage` throws a SecurityError. | [ ] |
| 8.3 | Inspect CSP header | `default-src 'none'` prevents outbound network exfiltration. | [ ] |
