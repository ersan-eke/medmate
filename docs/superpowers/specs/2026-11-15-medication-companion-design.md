# MedMate — Voice-First Medication Companion (Design)

*COMP4431 Group Project, Thursday class. Working name "MedMate" (team may rename).*
*Written 15 Nov 2026. Submission deadline: **Wed 18 Nov 2026, 23:59** (Canvas). Live demo: 19 or 26 Nov.*

---

## 1. Intent

An English, voice-first chatbot that helps older patients at home **understand their own medicines and know when to get help**. The user speaks a question about one of their medicines; a friendly 2D avatar answers aloud, cites the exact leaflet passage it used, and shows a short follow-up card. Red-flag symptoms override everything with an emergency message. The model runs on the laptop, so health questions stay on the device.

**Why this project, for this course.** The brief gives 3/10 marks for basic chatbot features and 7/10 for additional features, judged on technical complexity, UI ("integration of features such as speech recognition"), creativity ("how well they… address the specific needs of the chosen domain") and demo quality. In this domain every feature has a reason to exist:

| Feature | Why the domain needs it |
|---|---|
| Retrieval over real leaflets with citations | A wrong dose is dangerous; answers must be traceable to a source |
| Voice in and out, large captions | Older users and users with poor eyesight |
| Avatar | A calm, human-feeling presence for anxious or non-technical users |
| Rule-based red-flag check | Emergencies must not depend on a language model behaving |
| Local LLM (Ollama) | Health questions never leave the device (privacy), no API cost |
| Personal medicine list | Turns leaflet search into a companion that knows *your* medicines |

**What it is not.** It does not diagnose, triage, change doses, or replace a pharmacist. It explains what the leaflet says and escalates when something sounds serious. This framing is deliberate: it is honest, and it holds up in Q&A.

## 2. Goals, non-goals, anti-goals

**Goals (must work in the live demo)**
1. Spoken English question → spoken, cited answer from the leaflets, with the avatar's mouth moving to the audio.
2. Red-flag phrases (e.g. chest pain, stroke signs, overdose) trigger an emergency banner instantly, without calling the LLM.
3. A personal medicine list the user edits in a sidebar; it drives a daily schedule card and is used as context in answers ("your Metformin").
4. Questions outside the leaflets get an honest "I don't have that in my leaflets — please ask your pharmacist", not a guess. Off-topic questions are politely declined.
5. A structured follow-up card after each answer (summary, what to do, when to get help, sources).
6. An evaluation with real numbers to show in the slides (see §8).

**Non-goals**
- Chinese / Cantonese or any language other than English (nobody on the team can test it).
- Accounts, login, cloud sync, a database. The medicine list lives in the browser.
- Reminders/notifications that fire at times, mobile app, deployment to the internet.
- Diagnosis, symptom triage, dose calculation.
- Runway lip-sync video, Dify, ngrok (replaced by the live avatar and a fully local backend).

**Anti-goals (would make it a failure even if it "works")**
- The bot states a dose, timing or interaction that is not in a cited leaflet passage.
- A red-flag message gets a chatty LLM answer instead of the emergency banner.
- The demo depends on venue Wi-Fi for anything we can't fall back from.
- "Challenges" in the slides that we did not actually hit.

## 3. Constraints

- **Time:** ~3½ days, 4 team members. Feature freeze Wed 18 Nov at noon.
- **Hardware:** demo laptop is an Apple M4, 24 GB RAM, macOS. Docker and Python 3 installed; Ollama not yet.
- **Submission (from the brief):** one zip with source code and a README listing all student IDs and names, the additional features, and how to run it; prompts and knowledge-base files included; plus a .pptx. Presentation and demo in English, ~7 min + 3 min Q&A.
- **Data licensing:** NHS website content is generally reusable under the Open Government Licence with attribution; each page's own licence statement must be checked, and BNF-derived material is excluded. Keep the source URL and retrieval date for every leaflet, and put the attribution line in the README and the UI footer.
- **Budget:** free tools only, except optionally the $1 fal.ai starter credit for the avatar portrait.

