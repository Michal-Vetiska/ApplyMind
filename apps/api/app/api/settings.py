"""Application settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth import UserAccount
from app.models.settings import AppSettings
from app.schemas.analytics import SettingsOut, SettingsUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SettingsOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> list[AppSettings]:
    result = await db.execute(select(AppSettings).order_by(AppSettings.key))
    return list(result.scalars().all())


@router.get("/runtime")
async def runtime_settings(_: UserAccount = Depends(get_current_user)) -> dict:
    """Non-secret runtime flags from environment (never expose API keys)."""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "debug": settings.debug,
        "llm_configured": settings.llm_configured,
        "llm_chat_model": settings.llm_chat_model,
        "llm_embedding_model": settings.llm_embedding_model,
        "llm_base_url": settings.llm_base_url,
        "llm_monthly_budget_usd": settings.llm_monthly_budget_usd,
        "email_dry_run": settings.email_dry_run,
        "email_sending_enabled": settings.email_sending_enabled,
        "daily_send_limit": settings.daily_send_limit,
    }


@router.get("/{key}", response_model=SettingsOut)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return row


@router.put("/{key}", response_model=SettingsOut)
async def upsert_setting(
    key: str,
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: UserAccount = Depends(get_current_user),
) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        row = AppSettings(key=key, value=payload.value)
        db.add(row)
    else:
        row.value = payload.value
    await record_audit(db, "settings.updated", "app_settings", row.id, {"key": key})
    await db.commit()
    await db.refresh(row)
    return row
