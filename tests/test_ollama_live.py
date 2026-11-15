import numpy as np
import pytest

from backend.kb import ollama_embed

pytestmark = pytest.mark.slow


def test_embed_shape_and_norm():
    vectors = ollama_embed()(["metformin with food", "when to take warfarin"], "document")
    assert vectors.shape[0] == 2 and vectors.shape[1] > 100
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)


def test_metformin_dinner_question_answers_with_metformin_source():
    from fastapi.testclient import TestClient

    from backend.app import default_app

    body = TestClient(default_app()).post(
        "/api/chat", json={"question": "Should I take metformin before or after dinner?"}
    ).json()
    assert body["kind"] == "answer"
    assert any(s["medicine"] == "Metformin" for s in body["sources"])
