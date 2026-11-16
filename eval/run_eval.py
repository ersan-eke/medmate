"""uv run python -m eval.run_eval --model llama3.2:3b [--retrieval-only]

Needs Ollama running and data/index built. Writes to eval/results/.
"""
import argparse
import csv
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.kb import load_index, ollama_embed
from backend.llm import ollama_generate
from backend.pipeline import ChatRequest, answer_question
from backend.retrieval import MIN_SIMILARITY, Retriever
from eval.metrics import best_threshold, citation_validity, hit_at_k, percentile, red_flag_stats, refusal_rate

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
MODES = ["bm25", "vector", "hybrid"]
SPEED_PROMPTS = [
    "Explain in about 80 words why a person might take a statin.",
    "List four common side effects of ibuprofen in one short paragraph.",
    "Describe, in about 80 words, how to take metformin safely.",
]


def retrieval_section(rows: list[dict], retriever: Retriever) -> dict:
    asked = [r for r in rows if r["expect_chunks"]]
    hit = {m: sum(hit_at_k([h.chunk.id for h in retriever.search(r["question"], r["medicines"], mode=m).hits],
                           r["expect_chunks"]) for r in asked) / len(asked) for m in MODES}
    sims = {r["id"]: retriever.search(r["question"], r["medicines"]).max_similarity for r in rows}
    sims_in = [sims[r["id"]] for r in asked]
    sims_out = [sims[r["id"]] for r in rows if r["category"] in ("not_in_kb", "off_topic")]
    plt.figure(figsize=(4, 3))
    plt.bar(MODES, [hit[m] for m in MODES])
    plt.ylim(0, 1)
    plt.ylabel("hit@4")
    plt.title(f"Retrieval hit@4 ({len(asked)} questions)")
    plt.tight_layout()
    plt.savefig(RESULTS / "retrieval.png", dpi=150)
    (RESULTS / "retrieval.csv").write_text("mode,hit_at_4\n" + "".join(f"{m},{hit[m]:.3f}\n" for m in MODES))
    best = best_threshold(sims_in, sims_out)
    print(f"hit@4 {hit}; best threshold {best:.3f} (current {MIN_SIMILARITY})")
    return {"hit": hit, "best_threshold": best, "min_similarity": MIN_SIMILARITY}


def speed(model: str) -> float:
    import ollama

    rates = []
    for prompt in SPEED_PROMPTS:
        r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], options={"temperature": 0})
        rates.append(r.eval_count / (r.eval_duration / 1e9))
    return sum(rates) / len(rates)


def full_run(rows: list[dict], retriever: Retriever, model: str, tag: str) -> dict:
    generate = ollama_generate(model, timeout=120)  # measure the slow models instead of timing them out
    generate([{"role": "user", "content": "hi"}], {"type": "object"})  # load the model before timing
    out = []
    for r in rows:
        meds = [{"name": m} for m in r["medicines"]]
        start = time.perf_counter()
        resp = answer_question(ChatRequest(question=r["question"], medicines=meds), retriever, generate)
        out.append({"id": r["id"], "category": r["category"], "question": r["question"], "expect_kind": r["expect_kind"],
                    "kind": resp.kind, "latency_s": round(time.perf_counter() - start, 2),
                    "sources": " ".join(s.id for s in resp.sources), "answer": resp.answer, "faithfulness": ""})
        print(f"{r['id']:8} {resp.kind:12} {out[-1]['latency_s']:5.1f}s")
    with (RESULTS / f"{tag}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    kinds = {o["id"]: o["kind"] for o in out}
    recall, fpr = red_flag_stats(rows, {i: k == "emergency" for i, k in kinds.items()})
    answered = {o["id"]: o["sources"].split() for o in out if o["kind"] == "answer"}
    latencies = [o["latency_s"] for o in out if o["kind"] in ("answer", "fallback", "not_covered", "off_topic")]
    return {"red_flag_recall": recall, "red_flag_fpr": fpr, "refusal_rate": refusal_rate(rows, kinds),
            "citation_validity": citation_validity(rows, answered), "p50_s": percentile(latencies, 50),
            "p95_s": percentile(latencies, 95), "tokens_per_s": speed(model)}


def write_summary() -> None:
    retrieval = json.loads((RESULTS / "retrieval.json").read_text())
    lines = ["# Evaluation summary", "",
             "Retrieval hit@4: " + ", ".join(f"{m} {retrieval['hit'][m]:.2f}" for m in MODES),
             f"Best similarity threshold {retrieval['best_threshold']:.3f}; in use {retrieval['min_similarity']}", "",
             "| model | red-flag recall | red-flag FPR | refusal | citation validity | p50 s | p95 s | tokens/s |",
             "|---|---|---|---|---|---|---|---|"]
    for path in sorted(RESULTS.glob("model-*.json")):
        m = json.loads(path.read_text())
        lines.append(f"| {m['model']} | {m['red_flag_recall']:.2f} | {m['red_flag_fpr']:.2f} | {m['refusal_rate']:.2f} "
                     f"| {m['citation_validity']:.2f} | {m['p50_s']:.1f} | {m['p95_s']:.1f} | {m['tokens_per_s']:.1f} |")
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()
    rows = [json.loads(line) for line in (ROOT / "eval" / "questions.jsonl").read_text().splitlines()]
    retriever = Retriever(load_index(ROOT / "data" / "index"), ollama_embed())
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "retrieval.json").write_text(json.dumps(retrieval_section(rows, retriever)))
    if not args.retrieval_only:
        tag = "model-" + args.model.replace(":", "-").replace("/", "-")
        metrics = {"model": args.model, **full_run(rows, retriever, args.model, tag)}
        (RESULTS / f"{tag}.json").write_text(json.dumps(metrics, indent=1))
    write_summary()


if __name__ == "__main__":
    main()
