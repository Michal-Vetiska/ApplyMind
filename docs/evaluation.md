# Evaluation

RAG evaluation fixtures live under `apps/api/tests/` and can be extended with a fixed dataset for Recall@K / Precision@K / MRR.

Rules:

- Report only measured metrics from a fixed test set
- Never fabricate accuracy percentages
- Compare vector-only vs keyword-only vs hybrid when LLM embeddings are configured

Unit tests currently cover salary parsing, matching, dedup, state transitions, email classification, and RRF fusion.
