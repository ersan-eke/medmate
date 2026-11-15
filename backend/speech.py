import io
import logging
import subprocess
import tempfile
from typing import Callable

log = logging.getLogger(__name__)

Engine = Callable[[str], bytes]  # text -> WAV bytes; raises on failure


def kokoro_engine(voice: str = "af_heart", speed: float = 0.9) -> Engine:
    pipeline = None

    def speak(text: str) -> bytes:
        nonlocal pipeline
        import numpy as np
        import soundfile

        if pipeline is None:
            from kokoro import KPipeline

            pipeline = KPipeline(lang_code="a")
        parts = [np.asarray(audio) for _, _, audio in pipeline(text, voice=voice, speed=speed)]
        if not parts:
            raise RuntimeError("kokoro produced no audio")
        buf = io.BytesIO()
        soundfile.write(buf, np.concatenate(parts), 24000, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    return speak


def say_engine(rate: int = 165) -> Engine:
    def speak(text: str) -> bytes:
        # WAV, not say's default AIFF, which browsers can't decode.
        with tempfile.NamedTemporaryFile(suffix=".wav") as out:
            subprocess.run(["say", "-r", str(rate), "-o", out.name, "--data-format=LEI16@22050", "--", text],
                           check=True, capture_output=True)
            return out.read()

    return speak


def synthesize(text: str, engines: list[Engine]) -> bytes:
    for engine in engines:
        try:
            return engine(text)
        except Exception:
            log.exception("TTS engine failed, trying the next one")
    raise RuntimeError("every TTS engine failed")
