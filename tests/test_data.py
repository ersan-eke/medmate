import datetime
from pathlib import Path

import pytest

from backend.kb import build_index, chunk_leaflet, load_interactions, parse_leaflet, validate_interactions

DATA = Path(__file__).parent.parent / "data"
LEAFLETS = sorted((DATA / "leaflets").glob("*.md"))


@pytest.fixture(scope="module")
def index():
    from tests.conftest import fake_embed_fn

    return build_index(DATA / "leaflets", fake_embed_fn)


def test_leaflet_count():
    assert 12 <= len(LEAFLETS) <= 15


@pytest.mark.parametrize("path", LEAFLETS, ids=lambda p: p.stem)
def test_every_leaflet_parses_with_full_header(path):
    text = path.read_text(encoding="utf-8")
    header, _ = parse_leaflet(text)
    assert chunk_leaflet(text)
    assert header["source_url"].startswith("https://www.nhs.uk/medicines/")
    datetime.date.fromisoformat(header["retrieved"])
    assert "Open Government Licence" in header["licence"]


def test_demo_sections_exist(index):
    ids = {c.id for c in index.chunks}
    assert "metformin#how-to-take-metformin" in ids
    assert "metformin#side-effects-of-metformin" in ids


def test_interactions_valid(index):
    interactions = load_interactions(DATA / "interactions.csv")
    assert interactions
    validate_interactions(interactions, index)


def test_demo_interaction_present():
    pairs = {frozenset((i.medicine_a, i.medicine_b)) for i in load_interactions(DATA / "interactions.csv")}
    assert frozenset(("Warfarin", "Ibuprofen")) in pairs
