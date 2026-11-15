import logging
import os
from typing import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import messages
from .kb import Embed, Index, Interaction, load_index, load_interactions, ollama_embed
from .llm import Generate, ollama_generate, triage
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
    chunks = {c.id: c for c in index.chunks}
    warnings = [
        {"a": i.medicine_a, "b": i.medicine_b, "warning": i.warning,
         "source": Source(id=i.source_chunk, medicine=chunks[i.source_chunk].medicine,
                          section=chunks[i.source_chunk].section, url=chunks[i.source_chunk].source_url)}
        for i in interactions
    ]

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> ChatResponse:
        return answer_question(req, retriever, generate)

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


def default_app() -> FastAPI:
    """`uvicorn --factory backend.app:default_app`: real index and Ollama embedder."""

    embed, generate, engines = ollama_embed(), ollama_generate(CHAT_MODEL), [kokoro_engine(), say_engine()]
    # Load every model now so the first answer doesn't stall. A failure only means a slower first request.
    for name, warm in [("embedder", lambda: embed(["warm up"], "query")),
                       ("chat model", lambda: triage("warm up", generate)),
                       ("speech", lambda: warm_speech(engines))]:
        try:
            warm()
        except Exception:
            log.exception("warming the %s failed", name)
    return create_app(load_index(ROOT / "data" / "index"), embed, generate,
                      load_interactions(ROOT / "data" / "interactions.csv"),
                      engines=engines, transcribe=transcribe)
