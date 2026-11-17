import json

from types import SimpleNamespace

from backend.llm import (ANSWER_SCHEMA, answer_schema, TIMEOUT_SECONDS, WARMUP_TIMEOUT_SECONDS, TRIAGE_SCHEMA, TRIAGE_TIMEOUT_SECONDS, MedicineEntry,
                         build_messages, ollama_generate, validate)
from backend.kb import Chunk
from backend.retrieval import TOP_K, Hit

HITS = [
    Hit(Chunk("metformin#how-and-when-to-take-it", "Metformin", "How and when to take it", "Metformin — How\nTake with meals.", "u"), 1.0),
    Hit(Chunk("warfarin#side-effects", "Warfarin", "Side effects", "Warfarin — Side effects\nBruising.", "u"), 0.5),
]

SENT = {h.chunk.id: h.chunk.text for h in HITS}
ID = "metformin#how-and-when-to-take-it"


def raw(**over):
    body = {
        "in_scope": True, "covered": True, "answer": "Take it with meals.",
        "citations": ["metformin#how-and-when-to-take-it"],
        "card": {"summary": "s", "what_to_do": ["a"], "get_help_if": ["b"]},
    } | over
    return json.dumps(body)


def test_prompt_lists_every_chunk_id_and_the_users_medicines():
    text = "\n".join(m["content"] for m in build_messages("when?", [MedicineEntry(name="Aspirin", dose="75 mg")], HITS))
    assert all(h.chunk.id in text for h in HITS)
    assert "Aspirin" in text and "75 mg" in text
    assert "none listed" in "\n".join(m["content"] for m in build_messages("when?", [], HITS))


def test_covered_answer_valid_with_sent_citation():
    assert validate(raw(), SENT, "").answer == "Take it with meals."


def test_covered_answer_without_citation_invalid():
    assert isinstance(validate(raw(citations=[]), SENT, ""), str)


def test_citation_not_sent_invalid():
    assert "made#up" in validate(raw(citations=["made#up"]), SENT, "")


def test_not_covered_needs_no_citation():
    assert not isinstance(validate(raw(covered=False, citations=[]), {}, ""), str)


def test_bad_json_invalid():
    assert isinstance(validate("nope", {}, ""), str)


def test_bracketed_citation_accepted():
    answer = validate(raw(citations=["[metformin#how-and-when-to-take-it]"]), SENT, "")
    assert answer.citations == ["metformin#how-and-when-to-take-it"]


def test_schema_caps_citations_at_the_passages_sent():
    # Without a cap the 3B model can repeat one id until the timeout.
    assert ANSWER_SCHEMA["properties"]["citations"]["maxItems"] == TOP_K


def test_reply_with_more_citations_than_passages_still_parses():
    # The cap is enforced by Ollama while it writes; a reply over it must not fail parsing and cost a retry.
    ids = [f"metformin#s{i}" for i in range(TOP_K + 1)]
    answer = validate(raw(citations=ids), {i: "Take with meals." for i in ids}, "")
    assert not isinstance(answer, str)


def test_passage_ids_removed_from_answer_text():
    pid = "metformin#side-effects-2"
    answer = validate(raw(answer=f"Take it with food. [{ID}] Nausea is common. [{pid}]", citations=[ID, pid]),
                      {ID: "Take with meals.", pid: "Feeling sick is common."}, "")
    assert answer.answer == "Take it with food. Nausea is common."


def test_covered_blank_answer_invalid():
    assert isinstance(validate(raw(answer="  "), SENT, ""), str)


def check(answer, text, doses=""):
    return validate(raw(answer=answer), {ID: text}, doses)


def test_number_not_in_cited_text_rejected():
    reason = check("Take 1000 mg.", "Take 500 mg.", "500 mg")
    assert isinstance(reason, str) and "1000" in reason


def test_word_number_rejected():
    reason = check("Take three tablets.", "Take one tablet.")
    assert isinstance(reason, str) and "3" in reason


def test_one_as_pronoun_is_not_a_number():
    assert not isinstance(check("One of the side effects is nausea.", "Nausea is common."), str)
    assert not isinstance(check("No one should stop it alone.", "Ask your doctor."), str)


def test_one_before_a_unit_is_1():
    assert not isinstance(check("Take 1 tablet.", "Take one tablet."), str)
    assert isinstance(check("Take one tablet.", "Take 2 tablets."), str)


def test_twice_matches_2_both_ways():
    assert not isinstance(check("Take it 2 times a day.", "Take it twice a day."), str)
    assert not isinstance(check("Take it twice a day.", "Take it 2 times a day."), str)


