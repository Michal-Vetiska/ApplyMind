"""Automation control and history endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analytics import AutomationRun
from app.models.auth import UserAccount
from app.models.settings import AppSettings
from app.schemas.analytics import AutomationRunOut
from app.schemas.common import MessageOut
from app.services.audit import record_audit

router = APIRouter(prefix="/api/automations", tags=["automations"])

KNOWN_JOBS = [
    "discover_jobs",
    "normalize_jobs",
    "deduplicate_jobs",
    "evaluate_jobs",
    "generate_applications",
    "sync_inbox",
    "classify_responses",
    "suggest_followups",
    "refresh_source_health",
    "update_analytics",
]


@router.get("", response_model=list[AutomationRunOut])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[AutomationRun]:
    result = await db.execute(
        select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(100)
    )
    return list(result.scalars().all())


@router.get("/schedule")
async def schedule(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(AppSettings).where(AppSettings.key == "automation"))
    settings = result.scalar_one_or_none()
    value = settings.value if settings else {}
    return {
        "jobs": KNOWN_JOBS,
        "config": value,
        "defaults": {
            "discover_jobs_hours": 3,
            "sync_inbox_minutes": 10,
            "followup_days": 7,
            "email_dry_run": True,
            "email_sending_enabled": False,
        },
    }


@router.post("/run/{job_type}", response_model=AutomationRunOut)
async def trigger_run(
    job_type: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> AutomationRun:
    if job_type not in KNOWN_JOBS:
        raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")

    run = AutomationRun(
        job_type=job_type,
        status="RUNNING",
        logs=[{"event": "queued", "at": datetime.now(UTC).isoformat()}],
    )
    db.add(run)
    await db.flush()

    # Eager import to avoid circular imports at module load
    try:
        from app.workers import tasks

        task_fn = getattr(tasks, job_type, None)
        if task_fn is not None and hasattr(task_fn, "delay"):
            task_fn.delay(run_id=run.id)
            run.logs = list(run.logs) + [
                {"event": "celery_dispatched", "at": datetime.now(UTC).isoformat()}
            ]
        else:
            # Inline minimal completion when Celery unavailable
            run.status = "COMPLETED"
            run.completed_at = datetime.now(UTC)
            run.processed_count = 0
            run.success_count = 0
            run.logs = list(run.logs) + [
                {
                    "event": "inline_noop",
                    "detail": "Celery task not dispatched; recorded empty run",
                    "at": datetime.now(UTC).isoformat(),
                }
            ]
    except Exception as exc:
        run.status = "FAILED"
        run.completed_at = datetime.now(UTC)
        run.error_count = 1
        run.logs = list(run.logs) + [{"event": "error", "detail": str(exc)}]

    await record_audit(db, "automation.triggered", "automation_run", run.id, {"job_type": job_type})
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{run_id}/cancel", response_model=MessageOut)
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> MessageOut:
    run = await db.get(AutomationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "RUNNING":
        return MessageOut(message="Run is not running")
    run.status = "CANCELLED"
    run.completed_at = datetime.now(UTC)
    await db.commit()
    return MessageOut(message="Cancelled")
