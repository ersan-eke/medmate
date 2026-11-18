import logging
import os
import re
from typing import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from . import messages
from .kb import Embed, Index, Interaction, load_index, load_interactions, ollama_embed, validate_interactions
from .llm import ANSWER_SCHEMA, SYSTEM_PROMPT, WARMUP_TIMEOUT_SECONDS, Generate, ollama_generate
from .pipeline import ChatRequest, ChatResponse, Source, answer_question
from .retrieval import Retriever
from .speech import AudioTooLong, Engine, kokoro_engine, say_engine, synthesize, transcribe, warm_speech

# Weights come from `scripts/fetch_models.py`; never reach for the network at the venue.
# Set before anything imports huggingface_hub (all such imports are lazy).
os.environ.setdefault("HF_HUB_OFFLINE", "1")

ROOT = Path(__file__).resolve().parent.parent
CHAT_MODEL = os.environ.get("MEDMATE_CHAT_MODEL", "llama3.2:3b")
log = logging.getLogger(__name__)


MAX_AUDIO_BYTES = 1_000_000  # 30 s of opus is ~120 KB


class LimitUpload:
    """Counts request-body bytes for `path` as they arrive and answers 413 past `limit`.
    Starlette spools multipart files to disk before the handler runs, so only a limit on the stream stops a huge upload."""

    def __init__(self, app, path: str, limit: int):
        self.app, self.path, self.limit = app, path, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != self.path:
            return await self.app(scope, receive, send)
        received = 0

        async def counted():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.limit:
                raise HTTPException(413, "audio too large")  # ExceptionMiddleware, inside this one, turns it into the response
            return message

        await self.app(scope, counted, send)


def same_origin(request: Request) -> None:
    # Multipart uploads skip the CORS preflight, so a foreign page could otherwise POST /api/transcribe.
    origin = request.headers.get("origin")
    if origin is not None and origin != f"http://{request.headers['host']}":
        raise HTTPException(403, "cross-origin request refused")


class TtsRequest(BaseModel):
    text: str = Field(max_length=1500)


def create_app(index: Index, embed: Embed, generate: Generate, interactions: list[Interaction],
               engines: list[Engine] = [], transcribe: Callable[[bytes], str] | None = None) -> FastAPI:
    validate_interactions(interactions, index)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, dependencies=[Depends(same_origin)])

    # DNS rebinding keeps the attacker's hostname in Host; we only ever serve the local page.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.add_middleware(LimitUpload, path="/api/transcribe", limit=MAX_AUDIO_BYTES)
    retriever = Retriever(index, embed)
    warnings = [
        {"a": i.medicine_a, "b": i.medicine_b, "warning": i.warning, "source": Source.of(retriever.chunks[i.source_chunk])}
        for i in interactions
    ]

    # A leaflet's first section is its intro ("What X is for" or "About X"); chunk text is "Medicine — Section\nbody".
    intros = {}
    for c in index.chunks:
        intros.setdefault(c.medicine, c)
    leaflets = [
        {"medicine": m, "url": c.source_url, "description": re.split(r"(?<=[.!?])\s", c.text.split("\n", 1)[1], 1)[0]}
        for m, c in sorted(intros.items())
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
        except AudioTooLong:
            raise HTTPException(413, "audio too long")
        except Exception:
            raise HTTPException(503, "transcription failed")

    @app.get("/api/meta")
    def meta() -> dict:
        return {"medicines": sorted(set(retriever.medicines.values())), "interactions": warnings,
                "leaflets": leaflets, "attribution": messages.ATTRIBUTION}

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
    # Whisper mishears rare names like "amlodipine" unless primed with them.
    hint = "Questions about " + ", ".join(sorted({c.medicine for c in index.chunks})) + "."
    return create_app(index, embed, generate,
                      load_interactions(ROOT / "data" / "interactions.csv"),
                      engines=engines, transcribe=lambda audio: transcribe(audio, hint))
