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
