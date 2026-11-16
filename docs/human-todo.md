# Human to-do

Things only you can do, collected while the tickets were implemented. Come back here once every ticket is done.

Chat: Claude Code session `af342962-3779-481a-bb50-6e40ca7c63f4` (resume with `claude --resume af342962-3779-481a-bb50-6e40ca7c63f4`).

## #5 Honest refusals and safe fallbacks (commit `7121443`)

- [ ] Decide: the ticket says the "card says ask your pharmacist" for an unrelated question. Today the reply text says it and the card is empty, and the tests assert there is no card. Keep that, or ask for a real card (plan Task 5 step 4 describes one: "This isn't covered in my leaflets." / "Ask your pharmacist or GP.").
- [ ] Decide: the number check counts word numbers, so "one of these" or "ten minutes" can get a correct answer rejected and send it to the fallback. "1,000" only passes because the leaflet splits the same way. Accept, or ask for a fix.
- [ ] Tick the acceptance boxes on issue #5 and close it.

## #7 My medicines list, today's schedule and personal answers (commit `5bc4c50`)

- [ ] Run the "My medicines and Today" section of `docs/manual-ui-checklist.md` in Chrome with `uv run uvicorn --factory backend.app:default_app`: persistence after reload, edit/remove, corrupt `localStorage` reset, keyboard-only use, A+ 20 → 24 → 28 px remembered.
- [ ] Blocked until the leaflet content ticket lands: the manual "Amlodipine 5 mg morning" step needs an Amlodipine leaflet (the real KB has only Metformin and Warfarin).
- [ ] Decide: the page keeps CSS and script inline in `web/index.html` instead of the plan's `styles.css` / `app.js`. The voice ticket (plan Task 10) expects `app.js` to export `renderResponse` and `askQuestion`.
- [ ] Fix the plan / preflight docs: `node --test web/` fails on Node 24; the working command is `node --test web/logic.test.js`.
- [ ] Tick the acceptance boxes on issue #7 and close it.

## Earlier tickets

- [ ] The card checks at the top of `docs/manual-ui-checklist.md` (from commit `ba829a6`) are still unticked.

## #9 Spoken answers with an audio-driven avatar

