# Design Document: The Lenny Growth Assistant

## 1. Design Philosophy: Anti-Slop Principles

This application adopts the design vocabulary defined by Impeccable (`impeccable.style`). Generative AI tools often default to predictable design patterns: purple-tinted shadows, gratuitous gradient borders, cards nested inside cards, low-contrast gray text on dark surfaces, and meaningless status chips. 

We deliberately reject those patterns:

1. **High Contrast and Legible Typography:** Text uses system-level modern typefaces (`Inter` for body copy, `JetBrains Mono` for code and metadata). Body copy stays at an accessible contrast ratio (minimum 7:1 against background), not faint gray.
2. **Restraint Over Decoration:** Borders are crisp single-pixel rules. Surface colors are strictly functional (canvas, elevated panel, subtle hover). We do not use rainbow gradients or glowing neon buttons.
3. **Information Density with Breathing Room:** Dense data (citations, episode timestamps, model status) is organized into clear tabular and inline formats rather than bloated floating cards.
4. **No Simulated Complexity:** When the agent runs a search, the UI shows real, functional status indicators ("Searching 25 indexed episodes..."), not fake randomized loading copy or pulsating circular animations.

## 2. Information Architecture

The interface uses a two-column responsive split-pane layout:

```
+-----------------------------------------------------------------------------+
| Header: Brand ("Lenny Growth Assistant") | Model Indicator | Health Status  |
+-----------------------------------------------------------------------------+
| Sidebar (260px)  | Conversation Pane (Flex-1)       | Artifact Viewer (45%) |
| - New Chat       | - Message Stream                 | - Title & Meta Header |
| - Sessions List  |   * User Turn                    | - View Toggle (Render |
| - Ingestion Info |   * Assistant Turn               |   vs Raw Markdown)    |
| - Quick Prompts  |     - Answer body                | - Sandboxed iframe or |
|                  |     - Source citations           |   Markdown container  |
|                  |     - "View Artifact" trigger    | - Copy / Export CTA   |
|                  | - Input Bar with Send Button     |                       |
+-----------------------------------------------------------------------------+
```

### 1. Left Sidebar (Collapsible)
- **Session Management:** Grouped by recency (Today, Previous 7 Days). Clicking a session loads persisted conversation turns from PostgreSQL.
- **Corpus Summary:** Displays count of indexed episodes and chunks. Includes a direct button or indicator to trigger background re-indexing.
- **Curated Starter Prompts:** Grounded questions that demonstrate specific episode retrieval (Brian Chesky on founder mode, Elena Verna on growth anti-patterns, Shreyas Doshi on high-leverage product decisions).

### 2. Main Conversation Pane
- **Header Status Strip:** Displays active model provider (`Ollama: llama3.1:8b`, `Claude: claude-3-5-sonnet`, or `OpenAI: gpt-4o`). Shows a live health dot (green for operational, amber for degraded, red for offline).
- **Message List & Clean Conversation Flow:** User messages align to the right with clean dark surfaces; assistant responses align to the left. When the assistant generates code or artifacts (HTML, React, Markdown), the raw code block is extracted and stripped from the chat message bubble. The chat remains clean and conversational, presenting only the narrative summary and an inline Artifact Callout card.
- **Citation Badges:** Footnote-style chips beneath responses (`[Elena Verna 00:00:26]`). Clicking a badge expands the transcript snippet and provides a direct YouTube link with the exact start timestamp.
- **Artifact Callout:** When the assistant generates a Ship 30 essay, interactive React tool, or structured framework, it renders a dedicated inline card ("React Component: CAC Payback Calculator" or "Ship 30 Essay: 1,248 words") with an "Open in Viewer" button.
- **User Prompt Controls:** Hovering beneath any user message reveals action buttons:
  - **Edit:** Opens an inline textarea with Save/Send (Enter) and Cancel (Esc) shortcuts.
  - **Edit in Box:** Loads the prompt into the bottom composer input box for editing.
  - **Resend:** Re-submits the prompt immediately to test alternate models or re-evaluate responses.
  - **Copy:** Copies the raw prompt text to the clipboard with visual confirmation.

### 3. Right-Hand Artifact Viewer (Claude Artifacts Pattern)
- Slides out beside the conversation when an artifact is generated or selected.
- Supports resizing and closing.
- Three multi-modal artifact types:
  - **Markdown Documents & Ship 30 Essays:** High-contrast rendered typography with headings, bold anchors, and checklists.
  - **Executable HTML5/CSS Snippets:** Self-contained web components rendered in a sandboxed iframe.
  - **Interactive React Web Pages & Components:** Self-contained React 18 applications compiled live in-browser via Babel Standalone and styled with Tailwind CSS CDN. Includes full support for React hooks (`useState`, `useEffect`, `useMemo`, `useCallback`), interactive inputs, stateful recalculations, and runtime error boundary traps.
- Two view modes:
  - **Preview:** Sandboxed live execution or rendered Markdown.
  - **Raw:** Monospace code view with syntax styling and one-click clipboard copying.