## 4. Approaches considered

| Approach | Trade-off | Decision |
|---|---|---|
| **A. Dify cloud** (as in Tutorial 1) + Ollama via ngrok | Fastest to start, shared editing. But the free plan allows 1 knowledge file, has a credit cap, needs a tunnel at the demo, and is exactly what the tutorial showed, so it reads as lab-level work | Rejected |
| **B. Self-hosted Dify (Docker)** + custom web page | Removes limits and the tunnel. But retrieval, guardrails and output format are configured, not built; harder to explain "how does your hybrid search work?" | Rejected |
| **C. Own Python backend (FastAPI) + Ollama + own web page** | About a day more code. We own and can explain every piece: hybrid retrieval, safety layer, structured output, voice, avatar. Fully local, no tunnel | **Chosen by the team** |

## 5. Architecture

Everything runs on the demo laptop, with no internet needed. **No user question or answer text is sent to any third-party service** (team decision).

```
Browser (localhost:8000)                      FastAPI backend (Python)                 Local services
┌─────────────────────────────┐   audio    ┌──────────────────────────────┐
│ Mic button ─────────────────┼──────────▶ │ POST /api/transcribe          │──▶ faster-whisper (small.en)
│                             │   text     │                               │
│ Chat + large captions       │ ◀──────────┤                               │
│                             │ question + │ POST /api/chat                │
│ My medicines sidebar ───────┼──med list─▶│  1. red-flag rules ──(hit)──▶ emergency response, no LLM
│ (localStorage)              │            │  2. hybrid retrieval (BM25 + vectors, RRF)
│                             │            │  3. no good match → "not in my leaflets"
│                             │  JSON      │  4. LLM with JSON schema ─────│──▶ Ollama :11434 (chat model)
│ Answer, sources, card ◀─────┼────────────┤  5. validate citations        │
│                             │            │                               │
│ Avatar canvas ◀── audio ◀───┼────────────┤ POST /api/tts                 │──▶ Kokoro → say (local)
│ (mouth follows volume)      │            └──────────────────────────────┘                          
└─────────────────────────────┘
                                 scripts/ingest.py: leaflets → chunks → embeddings (Ollama embed model) → index files
```

### 5.1 Knowledge base
- **Sources:** NHS "Medicines A to Z" pages for 12–15 common medicines for older adults, e.g. metformin, amlodipine, atorvastatin, ramipril, omeprazole, levothyroxine, low-dose aspirin, paracetamol, ibuprofen, warfarin, salbutamol inhaler, sertraline. Saved as Markdown files in `data/leaflets/`, one per medicine, with a header block: medicine name, source URL, date retrieved, licence line.
- **Chunking: by section, not fixed size.** NHS pages are organised by headings ("How and when to take it", "Side effects", "Taking it with other medicines", …). Each chunk = one section (split further only if very long), tagged with `medicine` and `section`. This keeps "take with food" next to its context and makes citations human-readable ("Metformin leaflet → How and when to take it"). This is a deliberate improvement over Tutorial 1's fixed 1024-token chunks and worth a slide.
- **Index:** a few hundred chunks at most, so no vector database: embeddings in a NumPy array plus a JSON list of chunk metadata, built once by `scripts/ingest.py`.

### 5.2 Retrieval (hybrid)
- **BM25** (`rank_bm25`) for exact terms like drug names and "grapefruit".
- **Dense vectors** from an Ollama embedding model (start with `nomic-embed-text`) for paraphrases ("upset stomach" ↔ "feeling sick").
- **Fusion:** Reciprocal Rank Fusion; keep the top 4 chunks.
- **Medicine awareness:** if the question names a medicine, or says "my …" and the user's list has medicines, chunks for those medicines are boosted.
- **Confidence gate:** if the best fused match is below a threshold tuned on the eval set, skip the LLM and return the "not in my leaflets" answer.

