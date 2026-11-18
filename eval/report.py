"""uv run python -m eval.report --set final --model llama3.2:3b

Per-class results of a run, with 95% ranges, to eval/results/<set>-<model>-report.md. Calls no model, so it can be
rerun when the faithfulness grades come back (eval/grading/<set>-grades.csv).
"""
import argparse
import csv
import json
import math
from itertools import combinations

from eval.grader_sheet import GRADERS, GRADING
from eval.metrics import REFUSALS, cohen_kappa, wilson
from eval.run_eval import RESULTS, ROOT, load_rows

KINDS = ["emergency", "answer", "not_covered", "off_topic"]


def passed(expected: str, got: str) -> bool:
    """Either refusal counts for an expected refusal, as in kind_accuracy."""
    return got == expected or {got, expected} <= REFUSALS


def count(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k} of {n} ({lo:.0%}–{hi:.0%})" if n else "–"


def class_table(rows: list[dict], got: dict[str, str]) -> list[str]:
    lines = ["| expected | single question | chat | together |", "|---|---|---|---|"]
    for kind in KINDS:
        cells = []
        for part in ([r for r in rows if "history" not in r], [r for r in rows if "history" in r], rows):
            mine = [r for r in part if r["expect_kind"] == kind]
            cells.append(count(sum(passed(kind, got[r["id"]]) for r in mine), len(mine)))
        lines.append(f"| {kind} | " + " | ".join(cells) + " |")
    return lines


def report(rows: list[dict], run: list[dict], metrics: dict, grades: list[dict]) -> str:
    out = {o["id"]: o for o in run}
    got = {i: o["kind"] for i, o in out.items()}
    lines = [f"# Results: {metrics.get('model', '')}", ""]
    if "commit" in metrics:
        lines += [f"Commit {metrics['commit']}, started {metrics['started']}, models loaded: "
                  + ", ".join(metrics["ollama_before"]), ""]
    lines += ["Passes per expected reply. Either refusal counts for an expected refusal. Ranges are 95% Wilson intervals.",
              "", *class_table(rows, got), ""]
    others = [r for r in rows if r["expect_kind"] != "emergency"]
    lines.append("Over-triggering (the 999 reply on a row that does not expect it): "
                 + count(sum(got[r["id"]] == "emergency" for r in others), len(others)))
    caught = [out[r["id"]] for r in rows if r["expect_kind"] == "emergency" and got[r["id"]] == "emergency"]
    lines.append(f"Emergencies caught by the fixed phrases: {sum(o.get('red_flag') != 'model_triage' for o in caught)}; "
                 f"only by the model's yes/no step: {sum(o.get('red_flag') == 'model_triage' for o in caught)}")
    table = sum(o["kind"] == "answer" and o["llm_called"] == "False" for o in run)
    lines.append(f"Answered from the interaction table (fixed text, not graded for faithfulness): {table}")
    if metrics.get("hit_at_4") is not None:
        lines.append(f"Retrieval hit@4 on single questions: {metrics['hit_at_4']:.2f} ({metrics['hit_at_4_n']} questions)")
    if not math.isnan(metrics.get("citation_validity", math.nan)):  # nan without expect_chunks
        lines.append(f"Citation validity: {metrics['citation_validity']:.2f}")
    lines += ["", "## Misses", "", "| id | expected | got | question |", "|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['expect_kind']} | {got[r['id']]} | {r['question']} |"
              for r in rows if not passed(r["expect_kind"], got[r["id"]])]
    if grades:
        lines += ["", "## Faithfulness", "", "Share of graded answers scoring 3 of 3, per grader:", ""]
        for g in GRADERS:
            marks = [r[g].strip() for r in grades if r[g].strip()]
            lines.append(f"- {g}: {count(marks.count('3'), len(marks))}")
        lines.append("")
        for a, b in combinations(GRADERS, 2):
            both = [r for r in grades if r[a].strip() and r[b].strip()]
            if both:
                x, y = [r[a].strip() for r in both], [r[b].strip() for r in both]
                lines.append(f"- {a} and {b}: same grade on {sum(p == q for p, q in zip(x, y))} of {len(both)}, "
                             f"Cohen's kappa {cohen_kappa(x, y):.2f}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    tag = f"{args.set}-{args.model.replace(':', '-').replace('/', '-')}"
    run = list(csv.DictReader((RESULTS / f"{tag}.csv").open(encoding="utf-8")))
    grades_path = GRADING / f"{args.set}-grades.csv"
    grades = list(csv.DictReader(grades_path.open(encoding="utf-8"))) if grades_path.exists() else []
    text = report(load_rows(ROOT / "eval" / f"{args.set}.jsonl"), run, json.loads((RESULTS / f"{tag}.json").read_text()), grades)
    (RESULTS / f"{tag}-report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
