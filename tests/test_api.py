import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.messages import ATTRIBUTION, EMERGENCY, FALLBACK, NOT_COVERED, NOT_HEARD


class Counting:
    def __init__(self, fn=None):
        self.fn, self.calls = fn, 0

    def __call__(self, *a, **k):
        self.calls += 1
        if self.fn is None:
            raise AssertionError("must not be called")
        return self.fn(*a, **k)


@pytest.fixture
def spies(fake_embed):
    return Counting(fake_embed), Counting()


@pytest.fixture
def client(spies, tiny_index):
    embed, generate = spies
    return TestClient(create_app(tiny_index, embed, generate))


def chat(client, q):
    return client.post("/api/chat", json={"question": q})


def test_demo_red_flag_skips_llm(client, spies):
    r = chat(client, "Now my chest feels tight.")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "emergency"
    assert body["answer"] == EMERGENCY
    assert body["red_flag"] == "chest_pain"
    assert body["llm_called"] is False
    assert [s.calls for s in spies] == [0, 0]  # neither embedder nor LLM


def test_medicine_question_with_symptom_still_fires(client):
    assert chat(client, "is chest pain a side effect of amlodipine?").json()["kind"] == "emergency"


@pytest.mark.parametrize("q", ["", "   ", "\n\t "])
def test_blank_question_not_heard(client, q):
    r = chat(client, q)
    assert r.status_code == 200
    assert r.json()["kind"] == "not_heard"
    assert r.json()["answer"] == NOT_HEARD


def test_medicine_question_returns_top_4_sources(client, spies, monkeypatch):
    # The hashing fake embedder scores long leaflet chunks far below a real model's cosines.
    monkeypatch.setattr("backend.pipeline.MIN_SIMILARITY", 0.1)
    body = chat(client, "Should I take metformin before or after dinner?").json()
    assert body["kind"] == "fallback"  # no LLM answer yet
    assert body["answer"] == FALLBACK
    assert len(body["sources"]) == 4
    assert "How and when to take it" in {s["section"] for s in body["sources"]}
    assert {s["medicine"] for s in body["sources"]} == {"Metformin"}
    assert body["sources"][0]["url"] == "https://www.nhs.uk/medicines/metformin/"
    assert spies[1].calls == 0


def test_unrelated_question_not_covered(client):
    body = chat(client, "what is the capital of France").json()
    assert body["kind"] == "not_covered"
    assert body["answer"] == NOT_COVERED
    assert body["sources"] == []


def test_page_has_banner_and_footer(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'role="alert"' in r.text
    assert "999" in r.text
    assert ATTRIBUTION in r.text
    assert "innerHTML" not in r.text
