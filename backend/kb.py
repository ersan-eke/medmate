import csv
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np

MAX_CHUNK_CHARS = 1500
HEADER_KEYS = ("medicine", "source_url", "retrieved", "licence")

# Rows must come back L2-normalised so a dot product is a cosine.
Embed = Callable[[list[str], Literal["query", "document"]], np.ndarray]


@dataclass(frozen=True)
class Chunk:
    id: str
    medicine: str
    section: str
    text: str
    source_url: str


@dataclass(frozen=True)
class Interaction:
    medicine_a: str
    medicine_b: str
    warning: str
    source_chunk: str


@dataclass
class Index:
    chunks: list[Chunk]
    vectors: np.ndarray


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_leaflet(text: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    match = re.match(r"\s*---\n(.*?)\n---(?:\n(.*)|$)", text.lstrip("\ufeff").replace("\r\n", "\n"), re.DOTALL)
    if not match:
        raise ValueError("leaflet must start with a --- header block")
    header = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    header = {k.strip(): v.strip() for k, v in header.items()}
    for key in HEADER_KEYS:
        if not header.get(key):
            raise ValueError(f"leaflet header is missing '{key}'")
    parts = re.split(r"^## (.+)$", match.group(2) or "", flags=re.MULTILINE)
    if parts[0].strip():
        raise ValueError(f"{header['medicine']} leaflet has text before the first heading")
    return header, [(h.strip(), b.strip()) for h, b in zip(parts[1::2], parts[2::2])]


def _split(body: str) -> list[str]:
    # shortcut: a single paragraph over the limit stays whole, split it if leaflets ever need that.
    parts: list[str] = []
    for paragraph in re.split(r"\n\s*\n", body):
        if parts and len(parts[-1]) + len(paragraph) + 2 <= MAX_CHUNK_CHARS:
            parts[-1] += "\n\n" + paragraph
        else:
            parts.append(paragraph)
    return parts


def chunk_leaflet(text: str) -> list[Chunk]:
    header, sections = parse_leaflet(text)
    medicine = header["medicine"]
    chunks = []
    for section, body in sections:
        if not body:
            raise ValueError(f"{medicine} leaflet section '{section}' is empty")
        for n, part in enumerate(_split(body), start=1):
            suffix = "" if n == 1 else f"-{n}"
            chunks.append(Chunk(
                id=f"{_slug(medicine)}#{_slug(section)}{suffix}",
                medicine=medicine,
                section=section,
                text=f"{medicine} — {section}\n{part}",
                source_url=header["source_url"],
            ))
    _check_unique(chunks)
    return chunks


def _check_unique(chunks: list[Chunk]) -> None:
    seen: set[str] = set()
    for chunk in chunks:
        if chunk.id in seen:
            raise ValueError(f"duplicate chunk id '{chunk.id}': two sections share a heading")
        seen.add(chunk.id)


def build_index(leaflet_dir: Path, embed: Embed) -> Index:
    chunks = [c for path in sorted(leaflet_dir.glob("*.md")) for c in chunk_leaflet(path.read_text(encoding="utf-8"))]
    _check_unique(chunks)
    return Index(chunks, embed([c.text for c in chunks], "document").astype(np.float32))


def save_index(index: Index, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chunks.json").write_text(json.dumps([asdict(c) for c in index.chunks], indent=1))
    np.save(out_dir / "vectors.npy", index.vectors)


def load_index(out_dir: Path) -> Index:
    chunks = [Chunk(**c) for c in json.loads((out_dir / "chunks.json").read_text())]
    if not chunks:
        raise ValueError(f"The index in {out_dir} is empty. Run scripts/ingest.py to build it.")
    return Index(chunks, np.load(out_dir / "vectors.npy"))


def load_interactions(path: Path) -> list[Interaction]:
    with path.open(encoding="utf-8", newline="") as f:
        return [Interaction(**row) for row in csv.DictReader(f)]


def validate_interactions(interactions: list[Interaction], index: Index) -> None:
    chunks = {c.id: c for c in index.chunks}
    medicines = {c.medicine for c in index.chunks}
    pairs = [frozenset((row.medicine_a, row.medicine_b)) for row in interactions]
    for pair in pairs:
        if pairs.count(pair) > 1:
            raise ValueError(f"interaction {' + '.join(sorted(pair))} is listed more than once")
    for row in interactions:
        for name in (row.medicine_a, row.medicine_b):
            if name not in medicines:
                raise ValueError(f"interaction names unknown medicine '{name}'")
        chunk = chunks.get(row.source_chunk)
        if chunk is None:
            raise ValueError(f"interaction source '{row.source_chunk}' is not a chunk")
        # The cited passage must name both medicines; the warning wording itself is checked by hand.
        if chunk.medicine not in (row.medicine_a, row.medicine_b) or not all(
            re.search(rf"\b{re.escape(n)}\b", chunk.text, re.IGNORECASE) for n in (row.medicine_a, row.medicine_b)
        ):
            raise ValueError(f"'{row.source_chunk}' does not name both {row.medicine_a} and {row.medicine_b}")


EMBED_MODEL = "nomic-embed-text"
EMBED_TIMEOUT_SECONDS = 10  # a warm embedding takes well under a second


def ollama_embed(model: str = EMBED_MODEL, timeout: float | None = EMBED_TIMEOUT_SECONDS) -> Embed:
    import ollama

    client = ollama.Client(timeout=timeout)

    def embed(texts: list[str], mode: Literal["query", "document"]) -> np.ndarray:
        # nomic-embed-text needs these task prefixes.
        prefix = "search_query: " if mode == "query" else "search_document: "
        vectors = np.array(client.embed(model=model, input=[prefix + t for t in texts]).embeddings, dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    return embed
