# RAG

## Pipeline

1. Upload document (PDF/DOCX/MD/TXT)
2. Parse + clean text
3. Chunk (size/overlap configurable in code)
4. Embed via OpenAI-compatible embeddings (when configured)
5. Store vectors in pgvector + keep full text for FTS
6. Retrieve with hybrid search + reciprocal rank fusion
7. Build evidence package for generation
8. Verify claims against retrieved chunks when LLM returns claims

## Scopes

- `PERSONAL_KNOWLEDGE` — approved resumes and experience
- `COMPANY_KNOWLEDGE` — public company briefings
- `APPLICATION_HISTORY` — prior approved applications

Only **approved** personal documents are used as verified evidence.

## Debugger

UI: Znalostní báze → search/debug against `/api/knowledge/search`.
