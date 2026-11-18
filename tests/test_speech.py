import sys
import threading
import time
import types

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


def hammer(fn, n=6):
    threads = [threading.Thread(target=fn) for _ in range(n)]
    [t.start() for t in threads]
    [t.join() for t in threads]


class Overlap:
    """Counts how many threads are inside a fake model call at once, and how many loads happened."""

    def __init__(self):
        self.active = self.peak = self.loads = 0
        self.guard = threading.Lock()

    def load(self):
        with self.guard:
            self.loads += 1
        time.sleep(0.1)

    def work(self):  # a generator body: runs lazily, like the real segments / audio generators
        with self.guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.05)
        yield
        with self.guard:
            self.active -= 1


def test_transcribe_serialises_threads_and_loads_whisper_once(monkeypatch):
    from backend import speech

    o = Overlap()

    class FakeWhisper:
        def __init__(self, *a, **k):
            o.load()

        def transcribe(self, *a, **k):
            return (types.SimpleNamespace(text=" hi ") for _ in o.work()), types.SimpleNamespace(duration=1)

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeWhisper))
    monkeypatch.setattr(speech, "_whisper", None)
    hammer(lambda: transcribe(b"x"))
    assert (o.peak, o.loads) == (1, 1)


def test_kokoro_engine_serialises_threads_and_loads_once(monkeypatch):
    import numpy as np

    o = Overlap()

    class FakePipeline:
        def __init__(self, **k):
            o.load()

        def __call__(self, *a, **k):
            for _ in o.work():
                yield 0, 0, np.zeros(10, dtype="float32")

    monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakePipeline))
    engine = kokoro_engine()
    hammer(lambda: engine("hello"))
    assert (o.peak, o.loads) == (1, 1)
