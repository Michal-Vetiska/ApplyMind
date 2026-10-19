"""Job source management and sync endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.job import Company, Job, JobSource
from app.modules.discovery.registry import get_adapter, list_adapters
from app.schemas.common import MessageOut
from app.schemas.sources import AdapterInfo, SourceCreate, SourceOut, SourceUpdate
from app.services.audit import record_audit
from app.services.dedup import normalize_company_name
from app.services.normalize import normalize_job

router = APIRouter(prefix="/api/sources", tags=["sources"])


async def _upsert_discovered(db: AsyncSession, source: JobSource, discovered) -> Job:
    company = None
    if discovered.company_name:
        normalized = normalize_company_name(discovered.company_name)
        result = await db.execute(select(Company).where(Company.normalized_name == normalized))
        company = result.scalar_one_or_none()
        if company is None:
            company = Company(name=discovered.company_name, normalized_name=normalized)
            db.add(company)
            await db.flush()

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
    salary = normalized.salary
    existing = await db.execute(
        select(Job).where(
            Job.source_id == source.id,
            Job.external_id == discovered.external_id,
        )
    )
    job = existing.scalar_one_or_none()
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
            salary.salary_period if salary and salary.salary_period != "unknown" else None
        ),
        "original_salary_text": salary.original_salary_text if salary else None,
        "salary_flag": salary.salary_flag if salary else "SALARY_UNKNOWN",
        "technologies": normalized.technologies,
        "published_at": discovered.published_at,
        "source_url": discovered.source_url,
        "apply_url": discovered.apply_url,
        "contact_email": discovered.contact_email,
        "apply_method": (discovered.apply_capabilities.methods or ["MANUAL_EXTERNAL"])[0],
        "apply_capabilities": discovered.apply_capabilities.model_dump(),
        "content_hash": normalized.content_hash,
        "raw_payload": discovered.raw_payload,
        "company_id": company.id if company else None,
        "deleted_at": None,
    }
    if job is None:
        job = Job(
            external_id=discovered.external_id,
            source_id=source.id,
            status="DISCOVERED",
            **fields,
        )
        db.add(job)
    else:
        for key, value in fields.items():
            setattr(job, key, value)
    return job


@router.get("/adapters", response_model=list[AdapterInfo])
async def adapters(_: UserAccount = Depends(get_current_user)) -> list[AdapterInfo]:
    return [AdapterInfo(**item) for item in list_adapters()]


@router.get("", response_model=list[SourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[JobSource]:
    result = await db.execute(select(JobSource).order_by(JobSource.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=SourceOut, status_code=201)
async def create_source(
    payload: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> JobSource:
    # Validate provider exists
    try:
        get_adapter(payload.provider, payload.configuration)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source = JobSource(**payload.model_dump())
    db.add(source)
    await record_audit(db, "source.created", "job_source", None, {"provider": payload.provider})
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: str,
    payload: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> JobSource:
    source = await db.get(JobSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", response_model=MessageOut)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    source = await db.get(JobSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()
    return MessageOut(message="Deleted")


@router.post("/{source_id}/sync")
async def sync_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> dict:
    source = await db.get(JobSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    source.last_checked_at = datetime.now(UTC)
    try:
        adapter = get_adapter(source.provider, source.configuration)
        if adapter.support_level == "UNSUPPORTED":
            source.health_status = "UNSUPPORTED"
            source.last_error = "Provider marked UNSUPPORTED"
            await db.commit()
            raise HTTPException(status_code=400, detail=source.last_error)

        jobs = await adapter.list_jobs()
        for discovered in jobs:
            await _upsert_discovered(db, source, discovered)
        source.discovered_jobs_count = (source.discovered_jobs_count or 0) + len(jobs)
        source.last_success_at = datetime.now(UTC)
        source.health_status = "OK"
        source.last_error = None
        await record_audit(
            db, "source.synced", "job_source", source.id, {"count": len(jobs)}
        )
        await db.commit()
        return {"status": "ok", "imported": len(jobs), "source_id": source.id}
    except HTTPException:
        raise
    except Exception as exc:
        source.health_status = "ERROR"
        source.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc


@router.post("/{source_id}/health")
async def source_health(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> dict:
    source = await db.get(JobSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    adapter = get_adapter(source.provider, source.configuration)
    result = await adapter.health_check()
    source.health_status = str(result.get("status") or "UNKNOWN")
    source.last_checked_at = datetime.now(UTC)
    if result.get("error"):
        source.last_error = str(result["error"])
    await db.commit()
    return result
