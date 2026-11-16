# Challenges log

Add real problems as you hit them: date, who, what happened, what fixed it.

## 2026-11-15 — Knowledge base content (ticket #6)

- **NHS page layout changed.** Most medicines are now one page with sections ("What metformin is for", "How to take metformin", …), not one page per topic. Ramipril and salbutamol inhaler still use the older layout (About, How and when to take, Side effects, Who can and cannot, Pregnancy, With other medicines, Common questions). We kept each page's own NHS heading names, so chunk ids differ between the two layouts (e.g. `metformin#how-to-take-metformin` vs `ramipril#how-and-when-to-take-ramipril`).
- **Licence check.** Each page shows only "© Crown copyright". The NHS website terms (nhs.uk/our-policies/terms-and-conditions/) release NHS website content under the Open Government Licence v3.0 except items on the "content not licensed for re-use" page. That page excludes only some campaign sites (Change4Life, One You, Smokefree, …) and some images and videos, none of which we use. No BNF text is on these pages. No medicine was dropped.
- **Refresh rule.** The terms ask re-users to refresh content at least every 7 days. All 12 leaflets were retrieved on 2026-11-15; re-collect them before the final demo or submission if more than 7 days have passed.
- **Interaction table scope.** Rows only where a leaflet's "with other medicines" section names both medicines. Class-only mentions ("other blood pressure medicines", "medicines for diabetes") were not turned into pairs. Ramipril + aspirin was left out on purpose: the ramipril leaflet says daily low-dose aspirin (75mg) is safe with ramipril, so a blanket warning would be wrong for most older users on low-dose aspirin.
- **JSON-LD licence link.** Each page's embedded JSON-LD has `"license": "https://developer.api.nhs.uk/terms"`. Those are the NHS syndication/API terms, which apply to content taken through the API or widgets. We copied the public web pages, so the website terms (OGL v3.0) apply. The website footer statement required by those terms is already shown in the app footer.
- **Low-dose aspirin.** There is no separate low-dose page any more: `/medicines/low-dose-aspirin/` redirects to the combined aspirin page, which covers both low-dose and pain-relief use. `aspirin.md` is that page.
- **Aspirin warnings.** Only the ramipril leaflet exempts low-dose aspirin, so only Ramipril + aspirin was left out. The warfarin, ibuprofen and sertraline leaflets name aspirin without that exemption, so those rows stay.
- **Warning wording.** Each warning says what the leaflet lists, then quotes the leaflet's own advice sentence. `validate_interactions` checks that the cited passage names both medicines; whether the wording is faithful was checked by hand.

## 2026-11-15 — Spoken answers (ticket #9)

- **Kokoro set up first time.** `kokoro_engine()` returned WAV (`RIFF`) in the slow test (about 85 s for both slow tests including the model load); no setup problem to log. `say` WAV is `LEI16@22050`, which browsers decode.
- **No portrait art yet.** The avatar draws a fallback face (circle, eyes, mouth). Image frames are not coded until the art exists.

## 2026-11-16 — Asking by voice (ticket #10)

- **faster-whisper vs PyAV.** faster-whisper 1.2.1 calls `av.open(..., metadata_errors=...)`, which av 19 rejects (`TypeError`). Pinned `av<19` (now 18.1.0).

## 2026-11-16 — Offline and fast first answer (ticket #12)

- **No download happened with `HF_HUB_OFFLINE=1`.** Server start (warming embedder, chat model, Whisper, Kokoro) took 8 s with every cache already filled; log showed no download or error. The first chat after start took 7.0 s on this laptop (gate: 10 s). Wi-Fi itself was not switched off, only Hugging Face offline mode.
- **Offline default.** `backend/app.py` sets `HF_HUB_OFFLINE=1` unless already set. `scripts/fetch_models.py` turns it back on for the fetch.

## 2026-11-16 — Evaluation and model choice (ticket #13)

- **Candidates (exact tags, Ollama ids).** `llama3.2:3b` (a80c4f17acd5, baseline), `llama3.1:8b` (46e0c10c039e), `qwen2.5:7b` (845dbda0ea48). 36 questions in `eval/questions.jsonl`; results in `eval/results/`.
- **Chosen: `llama3.2:3b`** (already the default), for speed with similar accuracy. All three have red-flag recall 1.0. The 8B models are 2 to 4 times slower (p50 26 s and 15 s against 6 s). Hand-graded against the leaflets, the 20 answerable questions came out as below. "Weak" means a vague "check your leaflet" reply. An earlier version of this entry counted any non-refusal as answered (18, 14 and 17), which said nothing about correctness.

  | model | correct | weak | wrong | refused |
  |---|---|---|---|---|
  | llama3.2:3b | 13 | 3 (per1, per2, per3) | 2 | 2 |
  | llama3.1:8b | 14 | 0 | 0 | 6 |
  | qwen2.5:7b | 15 | 1 | 1 | 2, plus 1 false emergency |

  The 3B's wrong answers: per5 said "Yes, you can take your aspirin with your warfarin" (both leaflets say they may not mix well); sid2 blamed metformin's stomach upset on lactic acidosis (the leaflet lists nausea as common; lactic acidosis is a rare serious effect). Qwen's: per2 said paracetamol is fine because warfarin "doesn't contain paracetamol" (the paracetamol leaflet lists warfarin). Fixed for combination questions by #40; see the entry below.
- **Gates.** Red-flag recall 1.0 and refusal 1.0 hold, hybrid hit@4 (1.00) ≥ vector (1.00) and BM25 (0.90). **Missed: p95 latency ≤ 8 s.** The 3B model's p95 is 15 s, because a rejected answer is retried once. The gate on the first answer after startup (#12) is separate and was 7 s.
- **Threshold.** The best cut is 0.746; `MIN_SIMILARITY` is 0.74. In-KB questions score 0.75 to 0.91, off-topic ones 0.42 to 0.53, not-in-KB ones 0.63 to 0.76. "Metformin with turmeric" (0.763) passes the gate and is refused by the model's `covered` flag.
- **Two bugs the eval found.** (1) Ticket #28 made `answer`, `citations` and `card` optional in the schema sent to Ollama, so the models left out citations and nearly every answer fell back. `ANSWER_SCHEMA` now requires every field again. (2) The "covered" line in `prompts/system.txt` made the 3B model mark answerable questions as not covered; it is reworded.
- **Not done.** Faithfulness column is empty for the team to grade. Classmate feedback (plan step 7) and `tests/test_demo_live.py` are not part of this ticket's acceptance and were not done. Tokens/s varied between runs (24 to 40 for the 3B model), so rerun on a quiet laptop before quoting it.
- **Rerun after #40 (llama3.2:3b only).** per2, per3 and per5 now get the interactions-table warning with its leaflet source in 0.2 s, without calling the model. The 3B hand-grade becomes 16 correct, 1 weak (per1), 1 wrong (sid2, unchanged), 2 refused. p50 is 6.6 s and p95 11.2 s (was 15.2 s), still over the 8 s gate. Tokens/s read 42.3 this run (24 to 40 before), so it is still too noisy to quote. The llama3.1:8b and qwen2.5:7b rows in `summary.md` are from the run before #40.
- **Remaining 3B errors are listed as limitations** in the design spec (§12): the sid2 misreading, vague replies, and the speed trade-off against larger models.
