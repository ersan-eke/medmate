"""Pure scoring functions for the evaluation. Rows are the dicts of `questions.jsonl`."""
import math

REFUSALS = {"not_covered", "off_topic"}  # the similarity gate says not_covered even for off-topic questions


def _share(flags: list[bool]) -> float:
    """nan for an empty category, so a cut-down question file still gets a summary."""
    return sum(flags) / len(flags) if flags else math.nan


def hit_at_k(retrieved_ids: list[str], expected: list[str]) -> bool:
    return any(i in expected for i in retrieved_ids)


# By label, not category: a chat or a combination question can expect any kind.
def red_flag_stats(rows: list[dict], fired: dict[str, bool]) -> tuple[float, float]:
    """(recall over rows expecting the emergency reply, false-positive rate over all the others)."""
    flagged = [fired[r["id"]] for r in rows if r["expect_kind"] == "emergency"]
    others = [fired[r["id"]] for r in rows if r["expect_kind"] != "emergency"]
    return _share(flagged), _share(others)


def refusal_rate(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of rows expecting a refusal that got one."""
    return _share([kinds[r["id"]] in REFUSALS for r in rows if r["expect_kind"] in REFUSALS])


def answer_rate(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of answerable rows (the ones expecting an answer) that got one."""
    return _share([kinds[r["id"]] == "answer" for r in rows if r["expect_kind"] == "answer"])


def kind_accuracy(rows: list[dict], kinds: dict[str, str]) -> float:
    """Share of rows that got the expected kind; either refusal kind counts for an expected refusal."""
    return _share([kinds[r["id"]] == r["expect_kind"] or {kinds[r["id"]], r["expect_kind"]} <= REFUSALS for r in rows])


def citation_validity(rows: list[dict], sources: dict[str, list[str]]) -> float:
    """Share of answered rows citing only expected chunks or other chunks of an expected medicine.
    Rows with no expected chunks are skipped: there is nothing to check their citations against."""
    ok = []
    for r in rows:
        if r["id"] not in sources or not r["expect_chunks"]:
            continue
        medicines = {c.split("#")[0] for c in r["expect_chunks"]}
        ok.append(all(s in r["expect_chunks"] or s.split("#")[0] in medicines for s in sources[r["id"]]))
    return _share(ok)


def faithfulness_rate(grades: list[str]) -> float:
    """Share of the hand-graded answers (1 to 3) that scored 3; blank cells are not graded yet."""
    return _share([g.strip() == "3" for g in grades if g.strip()])


def percentile(values: list[float], p: float) -> float:
    """Linear interpolation between the closest ranks."""
    if not values:
        return math.nan
    v = sorted(values)
    pos = (len(v) - 1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k of n; as close to Clopper-Pearson as matters here, without scipy."""
    if not n:
        return math.nan, math.nan
    p = k / n
    centre, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Agreement of two graders on the same items, corrected for the agreement their grade shares give by chance."""
    n = len(a)
    if not n:
        return float("nan")
    observed = sum(x == y for x, y in zip(a, b)) / n
    chance = sum(a.count(g) * b.count(g) for g in set(a) | set(b)) / (n * n)
    return (observed - chance) / (1 - chance) if chance < 1 else 1.0  # one shared grade: they agree, nothing to correct


def gate_accuracy(sims_in: list[float], sims_out: list[float], threshold: float) -> float:
    """Share of right gate decisions: answerable rows pass, the others are refused (similarity < threshold)."""
    return _share([s >= threshold for s in sims_in] + [s < threshold for s in sims_out])


def best_threshold(sims_in: list[float], sims_out: list[float]) -> float:
    """Most correct gate decisions wins; a tie goes to the lower threshold, which answers more."""
    return min(sorted(set(sims_in + sims_out)), key=lambda t: (-gate_accuracy(sims_in, sims_out, t), t))
