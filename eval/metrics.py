"""Pure scoring functions for the evaluation. Rows are the dicts of `questions.jsonl`."""
import math

REFUSALS = {"not_covered", "off_topic"}  # the similarity gate says not_covered even for off-topic questions


def _share(flags: list[bool]) -> float:
    """nan for an empty category, so a cut-down question file still gets a summary."""
    return sum(flags) / len(flags) if flags else math.nan


def hit_at_k(retrieved_ids: list[str], expected: list[str]) -> bool:
    return any(i in expected for i in retrieved_ids)


def red_flag_stats(rows: list[dict], fired: dict[str, bool]) -> tuple[float, float]:
    """(recall over red_flag rows, false-positive rate over all the others)."""
    flagged = [fired[r["id"]] for r in rows if r["category"] == "red_flag"]
    others = [fired[r["id"]] for r in rows if r["category"] != "red_flag"]
    return _share(flagged), _share(others)


def refusal_rate(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of not_in_kb and off_topic rows that got a refusal."""
    return _share([kinds[r["id"]] in REFUSALS for r in rows if r["category"] in ("not_in_kb", "off_topic")])


def answer_rate(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of answerable rows (the ones expecting an answer) that got one."""
    return _share([kinds[r["id"]] == "answer" for r in rows if r["expect_kind"] == "answer"])


def citation_validity(rows: list[dict], sources: dict[str, list[str]]) -> float:
    """Share of answered rows citing only expected chunks or other chunks of an expected medicine."""
    ok = []
    for r in rows:
        if r["id"] not in sources:
            continue
        medicines = {c.split("#")[0] for c in r["expect_chunks"]}
        ok.append(all(s in r["expect_chunks"] or s.split("#")[0] in medicines for s in sources[r["id"]]))
    return _share(ok)


def percentile(values: list[float], p: float) -> float:
    """Linear interpolation between the closest ranks."""
    if not values:
        return math.nan
    v = sorted(values)
    pos = (len(v) - 1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def gate_accuracy(sims_in: list[float], sims_out: list[float], threshold: float) -> float:
    """Share of right gate decisions: answerable rows pass, the others are refused (similarity < threshold)."""
    return _share([s >= threshold for s in sims_in] + [s < threshold for s in sims_out])


def best_threshold(sims_in: list[float], sims_out: list[float]) -> float:
    """Most correct gate decisions wins; a tie goes to the lower threshold, which answers more."""
    return min(sorted(set(sims_in + sims_out)), key=lambda t: (-gate_accuracy(sims_in, sims_out, t), t))
