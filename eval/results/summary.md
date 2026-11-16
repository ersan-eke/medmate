# Evaluation summary

Retrieval hit@4: bm25 0.89, vector 1.00, hybrid 1.00
Best similarity threshold 0.725; in use 0.72
Held-out gate accuracy at 0.72: 0.80 (10 reworded questions never used for tuning)

| model | red-flag recall | red-flag FPR | refusal | answer rate | citation validity | p50 s | p95 s | tokens/s |
|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | 1.00 | 0.00 | 1.00 | 0.85 | 1.00 | 25.0 | 30.9 | 14.4 |
| llama3.2:3b | 1.00 | 0.00 | 1.00 | 0.85 | 1.00 | 8.5 | 13.0 | 44.0 |
| qwen2.5:7b | 1.00 | 0.02 | 0.86 | 0.85 | 0.92 | 19.9 | 24.7 | 17.8 |

Model choice: red-flag recall and refusal must be 1.00 and p95 under 15 s; then the highest answer rate; then the lowest p95.
Off-topic questions are all refused by the similarity gate before a model sees them, so the refusal column tests the model only on not-covered questions that pass the gate.
