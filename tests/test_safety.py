import pytest

from backend import safety
from backend.safety import check_red_flags

FIRES = {
    "chest_pain": ["Now my chest feels tight.", "I have CHEST PAIN", "is chest pain a side effect of amlodipine?", "my chest hurts", "my chest is really painful"],
    "breathing": ["I can't breathe", "i cant breathe properly", "I cannot breathe", "struggling to breathe", "trouble breathing", "I'm breathless"],
    "stroke": ["my face is drooping on one side", "my arm feels weak and my speech is slurred", "slurred speech"],
    "anaphylaxis": ["my lips are swelling", "my tongue is swollen", "throat feels like it's closing", "swollen tongue"],
    "overdose": ["I took too many tablets", "I think I overdosed", "took double my dose by mistake", "I took 3 times the dose"],
    "bleeding": ["I'm coughing up blood", "vomiting blood", "there is blood in my vomit", "bleeding heavily"],
    "self_harm": ["I want to end my life", "thinking about hurting myself", "I want to kill myself", "I want to die", "I feel suicidal"],
    "fainting": ["I fainted this morning", "I keep passing out", "I collapsed", "I feel faint", "I blacked out"],
}
NEAR_MISSES = [
    "what are the side effects of aspirin?",
    "When should I take amlodipine?",
    "Can I take paracetamol with my medicines?",
    "I forgot my evening dose",
    "Does atorvastatin cause muscle pain?",
    "how much water should I drink with it",
]


@pytest.mark.parametrize("id,text", [(i, t) for i, ts in FIRES.items() for t in ts])
def test_fires(id, text):
    assert check_red_flags(text).id == id


def test_curly_apostrophe_and_spacing():
    assert check_red_flags("I can’t   breathe").id == "breathing"


@pytest.mark.parametrize("text", NEAR_MISSES)
def test_near_miss(text):
    assert check_red_flags(text) is None


def test_every_pattern_has_a_test():
    assert {p[0] for p in safety.PATTERNS} == FIRES.keys()
    assert all(FIRES.values())
