# Two-part answers for a reliable demo (#45)

## Intent

A reliable live demo. Step 3 ("I forgot whether I should take my Metformin before or after dinner, and my stomach feels a bit unsettled.") must pass every time with `llama3.2:3b`, and what the audience hears must be a real answer to both parts.

The chat model runs at temperature 0, so the same question and passages give (almost) the same answer each time. Reliability therefore means: one good step-3 answer, no other demo step broken by the change, and a first answer under 10 s on the day.

## Goals

- The step-3 answer covers both the timing (the leaflet says "with food") and the unsettled stomach (feeling sick is a listed side effect), and cites how-to-take and side-effects.
- Every live demo gate step still passes.
- No eval correctness metric gets worse.

## Non-goals

- A content check in the gate (no word matching on the answer).
- A bigger model, a different demo question, or any change to the gate.
- Prompt rules other than the one below. Each extra rule can shift how the 3B model answers other questions.

## Anti-goal

The gate passes while the step-3 answer is hollow ("check your leaflet…"). The stored 3B answer is exactly that.

## Revision (2026-11-17): symptom rule instead of the two-part rule

The two-part rule passed the gate but not the hand read. The raw reply showed why: the model "cited each part" by writing both ids at the end of the answer text (which #44 then strips), and filed the stomach under `card.get_help_if`, the prompt's only place for a symptom. The stomach is not a question to the model; it is a mentioned symptom, and no rule said what to do with one. The side-effects passage already holds the answer.

An in-memory spike chose these two changes in place of the two-part rule (design step 1 below is replaced):

- Before the answer-length rule: `- If the user mentions a symptom or feeling, answer it in the answer text: say whether the passages list it as a side effect, what the passages say to do about it, and when to get help.`
- `card.get_help_if` becomes "a short list of warning signs taken from the passages that mean calling a pharmacist, doctor or 999."

Rejected in the spike: the symptom rule alone (invented "wait until your next meal to take it"), and adding "a common side effect the user mentions is not a warning sign by itself" (turmeric ran to the 20 s timeout and fell back). The rest of the design (gate runs, hand read, eval, to-do) is unchanged.

The first eval rerun dropped refusal to 0.93: turmeric without doses (the eval omits them) made the 3B model repeat one citation id until the timeout. `LlmAnswer.citations` is now capped at `TOP_K` (the 4 passages sent), which Ollama enforces through the schema's `maxItems`.

## Approaches

- **A. The ticket, tightened (chosen):** add the prompt rule, then verify the whole demo and read the actual answer.
- B. A, plus a content check in the gate: rejected. At temperature 0 a careful read gives about the same assurance, and word checks fail on harmless rephrasing.
- C. Change step 3 to a one-part question: kept only as the fallback if A fails, and that is the user's call.
- A bigger model: ruled out. The 8B p50 is 25 s, over the 10 s limit.

## Design

1. **Prompt:** in `prompts/system.txt`, add before the "answer is at most 4 sentences" rule:
   `- If the question asks or mentions more than one thing, answer each part, and cite the passage for each part.`
2. **Live gate:** run all of `tests/test_demo_live.py` (not only step 3) 3 runs in a row with only `llama3.2:3b` loaded (check `ollama ps` first). The gate file is not changed.
3. **Read the answer:** record the step-3 answer text from a passing run. If it does not cover both timing and stomach, stop and report.
4. **Eval:** rerun the 36 questions with the 3B model only. The baseline is commit `37bf319` (the #42 rerun at gate 0.72).
   - Block on correctness only: red-flag recall, red-flag FPR, refusal, answer rate, citation validity. If any of these is worse, stop and report before and after. Do not commit the prompt change.
   - Latency (p50, p95, tokens/s) is reported, not blocking. It moved 3 s between runs with no prompt change. Flag the p95, which is already 15.3 s and over the summary's 15 s model-choice rule.
   - Otherwise update the stored 3B results and the summary.
5. **Unit suite** passes.
6. **Human to-do (`docs/human-todo.md`):**
   - Tick the step-3 "Gate failing" item(s) with the 2026-11-16 numbers and the recorded answer text.
   - Demo run-sheet line: before presenting, run `ollama ps` and stop the 8B and qwen models (untested; the likely cause of the old 12.6–13 s first answer).
   - Note that the stomach part of the step-3 answer is checked by hand, not by the gate.

## Left to the builder

The exact to-do wording, and how the eval is limited to the 3B model (use whatever `eval/run_eval.py` already supports).
