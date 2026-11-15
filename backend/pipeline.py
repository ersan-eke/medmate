from typing import Literal

from pydantic import BaseModel, Field

from . import messages
from .llm import Card, Generate, MedicineEntry, ask_llm
from .retrieval import MIN_SIMILARITY, Retriever
from .safety import check_red_flags


class ChatRequest(BaseModel):
    question: str = Field(max_length=500)
    medicines: list[MedicineEntry] = Field([], max_length=50)


class Source(BaseModel):
    id: str
    medicine: str
    section: str
    url: str


class ChatResponse(BaseModel):
    kind: Literal["emergency", "answer", "not_covered", "off_topic", "fallback", "not_heard"]
    answer: str
    sources: list[Source] = []
    card: Card | None = None
    red_flag: str | None = None
    llm_called: bool = False


def answer_question(req: ChatRequest, retriever: Retriever, generate: Generate) -> ChatResponse:
    question = req.question.strip()
    if not question:
        return ChatResponse(kind="not_heard", answer=messages.NOT_HEARD)
    if flag := check_red_flags(question):
        return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag=flag.id)
    result = retriever.search(question, [m.name for m in req.medicines])
    if result.max_similarity < MIN_SIMILARITY:
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED)
    llm = ask_llm(question, req.medicines, result.hits, generate)
    if llm is None:
        return ChatResponse(kind="fallback", answer=messages.FALLBACK, llm_called=True)
    if not llm.in_scope:
        return ChatResponse(kind="off_topic", answer=messages.OFF_TOPIC, llm_called=True)
    if not llm.covered:
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED, llm_called=True)
    by_id = {h.chunk.id: h.chunk for h in result.hits}
    sources = [
        Source(id=c.id, medicine=c.medicine, section=c.section, url=c.source_url)
        for c in (by_id[i] for i in dict.fromkeys(llm.citations))  # citation order, no repeats
    ]
    return ChatResponse(kind="answer", answer=llm.answer, sources=sources, card=llm.card, llm_called=True)
