import json

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.messages import ATTRIBUTION, EMERGENCY, FALLBACK, NOT_COVERED, NOT_HEARD, OFF_TOPIC


METFORMIN = "metformin#how-and-when-to-take-it"
SIDE_EFFECTS = "metformin#side-effects"
CARD = {"summary": "Take it with food.", "what_to_do": ["Eat first."], "get_help_if": ["You feel very unwell."]}


def reply(**over):
    body = {"in_scope": True, "covered": True, "answer": "Take it with food.",
            "citations": [SIDE_EFFECTS, METFORMIN, SIDE_EFFECTS], "card": CARD} | over
    return json.dumps(body)


class Counting:
    def __init__(self, fn=None):
        self.fn, self.calls, self.messages = fn, 0, None

    def __call__(self, *a, **k):
        self.calls += 1
        self.messages = a[0] if a else None
        if self.fn is None:
            raise AssertionError("must not be called")
        return self.fn(*a, **k)


@pytest.fixture
def spies(fake_embed):
    return Counting(fake_embed), Counting(lambda m, s: reply())


@pytest.fixture
def client(spies, tiny_index):
    embed, generate = spies
    return TestClient(create_app(tiny_index, embed, generate))


def chat(client, q, medicines=()):
    return client.post("/api/chat", json={"question": q, "medicines": list(medicines)})


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
    assert body["kind"] == "answer"
    assert body["answer"] == "Take it with food."
    assert [s["id"] for s in body["sources"]] == [SIDE_EFFECTS, METFORMIN]  # citation order, not rank
    assert body["sources"][1] == {
        "id": METFORMIN, "medicine": "Metformin", "section": "How and when to take it",
        "url": "https://www.nhs.uk/medicines/metformin/",
    }
    assert body["card"] == CARD
    assert body["llm_called"] is True
    assert spies[1].calls == 1


def test_prompt_carries_passages_and_medicines(client, spies, monkeypatch):
    monkeypatch.setattr("backend.pipeline.MIN_SIMILARITY", 0.1)
    chat(client, "Should I take metformin before or after dinner?", [{"name": "Aspirin"}])
    user = spies[1].messages[-1]["content"]
    assert f"[{METFORMIN}]" in user and "Aspirin" in user


def test_invalid_llm_output_falls_back(client, spies, monkeypatch):
    monkeypatch.setattr("backend.pipeline.MIN_SIMILARITY", 0.1)
    spies[1].fn = lambda m, s: "not json"
    body = chat(client, "Should I take metformin before or after dinner?").json()
    assert body["kind"] == "fallback" and body["answer"] == FALLBACK
    assert body["sources"] == [] and spies[1].calls == 2


def test_llm_not_covered_and_off_topic(client, spies, monkeypatch):
    monkeypatch.setattr("backend.pipeline.MIN_SIMILARITY", 0.1)
    spies[1].fn = lambda m, s: reply(covered=False, citations=[])
    assert chat(client, "Should I take metformin before or after dinner?").json()["kind"] == "not_covered"
    spies[1].fn = lambda m, s: reply(in_scope=False, citations=[])
    body = chat(client, "Should I take metformin before or after dinner?").json()
    assert body["kind"] == "off_topic" and body["answer"] == OFF_TOPIC


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
