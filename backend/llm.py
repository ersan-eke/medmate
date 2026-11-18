import logging
import re
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

from .retrieval import TOP_K, Hit

# (chat messages, JSON schema) -> raw JSON string. Raises on transport failure.
Generate = Callable[[list[dict], dict], str]

SYSTEM_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "system.txt").read_text(encoding="utf-8")
TRIAGE_PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "triage.txt").read_text(encoding="utf-8")
ATTEMPTS = 2
TIMEOUT_SECONDS = 20  # a warm 3B answer takes a few seconds; the first-answer gate is 10 s
WARMUP_TIMEOUT_SECONDS = 120  # a cold model load can take a minute
TRIAGE_TIMEOUT_SECONDS = 5  # a yes/no reply from a warm model; a cold one skips triage and the rules still apply
log = logging.getLogger(__name__)
ONES = "one two three four five six seven eight nine".split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
WORD_NUMBERS = {w: str(n) for n, w in enumerate(ONES + ["ten", "eleven", "twelve"], start=1)} | {
    "twice": "2", "half": "0.5"} | {w: str(n) for n, w in zip(range(20, 100, 10), TENS)}
WORD_NUMBERS |= {f"{t} {o}": str(int(WORD_NUMBERS[t]) + int(WORD_NUMBERS[o])) for t in TENS for o in ONES}
# "twenty-five" comes first so it is read as 25, not as 20 and 5.
# "one" is a pronoun more often than a count ("one of the side effects"), so it counts only before a unit.
NUMBER = re.compile(r"\b(?:" + "|".join(TENS) + r")[ -]+(?:" + "|".join(ONES) + r")\b"
                    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\bone(?=\s+(?:tablet|dose|capsule|time)s?\b)|\b(?:"
                    + "|".join(w for w in WORD_NUMBERS if w != "one" and " " not in w) + r")\b", re.IGNORECASE)


class MedicineEntry(BaseModel):
    name: str = Field(max_length=100)
    dose: str = Field("", max_length=100)


class Card(BaseModel):
    summary: str
    what_to_do: list[str]
    get_help_if: list[str]


class LlmAnswer(BaseModel):
    in_scope: bool
    covered: bool
    # A refusal needs only the two flags; validate() requires the rest of a covered answer.
    answer: str = ""
    # Capped at the passages sent in the schema Ollama decodes against, not when parsing: uncapped, the 3B model can
    # repeat one id until the timeout, but a reply that cites too many should still be used, not retried.
    citations: list[str] = Field([], json_schema_extra={"maxItems": TOP_K})
    card: Card | None = None

    @field_validator("citations")
    @classmethod
    def _unbracket(cls, ids: list[str]) -> list[str]:
        # Small models copy the brackets the prompt wraps ids in.
        return [i.strip().strip("[]") for i in ids]

    @field_validator("answer")
    @classmethod
    def _drop_ids(cls, text: str) -> str:
        # Small models write passage ids into the text; their digits would trip the number check.
        # A trailing "Citations: [id], [id]" then leaves "Citations: ," behind, so that label goes too.
        text = re.sub(r"\s*\[[^\]]*#[^\]]*\]", "", text)
        return re.sub(r"\s*\b(citations?|sources?)\s*:[\s,.;]*$", "", text, flags=re.IGNORECASE).strip()


# Every field is required of the model, or a small one leaves out the citations; the defaults only serve parsing.
ANSWER_SCHEMA = LlmAnswer.model_json_schema()
ANSWER_SCHEMA["required"] = list(ANSWER_SCHEMA["properties"])


def answer_schema(ids: list[str]) -> dict:
    """ANSWER_SCHEMA with citations limited to the ids sent: the 3B model invents ids like "omeprazole#important"."""
    citations = ANSWER_SCHEMA["properties"]["citations"] | {"items": {"type": "string", "enum": ids}}
    return ANSWER_SCHEMA | {"properties": ANSWER_SCHEMA["properties"] | {"citations": citations}}


class Triage(BaseModel):
    """One narrow yes/no per NHS 999 sign: the 3B model missed a stroke when asked for one overall judgement."""
    chest_pain: bool
    breathing: bool
    stroke: bool
    allergy: bool
    overdose: bool
    bleeding: bool
    collapse: bool
    self_harm: bool

    @property
    def urgent(self) -> bool:
        return any(self.model_dump().values())


TRIAGE_SCHEMA = Triage.model_json_schema()


def _plain(text: str) -> str:
    """One line with no passage markers, so user-typed text can't pose as instructions or passages."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", text).replace("[", "").replace("]", "").split())


def build_messages(question: str, medicines: list[MedicineEntry], hits: list[Hit]) -> list[dict]:
    passages = "\n\n".join(f"[{h.chunk.id}] {h.chunk.text}" for h in hits)
    listed = "; ".join(_plain(f"{m.name} {m.dose}") for m in medicines) or "none listed"
    user = f"Passages:\n\n{passages}\n\nThe user's medicines: {listed}\n\nQuestion: {_plain(question)}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _as_digits(match: str) -> str:
    """The number a match stands for, as digits: "twenty-five" -> "25", "1,500" -> "1500"."""
    return WORD_NUMBERS.get(" ".join(re.split(r"[ -]+", match.lower())), match.replace(",", ""))


def numbers(text: str) -> set[str]:
    return {_as_digits(m) for m in NUMBER.findall(text)}


def shown_text(answer: LlmAnswer) -> str:
    card = answer.card
    assert card  # only called on covered answers, which validate() has checked have a card
    return " ".join([answer.answer, card.summary, *card.what_to_do, *card.get_help_if])


def validate(raw: str, sent: dict[str, str], doses: str) -> LlmAnswer | str:
    """The answer, or the reason it is unusable (fed back to the model on the retry)."""
    try:
        answer = LlmAnswer.model_validate_json(raw)
    except ValidationError:
        return "Your reply was not valid JSON matching the schema."
    if answer.in_scope and answer.covered:
        if not answer.answer.strip():
            return "Your answer text was empty."
        if answer.card is None:
            return "You gave no card."
        if not answer.citations:
            return "You gave no citations. Cite the ids of the passages you used."
        if unsent := [i for i in answer.citations if i not in sent]:
            return f"These citations were not among the passages: {', '.join(unsent)}. Cite only the ids given."
        allowed = {"999", "111"} | numbers(doses) | numbers(" ".join(sent[i] for i in answer.citations))
        if invented := sorted(numbers(shown_text(answer)) - allowed):
            return f"These numbers are not in the cited passages: {', '.join(invented)}. Use only numbers from them."
    return answer


def ask_llm(question: str, medicines: list[MedicineEntry], hits: list[Hit], generate: Generate) -> LlmAnswer | None:
    messages = build_messages(question, medicines, hits)
    sent = {h.chunk.id: h.chunk.text for h in hits}
    doses = " ".join(m.dose for m in medicines)
    for _ in range(ATTEMPTS):
        try:
            raw = generate(messages, answer_schema(list(sent)))
        except Exception:  # Ollama down, slow or model missing: the page must still get an answer
            log.warning("chat call failed", exc_info=True)
            return None
        result = validate(raw, sent, doses)
        if isinstance(result, LlmAnswer):
            return result
        log.warning("answer rejected: %s", result)
        # At temperature 0 a repeat would return the same reply, so say what was wrong.
        messages = messages[:2] + [{"role": "assistant", "content": raw}, {"role": "user", "content": result}]
    return None


def triage(question: str, generate: Generate) -> bool:
    """Whether the model thinks the question describes an emergency. Any failure counts as no: the rules already ran."""
    messages = [{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": _plain(question)}]
    try:
        return Triage.model_validate_json(generate(messages, TRIAGE_SCHEMA)).urgent
    except Exception:
        log.warning("triage failed", exc_info=True)
        return False


def ollama_generate(model: str, timeout: float = TIMEOUT_SECONDS) -> Generate:
    import ollama

    answer_client = ollama.Client(timeout=timeout)
    triage_client = ollama.Client(timeout=TRIAGE_TIMEOUT_SECONDS)

    def generate(messages: list[dict], schema: dict) -> str:
        response = (triage_client if schema is TRIAGE_SCHEMA else answer_client).chat(
            model=model, messages=messages, format=schema, options={"temperature": 0}, keep_alive="30m"
        )
        return response.message.content

    return generate
