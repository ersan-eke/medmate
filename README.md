<p align="center">
  <img src="assets/medmate_hero.png" alt="MedMate: your friendly NHS medicine companion" width="100%">
</p>

**A voice-first companion that answers questions about your medicines from 12 NHS leaflets, and refuses everything else.**

COMP4431 Artificial Intelligence, group project: a domain-specific chatbot for healthcare, in English. It runs fully on the laptop, with a local language model, local speech recognition and local speech synthesis.

> MedMate is not medical advice. It answers only from the leaflets in `data/leaflets/`, refers people to a pharmacist, and replies with the 999 message when a question describes an emergency.

## Contents

- [Team](#team)
- [Features](#features)
- [How an answer is made](#how-an-answer-is-made)
- [Getting started](#getting-started)
- [Testing and evaluation](#testing-and-evaluation)
- [Results](#results)
- [Hosting it with your own leaflets](#hosting-it-with-your-own-leaflets)
- [Project structure](#project-structure)
- [Content and licence](#content-and-licence)

## Team

| Name | Student ID |
|---|---|
| Ersan Eke | 26012487X |
| Karin Ishikawa | 23031369D |
| Sela De Jong | 26012648X |
| Katina Casimaty | 26012457X |

## Features

### Basic

English chat about 12 leaflet medicines: metformin, warfarin, amlodipine, aspirin, atorvastatin, ibuprofen, levothyroxine, omeprazole, paracetamol, ramipril, salbutamol and sertraline. Every answer cites the leaflet passages it used. Terms are defined in [`GLOSSARY.md`](GLOSSARY.md).

### Additional

| Feature | What it does | Where |
|---|---|---|
| **Voice recognition** | Hold the mic and talk; faster-whisper `small.en` transcribes it on the laptop | `backend/speech.py`, `web/js/voice.js` |
| **Voice synthesis** | Answers are spoken by Kokoro; macOS `say` if Kokoro is missing, captions only if both are | `backend/speech.py` |
| **2D avatar** | A portrait made of four image frames. Its mouth follows the audio volume through a Web Audio analyser, and it blinks | `web/avatar/`, `web/js/avatar.js`, `prompts/avatar.txt` |
| **User-friendly interface** | Chat with reply cards, a "My medicines" list with a Today schedule that personalises answers, an NHS leaflets viewer, text size A+ (20, 24 or 28 px), keyboard-only use | `web/` |
| **Grounded answers** | Hybrid retrieval (BM25 plus vectors) over the leaflets; a similarity gate refuses off-topic questions before the model sees them | `backend/retrieval.py`, `backend/kb.py` |
| **Safety layers** | Emergency check, number check on doses, and a checked interaction table for medicine pairs | `backend/safety.py`, `backend/pipeline.py`, `data/interactions.csv` |
| **Local LLM** | `llama3.2:3b` through Ollama with a prompt in `prompts/`. Not fine-tuned. Chosen over `llama3.1:8b` and `qwen2.5:7b` in an evaluation | `backend/llm.py`, `eval/` |

## How an answer is made

1. **Emergency check.** Fixed phrases for each NHS 999 sign, then the model answers yes or no for each sign. Any match gives the 999 message.
2. **Similarity gate.** If no leaflet passage is close enough and the question is not about a leaflet medicine, MedMate refuses.
3. **Retrieval.** BM25 and vector search pick the leaflet passages.
4. **Answer.** The model answers from those passages and cites them.
5. **Number check.** An answer with a number not found in the cited passages, the user's own doses or the emergency number goes back to the model.
6. **Speech.** The reply is spoken and the avatar's mouth follows the audio.

## Getting started

### Requirements

- macOS (the tested platform; the `say` fallback and the commands below are macOS-only)
- [uv](https://docs.astral.sh/uv/), which installs Python 3.12 and the packages (FastAPI, uvicorn, faster-whisper, Kokoro and others, from `pyproject.toml` and `uv.lock`)
- [Ollama](https://ollama.com/), running as a service
- `espeak-ng`: Kokoro uses it for words missing from its dictionary, such as medicine names. Without it those words are skipped in speech
- Chrome, with microphone access
- Node.js, only for the `preflight` check below
- Internet, once, to download the models

**Tested on:** MacBook with Apple M4, 24 GB memory, macOS 27.2.1, Python 3.12, uv 0.13.7, Ollama 0.40.16, Node 24. All latencies below are from this machine; a slower laptop will be slower.

### Setup

The zip holds the source, the leaflets and the ready-built search index (`data/index/`). The Python environment and the models are too large to include, so set them up once:

1. Install the tools and start Ollama:
   ```
   brew install uv ollama espeak-ng
   brew services start ollama
   ```
2. Download the chat model and the embedding model:
   ```
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ```
3. Install the Python environment:
   ```
   uv sync
   ```
4. Download the speech models (Whisper and Kokoro). After this the app runs offline:
   ```
   uv run python -m scripts.fetch_models
   ```

### Run

```
uv run uvicorn --factory backend.app:default_app
```

Open <http://127.0.0.1:8000> in Chrome and allow the microphone.

## Testing and evaluation

None of this is needed to run the app.

| Command | What it checks | Needs |
|---|---|---|
| `uv run pytest` | The 338 fast tests, about a second: the API endpoints, leaflet indexing and retrieval, the emergency phrases, prompt building and answer validation, the speech text, the evaluation metrics and the data files. Models are replaced by stand-ins | `uv sync` only |
| `uv run python -m scripts.preflight` | The release gates for demo morning, with Hugging Face offline: both Ollama models are installed, all Python tests pass including the 11 that call the real models (the spec's demo script, spoken emergencies, first-answer time), and the web logic tests pass. Prints PASS or FAIL for each | Ollama running, models fetched, Node |
| `uv run python -m eval.run_eval --model llama3.2:3b` | Runs the 47 evaluation questions through the whole pipeline with the real model and writes recall, refusal, answer rate, citation validity and timings to `eval/results/` | Ollama running |

Before an evaluation rerun, unload other Ollama models (`ollama ps`, `ollama stop <model>`), so the timings are comparable.

## Results

`llama3.2:3b` on the 47-question main set, on the M4 laptop above:

| Measure | Result | Note |
|---|---|---|
| Retrieval hit@4 (hybrid) | 1.00 | BM25 alone 0.89, vectors alone 1.00 |
| Red-flag recall | 1.00 | Emergencies that got the 999 message |
| Red-flag false alarms | 0.05 | Non-emergencies that got the 999 message |
| Refusal | 1.00 | Questions MedMate should refuse that it refused |
| Answer rate | 0.81 | Answerable questions that got a real answer |
| Faithful answers | 0.82 | Graded by hand on 22 answers, not the full set |
| Citation validity | 1.00 | |
| Latency p50 / p95 | 8.2 s / 12.5 s | |

The 1.00 recall is on a set we tuned against. On a fresh emergency set, written after the rules were frozen, recall is 0.92 with 1 false alarm in 8 near-misses.

Model choice, same set. Recall and refusal had to be 1.00 and p95 under 15 s; then the highest answer rate; then the lowest p95:

| Model | Red-flag recall | Refusal | Answer rate | p95 | Verdict |
|---|---|---|---|---|---|
| `llama3.2:3b` | 1.00 | 1.00 | 0.81 | 12.5 s | **chosen** |
| `llama3.1:8b` | 1.00 | 1.00 | 0.85 | 30.9 s | too slow |
| `qwen2.5:7b` | 1.00 | 0.86 | 0.85 | 24.7 s | too slow, refusal under 1.00 |

Full tables: [`eval/results/summary.md`](eval/results/summary.md). Every change we tried, with before and after: [`eval/decisions.md`](eval/decisions.md). Problems met while building: [`CHALLENGES.md`](CHALLENGES.md).

## Hosting it with your own leaflets

The knowledge base is the Markdown files in `data/leaflets/`. To add a medicine:

1. Save its leaflet in `data/leaflets/`, in the same layout as the existing files.
2. Add any medicine pairs it warns about to `data/interactions.csv`.
3. Rebuild the index (needs `nomic-embed-text` in Ollama):
   ```
   uv run python -m scripts.ingest
   ```
4. Restart the server. It checks the interaction table against the index at start and stops if a row cites a passage that is not there.

The committed `data/index/` was built from the 12 leaflets above.

## Project structure

```
medmate/
├── backend/            FastAPI server
│   ├── app.py            routes and start-up
│   ├── pipeline.py       the answer steps above
│   ├── retrieval.py      BM25 + vector search, similarity gate
│   ├── kb.py             leaflet chunks, index, interaction table
│   ├── llm.py            Ollama calls and answer validation
│   ├── messages.py       prompt and reply text
│   ├── safety.py         emergency check
│   └── speech.py         Whisper, Kokoro, say
├── web/                Chrome front end
│   ├── index.html
│   ├── css/
│   ├── js/               chat, voice, avatar, medicines, leaflets
│   ├── avatar/           four portrait frames
│   └── fonts/
├── data/               knowledge base
│   ├── leaflets/         12 NHS leaflets
│   ├── interactions.csv  checked medicine pairs
│   └── index/            built search index
├── prompts/            model prompts and avatar prompts
├── eval/               questions, metrics, run_eval.py
│   ├── results/          summary.md and per-run tables
│   └── decisions.md      what each change did
├── scripts/            fetch_models, ingest, preflight, package.sh
├── tests/              pytest suite
├── docs/               manual UI checklist
├── GLOSSARY.md         project terms
├── CHALLENGES.md       problems met and how they were fixed
└── pyproject.toml      Python dependencies (with uv.lock)
```

`scripts/package.sh` builds `medmate.zip` from the last commit.

## Content and licence

The leaflets are NHS website pages under the Open Government Licence v3.0, collected on 2026-11-15. The NHS terms ask re-users to refresh content at least every 7 days: re-collect them if more than 7 days have passed.
