import io
import logging
import re
import subprocess
import tempfile
from typing import Callable

log = logging.getLogger(__name__)

Engine = Callable[[str], bytes]  # text -> WAV bytes; raises on failure

# Kokoro reads "2.5mg" as "two . five em-gee" and "mg/ml" as "slash"; spelled-out units read right.
# "µg" is the micro sign, "μg" the Greek mu: leaflets and model output use both.
SPOKEN_UNITS = {"mg": "milligram", "g": "gram", "ml": "millilitre",
                "mcg": "microgram", "µg": "microgram", "μg": "microgram"}
DOSE_NUMBER = r"\d+(?:[.,]\d+)*"
DOSE_UNIT = "|".join(SPOKEN_UNITS)
DOSE = re.compile(rf"({DOSE_NUMBER})\s*({DOSE_UNIT})\b(?:\s*/\s*({DOSE_NUMBER})?(?:\s*({DOSE_UNIT})\b)?)?", re.IGNORECASE)


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


def spoken(text: str) -> str:
    """'250mg/5ml' -> '250 milligrams per 5 millilitres'; the shown text keeps the leaflet's form."""
    def say_amount(number: str | None, unit: str) -> str:
        word = SPOKEN_UNITS[unit.lower()]
        return word if number is None else f"{number} {word}" + ("" if number == "1" else "s")

    def say_dose(m: re.Match) -> str:
        number, unit, per_number, per_unit = m.groups()
        said = say_amount(number, unit)
        if "/" in m[0]:  # "2 g/day" leaves "day" in the text after the match
            said += " per " + (say_amount(per_number, per_unit) if per_unit else per_number or "")
        return said

    return DOSE.sub(say_dose, text)


def synthesize(text: str, engines: list[Engine]) -> bytes:
    text = spoken(text)
    for engine in engines:
        try:
            return engine(text)
        except Exception:
            log.exception("TTS engine failed, trying the next one")
    raise RuntimeError("every TTS engine failed")


MAX_AUDIO_SECONDS = 30  # web/js/chat.js stops recording at the same length


class AudioTooLong(Exception):
    pass


_whisper = None


def transcribe(audio: bytes, prompt: str | None = None) -> str:
    """Whatever MediaRecorder sends (webm/opus); faster-whisper decodes it via PyAV.
    `prompt` primes Whisper with words it should expect, such as rare medicine names."""
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        _whisper = WhisperModel("small.en", device="cpu", compute_type="int8")
    segments, info = _whisper.transcribe(io.BytesIO(audio), language="en", vad_filter=True, initial_prompt=prompt)
    if info.duration > MAX_AUDIO_SECONDS:  # `segments` is lazy: nothing has been transcribed yet
        raise AudioTooLong
    return " ".join(s.text.strip() for s in segments).strip()


def warm_speech(engines: list[Engine]) -> None:
    """Load Whisper and the first TTS engine now (raises if it can't), so the first request doesn't stall (or download)."""
    import numpy as np
    import soundfile

    silence = io.BytesIO()
    soundfile.write(silence, np.zeros(16000, dtype="float32"), 16000, format="WAV")
    transcribe(silence.getvalue())
    engines[0]("Ready.")  # not synthesize(): a silent fall-through to `say` would leave Kokoro uncached
