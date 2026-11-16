import logging
import os
from typing import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import messages
from .kb import Embed, Index, Interaction, load_index, load_interactions, ollama_embed
from .llm import ANSWER_SCHEMA, SYSTEM_PROMPT, WARMUP_TIMEOUT_SECONDS, Generate, ollama_generate
from .pipeline import ChatRequest, ChatResponse, Source, answer_question
from .retrieval import Retriever
from .speech import Engine, kokoro_engine, say_engine, synthesize, transcribe, warm_speech

# Weights come from `scripts/fetch_models.py`; never reach for the network at the venue.
# Set before anything imports huggingface_hub (all such imports are lazy).
os.environ.setdefault("HF_HUB_OFFLINE", "1")

ROOT = Path(__file__).resolve().parent.parent
CHAT_MODEL = os.environ.get("MEDMATE_CHAT_MODEL", "llama3.2:3b")
log = logging.getLogger(__name__)


class TtsRequest(BaseModel):
    text: str = Field(max_length=1500)


def create_app(index: Index, embed: Embed, generate: Generate, interactions: list[Interaction],
               engines: list[Engine] = [], transcribe: Callable[[bytes], str] | None = None) -> FastAPI:
    app = FastAPI()
    retriever = Retriever(index, embed)
    warnings = [
        {"a": i.medicine_a, "b": i.medicine_b, "warning": i.warning, "source": Source.of(retriever.chunks[i.source_chunk])}
        for i in interactions
    ]

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> ChatResponse:
        return answer_question(req, retriever, generate, interactions)

    @app.post("/api/tts")
    def tts(req: TtsRequest) -> Response:
        try:
            return Response(synthesize(req.text, engines), media_type="audio/wav")
        except RuntimeError:
            # The page then shows captions only.
            raise HTTPException(503, "speech unavailable")

    @app.post("/api/transcribe")
    def transcribe_audio(audio: UploadFile) -> dict:
        if transcribe is None:
            raise HTTPException(503, "transcription unavailable")
        try:
            return {"text": transcribe(audio.file.read())}
        except Exception:
            raise HTTPException(503, "transcription failed")

    @app.get("/api/meta")
    def meta() -> dict:
        return {"medicines": sorted(set(retriever.medicines.values())), "interactions": warnings,
                "attribution": messages.ATTRIBUTION}

    # Mounted last so it never shadows the API routes.
    app.mount("/", StaticFiles(directory=ROOT / "web", html=True))
    return app


def warm_models(warmers: dict[str, Callable[[], object]]) -> None:
    """Run each warm-up once. A failure only means a slower first request."""
    for name, warm in warmers.items():
        try:
            warm()
        except Exception:
            log.exception("warming the %s failed", name)


def default_app() -> FastAPI:
    """`uvicorn --factory backend.app:default_app`: real index and Ollama embedder."""

    index = load_index(ROOT / "data" / "index")  # first: a bad index should stop startup before the slow warm-up
    embed, generate, engines = ollama_embed(), ollama_generate(CHAT_MODEL), [kokoro_engine(), say_engine()]
    # Load every model now so the first answer doesn't stall; warm-up clients wait longer than request ones.
    warm_models({
        "embedder": lambda: ollama_embed(timeout=WARMUP_TIMEOUT_SECONDS)(["warm up"], "query"),
        "chat model": lambda: ollama_generate(CHAT_MODEL, WARMUP_TIMEOUT_SECONDS)(
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "warm up"}], ANSWER_SCHEMA),
        "speech": lambda: warm_speech(engines),
    })
    return create_app(index, embed, generate,
                      load_interactions(ROOT / "data" / "interactions.csv"),
                      engines=engines, transcribe=transcribe)
