# Evaluation summary

Retrieval hit@4: bm25 0.89, vector 1.00, hybrid 1.00
Best similarity threshold 0.725; in use 0.72
Held-out gate accuracy at 0.72: 0.80 (10 reworded questions never used for tuning)

| model | red-flag recall | red-flag FPR | refusal | answer rate | citation validity | p50 s | p95 s | tokens/s |
|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | 1.00 | 0.00 | 1.00 | nan | 1.00 | 25.9 | 36.1 | 12.6 |
| llama3.2:3b | 1.00 | 0.00 | 1.00 | nan | 1.00 | 6.6 | 11.2 | 42.3 |
| qwen2.5:7b | 1.00 | 0.03 | 0.90 | nan | 0.94 | 15.2 | 53.3 | 21.4 |
