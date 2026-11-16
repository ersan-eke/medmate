"""Pure scoring functions for the evaluation. Rows are the dicts of `questions.jsonl`."""
import math

REFUSALS = {"not_covered", "off_topic"}  # the similarity gate says not_covered even for off-topic questions


def hit_at_k(retrieved_ids: list[str], expected: list[str]) -> bool:
    return any(i in expected for i in retrieved_ids)


def red_flag_stats(rows: list[dict], fired: dict[str, bool]) -> tuple[float, float]:
    """(recall over red_flag rows, false-positive rate over all the others)."""
    flagged = [fired[r["id"]] for r in rows if r["category"] == "red_flag"]
    others = [fired[r["id"]] for r in rows if r["category"] != "red_flag"]
    return sum(flagged) / len(flagged), sum(others) / len(others)


def refusal_rate(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of not_in_kb and off_topic rows that got a refusal."""
    refused = [kinds[r["id"]] in REFUSALS for r in rows if r["category"] in ("not_in_kb", "off_topic")]
    return sum(refused) / len(refused)


def citation_validity(rows: list[dict], sources: dict[str, list[str]]) -> float:
    """Share of answered rows citing only expected chunks or other chunks of an expected medicine."""
    ok = []
    for r in rows:
        if r["id"] not in sources:
            continue
        medicines = {c.split("#")[0] for c in r["expect_chunks"]}
        ok.append(all(s in r["expect_chunks"] or s.split("#")[0] in medicines for s in sources[r["id"]]))
    return sum(ok) / len(ok) if ok else math.nan


def percentile(values: list[float], p: float) -> float:
    """Linear interpolation between the closest ranks."""
    v = sorted(values)
    pos = (len(v) - 1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def best_threshold(sims_in: list[float], sims_out: list[float]) -> float:
    """The gate refuses when similarity < threshold. Most correct decisions wins; a tie goes to the lower one."""
    def correct(t: float) -> int:
        return sum(s >= t for s in sims_in) + sum(s < t for s in sims_out)

    return min(sorted(set(sims_in + sims_out)), key=lambda t: (-correct(t), t))
