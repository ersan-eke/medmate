from typing import Literal

from pydantic import BaseModel, Field

from . import messages
from .retrieval import MIN_SIMILARITY, Retriever
from .safety import check_red_flags


class ChatRequest(BaseModel):
    question: str = Field(max_length=500)


class Source(BaseModel):
    id: str
    medicine: str
    section: str
    url: str


class ChatResponse(BaseModel):
    kind: Literal["emergency", "not_covered", "fallback", "not_heard"]
    answer: str
    sources: list[Source] = []
    red_flag: str | None = None
    llm_called: bool = False


def answer_question(req: ChatRequest, retriever: Retriever) -> ChatResponse:
    question = req.question.strip()
    if not question:
        return ChatResponse(kind="not_heard", answer=messages.NOT_HEARD)
    if flag := check_red_flags(question):
        return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag=flag.id)
    result = retriever.search(question, [])
    if result.max_similarity < MIN_SIMILARITY:
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED)
    # The LLM arrives in a later ticket; until then the matched passages are the answer.
    sources = [
        Source(id=h.chunk.id, medicine=h.chunk.medicine, section=h.chunk.section, url=h.chunk.source_url)
        for h in result.hits
    ]
    return ChatResponse(kind="fallback", answer=messages.FALLBACK, sources=sources)
