"""Analytics endpoints backed by live database aggregates."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.analytics import AutomationRun, LLMUsage
from app.models.application import Application
from app.models.auth import UserAccount
from app.models.job import Job, JobMatch
from app.schemas.analytics import (
    AutomationRunOut,
    FunnelStep,
    LLMUsageOut,
    OverviewMetrics,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewMetrics)
async def overview(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> OverviewMetrics:
    jobs_discovered = int(
        (
            await db.execute(
                select(func.count()).select_from(Job).where(Job.deleted_at.is_(None))
            )
        ).scalar()
        or 0
    )
    jobs_relevant = int(
        (
            await db.execute(
                select(func.count()).select_from(JobMatch).where(JobMatch.overall_score >= 60)
            )
        ).scalar()
        or 0
    )
    applications_drafted = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.status.in_(["DRAFTED", "READY_FOR_REVIEW", "APPROVED"]))
            )
        ).scalar()
        or 0
    )
    applications_sent = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.status.in_(
                        ["SENT_UNCONFIRMED", "SUBMITTED", "EMPLOYER_REPLIED", "INTERVIEW", "OFFER"]
                    )
                )
            )
        ).scalar()
        or 0
    )
    employer_replies = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.status == "EMPLOYER_REPLIED")
            )
        ).scalar()
        or 0
    )
    interviews = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.status.in_(["INTERVIEW", "TECHNICAL_ASSIGNMENT"]))
            )
        ).scalar()
        or 0
    )

    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    llm_cost = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(LLMUsage.estimated_cost_usd), 0.0)).where(
                    LLMUsage.created_at >= month_start
                )
            )
        ).scalar()
        or 0.0
    )

    return OverviewMetrics(
        jobs_discovered=jobs_discovered,
        jobs_relevant=jobs_relevant,
        applications_drafted=applications_drafted,
        applications_sent=applications_sent,
        employer_replies=employer_replies,
        interviews=interviews,
        llm_cost_usd_month=round(llm_cost, 4),
    )


@router.get("/funnel", response_model=list[FunnelStep])
async def funnel(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[FunnelStep]:
    result = await db.execute(
        select(Application.status, func.count())
        .group_by(Application.status)
        .order_by(func.count().desc())
    )
    return [FunnelStep(status=row[0], count=int(row[1])) for row in result.all()]


@router.get("/llm-usage", response_model=list[LLMUsageOut])
async def llm_usage(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
) -> list[LLMUsage]:
    result = await db.execute(
        select(LLMUsage).order_by(LLMUsage.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/automations", response_model=list[AutomationRunOut])
async def automation_history(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
) -> list[AutomationRun]:
    result = await db.execute(
        select(AutomationRun).order_by(AutomationRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
