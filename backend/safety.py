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
        ("stroke", "Possible stroke", r"\bface\b.{0,20}\bdroop\w*|\bdroop\w* face\b|\bslurred speech\b|\bspeech\b.{0,15}\bslurred\b|\b(arm|leg)\b.{0,15}\b(weak\w*|numb\w*)|\b(weak|numb) (arm|leg)\b|\b(can ?not|can'?t|cant|unable to|trouble|difficulty) (speak\w*|talk\w*)"
                   r"|\bmouth\b.{0,25}\b(dropped|droop\w*|slipped|gone down)\b|\bone side of (his|her|my|their|the) (face|mouth)\b"
                   r"|\b(words|speech|talking)\b.{0,25}\b(jumbled|muddled|garbled|not making sense)\b"),
        # NHS: severe allergic reaction (anaphylaxis)
        ("anaphylaxis", "Severe allergic reaction", r"\b(lips?|tongue|face|throat)\b.{0,25}\b(swell\w*|swollen|closing)\b|\b(swollen|swelling) (lips?|tongue|face|throat)\b"),
        # NHS: overdose / poisoning
        ("overdose", "Possible overdose", r"\boverdos\w*|\btook (too many|double|too much)\b|\btaken (too many|double|too much)\b|\b(took|taken) \d+ times\b|\bswallowed\b.{0,25}\b(whole|entire|lots of)\b"
                     r"|\b(took|taken|had|swallowed|downed)\b.{0,25}\b(whole|entire|full)\b.{0,10}\b(strip|pack\w*|box|bottle|blister)"),
        # NHS: vomiting or coughing blood
        ("bleeding", "Serious bleeding", r"\b(coughing|vomiting|throwing) (up )?blood\b|\bblood in (my )?vomit\b|\bbleeding (heavily|badly|a lot)\b|\b(can ?not|can'?t|cant|unable to) stop bleeding\b|\bbleeding (won'?t|will not|wont|doesn'?t|does not) stop\b|\bcoffee grounds?\b"
                     r"|\bbleed\w*\b.{0,30}\b(won'?t|wont|will not|doesn'?t|does not|isn'?t|not) stop\w*|\b(won'?t|wont|will not) stop bleeding\b"
                     r"|\bblack (poo|stools?|tarry)\b|\b(poo|stools?) (is|are|has been|have been|looks?|went|gone) (all )?black\b"),
        # NHS: suicidal thoughts and self-harm
        ("self_harm", "Self-harm", r"\b(end|take) my (own )?life\b|\b(kill|hurt|harm)(ing)? myself\b|\bwant to die\b|\bsuicidal\b|\b(no|see the|see any) point (in )?(going on|living|carrying on)\b|\b(saving|saved|stockpil\w*) up (my |the |all )?(\w+ )?(tablets|pills)\b|\bend it all\b"),
        # NHS: loss of consciousness
        ("fainting", "Fainting or collapse", r"\bfaint(ed|ing)\b|\bpass(ed|ing)? out\b|\bcollaps\w*|\bblack(ed|ing)? out\b|\bfeel faint\b"),
        # NHS: someone unconscious or having a seizure
        ("unresponsive", "Unconscious or seizure", r"\b(not|isn'?t|is not|won'?t|stopped) (answering|responding|waking up|breathing)\b|\bunconscious\b|\bunresponsive\b|\bseizure\b|\bhaving a fit\b|\bfitting\b|\bconvuls\w*"),
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
# "You can take omeprazole with salbutamol." Not for a drink or food: "you can have a drink" would refuse the leaflet's alcohol advice.
CAN_CLAIM = re.compile(r"\b(can|could|may) (safely )?(take|have|use|be taken)\b", re.IGNORECASE)
NOT_A_MEDICINE = re.compile(r"\b(alcohol|drinks?|drinking|wine|beer|pints?|lager|spirits|whiske?y|gin|vodka|food|meals?|eat\w*|coffee|tea|milk|juice)\b",
                            re.IGNORECASE)


SEQUENCE = re.compile(r"\b(before|after|then)\b", re.IGNORECASE)


def is_combination(question: str, named: set[str]) -> bool:
    """A question about taking things together, or one leaflet medicine after another ("metformin after ibuprofen").
    Before/after count only with two named medicines: "before or after dinner" is a dosing question."""
    return bool(COMBINING.search(question) or len(named) >= 2 and SEQUENCE.search(question))


def claims_safe_combination(question: str, answer: str, named: set[str] = frozenset()) -> bool:
    """A model answer calling a combination safe. Only the table may say that: the 3B model called
    amoxicillin with warfarin safe while citing a leaflet that lists antibiotics as a risk."""
    if not is_combination(question, named):
        return False
    return bool(SAFE_CLAIM.search(answer) or not NOT_A_MEDICINE.search(question) and CAN_CLAIM.search(answer))


def check_interactions(question: str, named: set[str], listed: set[str],
                       interactions: list[Interaction]) -> tuple[list[Interaction], list[Interaction]]:
    """Known pairs of a combination question: (asked, also). Asked pairs join two named medicines, or one named
    medicine and My medicines when the question says "my" ("ibuprofen with my other tablets"); otherwise pairs
    between a named medicine and one only on My medicines come back as `also`, to mention after the answer."""
    if not is_combination(question, named):
        return [], []
    in_question = {m.lower() for m in named}
    on_list = {m.lower() for m in listed} - in_question
    pairs = [(i, {i.medicine_a.lower(), i.medicine_b.lower()}) for i in interactions]
    between_named = [i for i, pair in pairs if pair <= in_question]
    with_list = [i for i, pair in pairs if pair <= in_question | on_list and pair & in_question and pair & on_list]
    if len(in_question) == 1 and re.search(r"\bmy\b", question, re.IGNORECASE):
        return with_list, []
    return between_named, with_list
