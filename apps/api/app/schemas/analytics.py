"""Analytics and automation schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    jobs_discovered: int = 0
    jobs_relevant: int = 0
    applications_drafted: int = 0
    applications_sent: int = 0
    employer_replies: int = 0
    interviews: int = 0
    llm_cost_usd_month: float = 0.0


class FunnelStep(BaseModel):
    status: str
    count: int


class AutomationRunOut(BaseModel):
    id: str
    job_type: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str
    processed_count: int
    success_count: int
    error_count: int
    logs: list = []

    model_config = {"from_attributes": True}


class LLMUsageOut(BaseModel):
    id: str
    operation: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    created_at: datetime
    error: str | None = None

    model_config = {"from_attributes": True}


class SettingsOut(BaseModel):
    key: str
    value: dict[str, Any]

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    value: dict[str, Any]
