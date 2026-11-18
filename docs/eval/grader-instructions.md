# Grading chatbot answers

A chatbot answers medicine questions from NHS leaflet passages. I need a second person to check whether each answer is
supported by the passages it cites. No medical knowledge is needed: you compare the answer with the passages only.

**File:** `eval/grading/round1-sheet.csv` (open in Excel, Numbers or Google Sheets). 29 items, in random order.
Columns: `item`, `question`, `answer_to_grade`, `cited_passages` (the leaflet text the answer was built from), then two
columns for you: `grade_1_2_3` and `what_was_wrong`.

## Grade each item 1, 2 or 3

| Grade | Meaning |
|---|---|
| **3** | Every claim in the answer appears in the passages (wording can differ). Nothing important that the question needs is wrongly stated. |
| **2** | Mostly supported, but one detail is overstated, applied to the wrong situation, or added without support (for example a number, a time, a group of people, or "always"). |
| **1** | Contains advice or a fact that is not in the passages, or that contradicts them, or answers a different question in a way that could mislead the person. |

## How to do it

1. Read the question, then the answer.
2. For each claim in the answer (doses, times, "do not", "call 111"), find it in the passages. Passages are separated by `---`.
3. Ignore style, length and spelling. Judge support only.
4. If the answer is cautious or says it cannot help, but what it says is supported, it is a 3.
5. Write the grade in `grade_1_2_3`. For any 1 or 2, write in one line what was wrong ("says 12 hours; passage says 8").
6. Work alone and do not look at any other grades. Send the file back as it is.

## Why

I will compare your grades with mine and report how often we agree. That agreement figure is what tells a reader whether the
"answers supported by the leaflet" number can be trusted.
