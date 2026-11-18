"""Release gates on the real index and models: the spec §7 demo script, the spoken red flags and the first-answer time."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.app import CHAT_MODEL, ROOT
from backend.kb import EMBED_MODEL
from backend.speech import say_engine

pytestmark = pytest.mark.slow

FIRST_ANSWER_SECONDS = 10
DEMO_LIST = [{"name": "Metformin", "dose": "500 mg", "times": ["evening"]},
             {"name": "Amlodipine", "dose": "5 mg", "times": ["morning"]}]


@pytest.fixture(scope="module")
def client():
    if not (ROOT / "data" / "index" / "chunks.json").exists():
        pytest.skip("no index: run `uv run python -m scripts.ingest`")
    try:
        import ollama

        have = {m.model for m in ollama.list().models}
    except Exception as e:
        pytest.skip(f"Ollama is not running: {e}")
    for model in (CHAT_MODEL, EMBED_MODEL):
        if model not in have and f"{model}:latest" not in have:
            pytest.skip(f"Ollama model missing: ollama pull {model}")
    from backend.app import default_app

    return TestClient(default_app(), base_url="http://localhost")  # warms every model, as at startup


def chat(client, question):
    return client.post("/api/chat", json={"question": question, "medicines": DEMO_LIST}).json()


def test_step3_first_answer_is_fast_and_cites_metformin(client):
    start = time.monotonic()
    body = chat(client, "I forgot whether I should take my Metformin before or after dinner, "
                        "and my stomach feels a bit unsettled.")
    assert time.monotonic() - start <= FIRST_ANSWER_SECONDS
    assert body["kind"] == "answer"
    ids = [s["id"] for s in body["sources"]]
    assert any(i.startswith("metformin#how-to-take") for i in ids)
    assert any(i.startswith("metformin#side-effects") for i in ids)


def test_step4_turmeric_is_not_covered(client):
    body = chat(client, "Can I take Metformin with turmeric supplements?")
    assert body["kind"] == "not_covered" and body["sources"] == []


def test_step5_chest_tightness_is_an_emergency_without_the_model(client):
    body = chat(client, "Now my chest feels tight.")
    assert body["kind"] == "emergency" and body["llm_called"] is False


@pytest.mark.skipif(__import__("sys").platform != "darwin", reason="macOS say")
@pytest.mark.parametrize("phrase", ["Now my chest feels tight.", "my face is drooping on one side"])
def test_spoken_red_flag_reaches_the_emergency_message(client, phrase):
    heard = client.post("/api/transcribe", files={"audio": ("a.wav", say_engine()(phrase), "audio/wav")}).json()["text"]
    assert chat(client, heard)["kind"] == "emergency", f"Whisper heard {heard!r}"
