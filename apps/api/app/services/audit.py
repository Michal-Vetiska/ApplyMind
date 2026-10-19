"""Audit log helper."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AuditLog


async def record_audit(
    db: AsyncSession,
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )
    db.add(entry)
    return entry
