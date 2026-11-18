# Follow-ups are rewritten by the model, then checked by code

A follow-up ("what about ibuprofen?") is turned into an Answered question by one model call that sees only the previous question and the follow-up; the Rewrite check then refuses any Answered question that drops a medicine the follow-up named or adds a medicine or number the user never said, and MedMate asks for the whole question instead. Everything after that (Interaction table, retrieval, Number check) runs on the Answered question exactly as on a first question, so the answering model never sees chat history. The Emergency check runs first, on the previous message and the follow-up as typed, so a rewrite can never hide an emergency.

## Considered Options

- **Send the chat history to the answering model**: the deterministic checks (Interaction table, Number check, Combination question) work on one question's text and would miss a medicine named only in an earlier turn.
- **Join the previous message onto the follow-up by rule**: "what about ibuprofen?" after a paracetamol question became a paracetamol + ibuprofen Combination question; the word lists grew into a regex imitation of the model.
- **A model-written summary of the conversation**: unchecked text that carries its errors into every later turn, and a model call on every turn.
- **A model-written clarifying question**: unchecked text spoken to a patient, written at the moment the model has just failed to understand; MedMate asks back with a sentence filled in by code instead.

## Consequences

- A follow-up costs one extra model call; a first question costs none.
- The browser keeps the Answered question on the user's bubble and sends it as the previous question, so chained follow-ups keep their medicine.
- The 999 reply repeats once for whatever is asked next, since the Emergency check sees the previous message.
