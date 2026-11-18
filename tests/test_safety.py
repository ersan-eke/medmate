import pytest

from backend import safety
from backend.kb import Interaction
from backend.safety import (
    check_interactions,
    check_red_flags,
    claims_safe_combination,
    is_combination,
)

FIRES = {
    "chest_pain": ["Now my chest feels tight.", "I have CHEST PAIN", "is chest pain a side effect of amlodipine?", "my chest hurts", "my chest is really painful", "my chest feels heavy", "There is pressure in my chest.", "chest heaviness", "pain across my chest", "pain in my back and chest", "is this a heart attack?"],
    "breathing": ["I can't breathe", "i cant breathe properly", "I cannot breathe", "struggling to breathe", "trouble breathing", "I'm breathless", "I have difficulty in breathing", "DIFFICULTY IN BREATHING!", "I can't catch my breath", "I couldn't catch my breath"],
    "stroke": ["my face is drooping on one side", "my arm feels weak and my speech is slurred", "slurred speech", "I have a weak arm", "my arm feels numb", "my left leg is numb", "can't speak properly", "I can’t speak", "trouble speaking", "mum's words are all jumbled", "her mouth has dropped on one side", "one side of his face has gone"],
    "anaphylaxis": ["my lips are swelling", "my tongue is swollen", "throat feels like it's closing", "swollen tongue"],
    "overdose": ["I took too many tablets", "I think I overdosed", "took double my dose by mistake", "I took 3 times the dose", "I swallowed a whole bottle of pills", "took too many tablets", "I swallowed the entire packet", "I've had the whole strip again", "took a full box of them", "I took 10 tablets of paracetamol", "I've swallowed twelve pills", "I took fifteen tablets", "I took 10 of my tablets", "I have had 10 paracetamol tablets"],
    "bleeding": ["I'm coughing up blood", "vomiting blood", "there is blood in my vomit", "bleeding heavily", "I can't stop bleeding", "the bleeding won't stop", "bleeding will not stop", "I brought up what looks like coffee grounds", "a cut on my leg that won't stop bleeding", "the bleeding isn't stopping", "my poo is black", "I vomited blood", "I threw up blood", "I threw up some blood", "coughed up blood this morning"],
    "self_harm": ["I want to end my life", "thinking about hurting myself", "I want to kill myself", "I want to die", "I feel suicidal", "there's no point going on", "I've been saving up my tablets", "i don't see the point in going on", "saving up my sertraline tablets", "thinking about suicide", "I want to kill my self", "I'd be better off dead", "does sertraline raise suicide risk?"],  # over-triggers on purpose
    "fainting": ["I fainted this morning", "I keep passing out", "I collapsed", "I feel faint", "I blacked out"],
    "unresponsive": ["he's gone down and isn't answering me", "she's not responding", "my husband is unconscious", "she's having a seizure", "he's having a fit on the floor"],
}
NEAR_MISSES = [
    "what are the side effects of aspirin?",
    "When should I take amlodipine?",
    "Can I take paracetamol with my medicines?",
    "I forgot my evening dose",
    "Does atorvastatin cause muscle pain?",
    "how much water should I drink with it",
    "I had a nosebleed but it stopped",
    "Is a bruise normal on warfarin?",
    "Can I take 2 tablets of paracetamol?",
    "I take 2 tablets twice a day",
    "What pain relief can I take for a chest infection?",
    "pain medication for a chest cold",
    "I need to catch my breath after the stairs",
]


@pytest.mark.parametrize("id,text", [(i, t) for i, ts in FIRES.items() for t in ts])
def test_fires(id, text):
    assert check_red_flags(text).id == id


def test_curly_apostrophe_and_spacing():
    assert check_red_flags("I can’t   breathe").id == "breathing"


@pytest.mark.parametrize("text", ["ＣＨＥＳＴ ＰＡＩＮ", "pain in my\u200bchest", "chest\u200bpain"])
def test_fullwidth_and_zero_width_text(text):
    assert check_red_flags(text).id == "chest_pain"


@pytest.mark.parametrize("text", NEAR_MISSES)
def test_near_miss(text):
    assert check_red_flags(text) is None


def test_every_pattern_has_a_test():
    assert {p[0] for p in safety.PATTERNS} == FIRES.keys()
    assert all(FIRES.values())


