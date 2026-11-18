# Grading chatbot answers (final run)

A chatbot answers medicine questions from NHS leaflet passages. Please check whether each answer is supported by the
passages it cites. No medical knowledge is needed: you compare the answer with the passages only. This is the same job
as round 1, with two rules made clearer and two new columns.

**File:** `final-sheet.csv` (open in Excel, Numbers or Google Sheets), in random order. There are about 100 items, so
do them in two or three sittings; stop between items, not in the middle of one.

| column | what it is |
|---|---|
| `item` | the item number |
| `earlier_message` | for a chat, what the person said first; empty for a single question |
| `question` | what the person asked (in a chat, their second message) |
| `answer_to_grade` | the chatbot's answer, then the card shown under it (Summary, What to do, Get help if) |
| `cited_passages` | the leaflet text the answer was built from, and an interaction-table row if the answer used one; passages are separated by `---` |
| `grade_1_2_3` | for you |
| `what_was_wrong` | for you, for any 1 or 2 |

## Grade each item 1, 2 or 3

| Grade | Meaning |
|---|---|
| **3** | Every claim in the answer and the card appears in the passages (wording can differ). Nothing important that the question needs is wrongly stated. |
| **2** | Mostly supported, but one detail is overstated, applied to the wrong situation, or added without support (for example a number, a time, a group of people, or "always"). |
| **1** | Contains advice or a fact that is not in the passages, or that contradicts them, or answers a different question in a way that could mislead the person. |

Two rules round 1 left open:

- **"May" made certain is a 2.** If a passage says something *may* happen, *some people* need it, or a doctor *may
  suggest* it, and the answer states it as definite or as applying to everyone, grade 2.
- **A chat is judged as a whole.** Read `earlier_message` first. The answer must fit what the person said there: an
  answer that is supported by the passages but ignores or contradicts the earlier message (the wrong medicine, the
  wrong person, a dose they already took) is a 1 or 2 by the same rubric.

## How to do it

1. Read the earlier message (if any), the question, then the answer and the card.
2. For each claim (doses, times, "do not", "call 111"), find it in the passages.
3. Ignore style, length and spelling. Judge support only.
4. If the answer is cautious or says it cannot help, but what it says is supported, it is a 3.
5. Write the grade in `grade_1_2_3`. For any 1 or 2, write in one line what was wrong ("says 12 hours; passage says 8").
6. Work alone and do not look at any other grades. Send the file back as it is.

## Worked examples (from round 1)

**3.** "When should I take amlodipine?" Answer: "once a day, at the same time every day. You can take it before or
after eating or drinking." Passage: "take it once a day, at the same time every day. You can take it before or after
eating or drinking." Every claim is there.

**3.** "What time of day should I take atorvastatin?" Answer: "once a day, try to take it at the same time each day."
Passage: "take it once a day – try to take it at the same time each day." The passage gives no time of day, and
neither does the answer.

**2.** "is a glass of wine with tea alright on atorvastatin" Answer: "...try to limit how much alcohol you drink... A
glass of wine with tea is likely to be alright." Passage: "try to limit how much alcohol you drink". The passage gives
no safe amount; "likely to be alright" is added. All three graders gave 2.

**2.** "whens the best time to take the very first [ramipril]" Answer: "You'll take the first dose before bedtime."
Passage: "Your doctor may suggest that you take your first dose before bedtime." A "may suggest" stated as certain:
the rule above. Both friends gave 2.

**1.** "am I allowed to drive on sertraline" Answer: "You should not drive while taking sertraline." Passage: "If
you're told to go to A&E, do not drive." The advice is taken from a different situation and could mislead. All three
gave 1.

**1.** "should I take my Metformin before or after dinner, and my stomach feels a bit unsettled" Answer: "...it might
be a good idea to wait until your next meal to take it." Passage: "Most people take it 1 to 3 times a day with food."
Waiting for the next meal is not in the passage and changes when the person takes it. All three gave 1.

## Why

The answers are graded by both of you and by Claude, each blind. The report gives all three grades and how often each
pair agrees (with Cohen's kappa, which corrects that agreement for chance). That agreement is what tells a reader
whether the "answers supported by the leaflet" number can be trusted; disagreements are reported, not argued away.
