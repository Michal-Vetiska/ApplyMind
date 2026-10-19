"""Job source schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    id: str
    name: str
    provider: str
    source_url: str | None = None
    configuration: dict = {}
    enabled: bool
    poll_interval_minutes: int
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    health_status: str
    last_error: str | None = None
    discovered_jobs_count: int

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    name: str
    provider: str
    source_url: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    poll_interval_minutes: int = 180


class SourceUpdate(BaseModel):
    name: str | None = None
    source_url: str | None = None
    configuration: dict[str, Any] | None = None
    enabled: bool | None = None
    poll_interval_minutes: int | None = None


class AdapterInfo(BaseModel):
    provider: str
    display_name: str
    support_level: str
