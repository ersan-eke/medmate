import logging
from typing import Literal

from pydantic import BaseModel, Field

from . import messages
from .kb import Chunk, Interaction
from .llm import Card, Generate, MedicineEntry, ask_llm, shown_text, triage
from .retrieval import MIN_SIMILARITY, Retriever
from .safety import check_interactions, check_red_flags, claims_safe_combination

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
    named = retriever.named(question)
    asked, also = check_interactions(question, named, {m.name for m in medicines}, interactions)
    # Asked pairs are answered from the table, not the model: the small model has said a risky pair is fine.
    response = (ChatResponse(kind="answer", answer=_warnings(asked), sources=_sources(asked, retriever)) if asked
                else _from_leaflets(question, medicines, retriever, generate))
    if also:
        others = [m for p in also for m in (p.medicine_a, p.medicine_b) if m not in named]
        response.answer += " " + messages.ALSO_TAKE.format(_and(list(dict.fromkeys(others)))) + " " + _warnings(also)
        response.sources = list({s.id: s for s in response.sources + _sources(also, retriever)}.values())
    if (asked or also) and messages.INTERACTION_ADVICE not in response.answer:
        response.answer += " " + messages.INTERACTION_ADVICE
    return response


def _warnings(pairs: list[Interaction]) -> str:
    return " ".join(dict.fromkeys(p.warning for p in pairs))


def _sources(pairs: list[Interaction], retriever: Retriever) -> list[Source]:
    return [Source.of(retriever.chunks[i]) for i in dict.fromkeys(p.source_chunk for p in pairs)]


def _and(names: list[str]) -> str:
    return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]


def _from_leaflets(question: str, medicines: list[MedicineEntry], retriever: Retriever,
                   generate: Generate) -> ChatResponse:
    try:
        result = retriever.search(question, [m.name for m in medicines])
    except Exception:  # embedder down or slow: the page must still get an answer
        log.warning("retrieval failed (embedder down or slow?)", exc_info=True)
        return ChatResponse(kind="fallback", answer=messages.FALLBACK)
    # The gate keeps off-topic questions from the model; one about a leaflet medicine goes on to the model's
    # `covered` flag, as "my thyroid tablet" with Levothyroxine listed scored under the cut.
    if result.max_similarity < MIN_SIMILARITY and not retriever.targets(question, [m.name for m in medicines]):
        return ChatResponse(kind="not_covered", answer=messages.GATE_REFUSAL)
    llm = ask_llm(question, medicines, result.hits, generate)
    if llm is None:
        return ChatResponse(kind="fallback", answer=messages.FALLBACK, llm_called=True)
    # A question naming a leaflet medicine is in scope whatever the model says (a misspoken "1000 milliliters"
    # of aspirin made it say off-topic); it then refuses as not covered.
    if not llm.in_scope and not retriever.named(question):
        log.info("model refused: off_topic")
        return ChatResponse(kind="off_topic", answer=messages.OFF_TOPIC, llm_called=True)
    if not llm.covered or not llm.in_scope:
        log.info("model refused: not_covered")
        return ChatResponse(kind="not_covered", answer=messages.NOT_COVERED, llm_called=True)
    if claims_safe_combination(question, shown_text(llm), retriever.named(question)):
        log.info("model called a combination safe: referred")
        return ChatResponse(kind="not_covered", answer=messages.UNCONFIRMED_COMBINATION, llm_called=True)
    by_id = {h.chunk.id: h.chunk for h in result.hits}
    sources = [Source.of(by_id[i]) for i in dict.fromkeys(llm.citations)]  # citation order, no repeats
    return ChatResponse(kind="answer", answer=llm.answer, sources=sources, card=llm.card, llm_called=True)
