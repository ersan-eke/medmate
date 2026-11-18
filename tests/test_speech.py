import sys

import pytest
from fastapi.testclient import TestClient

from backend.app import MAX_AUDIO_BYTES, create_app
from backend.speech import AudioTooLong, kokoro_engine, say_engine, spoken, synthesize, transcribe
from tests.test_api import INTERACTIONS


def failing(text):
    raise RuntimeError("engine down")


def test_synthesize_falls_back():
    assert synthesize("hi", [failing, lambda t: b"RIFF..."]) == b"RIFF..."


@pytest.mark.parametrize("text, said", [
    ("Take 2.5mg daily.", "Take 2.5 milligrams daily."),
    ("Take 1g.", "Take 1 gram."),
    ("Take 1 mg or 0.5 mg.", "Take 1 milligram or 0.5 milligrams."),
    ("10 mL or 500 mcg", "10 millilitres or 500 micrograms"),
    ("250mg/5ml", "250 milligrams per 5 millilitres"),
    ("5 mg/ml", "5 milligrams per millilitre"),
    ("2 g/day", "2 grams per day"),
    ("2.5μg or 2.5µg", "2.5 micrograms or 2.5 micrograms"),  # Greek mu, then micro sign
    ("5 gallons, and/or 3 GPs", "5 gallons, and/or 3 GPs"),
])
def test_spoken_reads_doses_in_words(text, said):
    assert spoken(text) == said


def test_synthesize_speaks_the_spoken_text():
    heard = []
    synthesize("Take 2.5mg.", [lambda t: heard.append(t) or b"RIFF"])
    assert heard == ["Take 2.5 milligrams."]


def test_synthesize_all_fail_raises():
    with pytest.raises(RuntimeError):
        synthesize("hi", [failing, failing])


def tts(tiny_index, fake_embed, engines, text="Hello."):
    app = create_app(tiny_index, fake_embed, lambda m, s: "", INTERACTIONS, engines=engines)
    return TestClient(app, base_url="http://localhost").post("/api/tts", json={"text": text})


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
    return TestClient(app, base_url="http://localhost")


def test_transcribe_route_returns_text(tiny_index, fake_embed):
    seen = []
    client = transcribe_client(tiny_index, fake_embed, lambda audio: seen.append(audio) or "hello")
    r = client.post("/api/transcribe", files={"audio": ("a.webm", b"bytes", "audio/webm")})
    assert r.json() == {"text": "hello"}
    assert seen == [b"bytes"]


def test_transcribe_route_413_on_oversized_upload(tiny_index, fake_embed):
    seen = []
    client = transcribe_client(tiny_index, fake_embed, lambda audio: seen.append(audio) or "hello")
    r = client.post("/api/transcribe", files={"audio": ("a.webm", b"x" * (MAX_AUDIO_BYTES + 1), "audio/webm")})
    assert r.status_code == 413
    assert seen == []


def test_transcribe_route_413_on_oversized_chunked_upload(tiny_index, fake_embed):
    seen = []
    client = transcribe_client(tiny_index, fake_embed, lambda audio: seen.append(audio) or "hello")
    chunks = (b"x" * 100_000 for _ in range(20))  # a generator body is sent chunked, with no Content-Length
    r = client.post("/api/transcribe", content=chunks, headers={"content-type": "multipart/form-data; boundary=b"})
    assert r.status_code == 413
    assert seen == []


def test_transcribe_route_413_when_audio_too_long(tiny_index, fake_embed):
    def too_long(audio):
        raise AudioTooLong

    r = transcribe_client(tiny_index, fake_embed, too_long).post(
        "/api/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    assert r.status_code == 413


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
def test_transcribe_rejects_audio_over_the_limit():
    import io
    import numpy as np
    import soundfile

    buf = io.BytesIO()
    soundfile.write(buf, np.zeros(16000 * 31, dtype="float32"), 16000, format="WAV")
    with pytest.raises(AudioTooLong):
        transcribe(buf.getvalue())


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
