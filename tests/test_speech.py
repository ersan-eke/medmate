import sys

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.speech import kokoro_engine, say_engine, synthesize
from tests.test_api import INTERACTIONS


def failing(text):
    raise RuntimeError("engine down")


def test_synthesize_falls_back():
    assert synthesize("hi", [failing, lambda t: b"RIFF..."]) == b"RIFF..."


def test_synthesize_all_fail_raises():
    with pytest.raises(RuntimeError):
        synthesize("hi", [failing, failing])


def tts(tiny_index, fake_embed, engines, text="Hello."):
    app = create_app(tiny_index, fake_embed, lambda m, s: "", INTERACTIONS, engines=engines)
    return TestClient(app).post("/api/tts", json={"text": text})


def test_tts_route_503_when_all_fail(tiny_index, fake_embed):
    assert tts(tiny_index, fake_embed, [failing]).status_code == 503


def test_tts_route_503_without_engines(tiny_index, fake_embed):
    assert tts(tiny_index, fake_embed, []).status_code == 503


def test_tts_route_returns_wav(tiny_index, fake_embed):
    r = tts(tiny_index, fake_embed, [lambda t: b"RIFF..."])
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == b"RIFF..."


def test_tts_route_rejects_long_text(tiny_index, fake_embed):
    assert tts(tiny_index, fake_embed, [lambda t: b"RIFF"], text="a" * 1501).status_code == 422


@pytest.mark.slow
def test_kokoro_produces_wav():
    assert kokoro_engine()("Hello.").startswith(b"RIFF")


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS say")
def test_say_produces_wav():
    wav = say_engine()("When should I take amlodipine?")
    assert wav.startswith(b"RIFF") and b"WAVE" in wav[:12]
