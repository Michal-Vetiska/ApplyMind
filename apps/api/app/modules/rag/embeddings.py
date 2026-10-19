"""OpenAI-compatible embedding client."""

from __future__ import annotations

from typing import Sequence

from app.integrations.llm import LLMClient, get_llm_client


async def embed_texts(
    texts: Sequence[str],
    *,
    client: LLMClient | None = None,
    operation: str = "embeddings",
) -> list[list[float]]:
    """Embed a batch of texts. Returns empty vectors when LLM is not configured."""
    llm = client or get_llm_client()
    if not texts:
        return []
    if not llm.is_configured:
        dims = llm.embedding_dims
        return [[0.0] * dims for _ in texts]
    return await llm.embed(list(texts), operation=operation)


async def embed_query(text: str, *, client: LLMClient | None = None) -> list[float]:
    vectors = await embed_texts([text], client=client, operation="embed_query")
    return vectors[0] if vectors else []
