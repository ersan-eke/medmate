import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import messages
from .kb import Embed, Index, load_index, ollama_embed
from .llm import Generate, ollama_generate
from .pipeline import ChatRequest, ChatResponse, answer_question
from .retrieval import Retriever

ROOT = Path(__file__).resolve().parent.parent


def create_app(index: Index, embed: Embed, generate: Generate) -> FastAPI:
    app = FastAPI()
    retriever = Retriever(index, embed)

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> ChatResponse:
        return answer_question(req, retriever, generate)

    @app.get("/api/meta")
    def meta() -> dict:
        return {"medicines": sorted(set(retriever.medicines.values())), "attribution": messages.ATTRIBUTION}

    # Mounted last so it never shadows the API routes.
    app.mount("/", StaticFiles(directory=ROOT / "web", html=True))
    return app


def default_app() -> FastAPI:
    """`uvicorn --factory backend.app:default_app`: real index and Ollama embedder."""

    model = os.environ.get("MEDMATE_CHAT_MODEL", "llama3.2:3b")
    return create_app(load_index(ROOT / "data" / "index"), ollama_embed(), ollama_generate(model))
