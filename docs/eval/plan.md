# Evaluation plan

Two kinds of question sets. Nothing else.

| | Dev | Final |
|---|---|---|
| files | `eval/questions.jsonl` (47), `eval/heldout.jsonl` (10), `eval/dev.jsonl` (104), `eval/dev_chats.jsonl` (20 chats) | `eval/final.jsonl` (239 items, 64 of them chats) |
| use | change code, prompts and rules; look at failures freely | run **once** on frozen code; report these numbers |
| tuned on? | yes | never |

`questions.jsonl` and `heldout.jsonl` stay separate files because the similarity-gate tuning and its tests read them.
`dev.jsonl` is the old `variety_dev`, `variety_test` and `emergency_fresh` merged; each row has a `source` field.
`dev_chats.jsonl` was written by Claude, so every friend chat stays in the final set; it is a separate file so
`run_eval --set dev` stays single-turn until `run_eval` supports chats.
All of dev has been seen, so it can only show that nothing broke, not how well the system does on new questions.

Raw friend files stay in `content/` (not in git). Grading lives in `eval/grading/`.

## Final set

| | single question | chat (label is message 2) | total |
|---|---|---|---|
| emergency | 61 | 13 | 74 |
| answer | 77 | 38 | 115 |
| not covered | 27 | 7 | 34 |
| off-topic | 10 | 6 | 16 |

- Sources: round 1 `friend_a` (47), `friend_b` (44); round 2 `round2_friend1` (53, ids `r2x-`), `round2_friend2`
  (57, ids `r2t-`); round 3, chats only (`docs/eval/friend-instructions-chats.md`), `round3_friend1` (20, `r3x-`),
  `round3_friend2` (18, `r3t-`). 120 items are friend 1's (`friend_a` and the `*_friend1` rounds), 119 friend 2's.
