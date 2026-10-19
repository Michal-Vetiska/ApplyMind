"""Hybrid retrieval: vector similarity + PostgreSQL FTS fused with RRF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.embeddings import embed_query


@dataclass
class RetrievalHit:
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank_vector: int | None
    rank_fts: int | None
    metadata: dict
    section_heading: str | None
    document_title: str | None = None
    document_type: str | None = None


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Compute RRF scores for document/chunk ids across ranked lists."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


async def _vector_search(
    db: AsyncSession,
    query_embedding: list[float],
    *,
    limit: int,
    scope: str | None,
    approved_only: bool,
) -> list[tuple[str, float]]:
    if not query_embedding or all(v == 0 for v in query_embedding):
        return []

    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
    stmt: Select = (
        select(KnowledgeChunk.id, distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .where(KnowledgeChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    if approved_only:
        stmt = stmt.where(KnowledgeDocument.approved.is_(True))
    if scope:
        stmt = stmt.where(KnowledgeDocument.scope == scope)

    result = await db.execute(stmt)
    rows = result.all()
    # Convert distance to similarity-ish score for ordering only; RRF uses ranks
    return [(str(row.id), float(1.0 / (1.0 + (row.distance or 0)))) for row in rows]


async def _fts_search(
    db: AsyncSession,
    query: str,
    *,
    limit: int,
    scope: str | None,
    approved_only: bool,
) -> list[tuple[str, float]]:
    if not query.strip():
        return []

    # Use plainto_tsquery for safe user input; ts_rank_cd for ranking
    ts_query = func.plainto_tsquery("simple", query)
    rank = func.ts_rank_cd(func.to_tsvector("simple", KnowledgeChunk.content), ts_query)
    stmt: Select = (
        select(KnowledgeChunk.id, rank.label("rank"))
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .where(func.to_tsvector("simple", KnowledgeChunk.content).op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(limit)
    )
    if approved_only:
        stmt = stmt.where(KnowledgeDocument.approved.is_(True))
    if scope:
        stmt = stmt.where(KnowledgeDocument.scope == scope)

    result = await db.execute(stmt)
    return [(str(row.id), float(row.rank or 0)) for row in result.all()]


async def hybrid_search(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 8,
    scope: str | None = None,
    approved_only: bool = True,
    candidate_pool: int = 40,
) -> list[RetrievalHit]:
    """Vector + FTS hybrid search fused with Reciprocal Rank Fusion."""
    embedding = await embed_query(query)
    vector_hits = await _vector_search(
        db, embedding, limit=candidate_pool, scope=scope, approved_only=approved_only
    )
    fts_hits = await _fts_search(
        db, query, limit=candidate_pool, scope=scope, approved_only=approved_only
    )

    vector_ids = [hid for hid, _ in vector_hits]
    fts_ids = [hid for hid, _ in fts_hits]
    fused = reciprocal_rank_fusion([vector_ids, fts_ids])
    top = fused[:limit]
    if not top:
        return []

    ids = [item_id for item_id, _ in top]
    vector_rank = {hid: i + 1 for i, hid in enumerate(vector_ids)}
    fts_rank = {hid: i + 1 for i, hid in enumerate(fts_ids)}
    score_map = dict(top)

    result = await db.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeChunk.id.in_(ids))
    )
    rows = {str(chunk.id): (chunk, doc) for chunk, doc in result.all()}

    hits: list[RetrievalHit] = []
    for chunk_id, _ in top:
        pair = rows.get(chunk_id)
        if not pair:
            continue
        chunk, doc = pair
        hits.append(
            RetrievalHit(
                chunk_id=chunk.id,
                document_id=doc.id,
                content=chunk.content,
                score=round(score_map.get(chunk_id, 0.0), 6),
                rank_vector=vector_rank.get(chunk_id),
                rank_fts=fts_rank.get(chunk_id),
                metadata=chunk.metadata_json or {},
                section_heading=chunk.section_heading,
                document_title=doc.title,
                document_type=doc.document_type,
            )
        )
    return hits


async def ensure_fts_index(db: AsyncSession) -> None:
    """Best-effort GIN FTS index creation (also covered by migration)."""
    await db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_content_fts "
            "ON knowledge_chunks USING gin (to_tsvector('simple', content))"
        )
    )
