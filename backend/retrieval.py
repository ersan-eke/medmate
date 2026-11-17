import re
from dataclasses import dataclass
from typing import Literal

import numpy as np
from rank_bm25 import BM25Okapi

from .kb import Chunk, Embed, Index

RRF_K = 60
TOP_K = 4  # passages sent to the model
BOOST = 1.5
# Tuned on eval/questions.jsonl (47 questions, 10 of them casual rewordings): the best cut is 0.725; 0.72 leaves a
# little margin. No cut separates every question, so the model's `covered` and `in_scope` flags refuse the rest:
# turmeric-with-metformin (0.763) and amoxicillin-with-warfarin (0.730) pass, and qwen2.5:7b answered turmeric.
MIN_SIMILARITY = 0.72


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]
    max_similarity: float


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1-based rank of every row, best score first."""
    ranks = np.empty(len(scores), dtype=int)
    ranks[np.argsort(-scores, kind="stable")] = np.arange(1, len(scores) + 1)
    return ranks


class Retriever:
    def __init__(self, index: Index, embed: Embed):
        self.index, self.embed = index, embed
        self.bm25 = BM25Okapi([_tokens(c.text) for c in index.chunks])
        self.medicines = {c.medicine.lower(): c.medicine for c in index.chunks}
        self.chunks = {c.id: c for c in index.chunks}

    def named(self, question: str) -> set[str]:
        """Leaflet medicines the question names, in their leaflet spelling."""
        return {m for key, m in self.medicines.items() if re.search(rf"\b{re.escape(key)}\b", question.lower())}

    def targets(self, question: str, medicines: list[str]) -> set[str]:
        """Leaflet medicines the question is about: the ones it names, else My medicines when it says "my"."""
        named = self.named(question)
        if named or "my" not in _tokens(question):
            return named
        return {self.medicines[m.lower()] for m in medicines if m.lower() in self.medicines}

    def search(
        self,
        question: str,
        medicines: list[str],
        k: int = TOP_K,
        mode: Literal["hybrid", "bm25", "vector"] = "hybrid",
    ) -> Retrieval:
        query = self.embed([question], "query")[0]
        similarities = self.index.vectors @ query

        fused = np.zeros(len(self.index.chunks))
        if mode in ("hybrid", "bm25"):
            fused += 1 / (RRF_K + _ranks(self.bm25.get_scores(_tokens(question))))
        if mode in ("hybrid", "vector"):
            fused += 1 / (RRF_K + _ranks(similarities))

        targets = self.targets(question, medicines)
        boost = np.array([BOOST if c.medicine in targets else 1.0 for c in self.index.chunks])
        fused *= boost

        top = np.argsort(-fused, kind="stable")[:k]
        return Retrieval(
            hits=[Hit(self.index.chunks[i], float(fused[i])) for i in top],
            max_similarity=float(similarities.max()),  # every passage, not just the ranked top
        )
