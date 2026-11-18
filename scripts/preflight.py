"""Release gates: run at feature freeze and on demo morning, Wi-Fi off. Exits non-zero if any gate fails."""
import os
import subprocess
import sys

from backend.app import CHAT_MODEL
from backend.kb import EMBED_MODEL

OFFLINE = {**os.environ, "HF_HUB_OFFLINE": "1"}


def models_present() -> bool:
    import ollama

    have = {m.model for m in ollama.list().models}
    missing = [m for m in (CHAT_MODEL, EMBED_MODEL) if m not in have and f"{m}:latest" not in have]
    for m in missing:
        print(f"  missing: ollama pull {m}")
    return not missing


def run(*cmd: str) -> bool:
    return subprocess.run(cmd, env=OFFLINE).returncode == 0


def main() -> int:
    gates = {
        "Ollama models present": models_present,
        # -rs lists any skipped live test with its reason: a skipped gate is not a passed gate.
        "Python tests, slow included, offline": lambda: run(sys.executable, "-m", "pytest", "-m", "slow or not slow", "-rs"),
        "Node tests": lambda: run("node", "--test", "web/js/logic.test.js"),
    }
    results = {}
    for name, gate in gates.items():
        print(f"\n== {name}")
        try:
            results[name] = gate()
        except Exception as e:
            print(f"  {e}")
            results[name] = False
    print()
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
