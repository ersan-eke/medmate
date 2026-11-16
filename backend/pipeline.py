import logging
from typing import Literal

from pydantic import BaseModel, Field

from . import messages
from .kb import Chunk, Interaction
from .llm import Card, Generate, MedicineEntry, ask_llm, triage
from .retrieval import MIN_SIMILARITY, Retriever
from .safety import check_interactions, check_red_flags

log = logging.getLogger(__name__)
MAX_MEDICINES = 20


class ChatRequest(BaseModel):
    question: str = Field(max_length=500)
    medicines: list[MedicineEntry] = Field([], max_length=50)


class Source(BaseModel):
    id: str
    medicine: str
    section: str
    url: str

    @classmethod
    def of(cls, chunk: Chunk) -> "Source":
        return cls(id=chunk.id, medicine=chunk.medicine, section=chunk.section, url=chunk.source_url)


class ChatResponse(BaseModel):
    kind: Literal["emergency", "answer", "not_covered", "off_topic", "fallback", "not_heard"]
    answer: str
    sources: list[Source] = []
    card: Card | None = None
    red_flag: str | None = None
    llm_called: bool = False


def known_medicines(entries: list[MedicineEntry], names: dict[str, str]) -> list[MedicineEntry]:
    """Entries naming a leaflet medicine, renamed to its spelling, first of each, at most MAX_MEDICINES."""
    kept: dict[str, MedicineEntry] = {}
    for m in entries:
        if (name := names.get(m.name.strip().lower())) and name not in kept:
            kept[name] = m.model_copy(update={"name": name})
    return list(kept.values())[:MAX_MEDICINES]


def answer_question(req: ChatRequest, retriever: Retriever, generate: Generate,
                    interactions: list[Interaction]) -> ChatResponse:
    question = req.question.strip()
    if not question:
        return ChatResponse(kind="not_heard", answer=messages.NOT_HEARD)
    if flag := check_red_flags(question):
        return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag=flag.id)
    if triage(question, generate):  # before retrieval: a novel wording matches no leaflet and would stop at the gate
        return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag="model_triage", llm_called=True)
    medicines = known_medicines(req.medicines, retriever.medicines)
    # Answered from the table, not the model: the small model has said a risky pair is fine.
    if pairs := check_interactions(question, retriever.named(question), {m.name for m in medicines}, interactions):
        sources = [Source.of(retriever.chunks[i]) for i in dict.fromkeys(p.source_chunk for p in pairs)]
        answer = " ".join([*dict.fromkeys(p.warning for p in pairs), messages.INTERACTION_ADVICE])
        return ChatResponse(kind="answer", answer=answer, sources=sources)
    try:
        result = retriever.search(question, [m.name for m in medicines])
    except Exception:  # embedder down or slow: the page must still get an answer
        log.warning("retrieval failed (embedder down or slow?)", exc_info=True)
        return ChatResponse(kind="fallback", answer=messages.FALLBACK)
    if result.max_similarity < MIN_SIMILARITY:
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED)
    llm = ask_llm(question, medicines, result.hits, generate)
    if llm is None:
        return ChatResponse(kind="fallback", answer=messages.FALLBACK, llm_called=True)
    if not llm.in_scope:
        log.info("model refused: off_topic")
        return ChatResponse(kind="off_topic", answer=messages.OFF_TOPIC, llm_called=True)
    if not llm.covered:
        log.info("model refused: not_covered")
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED, llm_called=True)
    by_id = {h.chunk.id: h.chunk for h in result.hits}
    sources = [Source.of(by_id[i]) for i in dict.fromkeys(llm.citations)]  # citation order, no repeats
    return ChatResponse(kind="answer", answer=llm.answer, sources=sources, card=llm.card, llm_called=True)
