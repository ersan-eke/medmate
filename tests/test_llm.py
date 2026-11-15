import json

from backend.llm import MedicineEntry, build_messages, validate
from backend.kb import Chunk
from backend.retrieval import Hit

HITS = [
    Hit(Chunk("metformin#how-and-when-to-take-it", "Metformin", "How and when to take it", "Metformin — How\nTake with meals.", "u"), 1.0),
    Hit(Chunk("warfarin#side-effects", "Warfarin", "Side effects", "Warfarin — Side effects\nBruising.", "u"), 0.5),
]


def raw(**over):
    body = {
        "in_scope": True, "covered": True, "answer": "Take it with meals.",
        "citations": ["metformin#how-and-when-to-take-it"],
        "card": {"summary": "s", "what_to_do": ["a"], "get_help_if": ["b"]},
    } | over
    return json.dumps(body)


def test_prompt_lists_every_chunk_id_and_the_users_medicines():
    text = "\n".join(m["content"] for m in build_messages("when?", [MedicineEntry(name="Aspirin", dose="75 mg")], HITS))
    assert all(h.chunk.id in text for h in HITS)
    assert "Aspirin" in text and "75 mg" in text
    assert "none listed" in "\n".join(m["content"] for m in build_messages("when?", [], HITS))


def test_covered_answer_valid_with_sent_citation():
    assert validate(raw(), {h.chunk.id for h in HITS}).answer == "Take it with meals."


def test_covered_answer_without_citation_invalid():
    assert isinstance(validate(raw(citations=[]), {h.chunk.id for h in HITS}), str)


def test_citation_not_sent_invalid():
    assert "made#up" in validate(raw(citations=["made#up"]), {h.chunk.id for h in HITS})


def test_not_covered_needs_no_citation():
    assert not isinstance(validate(raw(covered=False, citations=[]), set()), str)


def test_bad_json_invalid():
    assert isinstance(validate("nope", set()), str)


def test_bracketed_citation_accepted():
    answer = validate(raw(citations=["[metformin#how-and-when-to-take-it]"]), {h.chunk.id for h in HITS})
    assert answer.citations == ["metformin#how-and-when-to-take-it"]


def test_covered_blank_answer_invalid():
    assert isinstance(validate(raw(answer="  "), {h.chunk.id for h in HITS}), str)
