import re
from dataclasses import dataclass
from typing import Literal

import numpy as np
from rank_bm25 import BM25Okapi

from .kb import Chunk, Embed, Index

RRF_K = 60
BOOST = 1.5
MIN_SIMILARITY = 0.45  # placeholder, tuned by the evaluation task


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

    def _targets(self, question: str, medicines: list[str]) -> set[str]:
        words = set(_tokens(question))
        named = {m for key, m in self.medicines.items() if key in words}
        if named or "my" not in words:
            return named
        return {self.medicines[m.lower()] for m in medicines if m.lower() in self.medicines}

    def search(
        self,
        question: str,
        medicines: list[str],
        k: int = 4,
        mode: Literal["hybrid", "bm25", "vector"] = "hybrid",
    ) -> Retrieval:
        query = self.embed([question], "query")[0]
        similarities = self.index.vectors @ query

        fused = np.zeros(len(self.index.chunks))
        if mode in ("hybrid", "bm25"):
            fused += 1 / (RRF_K + _ranks(self.bm25.get_scores(_tokens(question))))
        if mode in ("hybrid", "vector"):
            fused += 1 / (RRF_K + _ranks(similarities))

        targets = self._targets(question, medicines)
        boost = np.array([BOOST if c.medicine in targets else 1.0 for c in self.index.chunks])
        fused *= boost

        top = np.argsort(-fused, kind="stable")[:k]
        return Retrieval(
            hits=[Hit(self.index.chunks[i], float(fused[i])) for i in top],
            max_similarity=float(similarities[top].max()),
        )
