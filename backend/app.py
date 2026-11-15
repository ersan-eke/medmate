from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .pipeline import ChatRequest, ChatResponse, answer_question

Embed = Callable[[list[str]], list[list[float]]]
Generate = Callable[..., str]

WEB = Path(__file__).resolve().parent.parent / "web"


def create_app(embed: Embed, generate: Generate) -> FastAPI:
    app = FastAPI()
    app.state.embed, app.state.generate = embed, generate

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> ChatResponse:
        return answer_question(req)

    # Mounted last so it never shadows the API routes.
    app.mount("/", StaticFiles(directory=WEB, html=True))
    return app
