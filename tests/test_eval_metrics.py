import json
from pathlib import Path

from eval.metrics import best_threshold, citation_validity, hit_at_k, percentile, red_flag_stats, refusal_rate

ROOT = Path(__file__).resolve().parents[1]

ROWS = [
    {"id": "a", "category": "red_flag"},
    {"id": "b", "category": "red_flag"},
    {"id": "c", "category": "dosing"},
    {"id": "d", "category": "not_in_kb"},
    {"id": "e", "category": "off_topic"},
]


def test_hit_at_k():
    assert hit_at_k(["x", "y"], ["y", "z"])
    assert not hit_at_k(["x"], ["y"])


def test_red_flag_stats():
    recall, fpr = red_flag_stats(ROWS, {"a": True, "b": False, "c": True, "d": False, "e": False})
    assert (recall, fpr) == (0.5, 1 / 3)


def test_refusal_rate_counts_either_refusal_kind():
    kinds = {"d": "off_topic", "e": "answer"}
    assert refusal_rate(ROWS, kinds) == 0.5


def test_percentile():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([5], 95) == 5
    assert percentile([1, 2, 3, 4, 5], 100) == 5


def test_best_threshold():
    assert best_threshold([0.8, 0.7, 0.6], [0.3, 0.5]) == 0.6


def test_best_threshold_tie_prefers_answering():
    # 0.5 and 0.6 are both right on 3 of 4; the lower one answers more.
    assert best_threshold([0.6, 0.5], [0.4, 0.55]) == 0.5


def test_citation_validity():
    rows = [{"id": "a", "expect_chunks": ["metformin#how"]}, {"id": "b", "expect_chunks": ["warfarin#how"]}]
    sources = {"a": ["metformin#side-effects"], "b": ["aspirin#what"]}
    assert citation_validity(rows, sources) == 0.5


def test_question_file_covers_every_category():
    rows = [json.loads(line) for line in (ROOT / "eval/questions.jsonl").read_text().splitlines()]
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    assert set(cats) == {"dosing", "side_effects", "personal", "red_flag", "near_miss", "not_in_kb", "off_topic"}
    assert min(cats.values()) >= 4 and 30 <= len(rows) <= 40
    assert len({r["id"] for r in rows}) == len(rows)


def test_expected_chunks_exist():
    import pytest

    path = ROOT / "data/index/chunks.json"
    if not path.exists():
        pytest.skip("no built index")
    ids = {c["id"] for c in json.loads(path.read_text())}
    for line in (ROOT / "eval/questions.jsonl").read_text().splitlines():
        row = json.loads(line)
        assert set(row["expect_chunks"]) <= ids, row["id"]
