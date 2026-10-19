"""LLM structured application generation with claim verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm import LLMClient, get_llm_client
from app.modules.rag.retrieval import RetrievalHit, hybrid_search


class GeneratedClaim(BaseModel):
    claim: str
    source_chunk_id: str | None = None
    verification_status: str = "UNVERIFIED"


class GeneratedApplication(BaseModel):
    subject: str
    message: str
    language: str = "cs"
    claims: list[GeneratedClaim] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class GenerationContext:
    job_title: str
    company_name: str | None
    job_description: str | None
    profile_summary: str | None
    profile_technologies: list[str] = field(default_factory=list)
    tone: str = "professional_concise"
    language: str = "cs"
    matching_explanation: dict | None = None


def _fallback_draft(ctx: GenerationContext) -> GeneratedApplication:
    """Deterministic draft when LLM is unavailable — no invented claims."""
    if ctx.language == "en":
        subject = f"Application — {ctx.job_title}"
        if ctx.company_name:
            subject = f"Application — {ctx.job_title} at {ctx.company_name}"
        message = (
            f"Dear hiring team,\n\n"
            f"I am writing to express interest in the {ctx.job_title} role"
            f"{f' at {ctx.company_name}' if ctx.company_name else ''}.\n\n"
            f"{ctx.profile_summary or 'Please find my resume attached for your review.'}\n\n"
            f"Relevant technologies: {', '.join(ctx.profile_technologies[:12]) or 'see resume'}.\n\n"
            f"Thank you for your consideration.\n"
        )
    else:
        subject = f"Přihláška — {ctx.job_title}"
        if ctx.company_name:
            subject = f"Přihláška — {ctx.job_title} / {ctx.company_name}"
        message = (
            f"Dobrý den,\n\n"
            f"mám zájem o pozici {ctx.job_title}"
            f"{f' ve společnosti {ctx.company_name}' if ctx.company_name else ''}.\n\n"
            f"{ctx.profile_summary or 'V příloze zasílám životopis.'}\n\n"
            f"Relevantní technologie: {', '.join(ctx.profile_technologies[:12]) or 'viz CV'}.\n\n"
            f"Děkuji za zvážení mé přihlášky.\n"
        )
    return GeneratedApplication(
        subject=subject,
        message=message,
        language=ctx.language,
        claims=[],
        unsupported_claims=[],
        metadata={"generator": "fallback", "llm_used": False},
    )


def verify_claims_against_hits(
    claims: list[str],
    hits: list[RetrievalHit],
    *,
    min_overlap_tokens: int = 3,
) -> tuple[list[GeneratedClaim], list[str]]:
    """Mark claims as VERIFIED when enough content overlap exists with retrieved chunks."""
    verified: list[GeneratedClaim] = []
    unsupported: list[str] = []

    def tokens(s: str) -> set[str]:
        return {t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in s).split() if len(t) > 2}

    for claim in claims:
        claim_tokens = tokens(claim)
        best_id = None
        best_overlap = 0
        for hit in hits:
            overlap = len(claim_tokens & tokens(hit.content))
            if overlap > best_overlap:
                best_overlap = overlap
                best_id = hit.chunk_id
        if best_id and best_overlap >= min_overlap_tokens:
            verified.append(
                GeneratedClaim(
                    claim=claim,
                    source_chunk_id=best_id,
                    verification_status="VERIFIED",
                )
            )
        else:
            unsupported.append(claim)
            verified.append(
                GeneratedClaim(
                    claim=claim,
                    source_chunk_id=best_id,
                    verification_status="UNSUPPORTED",
                )
            )
    return verified, unsupported


def strip_unsupported_sentences(message: str, unsupported: list[str]) -> str:
    """Remove sentences that closely match unsupported claims."""
    if not unsupported:
        return message
    lines = message.splitlines()
    kept: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(claim.lower() in lower or lower in claim.lower() for claim in unsupported if len(claim) > 12):
            continue
        kept.append(line)
    return "\n".join(kept).strip() or message


async def generate_application(
    db: AsyncSession,
    ctx: GenerationContext,
    *,
    client: LLMClient | None = None,
    use_rag: bool = True,
) -> GeneratedApplication:
    hits: list[RetrievalHit] = []
    if use_rag:
        query = f"{ctx.job_title} {ctx.company_name or ''} {' '.join(ctx.profile_technologies[:8])}"
        try:
            hits = await hybrid_search(db, query, limit=6, approved_only=True)
        except Exception:
            hits = []

    llm = client or get_llm_client(db)
    if not llm.is_configured:
        draft = _fallback_draft(ctx)
        draft.metadata["rag_hits"] = len(hits)
        return draft

    evidence_block = "\n\n".join(
        f"[{h.chunk_id}] ({h.document_title})\n{h.content[:800]}" for h in hits
    ) or "(no approved knowledge chunks retrieved)"

    lang_name = "Czech" if ctx.language == "cs" else "English"
    system = (
        "You write concise job application emails. "
        "Only use facts present in the candidate profile summary, technologies list, "
        "or provided evidence chunks. Never invent employers, metrics, certifications, "
        "or years of experience. Respond as JSON with keys: "
        "subject, message, claims (array of strings asserted in the message)."
    )
    user = (
        f"Language: {lang_name}\n"
        f"Tone: {ctx.tone}\n"
        f"Job title: {ctx.job_title}\n"
        f"Company: {ctx.company_name or 'unknown'}\n"
        f"Job description (excerpt):\n{(ctx.job_description or '')[:2500]}\n\n"
        f"Candidate summary:\n{ctx.profile_summary or ''}\n"
        f"Technologies: {', '.join(ctx.profile_technologies)}\n\n"
        f"Evidence chunks:\n{evidence_block}\n"
    )

    raw = await llm.chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        operation="generate_application",
    )

    subject = str(raw.get("subject") or _fallback_draft(ctx).subject)
    message = str(raw.get("message") or "")
    claims_raw = raw.get("claims") or []
    if not isinstance(claims_raw, list):
        claims_raw = []
    claim_texts = [str(c) for c in claims_raw if str(c).strip()]

    verified, unsupported = verify_claims_against_hits(claim_texts, hits)
    # Also treat claims with no RAG as unverified if they look specific and hits empty
    if unsupported:
        message = strip_unsupported_sentences(message, unsupported)

    return GeneratedApplication(
        subject=subject,
        message=message,
        language=ctx.language,
        claims=verified,
        unsupported_claims=unsupported,
        metadata={
            "generator": "llm",
            "llm_used": True,
            "rag_hits": len(hits),
            "model": llm.chat_model,
        },
    )