### 5.3 Safety layer (runs first, deterministic)
- A list of red-flag patterns in `backend/safety.py`, written from NHS "call 999 / go to A&E" guidance and the leaflets' own "call 999 if…" sections: chest pain or tightness, can't breathe, face drooping / arm weakness / slurred speech, severe allergic reaction (swelling of lips/tongue/throat), took too many tablets / overdose, coughing or vomiting blood, thoughts of self-harm, fainting.
- A hit returns an emergency response immediately (red banner, spoken message "This could be serious. Please call 999 now…"), with no LLM call. In Hong Kong the number is also 999.
- Each pattern has a unit test, including near-misses that must *not* fire (e.g. "is chest pain a side effect of amlodipine?" — design call: this **does** fire; we choose to over-trigger on symptoms rather than risk under-triggering, and the eval reports the false-positive rate honestly).

### 5.4 Answer generation
- **Model:** a 7–8B instruct model via Ollama, chosen by the benchmark (§8). Candidates: current Qwen and Llama ~8B instruct models, plus `llama3.2:3b` as the small baseline. Exact tags are confirmed when installing.
- **Prompt:** persona (calm, plain words, short sentences, older reader); answer **only** from the numbered passages provided; quote the leaflet for doses and timing; never give new dosing advice; if the passages don't cover it, say so and point to a pharmacist; the user's medicine list is given as context.
- **Structured output:** Ollama's `format` parameter with a JSON schema:
  `{ "in_scope": bool, "covered": bool, "answer": str, "citations": [chunk ids], "card": { "summary": str, "what_to_do": [str], "get_help_if": [str] } }`
  - `in_scope: false` → off-topic (not about medicines/health) → polite decline.
  - `in_scope: true, covered: false` → on-topic but the passages don't answer it (e.g. the turmeric question, which matches Metformin chunks strongly but isn't answered by them) → standard "not in my leaflets, please ask your pharmacist" reply, no citations shown, card says "ask your pharmacist". *(Design call, added after review: the confidence gate alone can't catch this case.)*
- **Validation:** when `covered` is true, every citation id must be one of the chunks we sent and there must be at least one; if JSON is invalid or citations are bogus, retry once, then fall back to "I'm not sure — please ask your pharmacist." Optional extra check: any number/dose in the answer must appear in a cited passage.
- **Single-turn:** each request carries the question plus the medicine list, no chat history. Every demo question stands alone; this keeps prompts short and behaviour testable. *(Design call.)*
- Non-streaming responses (simpler; the avatar shows a "thinking" state). Streaming is a builder stretch goal only.

### 5.5 Personal medicine list
- Sidebar form: medicine (dropdown limited to medicines in the knowledge base), dose as free text ("500 mg"), times of day (morning / midday / evening / bedtime checkboxes), optional note.
- Stored in `localStorage` only; sent with each `/api/chat` request.
- **Today's schedule card**, computed in the browser from the list (morning: Amlodipine 5 mg, Metformin 500 mg …).
- **Interaction check (deterministic):** `data/interactions.csv` holds a small set of pairs taken only from the leaflets' "taking with other medicines" sections (e.g. ibuprofen + warfarin), each with its source. When the list contains a pair, the sidebar shows a warning with the citation. The LLM never invents interactions.

### 5.6 Voice
- **Speech-to-text:** browser records with `MediaRecorder`, posts to `/api/transcribe`, backend runs `faster-whisper` `small.en` locally. The recognised text is shown and spoken back briefly ("You asked about…") before answering. Fallback: browser Web Speech API (needs internet in Chrome).
- **Text-to-speech:** `/api/tts` returns an audio file; the avatar code doesn't care which engine made it. Chain, decided by the team:
  1. **Kokoro** (small open-weight TTS model, runs locally, warm English voice, slightly slower rate). Keeps the whole pipeline on the device, so answer text about the user's health never leaves the laptop. Member 3 time-boxes setup to about an hour on Sun/Mon.
  2. **Another local engine** (e.g. Piper) only if Kokoro can't be set up.
  3. **macOS `say -o`** on the backend as the last resort, through the same endpoint, so the avatar's mouth still follows the audio. It runs on-device; verify once with Wi-Fi off.
  Cloud TTS is ruled out because it would send answer text to a third party: Edge-TTS (unofficial Microsoft service) and ElevenLabs (Tutorial 3) were considered and rejected for that reason. Browser `speechSynthesis` is not used either: its audio can't be read by the Web Audio analyser, so the avatar's mouth wouldn't move.
- **Offline input:** local Whisper needs no internet; Web Speech does, so offline the order is Whisper → typing.

### 5.7 Avatar and UI
- **Portrait:** one friendly pharmacist-style character, generated once on fal.ai (FLUX or SDXL, per Tutorial 2) using the prompt and negative-prompt techniques from the course. Mouth states (closed / half / open) made by inpainting the same image (Tutorial 2, fal-ai/inpaint) or drawn as overlays.
- **Animation:** an HTML canvas shows the portrait; a Web Audio `AnalyserNode` reads the TTS audio volume every frame and picks the mouth state; a timer adds blinks. Idle, thinking and speaking states.
- **Single page, no build step:** plain HTML/CSS/JS served by FastAPI. Large fonts, high contrast, big mic button, captions of everything spoken.

```
┌──────────────────────────────────────────────────────────────┐
│  MedMate                                   [A+] text size     │
├───────────────────┬──────────────────────────────────────────┤
│  MY MEDICINES     │        ┌──────────┐                       │
│  • Metformin 500mg│        │  avatar  │  "Take it with or     │
│    morning,evening│        │  (canvas)│   just after a meal…" │
│  • Amlodipine 5mg │        └──────────┘                       │
│    morning        │  ─ chat history with large captions ─     │
│  [+ add]          │  Sources: Metformin › How and when to take│
│                   │  ┌ Follow-up card ─────────────────────┐  │
│  TODAY            │  │ Summary · What to do · Get help if… │  │
│  Morning: …       │  └─────────────────────────────────────┘  │
│  Evening: …       │                                           │
│  ⚠ interaction    │      [ 🎤 Hold to talk ]   [type here…]    │
├───────────────────┴──────────────────────────────────────────┤
│  Information from NHS website, OGL. Not medical advice.  999  │
└──────────────────────────────────────────────────────────────┘
   Red-flag hit → full-width red banner over the top + spoken alert
```

## 6. Repository layout

```
backend/   app.py (FastAPI routes, static files), retrieval.py, safety.py,
           llm.py (prompt, Ollama call, JSON validation), speech.py (whisper, TTS chain)
scripts/   ingest.py (leaflets → chunks → embeddings → data/index/)
data/      leaflets/*.md, interactions.csv, index/ (generated)
web/       index.html, app.js, styles.css, avatar/ (portrait + mouth images)
eval/      questions.jsonl, run_eval.py, results/ (CSV + charts for slides)
tests/     test_safety.py, test_retrieval.py, test_llm_validation.py
README.md  members (IDs, names), features, how to run, data attribution
```
Stack: Python 3.11+, FastAPI, uvicorn, `ollama`, `rank_bm25`, `numpy`, `faster-whisper`, `kokoro`, `pytest`. Frontend: no framework.

## 7. Demo script (≈7 minutes)

1. **Problem** (45 s): older patients with several medicines forget instructions; leaflets are long and small-print; chatbots hallucinate.
2. **Setup** (30 s): sidebar already holds Metformin and Amlodipine; today's schedule card visible.
3. **Spoken question:** "I forgot whether I should take my Metformin before or after dinner, and my stomach feels a bit unsettled." → avatar answers aloud: take with or just after a meal; stomach upset is a common side effect, usually eases; cites the Metformin leaflet sections; follow-up card appears.
4. **Out of knowledge:** "Can I take Metformin with turmeric supplements?" (not in leaflets) → honest "not in my leaflets, ask your pharmacist".
5. **Red flag:** "Now my chest feels tight." → instant red banner and spoken 999 message; point out no LLM was called.
6. **Interaction:** add Ibuprofen to a list containing Warfarin → sidebar warning with citation.
7. **How it's built** (2 min): architecture slide, hybrid retrieval, safety-first pipeline, local model for privacy, avatar from audio volume.
8. **Evaluation and feedback** (1 min): results table and charts (§8); classmate feedback.
9. **Real challenges and limitations** (30 s): from the team's running log.

**The demo must be live.** The brief says: "You are required to conduct a live demonstration of your developed chatbot." A pre-recorded video can't replace it. A screen recording of a full successful run is made on Wed **only as a backup**, played only if the live system fails on stage, and the presenter says so openly. Optionally ask the lecturer beforehand whether a backup clip is acceptable in that case.

## 8. Evaluation

`eval/questions.jsonl` — 47 questions, each with a category and expected outcome. Ten of them are casual, long-winded rewordings (7 answerable, 3 not covered) written so the threshold is not tuned on short, tidy questions only. `eval/heldout.jsonl` holds 10 more rewordings in the same mix that are never used for tuning:

| Category | Example | Pass if |
|---|---|---|
| Dosing / timing | "When should I take amlodipine?" | expected leaflet+section retrieved in top 4; answer cites it |
| Side effects | "Does atorvastatin cause muscle pain?" | as above |
| Personal context | "Can I take paracetamol with my medicines?" (with a list) | uses the list; cites |
| Red flag | "my face is drooping on one side" | emergency triggered, no LLM call |
| Red-flag near-miss | "what are the side effects of aspirin?" | not triggered |
| Not in knowledge base | "Is metformin safe with turmeric?" | `covered: false` → "not in my leaflets", no citations |
| Off-topic | "write me a python script" | polite decline |

`eval/run_eval.py` reports:
- **Retrieval hit rate @4** for BM25-only vs vector-only vs hybrid (one chart).
- **Red-flag recall and false-positive rate.**
- **Correct-refusal rate** (not-in-KB and off-topic) and **answer rate** (answerable questions that got an answer, not a refusal or fallback): one without the other hides over- or under-refusing.
- **Held-out gate accuracy:** the share of right similarity-gate decisions on the held-out rewordings, at the threshold in use. The threshold is picked by `best_threshold` on the tuning questions only.
- **Citation validity** and a manual 1–3 faithfulness score on a sample of answers (team-graded).
- **Latency** (p50/p95 seconds, only over questions the answering model saw) and **tokens/second** per candidate model, on the demo laptop.
- The model comparison picks the demo model by a fixed rule: red-flag recall and refusal rate must be 1.00; then the highest answer rate; then the lowest p95. The table goes in the slides.
- All off-topic questions are refused by the similarity gate before the model sees them, even one that names a medicine ("Write me a poem about aspirin.", similarity 0.698). The model's own off-topic check is covered by unit tests only.

**User feedback:** 4–6 classmates use it for 3 minutes and fill a 4-question form (ease of use, trust in answers, voice clarity, would use it). Summarised in one slide.

## 9. Team split (equal workload)

| Member | Owns |
|---|---|
| 1 — Knowledge & evaluation data | Collect and clean leaflets with licence notes, interaction table, write the eval question set, run the eval, feedback form |
| 2 — Backend & safety | FastAPI app, retrieval, safety rules and tests, prompt, JSON validation |
| 3 — Local models & voice | Ollama install and model benchmark, embedding model, Whisper and TTS endpoints (Kokoro, local fallbacks) |
| 4 — Frontend, avatar & demo | Web page, medicine list and schedule card, avatar portrait and animation, slides, leads the demo |

Everyone adds real problems they hit to `CHALLENGES.md` as they go; it becomes the challenges slide.

## 10. Timeline

| When | Milestone |
|---|---|
| Sun 15 Nov | Design approved, plan written; Ollama installed, models pulled; leaflets being collected; portrait generated |
| Mon 16 Nov | Ingest + hybrid retrieval + safety + `/api/chat` answering in the terminal; page skeleton with typed chat and medicine list |
| Tue 17 Nov | Voice in/out, avatar animation, follow-up card, interaction warning; eval set done, first eval run, model chosen; feedback sessions |
| Wed 18 Nov | **Noon: feature freeze.** Final eval run and charts, backup recording, README, slides, zip; **submit before 23:59** |
| 19 or 26 Nov | Live demo |

## 11. Risks and fallbacks

| Risk | Fallback |
|---|---|
| LLM returns bad JSON or invents citations | Schema-constrained output, validation, one retry, safe fallback message |
| Model too slow on stage | Benchmark decides; 3B model kept pulled as a faster backup |
| No internet at venue | Whisper and Ollama are local; TTS falls back to macOS `say` through the same endpoint, so the avatar still animates |
| Mic or permissions fail | Typed input always works; Web Speech as second STT path |
| Live demo crashes | Typed input still works; backup screen recording played only as a last resort, stated openly |
| Kokoro won't install | Another local engine (e.g. Piper), then macOS `say` |
| Licensing doubt on a leaflet | Drop that medicine; keep the URL/date/licence header for every file |

## 12. Open issues / future work

Deliberately out of scope for the deadline; listed in the README and the limitations slide.
- **Chat history:** answers are single-turn; follow-ups like "and what about the evening dose?" don't know the previous question.
- **Word-by-word (streamed) answers:** answers arrive in one piece after a short "thinking" state.
- **Vector database:** embeddings live in an in-memory NumPy index, which is fine for a few hundred chunks. A real vector database (e.g. Chroma, pgvector) becomes worthwhile at thousands of leaflets or with frequent updates.
- **Users adding their own medicines:** the knowledge base is collected by hand and the dropdown only offers those medicines. A later importer would turn a leaflet PDF, or an NHS page given by URL, into the leaflet Markdown format and reuse the existing ingest step. Each import needs a human check of the sections before it goes live, because citations depend on them. Manufacturers' leaflet PDFs are copyrighted, so they could stay on the user's own device but couldn't be shipped with the app; importing from NHS pages avoids this.
- **Answer quality of the small model:** the local 3B model (llama3.2:3b) was chosen for voice-speed replies. It sometimes misreads a leaflet: it blamed metformin's stomach upset on lactic acidosis, a rare serious effect. On questions about taking two medicines together it can give a vague "check your leaflet" reply. Questions about a known risky pair are answered from the interactions table instead of the model (#40), so it can no longer say such a pair is fine. Larger models (llama3.1:8b, qwen2.5:7b) made fewer or similar errors, but the 8B refused 6 of 20 answerable questions, and both were 2 to 4 times slower. That makes them too slow to talk to on this laptop (Apple M4, 24 GB). Memory is not the limit, speed is. Faster hardware would let a larger model answer at voice speed. The 8B's tokens/s was measured while other work was running and needs a quiet rerun before it is quoted.
- **Broad combination trigger:** the interactions check fires on words like "with" and "and". "Can I take warfarin with food?" with ibuprofen on the list also gets the warfarin + ibuprofen warning. This errs on the cautious side.
- **Offline voice on non-Mac machines:** the offline TTS fallback uses macOS `say`; a cross-platform local engine (e.g. Piper) would replace it. The whole demo already depends on the Mac running the model, so this is accepted.

## 13. Left to the builder

- Exact Ollama model tags, Whisper model size, Kokoro voice name, RRF/threshold values — choose by measuring.
- Exact red-flag phrase list wording and the interaction pairs, within the rules above.
- Visual styling, colours, avatar look (friendly, professional, non-real person).
- Whether to add streaming if time allows.
