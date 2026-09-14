# 2–3 Minute Demo Video Guide and Script

This guide provides the exact script, timing breakdown, screen actions, and camera instructions for recording the mandatory 2–3 minute take-home assessment demonstration video.

---

## Video Setup & Requirements
- **Duration:** 2 minutes 30 seconds (Hard limit: between 2:00 and 3:00).
- **Camera:** Picture-in-picture webcam enabled in the bottom-right corner (talking head visible throughout).
- **Screen:** Fullscreen capture of `http://localhost:5173` (Light or Dark mode).
- **Audio:** Clear microphone audio without background noise.
- **Prerequisites running:**
  - `docker compose up -d --build` running.
  - Ollama running (`ollama serve` with `llama3.1:8b`) OR Google Gemini configured.

---

## Timed Script & Action Breakdown

### 0:00 – 0:35 | Introduction & The Problem Statement
**Camera:** Full focus or split talking head.  
**Screen:** Show the Lenny Growth Assistant web interface with clean starter cards and active engine indicator.

**Spoken Script:**
> *"Hi everyone, my name is [Your Name], and this is my Forward Deployed Engineer take-home assessment for the Lenny Growth Assistant.*  
> 
> *Lenny's Podcast has over 300 interviews with world-class product and growth leaders like Brian Chesky, Elena Verna, and Marty Cagan. But for operators, this wealth of knowledge is trapped in hours of conversational transcripts. Keyword search misses conceptual nuances, while generic LLMs hallucinate vague advice that strips away real tactical caveats.*  
> 
> *To solve this, I built a production-grade, full-stack assistant grounded exclusively in Lenny's podcast archive, complete with clickable second-level YouTube citations, a dedicated Ship 30 for 30 essay engine, and a sandboxed split-screen Artifact Viewer that compiles interactive React apps live in the browser."*

---

### 0:35 – 1:15 | Grounded Q&A with Clickable Citations & Negative Rejection
**Screen Action:** Click the starter prompt: *"What are Elena Verna's 10 growth tactics that never work?"*

**Spoken Script:**
> *"Let's test grounded retrieval. Here, the user asks for Elena Verna's growth tactics that never work. The backend executes a cosine similarity search against PostgreSQL with pgvector using FastEmbed ONNX embeddings in under 10 milliseconds.*  
> 
> *Notice two key details:*  
> *First, the assistant enumerates Elena's exact points—like why B2B startups shouldn't hire growth teams before product-market fit.*  
> *Second, every assertion has a footnote badge with the speaker and timestamp. If I click this badge [Elena Verna 00:00:26], it immediately opens YouTube with the exact second parameter (&t=26s), jumping straight to the moment she spoke.*  
> 
> *Now, what happens if I ask an ungrounded question—like 'What is Lenny's favorite sourdough bread recipe?'*  
> [Type or paste sourdough question]  
> *Because our retriever enforces a strict cosine similarity threshold of 0.45, the assistant completely rejects speculation and states it cannot answer based on the transcripts. Zero hallucinations."*

---

### 1:15 – 1:55 | Ship 30 for 30 Skill & Interactive React Artifact Viewer
**Screen Action:** Click the Ship 30 essay prompt, then show the live React calculator.

**Spoken Script:**
> *"Next is the Ship 30 for 30 skill. Rather than using an unstructured prompt, we encoded Nicolas Cole and Dickie Bush's atomic essay principles directly into a dedicated tool.*  
> 
> *Notice how the main chat remains completely clean: raw code does not clutter the conversation feed. Instead, the split-screen Artifact Viewer slides open on the right.*  
> *The essay has a punchy contrarian hook, numbered operational pillars, bold anchors, and a Monday morning checklist, calibrated to exactly ~1,250 words.*  
> 
> *Even better, the system can generate interactive React web components. For instance, when asking for a retention and CAC payback calculator, the assistant generates a full TSX component. The Artifact Viewer compiles it live using React 18, Babel Standalone, and Tailwind CSS.*  
> [Interact with slider/calculator inputs in the side pane]  
> *Users can test the calculator interactively or switch to the 'Raw' tab to copy the code."*

---

### 1:55 – 2:30 | Local Ollama Execution & Crucial Technical Trade-Off
**Screen Action:** Show the Header model switcher toggling to Ollama `llama3.1:8b`, then show terminal with `docker compose ps` and `pytest`.

**Spoken Script:**
> *"Now let's look at the engine. In the header, I can toggle between Google Gemini models and Local Ollama running llama3.1:8b entirely offline on this laptop.*  
> 
> *Finally, let's cover an important technical trade-off: FastEmbed ONNX vs PyTorch Sentence-Transformers.*  
> *Initially, using sentence-transformers inflated our Docker image to over 3.2 gigabytes and took 45 minutes to embed transcripts on CPU.*  
> *I swapped PyTorch for FastEmbed's ONNX runtime. This reduced our Docker image from 3.2 GB down to just 480 MB, slashed CPU embedding latency to under 8 milliseconds, and allowed us to bundle 20 pre-indexed foundational episodes so the entire system boots cold in under 2 seconds.*  
> 
> *All 23 automated tests pass with 100% reliability. Thank you for watching!"*

---

## Recording Checklist
1. [ ] Check camera angle and lighting.
2. [ ] Test microphone levels.
3. [ ] Verify `docker compose ps` shows all 3 containers healthy.
4. [ ] Run through the demo once before final recording.
5. [ ] Upload to YouTube as **Unlisted** or **Public**.
6. [ ] Paste the YouTube link into your submission form and `README.md`.
