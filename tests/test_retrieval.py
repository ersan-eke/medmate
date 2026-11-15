import pytest

from backend.retrieval import MIN_SIMILARITY, Retriever


@pytest.fixture
def retriever(tiny_index, fake_embed):
    return Retriever(tiny_index, fake_embed)


def ids(result):
    return [h.chunk.id for h in result.hits]


def test_exact_term_bm25(retriever):
    assert retriever.search("warfarin", [], mode="bm25").hits[0].chunk.medicine == "Warfarin"


def test_returns_top_4(retriever):
    assert len(retriever.search("what are the side effects", []).hits) == 4


def test_named_medicine_boost(retriever):
    result = retriever.search("What are the side effects of Warfarin?", [])
    assert {h.chunk.medicine for h in result.hits} == {"Warfarin"}


def test_my_uses_list(retriever):
    result = retriever.search("can I take my tablets with food", ["metformin"])
    assert result.hits[0].chunk.medicine == "Metformin"


def test_my_ignores_unknown_list_entries(retriever):
    assert len(retriever.search("can I take my tablets with food", ["Unknownol"]).hits) == 4


def test_unrelated_question_low_similarity(retriever):
    assert retriever.search("what is the capital of France", []).max_similarity < MIN_SIMILARITY


def test_modes_differ(retriever):
    q = "bleeding blood pain tablets"
    rankings = {m: ids(retriever.search(q, [], mode=m)) for m in ("hybrid", "bm25", "vector")}
    assert rankings["hybrid"] != rankings["bm25"]
    assert rankings["hybrid"] != rankings["vector"]
