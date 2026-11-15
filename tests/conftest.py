import hashlib
import re
from pathlib import Path

import numpy as np
import pytest

from backend.kb import build_index

DIMS = 512


def fake_embed_fn(texts, mode="document"):
    out = np.zeros((len(texts), DIMS), dtype=np.float32)
    for row, text in zip(out, texts):
        for word in re.findall(r"\w+", text.lower()):
            row[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMS] += 1
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


@pytest.fixture
def fake_embed():
    return fake_embed_fn


@pytest.fixture
def tiny_index(fake_embed):
    return build_index(Path(__file__).parent / "fixtures" / "leaflets", fake_embed)
