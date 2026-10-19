"""Knowledge / RAG schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeDocumentOut(BaseModel):
    id: str
    title: str
    document_type: str
    source: str
    scope: str
    checksum: str
    approved: bool
    indexed_at: datetime | None = None
    metadata_json: dict = {}
    embedding_model: str | None = None

    model_config = {"from_attributes": True}


class KnowledgeChunkOut(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    token_count: int
    section_heading: str | None = None
    metadata_json: dict = {}

    model_config = {"from_attributes": True}


class KnowledgeSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=50)
    scope: str | None = None
    approved_only: bool = True


class KnowledgeSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank_vector: int | None = None
    rank_fts: int | None = None
    section_heading: str | None = None
    document_title: str | None = None
    document_type: str | None = None
    metadata: dict[str, Any] = {}


class RagDebugOut(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]
    notes: list[str] = []