- [ ] Run the "Spoken answers and avatar" section of `docs/manual-ui-checklist.md` in Chrome: mouth follows the audio, Kokoro removed → `say` still speaks, all engines removed → captions only.
- [ ] Check "press the mic while the avatar speaks stops the audio": the mic now exists (#10), so it is covered by the "Asking by voice" checklist.
- [ ] Decide: the portrait art (`web/avatar/*.png`) is not made. The drawn face is the only face; image frames still need coding once the art exists.
- [ ] Tick the acceptance boxes on issue #9 and close it.

## #10 Asking by voice (hold to talk)

- [ ] Run the "Asking by voice" section of `docs/manual-ui-checklist.md` in Chrome (real microphone, mic denied, double Send). Also tap the mic very briefly (and on the first permission prompt): it must not stay on "Listening…" (fix `740b5d1`, untested in a browser).
- [ ] Not tested in a browser: the page code was only syntax-checked. The server side was checked with webm/opus audio made by ffmpeg.
- [ ] First transcribe downloads Whisper `small.en` weights; run it once online before the offline demo (plan Task 8 step 5, `scripts/fetch_models.py`, is not done).
- [ ] Decide: `scripts/fetch_models.py` and the offline check (plan Task 8 step 5) are in no ticket yet. Ask for it, or do it by hand before the demo.
- [ ] Tick the acceptance boxes on issue #10 and close it.

## #11 Avatar portrait art (commit `0e14f0f`)

- [ ] Make the four images and save them in `web/avatar/` as `portrait.png`, `mouth_half.png`, `mouth_open.png`, `eyes_closed.png` (same square size, aligned). Steps are in the chat for ticket #11.
- [ ] Save the prompts you used to `prompts/avatar.txt`.
- [ ] Run the "Avatar portrait" section of `docs/manual-ui-checklist.md`.
- [ ] Tick the acceptance boxes on issue #11 and close it.

## #12 Works offline with a fast first answer

- [ ] Online, once: `uv run python -m scripts.fetch_models`.
- [ ] Turn Wi-Fi off, start `uv run uvicorn --factory backend.app:default_app`, then do one voice question, one spoken answer and one chat. If anything tries to download, log it in `CHALLENGES.md` and fix it.
- [ ] Time the first chat answer after start on the demo laptop (must be ≤ 10 s; 7 s here with HF offline only).
- [ ] Tick the acceptance boxes on issue #12 and close it.

## #15 Release gates and pre-flight script

- [x] **Gate failing:** demo step 3 ("…before or after dinner, and my stomach feels a bit unsettled.") returns `not_covered` 4 of 4 times with `llama3.2:3b`. Retrieval is right (metformin side-effects and how-to-take chunks, similarity 0.75); the model sets `covered: false`. Fix the prompt or choose a bigger model (ticket #11), or say so in the slides. Do not loosen the test. **Fixed 2026-11-17 (#45):** passes 3 of 3 with only `llama3.2:3b` loaded; step 3 answers in about 6 s warm, 9.5 s on the first run after a cold start.
- [ ] Run `uv run python -m scripts.preflight` with Wi-Fi off at feature freeze and again on demo morning. It must print PASS for all three lines.
- [ ] Not covered by the script: the eval gates (red-flag recall 1.0, refusal ≥ 0.9, hybrid hit@4) belong to ticket #11's `eval/run_eval.py`.
- [ ] Tick the acceptance boxes on issue #15 and close it.

## #32 Page never shows a stale or silent answer (commit `040dff4`)

- [ ] Not tested in a browser. Run the two new items in `docs/manual-ui-checklist.md`: Send disabled while waiting, and the error text clearing the old answer, card and sources when the server stops.
- [ ] Tick the acceptance boxes on issue #32 and close it.

## #31 Number check understands written and grouped numbers (commit `28bfa8c`)

- [ ] Tick the acceptance boxes on issue #31 and close it. 'twenty-five' is a known gap, filed as a new issue.

## #33 Ingest rejects broken leaflets (commit `eedade5`)

- [ ] Tick the acceptance boxes on issues #33 and #23 and close them. Tickets #32 and #33 skipped the separate code-review step; run `/code-review` on them if you want it.

## #26 More emergency phrasings trigger the 999 message (commit `369bca3`, closed)

- [ ] Not covered: no test for the near-miss "is breathing difficulty a side effect of my tablets". The rules fire on it by design (they over-trigger), which the ticket's "behave as the existing rules decide" allows. Say if you want that softened.

## #27 Embedder down gives the pharmacist fallback (commit `db8dcde`, closed)

- [ ] Not tested against real Ollama: nothing checks that `ollama.Client(timeout=10)` actually times out. Stop Ollama, start the app, ask a question, and check the page shows "ask your pharmacist" and not an error.

## #28 Model refusals arrive as refusals (commit `26aa9d1`)

- [ ] Re-run the eval with `llama3.2:3b` and `llama3.1:8b`. The answer schema now requires only `in_scope` and `covered`, so a model can send a covered reply with nothing else. `validate()` rejects and retries it, which could raise the fallback rate.
- [ ] Tick the acceptance boxes on issue #28. It is already closed.

## #29 Server starts warm and rejects a bad index (commit `381740a`, closed)

- [x] **Gate failing:** `tests/test_demo_live.py::test_step3_first_answer_is_fast_and_cites_metformin` takes 12.6-13 s against the 10 s limit, after the warm-up. It fails the same way without this ticket's changes. `llama3.2:3b` and `nomic-embed-text` are installed, and so are `llama3.1:8b` and `qwen2.5:7b`. Not diagnosed: try with the other models unloaded (`ollama ps`, `ollama stop <model>`) and the laptop idle, then re-run `pytest -m slow tests/test_demo_live.py`. The "live smoke test still passes" box on #29 is not met until it does. **Fixed 2026-11-17 (#45):** passes 3 of 3 with only `llama3.2:3b` loaded; step 3 answers in about 6 s warm, 9.5 s on the first run after a cold start.
- [ ] A missing `chunks.json` or `vectors.npy` still gives a raw `FileNotFoundError` at startup, not a friendly message. Only an empty index has one.

## #30 Not-covered check uses every passage (commit `53f3ab3`)

- [ ] `backend/retrieval.py` still has your uncommitted `MIN_SIMILARITY = 0.74` change, with `eval/` and `tests/test_eval_metrics.py` untracked. I committed only my one-line hunk. Commit the rest when the eval work is ready.
- [ ] With 0.74 the gate gives the right result on all 36 eval questions, except turmeric-with-metformin (0.763), which only the model's `covered` flag refuses. Re-check after any index or embedder change.
- [ ] Tick the acceptance boxes on issue #30 and close it.

## #13 Evaluation, threshold tuning and model choice

- [ ] Grade the empty `faithfulness` column (1 to 3) in `eval/results/model-llama3.2-3b.csv` for a sample of answers.
- [ ] Rerun `uv run python -m eval.run_eval --model llama3.2:3b` with nothing else running, to get clean latency and tokens/s for the slides.
- [ ] Decide: p95 latency is 11.2 s against the plan's 8 s (15 s before #40). Accept it, or reduce the retries.
- [ ] Classmate feedback (plan Task 11 step 7) is in no ticket yet.
- [ ] Tick the acceptance boxes on issue #13 and close it.

## #40 Interaction answers in chat

- [ ] Try it in the running app: ask "Can I take my aspirin with my warfarin?", and "Is paracetamol OK with my other medicines?" with warfarin on the list. Check the warning reads well aloud.
- [ ] Decide whether the broad trigger is acceptable: "Can I take warfarin with food?" with ibuprofen on the list also gets the warfarin + ibuprofen warning.
- [ ] Tick the acceptance boxes on issue #40 and close it.

## #41 Answer quality and limitations

- [ ] Check the hand-graded counts in `CHALLENGES.md` (#13 entry) against your own reading before quoting them on a slide.
- [ ] Copy the new "Answer quality of the small model" limitation from the design spec §12 into the README and the limitations slide.
- [ ] Tick the acceptance boxes on issue #41 and close it.

## #45 Two-part answers: symptom rule and citation cap

- [ ] Demo run-sheet: before presenting, run `ollama ps` and stop `llama3.1:8b` and `qwen2.5:7b` (`ollama stop <model>`). Untested, but the likely cause of the old 12.6–13 s first answer.
- [ ] Demo run-sheet: after starting the server, ask one question before presenting. The first answer after a cold start took 9.5 s against the 10 s limit; the startup warm-up does not send the system prompt (`backend/app.py:87-88`). Not fixed here.
- [ ] The stomach part of the step-3 answer is checked by hand, not by the gate. Recorded answer (with the demo list, about 6 s): "You should take your Metformin with food. According to the leaflet, most people take it 1 to 3 times a day with food. If you're unsure, you can also ask a pharmacist or doctor for advice. If your stomach feels unsettled, it's possible that you're experiencing a common side effect of Metformin, such as diarrhoea or tummy pain. You can speak to a pharmacist or doctor if these side effects bother you or do not go away." Card get-help: "side effects that bother you or do not go away".
- [ ] Decide: the same question without doses (eval `per1`) gives invented advice, "it might be a good idea to wait until your next meal to take it", and cites only how-to-take. The answer depends on whether doses are entered. File a ticket or accept.
- [ ] Decide: eval `nea3` (bleeding gums, warfarin) now answers but adds "They may recommend a dental check-up", which is not in the leaflet. `sid2` ("Why does metformin upset my stomach?") now refuses; its old answer invented "metformin increases acid in your stomach".
- [ ] Eval (3B, vs `37bf319`): refusal 1.00 → 1.00, answer rate 0.81 → 0.85, citation validity 1.00, p50 9.2 → 8.5 s, p95 15.3 → 13.0 s. The p95 is now under the summary's 15 s rule.
- [ ] Tick the acceptance boxes on issues #45 and #43 and close them. The ticket's rule text was replaced by the symptom rule; see `docs/superpowers/specs/2026-11-16-two-part-answers-design.md`.
