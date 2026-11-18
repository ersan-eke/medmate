import json
import math
from pathlib import Path

from eval.metrics import (
    answer_rate,
    best_threshold,
    citation_validity,
    cohen_kappa,
    faithfulness_rate,
    gate_accuracy,
    hit_at_k,
    kind_accuracy,
    percentile,
    red_flag_stats,
    refusal_rate,
    wilson,
)
from eval.run_eval import cached, load_rows

ROOT = Path(__file__).resolve().parents[1]

ROWS = [
    {"id": "a", "category": "red_flag", "expect_kind": "emergency"},
    {"id": "b", "category": "chat", "expect_kind": "emergency"},  # scored by label, whatever the category
    {"id": "c", "category": "dosing", "expect_kind": "answer"},
    {"id": "d", "category": "combination", "expect_kind": "not_covered"},
    {"id": "e", "category": "off_topic", "expect_kind": "off_topic"},
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


def test_wilson_matches_the_ranges_in_the_plan():
    assert round(wilson(75, 75)[0], 3) == 0.951 and round(wilson(74, 75)[0], 3) == 0.928
    assert wilson(75, 75)[1] == 1.0 and all(math.isnan(x) for x in wilson(0, 0))


def test_cohen_kappa_reproduces_round_one():
    import csv

    rows = list(csv.DictReader((ROOT / "eval/grading/round1-grades.csv").open(encoding="utf-8")))
    col = {g: [r[g].strip() for r in rows] for g in ("claude", "friend1", "friend2")}
    assert round(cohen_kappa(col["friend1"], col["friend2"]), 2) == 0.74
    assert round(cohen_kappa(col["claude"], col["friend1"]), 2) == 0.67
    assert round(cohen_kappa(col["claude"], col["friend2"]), 2) == 0.49


def test_gate_accuracy():
    assert gate_accuracy([0.8, 0.6], [0.5, 0.75], 0.7) == 0.5


def test_best_threshold():
    assert best_threshold([0.8, 0.7, 0.6], [0.3, 0.5]) == 0.6


def test_best_threshold_tie_prefers_answering():
    # 0.5 and 0.6 are both right on 3 of 4; the lower one answers more.
    assert best_threshold([0.6, 0.5], [0.4, 0.55]) == 0.5


def test_citation_validity():
    rows = [{"id": "a", "expect_chunks": ["metformin#how"]}, {"id": "b", "expect_chunks": ["warfarin#how"]},
            {"id": "c", "expect_chunks": []}]  # nothing to check c against, so it is skipped
    sources = {"a": ["metformin#side-effects"], "b": ["aspirin#what"], "c": ["aspirin#what"]}
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
    for name in ("questions", "heldout", "dev", "dev_chats", "final"):
        for row in load_rows(ROOT / f"eval/{name}.jsonl"):
            assert set(row["expect_chunks"]) <= ids, row["id"]


def test_kind_accuracy_treats_both_refusal_kinds_alike():
    rows = [{"id": "a", "expect_kind": "answer"}, {"id": "b", "expect_kind": "not_covered"},
            {"id": "c", "expect_kind": "off_topic"}, {"id": "d", "expect_kind": "emergency"}]
    kinds = {"a": "answer", "b": "off_topic", "c": "not_covered", "d": "not_covered"}
    assert kind_accuracy(rows, kinds) == 0.75


def test_full_run_keeps_a_hand_grade_only_while_the_answer_is_unchanged(tmp_path, monkeypatch, capsys):
    import csv
    from types import SimpleNamespace

    from eval import run_eval

    monkeypatch.setattr(run_eval, "RESULTS", tmp_path)
    monkeypatch.setattr(run_eval, "ollama_generate", lambda *a, **k: lambda *x: None)
    monkeypatch.setattr(run_eval, "speed", lambda m: 1.0)
    answers = {"a": "same", "b": "new"}
    monkeypatch.setattr(run_eval, "answer_question", lambda req, *a: SimpleNamespace(
        kind="answer", red_flag=None, llm_called=True, sources=[], answer=answers[req.question], card=None))
    (tmp_path / "t.csv").write_text("id,answer,faithfulness\na,same,3\nb,old,2\n")
    rows = [{"id": q, "category": "c", "question": q, "medicines": [], "expect_kind": "answer", "expect_chunks": []} for q in "ab"]
    run_eval.full_run(rows, None, [], "m", "t")
    graded = {r["id"]: r["faithfulness"] for r in csv.DictReader((tmp_path / "t.csv").open())}
    assert graded == {"a": "3", "b": ""}


def test_full_run_refuses_chats_until_follow_ups_exist():
    import pytest

    from eval import run_eval

    with pytest.raises(SystemExit, match="follow-up"):
        run_eval.full_run([{"id": "c", "history": ["q1"], "question": "q2"}], None, [], "m", "t")


def test_freeze_runs_the_final_set_once_on_committed_code_with_only_its_models(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    import pytest

    from eval import run_eval

    status = SimpleNamespace(stdout="")
    monkeypatch.setattr(run_eval.subprocess, "run", lambda cmd, **k: SimpleNamespace(
        stdout="abc123\n" if "rev-parse" in cmd else status.stdout))
    loaded = {"llama3.2:3b": "d1", "nomic-embed-text:latest": "d2"}
    monkeypatch.setattr(run_eval, "loaded_models", lambda: dict(loaded))
    marker = tmp_path / "final-m.json"

    status.stdout = " M eval/run_eval.py\n"
    with pytest.raises(SystemExit, match="commit"):
        run_eval.freeze("llama3.2:3b", marker)
    status.stdout = ""
    loaded["qwen2.5:7b"] = "d3"
    with pytest.raises(SystemExit, match="qwen2.5:7b"):
        run_eval.freeze("llama3.2:3b", marker)
    del loaded["qwen2.5:7b"]
    assert not marker.exists()

    run = run_eval.freeze("llama3.2:3b", marker)
    assert run["commit"] == "abc123" and json.loads(marker.read_text())["ollama_before"] == loaded
    with pytest.raises(SystemExit, match="has been run"):
        run_eval.freeze("llama3.2:3b", marker)


def test_grader_sheet_has_one_blind_row_per_written_answer_with_its_passages():
    from backend.kb import Chunk, Interaction
    from eval.grader_sheet import sheet_rows

    chunks = {"w#how": Chunk("w#how", "Warfarin", "How", "Warfarin — How\ntake it daily", "u")}
    pair = Interaction("Warfarin", "Ibuprofen", "Ask a pharmacist first.", "w#how")
    rows = [{"id": i, "question": f"q{i}"} for i in "abc"] + [{"id": "d", "question": "q2", "history": ["q1"]}]
    run = [{"id": "a", "kind": "answer", "llm_called": "True", "sources": "w#how", "answer": "Daily. Ask a pharmacist first.",
            "card": "Summary: daily"},
           {"id": "b", "kind": "answer", "llm_called": "False", "sources": "w#how", "answer": "Ask a pharmacist first."},
           {"id": "c", "kind": "not_covered", "llm_called": "True", "sources": "", "answer": "Not in my leaflets."},
           {"id": "d", "kind": "answer", "llm_called": "True", "sources": "", "answer": "Yes."}]
    out = {o["run_id"]: o for o in sheet_rows(rows, run, chunks, [pair])}
    assert set(out) == {"a", "d"}  # the table-only answer and the refusal are not graded
    assert out["a"]["cited_passages"] == "Warfarin — How\ntake it daily\n\n---\n\nInteraction table — Warfarin and Ibuprofen\nAsk a pharmacist first."
    assert out["a"]["answer_to_grade"] == "Daily. Ask a pharmacist first.\n\nSummary: daily"  # the card is graded too
    assert out["d"]["earlier_message"] == "q1" and sorted(o["item"] for o in out.values()) == [1, 2]


def test_report_counts_by_expected_reply_and_lists_every_miss():
    from eval.report import report

    rows = [{"id": "a", "expect_kind": "emergency", "question": "qa", "source": "friend_a"},
            {"id": "b", "expect_kind": "not_covered", "question": "qb", "source": "friend_b", "history": ["x"]},
            {"id": "c", "expect_kind": "answer", "question": "qc", "source": "friend_b"}]
    run = [{"id": "a", "kind": "emergency", "red_flag": "model_triage", "llm_called": "True"},
           {"id": "b", "kind": "off_topic", "red_flag": "", "llm_called": "True"},
           {"id": "c", "kind": "emergency", "red_flag": "chest_pain", "llm_called": "False"}]
    grades = [{"claude": "3", "friend1": "3", "friend2": "2"}, {"claude": "2", "friend1": "2", "friend2": ""}]
    text = report(rows, run, {"model": "m"}, grades)
    assert "| emergency | 1 of 1 " in text and "| not_covered | – | 1 of 1 " in text  # either refusal passes
    assert "Over-triggering (the 999 reply on a row that does not expect it): 1 of 2" in text
    assert "only by the model's yes/no step: 1" in text and "| c | answer | emergency | qc |" in text
    assert "claude and friend1: same grade on 2 of 2" in text and "claude and friend2: same grade on 0 of 1" in text


def test_card_text_reads_like_the_page():
    from eval.run_eval import card_text

    from backend.llm import Card

    assert card_text(None) == ""
    assert card_text(Card(summary="S", what_to_do=["a"], get_help_if=["b", "c"])) == "Summary: S\nWhat to do:\n- a\nGet help if:\n- b\n- c"
