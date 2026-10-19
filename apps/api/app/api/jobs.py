"""Job listing, import, and evaluation endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.job import Company, Job, JobMatch, JobSource
from app.models.profile import SearchProfile
from app.modules.discovery.adapters.manual import ManualAdapter
from app.modules.matching.engine import MatchingEngine
from app.schemas.common import MessageOut, Paginated
from app.schemas.jobs import EvaluateRequest, JobDetailOut, JobMatchOut, JobOut, ManualJobImport
from app.services.audit import record_audit
from app.services.dedup import normalize_company_name
from app.services.normalize import normalize_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


async def _get_or_create_company(db: AsyncSession, name: str | None) -> Company | None:
    if not name:
        return None
    normalized = normalize_company_name(name)
    result = await db.execute(select(Company).where(Company.normalized_name == normalized))
    company = result.scalar_one_or_none()
    if company:
        return company
    company = Company(name=name, normalized_name=normalized)
    db.add(company)
    await db.flush()
    return company


async def _get_or_create_manual_source(db: AsyncSession) -> JobSource:
    result = await db.execute(select(JobSource).where(JobSource.provider == "manual").limit(1))
    source = result.scalar_one_or_none()
    if source:
        return source
    source = JobSource(name="Manual import", provider="manual", enabled=True, configuration={})
    db.add(source)
    await db.flush()
    return source


@router.get("", response_model=Paginated[JobOut])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = None,
    q: str | None = None,
    min_score: float | None = None,
) -> Paginated[JobOut]:
    stmt = select(Job).where(Job.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Job).where(Job.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Job.status == status)
        count_stmt = count_stmt.where(Job.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Job.title.ilike(like) | Job.location.ilike(like))
        count_stmt = count_stmt.where(Job.title.ilike(like) | Job.location.ilike(like))
    total = int((await db.execute(count_stmt)).scalar() or 0)
    result = await db.execute(stmt.order_by(Job.discovered_at.desc()).offset(offset).limit(limit))
    items = list(result.scalars().all())
    if min_score is not None:
        # Filter by best match score when requested
        filtered = []
        for job in items:
            match_result = await db.execute(
                select(JobMatch)
                .where(JobMatch.job_id == job.id)
                .order_by(JobMatch.overall_score.desc())
                .limit(1)
            )
            match = match_result.scalar_one_or_none()
            if match and match.overall_score >= min_score:
                filtered.append(job)
        items = filtered
    return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobDetailOut)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> JobDetailOut:
    result = await db.execute(
        select(Job)
        .options(selectinload(Job.matches), selectinload(Job.company))
        .where(Job.id == job_id, Job.deleted_at.is_(None))
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    data = JobDetailOut.model_validate(job)
    data.matches = [JobMatchOut.model_validate(m) for m in job.matches]
    data.company_name = job.company.name if job.company else None
    data.normalized_description = job.normalized_description
    data.requirements_json = job.requirements_json or {}
    data.raw_payload = job.raw_payload or {}
    return data


@router.post("/import", response_model=JobOut, status_code=201)
async def import_job(
    payload: ManualJobImport,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> Job:
    source = await _get_or_create_manual_source(db)
    adapter = ManualAdapter(
        {
            "jobs": [
                {
                    "title": payload.title,
                    "company_name": payload.company_name,
                    "url": payload.url,
                    "apply_url": payload.apply_url,
                    "location": payload.location,
                    "description": payload.description,
                    "description_html": payload.description_html,
                    "salary_text": payload.salary_text,
                    "contact_email": payload.contact_email,
                    "technologies": payload.technologies,
                    "remote_type": payload.remote_type,
                    "employment_type": payload.employment_type,
                }
            ]
        }
    )
    discovered = (await adapter.list_jobs())[0]
    normalized = normalize_job(
        title=discovered.title,
        company_name=discovered.company_name,
        description_html=discovered.description_html,
        description_text=discovered.description_text,
        location=discovered.location,
        salary_text=discovered.salary_text,
        technologies_hint=discovered.technologies,
        remote_type=discovered.remote_type,
        employment_type=discovered.employment_type,
    )
    company = await _get_or_create_company(db, discovered.company_name)

    existing = await db.execute(
        select(Job).where(
            Job.source_id == source.id,
            Job.external_id == discovered.external_id,
            Job.deleted_at.is_(None),
        )
    )
    job = existing.scalar_one_or_none()
    salary = normalized.salary
    fields = {
        "title": normalized.title,
        "normalized_title": normalized.normalized_title,
        "description": normalized.description_text,
        "normalized_description": normalized.description_text,
        "requirements_json": normalized.requirements,
        "location": normalized.location,
        "remote_type": normalized.remote_type,
        "employment_type": normalized.employment_type,
        "seniority": normalized.seniority,
        "salary_min": salary.salary_min if salary else None,
        "salary_max": salary.salary_max if salary else None,
        "currency": salary.currency if salary else None,
        "salary_period": (
            salary.salary_period
            if salary and salary.salary_period != "unknown"
            else None
        ),
        "original_salary_text": salary.original_salary_text if salary else None,
        "salary_flag": salary.salary_flag if salary else "SALARY_UNKNOWN",
        "technologies": normalized.technologies,
        "source_url": discovered.source_url,
        "apply_url": discovered.apply_url,
        "contact_email": discovered.contact_email,
        "apply_method": (discovered.apply_capabilities.methods or ["MANUAL_EXTERNAL"])[0],
        "apply_capabilities": discovered.apply_capabilities.model_dump(),
        "content_hash": normalized.content_hash,
        "raw_payload": discovered.raw_payload,
        "company_id": company.id if company else None,
        "status": "DISCOVERED",
    }
    if job is None:
        job = Job(
            external_id=discovered.external_id,
            source_id=source.id,
            **fields,
        )
        db.add(job)
    else:
        for key, value in fields.items():
            setattr(job, key, value)

    source.discovered_jobs_count = (source.discovered_jobs_count or 0) + 1
    await record_audit(db, "job.imported", "job", None, {"title": payload.title})
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/evaluate", response_model=JobMatchOut)
async def evaluate_job(
    job_id: str,
    payload: EvaluateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> JobMatch:
    job = await db.get(Job, job_id)
    if job is None or job.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_id = payload.search_profile_id if payload else None
    if profile_id:
        profile = await db.get(SearchProfile, profile_id)
    else:
        result = await db.execute(
            select(SearchProfile).where(SearchProfile.enabled.is_(True)).limit(1)
        )
        profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=400, detail="No search profile available")

    result_match = MatchingEngine.from_search_profile(profile).evaluate(profile, job)

    existing = await db.execute(
        select(JobMatch).where(
            JobMatch.job_id == job.id,
            JobMatch.search_profile_id == profile.id,
        )
    )
    match = existing.scalar_one_or_none()
    values = {
        "overall_score": result_match.overall_score,
        "skill_score": result_match.skill_score,
        "seniority_score": result_match.seniority_score,
        "location_score": result_match.location_score,
        "compensation_score": result_match.compensation_score,
        "other_score": result_match.other_score,
        "decision": result_match.decision,
        "explanation_json": result_match.explanation,
        "missing_skills_json": result_match.missing_skills,
        "evidence_json": result_match.evidence,
        "rule_score": result_match.overall_score,
        "evaluated_at": datetime.now(UTC),
    }
    if match is None:
        match = JobMatch(job_id=job.id, search_profile_id=profile.id, **values)
        db.add(match)
    else:
        for key, value in values.items():
            setattr(match, key, value)

    if result_match.decision == "SHORTLIST":
        job.status = "SHORTLISTED"
    elif result_match.decision == "EXCLUDE":
        job.status = "DISCOVERED"
    else:
        job.status = "MATCHED"

    await db.commit()
    await db.refresh(match)
    return match


@router.delete("/{job_id}", response_model=MessageOut)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.deleted_at = datetime.now(UTC)
    await db.commit()
    return MessageOut(message="Deleted")
