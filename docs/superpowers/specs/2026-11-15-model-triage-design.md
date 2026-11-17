# Model triage: a second emergency check behind the rules

## Intent
The red-flag rules (`backend/safety.py`) only recognise wordings someone wrote down. A novel emergency phrasing ("an elephant is sitting on my chest") matches nothing, scores too low in retrieval and returns `not_covered`, so the model never sees it. Add a model check that catches these.

## Goals
- A question the rules miss but the model judges urgent returns `emergency`, the same reply as the rules.
- Runs before retrieval, so the retrieval cutoff cannot hide an emergency.
- Failure never blocks the user: if the call errors, times out or returns bad JSON, the normal path continues.

## Non-goals
- Replacing or loosening the rules. They still run first and keep recall 1.0 on `FIRES`.
- Parallel triage, a second model, or any config. One extra call per question.
- Tuning false positives. Accepted: a small model over-triggers, and a larger model would reduce that (a stated limitation).

## Anti-goal
Triage must never make the answer path slower to fail or let a model outage drop the rules' protection.

## Approaches
1. `urgent` field in the existing answer schema: no extra call, but never runs for questions cut off by the retrieval gate, which are the cases this exists for.
2. **Chosen:** separate triage call (`{"urgent": bool}`) after the rules and before retrieval. Costs one model call per question (a few seconds on the 3B model).
3. Triage in parallel with retrieval and answer: no added latency but threading/async and wasted answer calls. Revisit only if latency hurts.

## Design
- `backend/llm.py`: `triage(question, generate) -> bool`. Own small schema and system prompt (`prompts/triage.txt`), reuses `Generate`. Any exception or invalid JSON returns `False` and logs a warning. One attempt, no retry.
- `backend/pipeline.py`: after `check_red_flags`, `if triage(question, generate): return ChatResponse(kind="emergency", answer=messages.EMERGENCY, red_flag="model_triage", llm_called=True)`.
- Tests with a fake `generate`: urgent returns `emergency` without the embedder or answer call; not urgent continues; exception and bad JSON continue; rules still short-circuit before triage (model not called). Existing API test fixtures that assert `llm calls == 0` or a call count need updating for the extra call.

## Left to the builder
Wording of the triage prompt (lean towards "when unsure, urgent"), and whether the live Ollama test gets a triage case.
