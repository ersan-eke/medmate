import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.messages import ATTRIBUTION, EMERGENCY, FALLBACK, NOT_HEARD


class Spy:
    def __init__(self):
        self.calls = 0

    def __call__(self, *a, **k):
        self.calls += 1
        raise AssertionError("must not be called")


@pytest.fixture
def spies():
    return Spy(), Spy()


@pytest.fixture
def client(spies):
    embed, generate = spies
    return TestClient(create_app(embed, generate))


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
    assert [s.calls for s in spies] == [0, 0]


def test_medicine_question_with_symptom_still_fires(client):
    assert chat(client, "is chest pain a side effect of amlodipine?").json()["kind"] == "emergency"


@pytest.mark.parametrize("q", ["", "   ", "\n\t "])
def test_blank_question_not_heard(client, q):
    r = chat(client, q)
    assert r.status_code == 200
    assert r.json()["kind"] == "not_heard"
    assert r.json()["answer"] == NOT_HEARD


def test_other_questions_get_fallback_for_now(client):
    body = chat(client, "When should I take amlodipine?").json()
    assert body["kind"] == "fallback"
    assert body["answer"] == FALLBACK


def test_page_has_banner_and_footer(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'role="alert"' in r.text
    assert "999" in r.text
    assert ATTRIBUTION in r.text
    assert "innerHTML" not in r.text
