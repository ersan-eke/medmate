# Manual UI checklist

Run `uv run uvicorn --factory backend.app:default_app` and ask the Metformin question.

- [ ] Card shows Summary, What to do and Get help if as lists
- [ ] "Get help if" sits in its own red-bordered block that stands out from the rest
- [ ] A reply with no card (refusal, emergency) shows no card headings
- [ ] An answer whose card has an empty section shows no heading for that section

## My medicines and Today

- [ ] Add Metformin 500 mg morning+evening and Amlodipine 5 mg morning, reload: both persist and Today shows Metformin under Morning and Evening, Amlodipine under Morning
- [ ] Edit an entry, then Remove it: the list and Today update and survive a reload
- [ ] Set `localStorage['medmate.medicines']='oops'` in devtools and reload: the page loads with an empty list
- [ ] Keyboard only (Tab, Space, Enter): add, edit and remove a medicine, tick times, send a question; focus is always visible
- [ ] A+ cycles text 20 → 24 → 28 → 20 px, and the size is kept after a reload

## Spoken answers and avatar

Run `uv run uvicorn --factory backend.app:default_app` in Chrome.

- [ ] Ask the Metformin question: the answer is spoken and the mouth visibly opens and closes with the audio, with a blink every few seconds
- [ ] Ask "Now my chest feels tight.": the 999 message is spoken at once
- [ ] Make `kokoro_engine()` fail (drop it from `engines` in `default_app`): the answer is still spoken by macOS `say` and the mouth still moves
- [ ] Make every engine fail (empty `engines`): the caption shows and nothing breaks
- [ ] Send a new question while the avatar speaks: the audio stops

## Asking by voice

Run `uv run uvicorn --factory backend.app:default_app` in Chrome.

- [ ] Hold "Hold to talk", ask "When should I take metformin?", release: "You asked: ..." shows and is spoken, then the answer is spoken with a card and sources
- [ ] Space on the focused mic button starts recording, Space again stops it
- [ ] Say "Now my chest feels tight": the banner and the 999 message are spoken
- [ ] Hold the mic and say nothing: the "didn't catch that" reply is shown and spoken
- [ ] Deny microphone permission: "Microphone not available. Please type your question." shows and the text box has focus; typing still works
- [ ] Press Send twice quickly: only one `/api/chat` request is made (devtools Network)
- [ ] Press the mic while the avatar speaks: the audio stops

## Avatar portrait

- [ ] With the four PNGs in `web/avatar/`, the portrait shows, the mouth changes between the frames as it speaks, and it blinks every few seconds
- [ ] Delete one PNG and reload: the drawn face is used instead
