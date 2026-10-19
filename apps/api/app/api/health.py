"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    settings = get_settings()
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "database": "up" if db_ok else "down",
        "llm_configured": settings.llm_configured,
        "email_dry_run": settings.email_dry_run,
        "email_sending_enabled": settings.email_sending_enabled,
    }
