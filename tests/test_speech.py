import sys

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.speech import kokoro_engine, say_engine, synthesize, transcribe
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


def transcribe_client(tiny_index, fake_embed, fn):
    app = create_app(tiny_index, fake_embed, lambda m, s: "", INTERACTIONS, transcribe=fn)
    return TestClient(app)


def test_transcribe_route_returns_text(tiny_index, fake_embed):
    seen = []
    client = transcribe_client(tiny_index, fake_embed, lambda audio: seen.append(audio) or "hello")
    r = client.post("/api/transcribe", files={"audio": ("a.webm", b"bytes", "audio/webm")})
    assert r.json() == {"text": "hello"}
    assert seen == [b"bytes"]


def test_transcribe_route_503_on_failure(tiny_index, fake_embed):
    def boom(audio):
        raise RuntimeError("no model")

    r = transcribe_client(tiny_index, fake_embed, boom).post(
        "/api/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 503


def test_transcribe_route_503_without_transcriber(tiny_index, fake_embed):
    r = transcribe_client(tiny_index, fake_embed, None).post(
        "/api/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 503


@pytest.mark.slow
def test_transcribe_empty_audio():
    import io
    import numpy as np
    import soundfile

    buf = io.BytesIO()
    soundfile.write(buf, np.zeros(16000, dtype="float32"), 16000, format="WAV")
    assert transcribe(buf.getvalue()) == ""


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "darwin", reason="macOS say")
def test_say_whisper_roundtrip():
    assert "amlodipine" in transcribe(say_engine()("When should I take amlodipine?")).lower()


def test_warm_speech_loads_whisper_and_first_engine(monkeypatch):
    import backend.speech as speech

    calls = []
    monkeypatch.setattr(speech, "transcribe", lambda audio: calls.append("whisper") or "")
    speech.warm_speech([lambda t: calls.append("tts") or b"RIFF", failing])
    assert calls == ["whisper", "tts"]
    with pytest.raises(RuntimeError):  # no quiet fall-through to the next engine
        speech.warm_speech([failing, lambda t: b"RIFF"])
