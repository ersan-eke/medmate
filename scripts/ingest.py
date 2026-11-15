import argparse
from pathlib import Path

from backend.kb import build_index, ollama_embed, save_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the leaflet index with the Ollama embedder.")
    parser.add_argument("--leaflets", type=Path, default=Path("data/leaflets"))
    parser.add_argument("--out", type=Path, default=Path("data/index"))
    args = parser.parse_args()
    index = build_index(args.leaflets, ollama_embed(timeout=None))  # one call embeds every chunk
    save_index(index, args.out)
    print(f"Indexed {len(index.chunks)} chunks into {args.out}")


if __name__ == "__main__":
    main()
