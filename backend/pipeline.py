from typing import Literal

from pydantic import BaseModel, Field

from . import messages
from .safety import check_red_flags


class ChatRequest(BaseModel):
    question: str = Field(max_length=500)


class ChatResponse(BaseModel):
    kind: Literal["emergency", "fallback", "not_heard"]
    answer: str
    red_flag: str | None = None
    llm_called: bool = False


def answer_question(req: ChatRequest) -> ChatResponse:
    question = req.question.strip()
    if not question:
        return ChatResponse(kind="not_heard", answer=messages.NOT_HEARD)
    if flag := check_red_flags(question):
        return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag=flag.id)
    # Retrieval and the LLM arrive in later tickets; until then every other question is unanswered.
    return ChatResponse(kind="fallback", answer=messages.FALLBACK)
