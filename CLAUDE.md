## Agent skills

### Issue tracker

GitHub Issues via the `gh` CLI (private repo `medmate`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Eval

The model was chosen on the first full eval (`eval/results/summary.md`). After a prompt or code change, rerun only the chosen model (`uv run python -m eval.run_eval --model llama3.2:3b`) with the other Ollama models unloaded (`ollama ps`, `ollama stop <model>`), and compare it with its own previous run, never with a run made under other loading. Rerun the other models only if the choice is reopened, for example when the chosen model fails the gate.
