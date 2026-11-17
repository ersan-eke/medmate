import json
import math
from pathlib import Path

from eval.metrics import (
    answer_rate,
    best_threshold,
    citation_validity,
    faithfulness_rate,
    gate_accuracy,
    hit_at_k,
    percentile,
    red_flag_stats,
    refusal_rate,
)
from eval.run_eval import cached, load_rows

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


def test_answer_rate_counts_only_answers_to_answerable_rows():
    rows = [{"id": "a", "expect_kind": "answer"}, {"id": "b", "expect_kind": "answer"},
            {"id": "c", "expect_kind": "not_covered"}]
    assert answer_rate(rows, {"a": "answer", "b": "not_covered", "c": "answer"}) == 0.5


def test_empty_categories_give_nan_not_a_crash():
    assert math.isnan(answer_rate([], {}))
    assert math.isnan(refusal_rate(ROWS[:1], {}))
    assert all(math.isnan(x) for x in red_flag_stats([], {}))
    assert math.isnan(percentile([], 50))


def test_load_rows_skips_blank_lines(tmp_path):
    path = tmp_path / "q.jsonl"
    path.write_text('{"id": "a"}\n\n{"id": "b"}\n')
    assert [r["id"] for r in load_rows(path)] == ["a", "b"]


def test_cached_embeds_each_question_once():
    calls = []
    embed = cached(lambda texts, kind: calls.append(texts) or [[1.0]])
    embed(["q"], "query"), embed(["q"], "query"), embed(["r"], "query")
    assert calls == [["q"], ["r"]]


def test_percentile():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([5], 95) == 5
    assert percentile([1, 2, 3, 4, 5], 100) == 5


def test_gate_accuracy():
    assert gate_accuracy([0.8, 0.6], [0.5, 0.75], 0.7) == 0.5


def test_best_threshold():
    assert best_threshold([0.8, 0.7, 0.6], [0.3, 0.5]) == 0.6


def test_best_threshold_tie_prefers_answering():
    # 0.5 and 0.6 are both right on 3 of 4; the lower one answers more.
    assert best_threshold([0.6, 0.5], [0.4, 0.55]) == 0.5


def test_citation_validity():
    rows = [{"id": "a", "expect_chunks": ["metformin#how"]}, {"id": "b", "expect_chunks": ["warfarin#how"]}]
    sources = {"a": ["metformin#side-effects"], "b": ["aspirin#what"]}
    assert citation_validity(rows, sources) == 0.5


def test_faithfulness_rate_is_the_share_of_graded_answers_scoring_3():
    assert faithfulness_rate(["3", "2", "", "3", "1"]) == 0.5  # the blank is not graded yet


def test_faithfulness_rate_is_nan_before_any_grade():
    assert math.isnan(faithfulness_rate(["", ""]))


def test_question_file_covers_every_category():
    rows = load_rows(ROOT / "eval/questions.jsonl")
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    assert set(cats) == {"dosing", "side_effects", "personal", "red_flag", "near_miss", "not_in_kb", "off_topic"}
    assert min(cats.values()) >= 4 and 30 <= len(rows) <= 50
    heldout = load_rows(ROOT / "eval/heldout.jsonl")
    assert len(heldout) == 10 and {r["expect_kind"] for r in heldout} == {"answer", "not_covered"}
    assert len({r["id"] for r in rows + heldout}) == len(rows) + len(heldout)


def test_expected_chunks_exist():
    import pytest

    path = ROOT / "data/index/chunks.json"
    if not path.exists():
        pytest.skip("no built index")
    ids = {c["id"] for c in json.loads(path.read_text())}
    for row in load_rows(ROOT / "eval/questions.jsonl") + load_rows(ROOT / "eval/heldout.jsonl"):
        assert set(row["expect_chunks"]) <= ids, row["id"]
