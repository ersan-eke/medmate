# MedMate

A voice-first companion that answers questions about a person's medicines from a fixed set of leaflets, and refuses everything else.

## People

**MedMate**:
The companion itself, including the face on screen that speaks its answers. Never called a pharmacist.
_Avoid_: pharmacist, assistant, bot

**Pharmacist**:
A real person the user can ask in a pharmacy. MedMate refers people to one; it is never one.

## Leaflets

**Leaflet medicine**:
A medicine MedMate has a leaflet for; the only medicines it can answer about.
_Avoid_: known medicine, supported drug

**My medicines**:
The medicines the person has said they take.
_Avoid_: saved medicines, listed medicines, medicine list

**Interaction table**:
The checked list of medicine pairs a leaflet warns about. The only thing allowed to answer whether two medicines can be taken together.
_Avoid_: interaction list, pairs file

## Answering

**Similarity gate**:
The check that refuses a question before the model sees it, when no leaflet passage is close enough to the question and the question is not about a leaflet medicine.
_Avoid_: threshold check, cut-off

**Number check**:
The check that sends an answer back to the model when it states a number not found in the passages it cites, the user's own doses, or the emergency number.
_Avoid_: number guard, dose check

**Emergency check**:
The checks that run before anything else and reply with the 999 message: fixed phrases for each NHS 999 sign, then the model answering yes or no for each sign. Any one match is enough.
_Avoid_: urgency check, risk score

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

**Faithful answer**:
An answer whose every claim and piece of advice is stated by the passages it cites.
_Avoid_: accurate, correct

**Tuning set**:
The evaluation questions the similarity gate's threshold is chosen on.
_Avoid_: training set, calibration set

**Held-out question**:
An evaluation question that was never used to tune anything, kept to test whether a tuned value generalises.
_Avoid_: test question, paraphrase set