def test_written_tens_and_half_are_numbers():
    assert isinstance(check("Take twenty milligrams.", "Take 10 mg."), str)
    assert not isinstance(check("Take twenty milligrams.", "Take 20 mg."), str)
    assert isinstance(check("Take half a tablet.", "Take one tablet."), str)
    assert not isinstance(check("Take half a tablet.", "Take half a tablet."), str)
    assert not isinstance(check("Take half a tablet.", "Take 0.5 tablet."), str)


def test_written_tens_and_ones_are_one_number():
    assert isinstance(check("Take twenty-five mg.", "Take 20 mg, then 5 mg."), str)
    assert not isinstance(check("Take twenty-five mg.", "Take 25 mg."), str)
    assert not isinstance(check("Take 25 mg.", "Take twenty five mg."), str)
    assert isinstance(check("Take 20 mg.", "Take Twenty-Five mg."), str)


def test_comma_grouped_number_is_one_number():
    assert isinstance(check("Take 1,500 mg.", "Take 1 mg or 500 mg."), str)
    assert not isinstance(check("Take 1,500 mg.", "Take 1500 mg."), str)
    assert not isinstance(check("Take 1500 mg.", "Take 1,500 mg."), str)


def test_written_number_in_card_rejected():
    card = {"summary": "Take twenty mg.", "what_to_do": ["Eat first."], "get_help_if": ["Unwell."]}
    assert isinstance(validate(raw(answer="Take 10 mg.", card=card), {ID: "Take 10 mg."}, ""), str)


def test_decimals_and_ranges():
    assert not isinstance(check("Take 0.5 g.", "Take 0.5 g."), str)
    assert isinstance(check("Take 5 g.", "Take 0.5 g."), str)


def test_user_dose_and_999_allowed():
    assert not isinstance(check("Your 500 mg tablet. Call 999 if unwell.", "Take with food.", "500 mg"), str)


def test_number_only_in_uncited_chunk_rejected():
    sent = {ID: "Take with food.", "other#x": "Take 9 tablets."}
    assert isinstance(validate(raw(answer="Take 9 tablets."), sent, ""), str)


def test_not_covered_skips_number_check():
    assert not isinstance(validate(raw(covered=False, citations=[], answer="Take 77."), SENT, ""), str)


def test_number_in_card_rejected():
    card = {"summary": "Take 4000 mg.", "what_to_do": ["Eat first."], "get_help_if": ["Unwell."]}
    reason = validate(raw(card=card), {ID: "Take 500 mg."}, "")
    assert isinstance(reason, str) and "4000" in reason
    card["summary"] = "Take 500 mg."
    assert not isinstance(validate(raw(answer="Take 500 mg.", card=card), {ID: "Take 500 mg."}, ""), str)


def test_triage_gets_a_shorter_timeout_than_the_answer(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def chat(self, **kwargs):
            return SimpleNamespace(message=SimpleNamespace(content=str(self.timeout)))

    monkeypatch.setattr("ollama.Client", FakeClient)
    generate = ollama_generate("m")
    assert generate([], TRIAGE_SCHEMA) == str(TRIAGE_TIMEOUT_SECONDS)
    assert generate([], ANSWER_SCHEMA) == str(TIMEOUT_SECONDS)
    assert TRIAGE_TIMEOUT_SECONDS < TIMEOUT_SECONDS


def test_generate_timeout_can_be_raised_for_warm_up(monkeypatch):
    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def chat(self, **kwargs):
            return SimpleNamespace(message=SimpleNamespace(content=str(self.timeout)))

    monkeypatch.setattr("ollama.Client", FakeClient)
    assert ollama_generate("m", timeout=WARMUP_TIMEOUT_SECONDS)([], ANSWER_SCHEMA) == str(WARMUP_TIMEOUT_SECONDS)
    assert WARMUP_TIMEOUT_SECONDS > TIMEOUT_SECONDS



def test_citations_label_left_in_the_answer_is_dropped():
    answer = validate(raw(answer="Take it with meals. Citations: [metformin#how-and-when-to-take-it],"), SENT, "")
    assert answer.answer == "Take it with meals."

def test_answer_schema_limits_citations_to_the_ids_sent():
    schema = answer_schema(list(SENT))
    assert schema["properties"]["citations"]["items"]["enum"] == list(SENT)
    assert schema["properties"]["citations"]["maxItems"] == TOP_K
    assert "enum" not in ANSWER_SCHEMA["properties"]["citations"]["items"]  # the shared schema is untouched
