"""Run once while online: fills the Hugging Face and Ollama caches so the demo works with Wi-Fi off."""
import os

from backend.app import CHAT_MODEL
from backend.kb import EMBED_MODEL
from backend.speech import kokoro_engine, say_engine, warm_speech


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "0"  # backend.app defaults it to 1
    import ollama

    for model in (CHAT_MODEL, EMBED_MODEL):
        ollama.pull(model)
    # Same code path the server uses, so whatever it would download at runtime is fetched here.
    warm_speech([kokoro_engine(), say_engine()])
    print("Models cached. Now check with Wi-Fi off: HF_HUB_OFFLINE=1 uv run uvicorn --factory backend.app:default_app")


if __name__ == "__main__":
    main()
