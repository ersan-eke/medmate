import os
from typing import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import messages
from .kb import Embed, Index, Interaction, load_index, load_interactions, ollama_embed
from .llm import Generate, ollama_generate
from .pipeline import ChatRequest, ChatResponse, Source, answer_question
from .retrieval import Retriever
from .speech import Engine, kokoro_engine, say_engine, synthesize, transcribe

ROOT = Path(__file__).resolve().parent.parent


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

    model = os.environ.get("MEDMATE_CHAT_MODEL", "llama3.2:3b")
    return create_app(load_index(ROOT / "data" / "index"), ollama_embed(), ollama_generate(model),
                      load_interactions(ROOT / "data" / "interactions.csv"),
                      engines=[kokoro_engine(), say_engine()], transcribe=transcribe)
