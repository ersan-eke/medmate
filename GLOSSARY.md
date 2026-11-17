# MedMate

A voice-first companion that answers questions about a person's medicines from a fixed set of leaflets, and refuses everything else.

## Answering

**Similarity gate**:
The check that refuses a question before the model sees it, when no leaflet passage is close enough to the question.
_Avoid_: threshold check, cut-off

**Number check**:
The check that sends an answer back to the model when it states a number not found in the passages it cites, the user's own doses, or the emergency number.
_Avoid_: number guard, dose check

**Refusal**:
A reply that declines to answer: either "not in my leaflets" or "only questions about your medicines".
_Avoid_: rejection, decline

## Evaluation

**Answerable question**:
An evaluation question the leaflets do answer: the dosing, side-effects, personal and near-miss categories.
_Avoid_: in-KB question, covered question

**Answer rate**:
The share of answerable questions that got a real answer, not a refusal or a fallback.
_Avoid_: coverage, recall

**Tuning set**:
The evaluation questions the similarity gate's threshold is chosen on.
_Avoid_: training set, calibration set

**Held-out question**:
An evaluation question that was never used to tune anything, kept to test whether a tuned value generalises.
_Avoid_: test question, paraphrase set
