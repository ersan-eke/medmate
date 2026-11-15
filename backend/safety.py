import re
from dataclasses import dataclass


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
        ("chest_pain", "Chest pain", r"\bchest\b.{0,20}\b(pain\w*|tight\w*|pressure|crushing|hurt\w*)\b|\b(pain|tightness|pressure) in (my |the )?chest\b"),
        # NHS: difficulty breathing
        ("breathing", "Difficulty breathing", r"\b(can ?not|can'?t|cant|unable to|struggling to|hard to|difficulty) breath\w*|\bshort(ness)? of breath\b|\btrouble breathing\b|\bbreathless\w*"),
        # NHS: stroke FAST signs
        ("stroke", "Possible stroke", r"\bface\b.{0,20}\bdroop\w*|\bdroop\w* face\b|\bslurred speech\b|\bspeech\b.{0,15}\bslurred\b|\barm\b.{0,15}\bweak\b"),
        # NHS: severe allergic reaction (anaphylaxis)
        ("anaphylaxis", "Severe allergic reaction", r"\b(lips?|tongue|face|throat)\b.{0,25}\b(swell\w*|swollen|closing)\b|\b(swollen|swelling) (lips?|tongue|face|throat)\b"),
        # NHS: overdose / poisoning
        ("overdose", "Possible overdose", r"\boverdos\w*|\btook (too many|double|too much)\b|\btaken (too many|double|too much)\b|\b(took|taken) \d+ times\b"),
        # NHS: vomiting or coughing blood
        ("bleeding", "Serious bleeding", r"\b(coughing|vomiting|throwing) (up )?blood\b|\bblood in (my )?vomit\b|\bbleeding (heavily|badly|a lot)\b"),
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
