# MedMate

A voice-first companion that answers questions about a person's medicines from 12 NHS leaflets, and refuses everything else.
COMP4431 group project: domain-specific chatbot (healthcare, English).

MedMate is not medical advice. It answers only from the leaflets in `data/leaflets/`, refers people to a pharmacist, and replies with the 999 message when a question describes an emergency.

## Team

| Name | Student ID |
|---|---|
| Ersan Eke | 26012487X |
| Karin Ishikawa | 23031369D |
| Sela De Jong | 26012648X |
| Katina Casimaty | 26012457X |

## Features

**Basic:** English chat about 12 leaflet medicines (metformin, warfarin, amlodipine, aspirin, atorvastatin, ibuprofen, levothyroxine, omeprazole, paracetamol, ramipril, salbutamol, sertraline). Every answer cites the leaflet passages it used. Terms are defined in [`GLOSSARY.md`](GLOSSARY.md).

**Additional:**

1. **Voice recognition.** Hold the mic and talk; faster-whisper `small.en` transcribes it on the laptop.
2. **Voice synthesis and 2D avatar.** Answers are spoken by Kokoro (macOS `say` if Kokoro is missing, captions only if both are). The avatar is a 2D portrait with four image frames in `web/avatar/` (`prompts/avatar.txt` has the prompts used to make them). Its mouth follows the audio volume through a Web Audio analyser, and it blinks.
3. **User-friendly interface.** A chat page with reply cards, a "My medicines" list with a Today schedule that personalises answers, an NHS leaflets viewer, text size A+ (20, 24 or 28 px), and keyboard-only use. Built in plain HTML, CSS and JavaScript in `web/`.
4. **Grounded answers.** Hybrid retrieval (BM25 plus vectors) over the leaflets, hit@4 1.00. A similarity gate refuses off-topic questions before the model sees them.
5. **Safety layers.** The emergency check (fixed phrases for each NHS 999 sign, then the model answers yes or no for each sign), the number check (a dose the leaflet does not state is sent back to the model), and a checked interaction table for medicine pairs (`data/interactions.csv`).
6. **LLM.** Not fine-tuned. `llama3.2:3b` runs locally through Ollama with a prompt in `prompts/`. We chose it over `llama3.1:8b` and `qwen2.5:7b` in an evaluation (below).

## Run it

Needs: macOS (the tested platform), Python 3.12 (uv installs it from `.python-version`), [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/), `espeak-ng` (Kokoro falls back to it for words missing from its dictionary, such as medicine names; without it those words are skipped in speech), and Chrome. Internet is needed once, to download models.

The zip holds the committed source, the leaflets and the ready-built search index (`data/index/`), so there is nothing to build. It leaves out the Python environment and the models, which are too large to commit, so set those up once (internet needed):

```
brew install uv ollama espeak-ng
brew services start ollama
ollama pull llama3.2:3b nomic-embed-text   # the chat model; the model that embeds leaflets and questions
uv sync                                    # Python 3.12 environment and all packages from uv.lock
uv run python -m scripts.fetch_models      # Whisper and Kokoro weights; after this the app runs offline
```

Then start the app:

```
uv run uvicorn --factory backend.app:default_app
```

Open <http://127.0.0.1:8000> in Chrome and allow the microphone. uvicorn and the other Python packages (FastAPI, faster-whisper, Kokoro, rank-bm25 and so on) are installed by `uv sync` from `pyproject.toml`.

### Hosting it yourself with other leaflets (optional)

The knowledge base is the Markdown files in `data/leaflets/`. To add a leaflet, save it there in the same layout as the existing files, add any medicine pairs it warns about to `data/interactions.csv`, and rerun `uv run python -m scripts.ingest` to rebuild `data/index` (needs `nomic-embed-text` in Ollama; the committed index was built from the 12 leaflets above). Restart the server afterwards. The server checks the interaction table against the index at start and stops if a row cites a passage that is not there.

### Check and evaluate (not needed to run the app)

```
uv run pytest                           # fast tests; no models needed beyond the above
uv run python -m scripts.preflight      # PASS or FAIL for the demo checks
uv run python -m eval.run_eval --model llama3.2:3b
```

Before an eval rerun, unload other Ollama models (`ollama ps`, `ollama stop <model>`), so the timings are comparable.

**Tested on:** MacBook with Apple M4, 24 GB memory, macOS 27.2.1, Python 3.12, uv 0.13.7, Ollama 0.40.16. All latencies below are from this machine; a slower laptop will be slower.

## Results

`llama3.2:3b`, main set of 47 questions: red-flag recall 1.00, refusal 1.00, answer rate 0.81, faithful answers 0.82 (22 hand-graded answers), p95 latency 12.5 s.

The 1.00 recall is on a set we tuned against. On a fresh emergency set written after the rules were frozen, recall is 0.92 with 1 false alarm in 8 near-misses. The two 7B/8B models caught every emergency there but were over the 15 s limit on this laptop, so we kept the 3B model.

Full tables: [`eval/results/summary.md`](eval/results/summary.md). Every change we tried, with before and after: [`eval/decisions.md`](eval/decisions.md). Problems met while building: [`CHALLENGES.md`](CHALLENGES.md).

## Folders

`backend/` FastAPI server, retrieval, safety checks, speech. `web/` the page and avatar frames. `prompts/` the model prompts. `data/` leaflets, interaction table and index (the knowledge base). `eval/` questions, metrics and results. `scripts/` ingest, model fetch and preflight. `tests/` tests.

## Content and licence

Leaflets are NHS website pages, Open Government Licence v3.0, collected on 2026-11-15. The NHS terms ask re-users to refresh content at least every 7 days: re-collect them if more than 7 days have passed.
