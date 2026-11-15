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

- [ ] Make the four images and save them in `web/avatar/` as `portrait.png`, `mouth-half.png`, `mouth-open.png`, `eyes-closed.png` (same square size, aligned). Steps are in the chat for ticket #11.
- [ ] Save the prompts you used to `prompts/avatar.txt`.
- [ ] Run the "Avatar portrait" section of `docs/manual-ui-checklist.md`.
- [ ] Tick the acceptance boxes on issue #11 and close it.

## #12 Works offline with a fast first answer

- [ ] Online, once: `uv run python -m scripts.fetch_models`.
- [ ] Turn Wi-Fi off, start `uv run uvicorn --factory backend.app:default_app`, then do one voice question, one spoken answer and one chat. If anything tries to download, log it in `CHALLENGES.md` and fix it.
- [ ] Time the first chat answer after start on the demo laptop (must be ≤ 10 s; 7 s here with HF offline only).
- [ ] Tick the acceptance boxes on issue #12 and close it.

## #15 Release gates and pre-flight script

- [ ] **Gate failing:** demo step 3 ("…before or after dinner, and my stomach feels a bit unsettled.") returns `not_covered` 4 of 4 times with `llama3.2:3b`. Retrieval is right (metformin side-effects and how-to-take chunks, similarity 0.75); the model sets `covered: false`. Fix the prompt or choose a bigger model (ticket #11), or say so in the slides. Do not loosen the test.
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

- [ ] **Gate failing:** `tests/test_demo_live.py::test_step3_first_answer_is_fast_and_cites_metformin` takes 12.6-13 s against the 10 s limit, after the warm-up. It fails the same way without this ticket's changes. `llama3.2:3b` and `nomic-embed-text` are installed, and so are `llama3.1:8b` and `qwen2.5:7b`. Not diagnosed: try with the other models unloaded (`ollama ps`, `ollama stop <model>`) and the laptop idle, then re-run `pytest -m slow tests/test_demo_live.py`. The "live smoke test still passes" box on #29 is not met until it does.
- [ ] A missing `chunks.json` or `vectors.npy` still gives a raw `FileNotFoundError` at startup, not a friendly message. Only an empty index has one.

## #30 Not-covered check uses every passage (commit `53f3ab3`)

- [ ] `backend/retrieval.py` still has your uncommitted `MIN_SIMILARITY = 0.74` change, with `eval/` and `tests/test_eval_metrics.py` untracked. I committed only my one-line hunk. Commit the rest when the eval work is ready.
- [ ] With 0.74 the gate gives the right result on all 36 eval questions, except turmeric-with-metformin (0.763), which only the model's `covered` flag refuses. Re-check after any index or embedder change.
- [ ] Tick the acceptance boxes on issue #30 and close it.
