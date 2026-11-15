import numpy as np
import pytest

from backend.kb import ollama_embed

pytestmark = pytest.mark.slow


def test_embed_shape_and_norm():
    vectors = ollama_embed()(["metformin with food", "when to take warfarin"], "document")
    assert vectors.shape[0] == 2 and vectors.shape[1] > 100
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)
