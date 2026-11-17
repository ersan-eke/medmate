# Manual UI checklist

Run `uv run uvicorn --factory backend.app:default_app` and ask the Metformin question.

- [x] Card shows Summary, What to do and Get help if as lists
- [x] "Get help if" sits in its own red-bordered block that stands out from the rest
- [x] A reply with no card (refusal, emergency) shows no card headings
- [x] An answer whose card has an empty section shows no heading for that section

## My medicines and Today

- [x] Add Metformin 500 mg morning+evening and Amlodipine 5 mg morning, reload: both persist and Today shows Metformin under Morning and Evening, Amlodipine under Morning
- [x] Edit an entry, then Remove it: the list and Today update and survive a reload
- [x] Set `localStorage['medmate.medicines']='oops'` in devtools and reload: the page loads with an empty list
- [x] Keyboard only (Tab, Space, Enter): add, edit and remove a medicine, tick times, send a question; focus is always visible
- [x] A+ cycles text 20 → 24 → 28 → 20 px, and the size is kept after a reload

## Spoken answers and avatar

Run `uv run uvicorn --factory backend.app:default_app` in Chrome.

- [x] Ask the Metformin question: the answer is spoken and the mouth visibly opens and closes with the audio, with a blink every few seconds
- [x] Ask "Now my chest feels tight.": the 999 message is spoken at once
- [x] Make `kokoro_engine()` fail (drop it from `engines` in `default_app`): the answer is still spoken by macOS `say` and the mouth still moves
- [x] Make every engine fail (empty `engines`): the caption shows and nothing breaks
- [ ] Ask about a decimal dose (Warfarin 2.5mg): it is spoken as "two point five milligrams", with no pause and no "em-gee"
- [ ] Ask about the Metformin liquid (250mg/5ml): it is spoken as "250 milligrams per 5 millilitres", with no "slash"
- [x] Send a new question while the avatar speaks: the audio stops. - no, send is greyed out when it speaks, the hold to talk button stops it though.

## Asking by voice

Run `uv run uvicorn --factory backend.app:default_app` in Chrome.

- [ ] Hold "Hold to talk", ask "When should I take metformin?", release: the question appears in full as your bubble in the thread, "You asked about ..." is spoken, then it is sent and the answer is spoken with a card and sources
- [x] Space on the focused mic button starts recording, Space again stops it
- [x] Right after the page loads (nothing focused), Space starts recording and Space again stops it
- [x] With focus in the question box, the Dose or Note box, a checkbox or another button, Space does its usual job and does not start recording
- [x] Say "Now my chest feels tight": the banner and the 999 message are spoken
- [x] Hold the mic and say nothing: the "didn't catch that" reply is shown and spoken
- [x] Deny microphone permission: "Microphone not available. Please type your question." shows and the text box has focus; typing still works
- [x] Press Send twice quickly: only one `/api/chat` request is made (devtools Network). no send twice, the button is greyed out after first
- [x] Press Send twice quickly: the Send button is disabled while the request waits
- [x] Ask a question, then stop the server (or go offline in devtools) and ask again: the error text shows and the old answer, card and sources are gone
- [x] Press the mic while the avatar speaks: the audio stops

## Avatar portrait

- [x] With the four PNGs in `web/avatar/`, the portrait shows, the mouth changes between the frames as it speaks, and it blinks every few seconds
- [x] Delete one PNG and reload: the drawn face is used instead

## Redesigned page

Run `uv run uvicorn --factory backend.app:default_app` in Chrome. Check each item at 360, 768 and 1280 px wide, at all three text sizes, and with the system in light and dark mode.

- [x] The red "In an emergency call 999" strip stays at the top while scrolling, and on a phone tapping 999 offers to call
- [x] No sideways scrolling at 360 px, even at the largest text size
- [ ] On a laptop screen at the smallest text size, the first screen shows the portrait, the mic, the question box and the reply, and My medicines starts only when you scroll down
- [ ] In the question box, Enter sends the question and a long question wraps onto the next line instead of scrolling sideways
- [x] Before any question, the reply label shows a greeting and three example questions; pressing one asks it
- [x] While waiting, the label says "Looking in your leaflets" with "One moment…", and the old card and sources are gone
- [x] A normal answer prints out as a white label with the card under it and "From the NHS leaflets" links along the bottom
- [x] "Get help if" has a red border and a warning triangle; nothing else on the page is red except the 999 strip and an emergency reply
- [x] Each reply kind shows its own title and icon: emergency "Call 999 now" (solid red, phone icon), not covered "Not in my leaflets", off topic "Medicines only", I'm not sure "Check with your pharmacist", not heard "Let's try again", server error "Let's try again" with "Sorry, something went wrong. Please try again."
- [x] Holding the mic turns the button white with a green border, it reads "Listening…" and a ring pulses; with reduced motion turned on, the ring is still but visible
- [x] Two medicines that interact (Warfarin and Ibuprofen) show an amber warning with a triangle and a "Source: Medicine › Section" link
- [x] Today shows one pill-box compartment per time of day that has a dose, each with its name on a coloured lid; with no doses it says "No doses added yet."
- [x] With no medicines, My medicines says "No medicines yet. Add yours here so I can answer about them."
- [x] Keyboard only: Tab reaches 999, Text size, the mic, the question box, Send, the example questions, the links, and every medicine control in that order, and the focus ring is always visible
- [x] The page works with the network off after the first load (font is served from `web/fonts/`)

## Chat thread (#49)

Not yet run in a browser. Run `uv run uvicorn --factory backend.app:default_app` in Chrome.

- [ ] Questions and replies build up as a thread; only the thread scrolls and the question box stays at the bottom, and the newest message is in view
- [ ] Shift+Enter adds a line, Enter sends
- [ ] The three suggestions are outlined, unfilled bubbles on the right; tapping one sends it, and they vanish after the first question
- [ ] Each reply kind: answer (blue, "From your leaflets"), emergency (red "Call 999 now"), the rest amber with their titles; every title has an icon
- [ ] An answer shows its NHS links and "In your medicines" (Metformin on the list) or "Not in your medicines"; a reply without sources shows no tag
- [ ] Reload keeps the thread; a new tab starts empty; Reset chat empties it and brings the suggestions back
- [ ] In DevTools set `sessionStorage["medmate.thread"]` to `{bad` and reload: the page loads with an empty thread
