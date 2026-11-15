# Manual UI checklist

Run `uv run uvicorn --factory backend.app:default_app` and ask the Metformin question.

- [ ] Card shows Summary, What to do and Get help if as lists
- [ ] "Get help if" sits in its own red-bordered block that stands out from the rest
- [ ] A reply with no card (refusal, emergency) shows no card headings
- [ ] An answer whose card has an empty section shows no heading for that section
