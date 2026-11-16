# Evaluation summary

Retrieval hit@4: bm25 0.90, vector 1.00, hybrid 1.00
Best similarity threshold 0.746; in use 0.74

| model | red-flag recall | red-flag FPR | refusal | citation validity | p50 s | p95 s | tokens/s |
|---|---|---|---|---|---|---|---|
| llama3.1:8b | 1.00 | 0.00 | 1.00 | 1.00 | 25.9 | 36.1 | 12.6 |
| llama3.2:3b | 1.00 | 0.00 | 1.00 | 1.00 | 6.4 | 15.2 | 24.6 |
| qwen2.5:7b | 1.00 | 0.03 | 0.90 | 0.94 | 15.2 | 53.3 | 21.4 |
