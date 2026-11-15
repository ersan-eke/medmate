from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .kb import Embed, Index, load_index, ollama_embed
from .pipeline import ChatRequest, ChatResponse, answer_question
from .retrieval import Retriever

Generate = Callable[..., str]

ROOT = Path(__file__).resolve().parent.parent


def create_app(index: Index, embed: Embed, generate: Generate) -> FastAPI:
    app = FastAPI()
    retriever = Retriever(index, embed)

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> ChatResponse:
        return answer_question(req, retriever)

    # Mounted last so it never shadows the API routes.
    app.mount("/", StaticFiles(directory=ROOT / "web", html=True))
    return app


def default_app() -> FastAPI:
    """`uvicorn --factory backend.app:default_app`: real index and Ollama embedder."""

    def no_llm(*args, **kwargs):
        raise NotImplementedError("the LLM arrives in a later ticket")

    return create_app(load_index(ROOT / "data" / "index"), ollama_embed(), no_llm)
