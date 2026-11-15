from pathlib import Path

import numpy as np
import pytest

from backend.kb import (
    Index,
    MAX_CHUNK_CHARS,
    Interaction,
    build_index,
    chunk_leaflet,
    load_index,
    load_interactions,
    parse_leaflet,
    save_index,
    validate_interactions,
)

LEAFLETS = Path(__file__).parent / "fixtures" / "leaflets"


def test_parse_header():
    header, sections = parse_leaflet((LEAFLETS / "metformin.md").read_text())
    assert set(header) == {"medicine", "source_url", "retrieved", "licence"}
    assert header["medicine"] == "Metformin"
    assert [h for h, _ in sections][:2] == ["About metformin", "How and when to take it"]


def test_chunk_ids_and_sections():
    chunks = {c.id: c for c in chunk_leaflet((LEAFLETS / "metformin.md").read_text())}
    c = chunks["metformin#side-effects"]
    assert c.medicine == "Metformin"
    assert c.section == "Side effects"
    assert c.source_url == "https://www.nhs.uk/medicines/metformin/"
    assert c.text.startswith("Metformin — Side effects\n")


def test_long_section_split():
    chunks = {c.id: c for c in chunk_leaflet((LEAFLETS / "metformin.md").read_text())}
    first, second = chunks["metformin#how-and-when-to-take-it"], chunks["metformin#how-and-when-to-take-it-2"]
    assert "metformin#how-and-when-to-take-it-3" not in chunks
    title = "Metformin — How and when to take it\n"
    for c in (first, second):
        assert c.section == "How and when to take it"
        assert len(c.text) <= MAX_CHUNK_CHARS + len(title)


@pytest.mark.parametrize("key", ["medicine", "source_url", "retrieved", "licence"])
def test_missing_header_key_raises(key):
    text = "\n".join(l for l in (LEAFLETS / "warfarin.md").read_text().splitlines() if not l.startswith(key + ":"))
    with pytest.raises(ValueError, match=key):
        chunk_leaflet(text)


def test_index_roundtrip(tmp_path, fake_embed):
    index = build_index(LEAFLETS, fake_embed)
    save_index(index, tmp_path)
    loaded = load_index(tmp_path)
    assert loaded.chunks == index.chunks
    assert loaded.vectors.dtype == np.float32
    assert np.allclose(loaded.vectors, index.vectors)


def test_crlf_leaflet_parses():
    text = (LEAFLETS / "warfarin.md").read_text().replace("\n", "\r\n")
    assert [c.id for c in chunk_leaflet(text)] == [c.id for c in chunk_leaflet((LEAFLETS / "warfarin.md").read_text())]


def test_duplicate_section_headings_raise():
    text = (LEAFLETS / "warfarin.md").read_text() + "\n## Side effects\nAgain.\n"
    with pytest.raises(ValueError, match="warfarin#side-effects"):
        chunk_leaflet(text)


def test_load_interactions(tmp_path):
    csv = tmp_path / "interactions.csv"
    csv.write_text("medicine_a,medicine_b,warning,source_chunk\nWarfarin,Metformin,\"Ask, first.\",warfarin#other-medicines\n")
    assert load_interactions(csv) == [Interaction("Warfarin", "Metformin", "Ask, first.", "warfarin#other-medicines")]


@pytest.mark.parametrize("row, message", [
    (Interaction("Warfarin", "Metformin", "w", "warfarin#nope"), "warfarin#nope"),
    (Interaction("Warfarin", "Aspirin", "w", "warfarin#other-medicines"), "Aspirin"),
    (Interaction("Warfarin", "Metformin", "w", "warfarin#side-effects"), "does not name"),
])
def test_interaction_source_must_exist(tiny_index, row, message):
    with pytest.raises(ValueError, match=message):
        validate_interactions([row], tiny_index)


def test_duplicate_interaction_pair_raises(tiny_index):
    row = Interaction("Warfarin", "Metformin", "w", "warfarin#other-medicines")
    swapped = Interaction("Metformin", "Warfarin", "w", "warfarin#other-medicines")
    with pytest.raises(ValueError, match="more than once"):
        validate_interactions([row, swapped], tiny_index)


def test_empty_section_raises():
    text = (LEAFLETS / "warfarin.md").read_text() + "\n## Storage\n\n"
    with pytest.raises(ValueError, match="Warfarin.*'Storage' is empty"):
        chunk_leaflet(text)


def test_empty_index_is_rejected_at_load(tmp_path):
    save_index(Index([], np.zeros((0, 4), dtype=np.float32)), tmp_path)
    with pytest.raises(ValueError, match="empty"):
        load_index(tmp_path)


HEADER = "---\nmedicine: Aspirin\nsource_url: u\nretrieved: 2026-01-01\nlicence: OGL\n---"


def test_text_before_first_heading_raises():
    with pytest.raises(ValueError, match="Aspirin.*before the first heading"):
        chunk_leaflet(f"{HEADER}\nstray text\n## Dose\nTake one.\n")


def test_bom_leaflet_parses():
    assert chunk_leaflet(f"﻿{HEADER}\n## Dose\nTake one.\n")[0].id == "aspirin#dose"


def test_header_closing_line_at_end_of_file_parses():
    assert parse_leaflet(HEADER) == ({"medicine": "Aspirin", "source_url": "u", "retrieved": "2026-01-01", "licence": "OGL"}, [])


def test_same_chunk_id_in_two_leaflets_raises(tmp_path, fake_embed):
    for name in ("a.md", "b.md"):
        (tmp_path / name).write_text(f"{HEADER}\n## Dose\nTake one.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aspirin#dose"):
        build_index(tmp_path, fake_embed)
