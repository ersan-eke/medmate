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
- [ ] Blocked on the voice ticket (#10): the mic button doesn't exist yet, so "press the mic while the avatar speaks stops the audio" is only wired as `avatar.stop()` on a new typed question.
- [ ] Decide: the portrait art (`web/avatar/*.png`) is not made. The drawn face is the only face; image frames still need coding once the art exists.
- [ ] Tick the acceptance boxes on issue #9 and close it.