@pytest.mark.parametrize("question,answer,flagged", [
    ("Is it safe to take amoxicillin with warfarin?", "Yes, it is safe to take amoxicillin with warfarin.", True),
    ("Can I take metformin with turmeric?", "You can take them together.", True),
    ("Can I take Omeprazole with Salbutamol?", "You can take omeprazole with salbutamol.", True),
    ("Can omeprazole and salbutamol be used together?", "They can be taken together.", True),
    ("Can I take metformin with food?", "Take it with or after a meal.", False),
    ("Can I take metformin after ibuprofen?", "You can take metformin after taking ibuprofen.", True),
    ("Should I take metformin before or after dinner?", "You can take it after dinner.", False),
    ("Does atorvastatin cause muscle pain?", "It is fine for most people.", False),
    ("Can I have a drink with sertraline?", "You can have a drink, but alcohol may make you drowsy.", False),
    ("Is a pint ok with my metformin?", "It is okay to drink a little.", True),  # "okay" still counts for a drink
    ("Can I take amoxicillin with warfarin?", "You can take amoxicillin with warfarin.", True),
    ("Is turmeric ok with metformin?", "There is no harm in taking both.", True),
    ("Is turmeric ok with metformin?", "They are compatible.", True),
    ("Is turmeric ok with metformin?", "Go ahead.", True),
    ("Is turmeric ok with metformin?", "That is alright.", True),
    ("Is turmeric ok with metformin?", "There are no known interactions.", True),
    ("Is turmeric ok with metformin?", "Turmeric won't affect metformin.", True),
    ("Is turmeric ok with metformin?", "Metformin doesn't interact with turmeric.", True),
    ("Does metformin with turmeric hurt?", "Metformin may harm your kidneys if you are dehydrated.", False),
])
def test_claims_safe_combination(question, answer, flagged):
    named = {m for m in ("Metformin", "Ibuprofen") if m.lower() in question.lower()}
    assert claims_safe_combination(question, answer, named) is flagged


IBU_WARF = {"Ibuprofen", "Warfarin"}


@pytest.mark.parametrize("question, named, combination", [
    ("ibuprofen plus warfarin ok", IBU_WARF, True),
    ("ibuprofen + warfarin", IBU_WARF, True),
    ("ibuprofen & warfarin", IBU_WARF, True),
    ("ibuprofen, warfarin", IBU_WARF, True),  # two named medicines are enough
    ("Is ibuprofen or warfarin better?", IBU_WARF, True),
    ("ibuprofen + turmeric?", {"Ibuprofen"}, True),
    ("are ibuprofen and turmeric both ok", {"Ibuprofen"}, True),
    ("can I have both ibuprofen doses", {"Ibuprofen"}, True),
    ("ibuprofen&turmeric", {"Ibuprofen"}, True),
    ("can I combine ibuprofen and turmeric", {"Ibuprofen"}, True),
    ("Should I take ibuprofen before or after dinner?", {"Ibuprofen"}, False),
    ("ibuprofen, how often?", {"Ibuprofen"}, False),
])
def test_is_combination(question, named, combination):
    assert is_combination(question, named) is combination


LEVO_OMEP = Interaction("Levothyroxine", "Omeprazole", "w1", "c1")
WARF_IBU = Interaction("Warfarin", "Ibuprofen", "w2", "c2")


@pytest.mark.parametrize("question, named, listed, asked, also", [
    # Two named medicines: only their pair is asked; the list pair is mentioned after.
    ("Can I take Omeprazole with Salbutamol?", {"Omeprazole", "Salbutamol"}, {"Levothyroxine"}, [], [LEVO_OMEP]),
    # One named medicine and an unknown one: the list is not what was asked.
    ("Can I take omeprazole with amoxicillin?", {"Omeprazole"}, {"Levothyroxine"}, [], [LEVO_OMEP]),
    # "my" with one named medicine asks about the list.
    ("Is ibuprofen OK with my other tablets?", {"Ibuprofen"}, {"Warfarin"}, [WARF_IBU], []),
    ("Can I take warfarin with ibuprofen?", {"Warfarin", "Ibuprofen"}, {"Levothyroxine"}, [WARF_IBU], []),
    ("When do I take omeprazole?", {"Omeprazole"}, {"Levothyroxine"}, [], []),  # not a combination question
    ("Can I take ibuprofen after warfarin?", {"Warfarin", "Ibuprofen"}, set(), [WARF_IBU], []),  # one after the other
])
def test_check_interactions_splits_asked_from_list_pairs(question, named, listed, asked, also):
    assert check_interactions(question, named, listed, [LEVO_OMEP, WARF_IBU]) == (asked, also)
