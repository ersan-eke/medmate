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


def test_multi_word_medicine_name_is_boosted(tmp_path, fake_embed):
    import shutil
    from pathlib import Path

    from backend.kb import build_index

    shutil.copy(Path(__file__).parent / "fixtures" / "leaflets" / "warfarin.md", tmp_path)
    (tmp_path / "cocodamol.md").write_text(
        "---\nmedicine: Co-codamol\nsource_url: https://www.nhs.uk/medicines/co-codamol/\n"
        "retrieved: 2026-11-15\nlicence: OGL\n---\n## About\nA painkiller.\n\n## Drowsiness\nIt can make you sleepy.\n"
    )
    r = Retriever(build_index(tmp_path, fake_embed), fake_embed)
    result = r.search("Co-codamol nosebleeds that do not stop, bleeding gums, blood in your urine, tell your doctor", [], k=1)
    assert result.hits[0].chunk.medicine == "Co-codamol"
