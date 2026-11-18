"""uv run python -m eval.grader_sheet --set final --model llama3.2:3b

Builds the blind faithfulness sheet from a run: eval/grading/<set>-sheet.csv goes to the graders, and
eval/grading/<set>-grades.csv maps each item back to its run id and collects the grades (as round1-grades.csv).
"""
import argparse
import csv
import random
from pathlib import Path

from backend.kb import load_index, load_interactions
from eval.run_eval import RESULTS, ROOT, load_rows

GRADING = ROOT / "eval" / "grading"
GRADERS = ["friend1", "friend2", "friend3", "claude"]


def sheet_rows(rows: list[dict], run: list[dict], chunks: dict, interactions: list) -> list[dict]:
    """One row per answer the model wrote, shuffled. Table-only answers are fixed text and are not graded."""
    by_id = {r["id"]: r for r in rows}
    written = [o for o in run if o["kind"] == "answer" and o["llm_called"] == "True"]
    random.Random(0).shuffle(written)  # fixed seed: rebuilding the sheet gives the same item numbers
    out = []
    for item, o in enumerate(written, start=1):
        passages = [chunks[i].text for i in o["sources"].split()]  # a chunk's text starts with "Medicine — Section"
        # Table warnings are copied into the answer word for word, so a match means the answer used that row.
        passages += [f"Interaction table — {p.medicine_a} and {p.medicine_b}\n{p.warning}"
                     for p in interactions if p.warning in o["answer"]]
        out.append({"item": item, "run_id": o["id"], "earlier_message": " / ".join(by_id[o["id"]].get("history", [])),
                    "question": by_id[o["id"]]["question"], "answer_to_grade": "\n\n".join(filter(None, [o["answer"], o.get("card", "")])),  # the page shows both
                    "cited_passages": "\n\n---\n\n".join(passages), "grade_1_2_3": "", "what_was_wrong": ""})
    return out


def write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    tag = f"{args.set}-{args.model.replace(':', '-').replace('/', '-')}"
    grades = GRADING / f"{args.set}-grades.csv"
    if grades.exists():  # it holds the grades once they come back
        raise SystemExit(f"{grades.name} exists; move it away to rebuild the sheet")
    run = list(csv.DictReader((RESULTS / f"{tag}.csv").open(encoding="utf-8")))
    index = load_index(ROOT / "data" / "index")
    out = sheet_rows(load_rows(ROOT / "eval" / f"{args.set}.jsonl"), run, {c.id: c for c in index.chunks},
                     load_interactions(ROOT / "data" / "interactions.csv"))
    # Graders see no run id, source, label or model.
    write(GRADING / f"{args.set}-sheet.csv", out,
          ["item", "earlier_message", "question", "answer_to_grade", "cited_passages", "grade_1_2_3", "what_was_wrong"])
    write(grades, out, ["item", "run_id", *GRADERS, *(f"{g}_note" for g in GRADERS)])
    print(f"{len(out)} answers to grade; {sum(o['kind'] == 'answer' for o in run) - len(out)} answered from the table")


if __name__ == "__main__":
    main()