- Chats are `history` plus `question`; `expect_kind_first` is the label of message 1. Message 1 is labelled when it
  asks something or reports a missed dose or a symptom ("i forgot my ramipril this morning", "my ankles have been a bit
  puffy since i started amlodipine"); it is empty, and not scored, when it only says who takes what ("i take warfarin
  every day"). Message 1 is scored where it has a label (45 of 64).
- Labels start from the friends' labels and were checked against `data/leaflets` and `data/interactions.csv`:
  - interaction-table pairs are `answer` (the system answers from the table and adds the pharmacist advice). The table
    holds every pair a leaflet names, by name or by a class that plainly contains the other medicine ("other blood
    pressure medicines" holds ramipril); `CLASS_NAMES` in `backend/kb.py` lists the classes and the table check
    enforces it. All 66 pairs were checked against the leaflets on 18 Nov, which added 7 class pairs, before any run;
  - leaflet-covered items are `answer`: small bruises, muscle aches, crushing ramipril (round 1); levothyroxine with
    calcium (the leaflet lists calcium supplements), stopping ramipril once blood pressure is lower (the leaflet has
    that heading) (round 2); levothyroxine and coffee, omeprazole capsules with water, ramipril or warfarin with
    the table pairs named in a chat (round 3);
  - a pair the leaflets do not name that way is `not_covered`, including a class whose examples are other medicines
    (amlodipine with atorvastatin: "medicines for high blood pressure or heart disease, such as diltiazem or verapamil");
  - a question the leaflet does not answer is `not_covered` even when it names a covered medicine (aspirin before a
    tooth extraction, salbutamol in the fridge, a blood-test value, a dose change);
  - `emergency` follows the NHS 999 and A&E signs where the leaflet is milder: a whole box or bottle or 10 or more
    tablets (as `ef05` in dev), black tarry poo, a head injury on warfarin with confusion and drowsiness (`r3t-C26`).
    Without such a sign the leaflet wins, which is why the amlodipine overdoses below are left out.
- Left out as ambiguous: `fb-06` and `r2x-E30` (6 or 7 amlodipine, leaflet says 111 not 999), `fb-15` (anxiety or heart
  attack), `fb-16` (bruise after a knock), `fb-18` (sprint, tight chest), `r2x-L13` (2-second chest twinge),
  `r2x-L14` (streak of blood after constipation on ibuprofen), `r2x-L16` (night sweats on sertraline, not a listed
  side effect and close to serotonin syndrome), `r3t-C24` (how long before football to use salbutamol: the leaflet
  says before exercise but gives no time), `fa-E08` ("loads more" metformin with drowsiness: no amount and no 999 sign,
  and the leaflet says 111, as the amlodipine overdoses), `r3t-C23` (an extra omeprazole capsule in the evening: the
  leaflet allows twice a day but the change is the person's own, so it is half dose change, half answer).
- Hard on purpose: `r2x-C10` says "her other tablet for her thyroid" without naming levothyroxine.
- Labels are frozen. They may change only before the first run, never after seeing answers.
- Known cost kept in the set: `fb-31`, `fb-45` and `r2x-I06` ask about ibuprofen with paracetamol. The leaflet says adults
  can, but the safe-combination guard turns a "you can take" answer into a pharmacist referral, so these may score as misses.
  `fb-35` asks whether ramipril and amlodipine clash with levothyroxine; the table answers the ramipril–amlodipine pair
  it names, so it passes on label while the levothyroxine part goes unanswered (table answers are not graded).
- Kept as labelled: `fb-48` ("is it safe with my other tablet" after levothyroxine, `not_covered`): the other tablet is
  never named, so nothing can be checked and a referral is the right reply.

## Grading (faithfulness)

Round 1: both friends graded the same 29 answers (`eval/grading/round1-sheet.csv`, every graded answer from the main and
variety_test runs), blind to each other and to Claude. `eval/grading/round1-grades.csv` has all three grades and notes.

| pair | same grade | Cohen's kappa |
|---|---|---|
| friend 1 – friend 2 | 25 of 29 | 0.74 |
| Claude – friend 1 | 24 of 29 | 0.67 |
| Claude – friend 2 | 22 of 29 | 0.49 |

Where both friends agreed and Claude did not, Claude was softer on items 3 and 26 (3 against 2: a "may" stated as a
definite) and differed by one on items 13 and 28 (1 against 2, and 2 against 1).
The final run's answers are graded by both friends and Claude, all blind, and the report gives all three and their
agreement. Disagreements are reported, not argued away.

### What each grader gets for the final run

Everything needed to judge support, nothing that hints at the expected result:

- `docs/eval/grader-instructions-final.md`: the round-1 rubric with the two rules round 1 left open (a "may" or "some
  people" stated as certain is a 2; a chat is judged as a whole, with its earlier message) and two worked examples per
  grade from round 1 (all three graders agreed, except the second 2, where both friends did: the "may" rule itself).
- `eval/grading/final-sheet.csv`, built by `eval/grader_sheet.py`: shuffled, one row per answer the model wrote,
  `item`, `earlier_message`, `question`, `answer_to_grade` (the answer and the card shown under it, since the person
  reads both; round 1 graded the answer only), `cited_passages` (the exact leaflet text, plus the interaction-table row
  when the answer used it), then `grade_1_2_3` and `what_was_wrong`.
- Not given: the expected label, the item's source, the model, anyone else's grades.

Fixed replies (the 999 card, the off-topic and not-covered refusals) and answers taken word for word from the
interaction table are not graded: they are scored by label, and the report gives the number of table answers.

## Order of work

1. Done: sets merged, final set built and labelled, rounds 2 and 3 added, soundness check (below).
2. Done: round-1 grading.
3. Optional before the freeze: a pharmacist (or a third person with the leaflets) checks the labels Claude changed or
   decided (the list above, about 30 items). That is the one part of the set no outsider has checked.
4. Build the multi-turn feature and `run_eval` chat support; tune on `dev_chats.jsonl`. Adversarial dev set.
5. Grade the 16 variety_dev answers (friends and Claude, blind) if a dev faithfulness number is wanted.
6. Keep tuning on dev until done; rerun `questions.jsonl` and dev on the chosen model after the last change.

### Final run

7. Freeze: commit everything (code, prompts, `data/`, this plan). The run refuses a dirty tree, so the commit it
   stores is the code that ran.
8. Prepare the machine: idle, on power, nothing else using Ollama (stop the app). `ollama ps`, then `ollama stop` every
   model except `llama3.2:3b` and `nomic-embed-text`; the run refuses to start otherwise.
9. Run once: `uv run python -m eval.run_eval --model llama3.2:3b --set final`. It writes
   `eval/results/final-llama3.2-3b.json` before the first question (commit, start time, the loaded models' digests),
   so it cannot be started a second time, even after a crash. A crash is reported as a crash, not rerun.
10. Commit the results as they are.

### Grading

11. `uv run python -m eval.grader_sheet --set final --model llama3.2:3b` writes `eval/grading/final-sheet.csv` (for the
    graders) and `eval/grading/final-grades.csv` (item, run id, one grade and note column per grader; never sent).
12. Send each friend the sheet and `docs/eval/grader-instructions-final.md`, separately. Claude grades in a fresh
    session that is given only those two files, before seeing the friends' grades.
13. Copy each grader's `grade_1_2_3` and `what_was_wrong` into their columns of `final-grades.csv` by `item`; commit.

### Report

14. `uv run python -m eval.report --set final --model llama3.2:3b` writes `eval/results/final-llama3.2-3b-report.md`:
    passes per expected reply (single, chat, together) with 95% ranges, over-triggering, emergencies caught by the
    phrases or only by the model step, table answers, hit@4, citation validity, every miss, and faithfulness per
    grader with each pair's agreement and Cohen's kappa. It calls no model, so it can be rerun as grades come in.
15. Write up with ranges ("60 of 62"), the limitations, and what failed. Do not fix and rerun the final set; further
    fixes count as a new version and need a new final set.

## Soundness check (18 Nov, after round 3)

What was checked, by script over all five files:

- Every row has a known `expect_kind`, a question, and `history` exactly when `category` is `chat`. Round 1 stored
  statement-only first messages as `null`; they are `""` now, as in the later rounds.
- No ID appears twice in or across the sets.
- Leaks between dev and final, by word overlap: the closest pairs share a topic (puffs a day, tea after levothyroxine),
  not wording. One dev chat (`dc04`) was close to `fa-N02` because Claude wrote the dev chats after reading the final
  set; it was reworded to a different medicine. Claude has read every final item, so no Claude-written item may join the
  final set, and tuning must not target a final item from memory.
- Near-duplicates inside final: 7 pairs by fuzzy match, 4 by the same friend across rounds (swollen tongue on ramipril,
  grapefruit on atorvastatin, pints on sertraline) and 3 across friends (`fa-E07`/`r2t-E27`, `fa-N05`/`r2t-N14`,
  `fb-31`/`r2x-I06`). Kept: they test different wording, but they are not
  independent, so a miss on one is usually a miss on both.

What this means for the report:

- Report per class, never one overall accuracy. Emergencies are 31% of the set, far more than real use, so an overall
  number mostly measures the emergency check.
- Emergency recall is the headline: 74 items, so 74 of 74 still allows a true recall of about 95%; one miss lowers that
  to about 93% (95% Wilson intervals, as `eval/report.py` prints them). Give the count, the range and each miss.
- Over-triggering is measured on the 62 look-alike and normal-question items (26 and 36) plus every non-emergency chat: the friends
  wrote look-alikes to sound frightening.
- Chats are scored on message 2 (and message 1 where labelled); they do not test chats longer than two messages, or a
  second message that only makes sense with the bot's own reply.
- `answer` only says the bot should answer; whether the answer is right is the faithfulness grade. An `answer` item the
  bot answers wrongly is a pass on label and a 1 on faithfulness, and the report shows both.
- The label rules follow the system's design in two places (table pairs are `answer`; the safe-combination guard cost is
  kept). State that, and give the three known-cost items separately.

Not worth doing now: more single questions (every class has at least 30 except off-topic, which the gate refuses before
the model sees it), or merging `questions.jsonl` and `heldout.jsonl` into `dev.jsonl` (the gate tests read them; merge
after the freeze if ever).

## Not run yet

Nothing from `final.jsonl` or `dev_chats.jsonl` has been run. `run_eval` has no multi-turn support yet, so the chats
cannot be scored until that is built. The 115 `answer` rows of the final set have `expect_chunks` (proposed by one agent from the
leaflets, checked by a second, before any run), so it reports citation validity and, on its 77 single questions,
retrieval hit@4; faithfulness is still the grade that says whether an answer is supported.