- Header bar includes artifact title, type badge, word count badge, Preview/Raw view toggles, and copy button.

## 3. Interaction States

### Empty State
When the user opens a new session, the conversation pane does not display a blank void. It displays:
- A clear heading: "Ask Lenny's Podcast Archive".
- A subhead explaining what the assistant does: "Grounded in 300+ real operator interviews. All answers cite episode timestamps."
- Three actionable starter cards:
  1. *Tactical Growth:* "What are Elena Verna's 10 growth tactics that never work?"
  2. *Product Strategy:* "How does Brian Chesky run product reviews and single roadmaps at Airbnb?"
  3. *Ship 30 Essay:* "Draft a Ship 30 for 30 essay on why performance marketing fails to create accumulating advantages."

### Loading and Streaming State
- During retrieval: A subtle status line below the input indicates "Searching transcript embeddings...".
- During generation: Tokens stream into the assistant bubble via Server-Sent Events (SSE). If an artifact is detected mid-stream, a live "Generating artifact in viewer..." indicator appears while code is excluded from the chat text.
- Auto-scroll behavior: The window auto-scrolls down as new tokens arrive. If the user scrolls up manually to inspect earlier text, auto-scroll pauses immediately until the user scrolls back to the bottom.

### Error and Degraded States
- **Ollama Offline:** If local Ollama is selected but unreachable, the UI displays a structured warning: "Ollama is unreachable at http://localhost:11434. Please run `ollama serve` and ensure model `llama3.1:8b` is pulled."
- **Empty Retrieval:** If a query returns no matching chunks above the similarity threshold, the assistant explicitly states: "I searched the episode transcripts, but did not find sufficient evidence to answer this question accurately."
- **DB Connection Loss:** The header health indicator turns red, and an actionable banner explains that session saving is temporarily offline.

## 4. Security Model for Artifact Viewer

Treating generated code and HTML as untrusted is a mandatory requirement. If an LLM generates user-supplied HTML, CSS, or JavaScript, rendering it directly inside the host DOM exposes the application to Cross-Site Scripting (XSS), token theft, and DOM tampering.

### Sandboxed iframe Architecture

All dynamic HTML and React artifacts are rendered strictly inside an isolated sandboxed `<iframe>`:

```html
<iframe
  srcdoc="<!DOCTYPE html><html><head><meta http-equiv='Content-Security-Policy' content=&quot;default-src 'none'; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' 'unsafe-eval' https:; font-src https: data:; img-src data: https:;&quot;><script src='https://cdn.tailwindcss.com'></script><script src='https://unpkg.com/react@18/umd/react.production.min.js'></script><script src='https://unpkg.com/react-dom@18/umd/react-dom.production.min.js'></script><script src='https://unpkg.com/@babel/standalone/babel.min.js'></script></head><body><div id='root'></div><script type='text/babel'>...</script></body></html>"
  sandbox="allow-scripts"
  referrerpolicy="no-referrer"
  loading="lazy"
  class="artifact-sandboxed-iframe"
/>
```

### Security Matrix

| Attribute / Policy | Setting | Reason |
| :--- | :--- | :--- |
| `sandbox="allow-scripts"` | Allowed | Permits internal interactive scripts and React runtime event handlers inside the preview. |
| `allow-same-origin` | **BLOCKED** | Crucial defense: Without this, the iframe cannot access the parent window's `localStorage`, cookies, or session storage. |
| `allow-top-navigation` | **BLOCKED** | Prevents generated scripts from redirecting the parent application window. |
| `allow-popups` | **BLOCKED** | Prevents malicious popups or phishing modals. |
| `allow-forms` | **BLOCKED** | Disables unauthorized form submission to external targets. |
| `Content-Security-Policy` | `default-src 'none'; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' 'unsafe-eval' https:; font-src https: data:; img-src data: https:;` | Strictly limits network access. Even if script execution is allowed, any attempt to `fetch()`, `XMLHttpRequest`, or open WebSocket connections to an exfiltration server is blocked by the browser. |

## 5. Accessibility and Responsive Behavior

- **Contrast:** Every text element meets or exceeds WCAG 2.1 AA standards (minimum 4.5:1 for body copy, 3:1 for large text).
- **Keyboard Navigation:** All interactive elements (prompts, citation badges, sidebar items, copy buttons) are navigable using standard Tab and Enter / Space keystrokes with visible focus outlines.
- **Screen Reader Announcements:** The streaming text container uses `aria-live="polite"` so screen readers announce incoming assistant responses without interrupting current speech.
- **Responsive Breakpoints:**
  - Desktop (>1100px): Three panes (Sidebar 260px, Chat flexible, Artifact 45%).
  - Tablet (768px - 1100px): Collapsible sidebar as overlay; Artifact pane overlays 50% or toggles into view.
  - Mobile (<768px): Full-width conversation pane; Artifact viewer opens as a full-screen drawer.
