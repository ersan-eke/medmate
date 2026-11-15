import json
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from .retrieval import Hit

# (chat messages, JSON schema) -> raw JSON string. Raises on transport failure.
Generate = Callable[[list[dict], dict], str]

SYSTEM_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "system.txt").read_text()
ATTEMPTS = 2


class MedicineEntry(BaseModel):
    name: str = Field(max_length=100)
    dose: str = Field("", max_length=100)
    times: list[Literal["morning", "midday", "evening", "bedtime"]] = []
    note: str = Field("", max_length=100)


class Card(BaseModel):
    summary: str
    what_to_do: list[str]
    get_help_if: list[str]


class LlmAnswer(BaseModel):
    in_scope: bool
    covered: bool
    answer: str
    citations: list[str]
    card: Card

    @field_validator("citations")
    @classmethod
    def _unbracket(cls, ids: list[str]) -> list[str]:
        # Small models copy the brackets the prompt wraps ids in.
        return [i.strip().strip("[]") for i in ids]


ANSWER_SCHEMA = LlmAnswer.model_json_schema()


def build_messages(question: str, medicines: list[MedicineEntry], hits: list[Hit]) -> list[dict]:
    passages = "\n\n".join(f"[{h.chunk.id}] {h.chunk.text}" for h in hits)
    listed = "; ".join(f"{m.name} {m.dose}".strip() for m in medicines) or "none listed"
    user = f"Passages:\n\n{passages}\n\nThe user's medicines: {listed}\n\nQuestion: {question}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def validate(raw: str, sent_ids: set[str]) -> LlmAnswer | str:
    """The answer, or the reason it is unusable (fed back to the model on the retry)."""
    try:
        answer = LlmAnswer.model_validate_json(raw)
    except ValidationError:
        return "Your reply was not valid JSON matching the schema."
    if answer.in_scope and answer.covered:
        if not answer.answer.strip():
            return "Your answer text was empty."
        if not answer.citations:
            return "You gave no citations. Cite the ids of the passages you used."
        if unsent := [i for i in answer.citations if i not in sent_ids]:
            return f"These citations were not among the passages: {', '.join(unsent)}. Cite only the ids given."
    return answer


def ask_llm(question: str, medicines: list[MedicineEntry], hits: list[Hit], generate: Generate) -> LlmAnswer | None:
    messages = build_messages(question, medicines, hits)
    sent_ids = {h.chunk.id for h in hits}
    for _ in range(ATTEMPTS):
        try:
            raw = generate(messages, ANSWER_SCHEMA)
        except Exception:  # Ollama down or model missing: the page must still get an answer
            return None
        result = validate(raw, sent_ids)
        if isinstance(result, LlmAnswer):
            return result
        # At temperature 0 a repeat would return the same reply, so say what was wrong.
        messages = messages[:2] + [{"role": "assistant", "content": raw}, {"role": "user", "content": result}]
    return None


def ollama_generate(model: str) -> Generate:
    import ollama

    def generate(messages: list[dict], schema: dict) -> str:
        response = ollama.chat(
            model=model, messages=messages, format=schema, options={"temperature": 0}, keep_alive="30m"
        )
        return response.message.content

    return generate
