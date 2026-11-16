import re
from dataclasses import dataclass

from .kb import Interaction


@dataclass(frozen=True)
class RedFlag:
    id: str
    label: str


# Deliberately over-triggers: a symptom phrase fires even inside a medicine question.
# Each pattern follows the matching NHS "call 999" guidance.
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (id, label, re.compile(rx, re.IGNORECASE))
    for id, label, rx in [
        # NHS: chest pain / tightness, call 999
        ("chest_pain", "Chest pain", r"\bchest\b.{0,20}\b(pain\w*|tight\w*|pressure|heav\w*|crushing|hurt\w*)\b|\b(pain|tightness|pressure) in (my |the )?chest\b"),
        # NHS: difficulty breathing
        ("breathing", "Difficulty breathing", r"\b(can ?not|can'?t|cant|unable to|struggling to|hard to|difficulty( in)?) breath\w*|\bshort(ness)? of breath\b|\btrouble breathing\b|\bbreathless\w*"),
        # NHS: stroke FAST signs
        ("stroke", "Possible stroke", r"\bface\b.{0,20}\bdroop\w*|\bdroop\w* face\b|\bslurred speech\b|\bspeech\b.{0,15}\bslurred\b|\b(arm|leg)\b.{0,15}\b(weak\w*|numb\w*)|\b(weak|numb) (arm|leg)\b|\b(can ?not|can'?t|cant|unable to|trouble|difficulty) (speak\w*|talk\w*)"),
        # NHS: severe allergic reaction (anaphylaxis)
        ("anaphylaxis", "Severe allergic reaction", r"\b(lips?|tongue|face|throat)\b.{0,25}\b(swell\w*|swollen|closing)\b|\b(swollen|swelling) (lips?|tongue|face|throat)\b"),
        # NHS: overdose / poisoning
        ("overdose", "Possible overdose", r"\boverdos\w*|\btook (too many|double|too much)\b|\btaken (too many|double|too much)\b|\b(took|taken) \d+ times\b|\bswallowed\b.{0,25}\b(whole|entire|lots of)\b"),
        # NHS: vomiting or coughing blood
        ("bleeding", "Serious bleeding", r"\b(coughing|vomiting|throwing) (up )?blood\b|\bblood in (my )?vomit\b|\bbleeding (heavily|badly|a lot)\b|\b(can ?not|can'?t|cant|unable to) stop bleeding\b|\bbleeding (won'?t|will not|wont|doesn'?t|does not) stop\b"),
        # NHS: suicidal thoughts and self-harm
        ("self_harm", "Self-harm", r"\b(end|take) my (own )?life\b|\b(kill|hurt|harm)(ing)? myself\b|\bwant to die\b|\bsuicidal\b"),
        # NHS: loss of consciousness
        ("fainting", "Fainting or collapse", r"\bfaint(ed|ing)\b|\bpass(ed|ing)? out\b|\bcollaps\w*|\bblack(ed|ing)? out\b|\bfeel faint\b"),
    ]
]


def check_red_flags(text: str) -> RedFlag | None:
    text = " ".join(text.lower().replace("’", "'").split())
    for id, label, rx in PATTERNS:
        if rx.search(text):
            return RedFlag(id, label)
    return None


COMBINING = re.compile(r"\b(with|together|and|mix\w*|alongside|same time|other)\b", re.IGNORECASE)
# Over-triggers on purpose: a false match turns an answer into a pharmacist referral, never into harm.
SAFE_CLAIM = re.compile(r"\b(safe|fine|okay|ok|no problem|no issues?)\b|\b(take|have|use) (them|it|these|both) together\b",
                        re.IGNORECASE)


def claims_safe_combination(question: str, answer: str) -> bool:
    """A model answer calling a combination safe. Only the table may say that: the 3B model called
    amoxicillin with warfarin safe while citing a leaflet that lists antibiotics as a risk."""
    return bool(COMBINING.search(question) and SAFE_CLAIM.search(answer))


def check_interactions(question: str, named: set[str], listed: set[str],
                       interactions: list[Interaction]) -> list[Interaction]:
    """Known pairs a combination question asks about: one medicine named, the other named or on the list."""
    if not COMBINING.search(question):
        return []
    in_question = {m.lower() for m in named}
    known = in_question | {m.lower() for m in listed}
    pairs = [(i, {i.medicine_a.lower(), i.medicine_b.lower()}) for i in interactions]
    return [i for i, pair in pairs if pair <= known and pair & in_question]
