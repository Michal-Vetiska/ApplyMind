"""Knowledge base and RAG endpoints."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.modules.rag.ingestion import ingest_document, reindex_document
from app.modules.rag.retrieval import hybrid_search
from app.schemas.common import MessageOut
from app.schemas.knowledge import (
    KnowledgeDocumentOut,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    RagDebugOut,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=list[KnowledgeDocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[KnowledgeDocument]:
    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.deleted_at.is_(None))
        .order_by(KnowledgeDocument.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/documents", response_model=KnowledgeDocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form("note"),
    scope: str = Form("PERSONAL_KNOWLEDGE"),
    approved: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> KnowledgeDocument:
    settings = get_settings()
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".md", ".txt", ".markdown"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content = await file.read()
    max_bytes = settings.upload_max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    checksum = hashlib.sha256(content).hexdigest()
    dest_dir = Path(settings.data_dir) / "knowledge"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{checksum}{suffix}"
    dest.write_bytes(content)

    try:
        doc = await ingest_document(
            db,
            title=title,
            document_type=document_type,
            file_path=str(dest),
            source="upload",
            scope=scope,
            approved=approved,
            metadata={"original_filename": file.filename},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await record_audit(db, "knowledge.uploaded", "knowledge_document", doc.id, {"title": title})
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post("/documents/text", response_model=KnowledgeDocumentOut, status_code=201)
async def ingest_text(
    title: str = Form(...),
    text: str = Form(...),
    document_type: str = Form("note"),
    scope: str = Form("PERSONAL_KNOWLEDGE"),
    approved: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> KnowledgeDocument:
    try:
        doc = await ingest_document(
            db,
            title=title,
            document_type=document_type,
            text=text,
            source="paste",
            scope=scope,
            approved=approved,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post("/documents/{document_id}/approve", response_model=KnowledgeDocumentOut)
async def approve_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> KnowledgeDocument:
    doc = await db.get(KnowledgeDocument, document_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.approved = True
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post("/documents/{document_id}/reindex", response_model=KnowledgeDocumentOut)
async def reindex(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> KnowledgeDocument:
    try:
        doc = await reindex_document(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}", response_model=MessageOut)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    doc = await db.get(KnowledgeDocument, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.deleted_at = datetime.now(UTC)
    await db.commit()
    return MessageOut(message="Deleted")


@router.post("/search", response_model=list[KnowledgeSearchHit])
async def search(
    payload: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[KnowledgeSearchHit]:
    hits = await hybrid_search(
        db,
        payload.query,
        limit=payload.limit,
        scope=payload.scope,
        approved_only=payload.approved_only,
    )
    return [
        KnowledgeSearchHit(
            chunk_id=h.chunk_id,
            document_id=h.document_id,
            content=h.content,
            score=h.score,
            rank_vector=h.rank_vector,
            rank_fts=h.rank_fts,
            section_heading=h.section_heading,
            document_title=h.document_title,
            document_type=h.document_type,
            metadata=h.metadata,
        )
        for h in hits
    ]


@router.post("/rag-debug", response_model=RagDebugOut)
async def rag_debug(
    payload: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> RagDebugOut:
    hits = await hybrid_search(
        db,
        payload.query,
        limit=payload.limit,
        scope=payload.scope,
        approved_only=payload.approved_only,
    )
    notes = [
        "Hybrid retrieval = vector cosine + PostgreSQL FTS fused with RRF",
        "Unapproved documents excluded when approved_only=true",
    ]
    if not hits:
        notes.append("No hits — check embeddings configuration and document approval")
    return RagDebugOut(
        query=payload.query,
        hits=[
            KnowledgeSearchHit(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                content=h.content,
                score=h.score,
                rank_vector=h.rank_vector,
                rank_fts=h.rank_fts,
                section_heading=h.section_heading,
                document_title=h.document_title,
                document_type=h.document_type,
                metadata=h.metadata,
            )
            for h in hits
        ],
        notes=notes,
    )


@router.get("/documents/{document_id}/chunks")
async def list_chunks(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[dict]:
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document_id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    return [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "token_count": c.token_count,
            "section_heading": c.section_heading,
            "content": c.content,
        }
        for c in result.scalars().all()
    ]
