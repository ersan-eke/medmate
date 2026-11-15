from pathlib import Path

import numpy as np
import pytest

from backend.kb import MAX_CHUNK_CHARS, build_index, chunk_leaflet, load_index, parse_leaflet, save_index

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
