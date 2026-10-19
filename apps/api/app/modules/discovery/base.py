"""Job source adapter interface and shared discovery models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AdapterSupport = Literal["IMPLEMENTED", "EXPERIMENTAL", "UNSUPPORTED", "PLANNED"]
ApplyMethod = Literal[
    "FORM_ASSISTED",
    "EMAIL_APPROVAL_REQUIRED",
    "EMAIL_DRY_RUN",
    "MANUAL_EXTERNAL",
    "API_AUTHORIZED",
    "UNAVAILABLE",
]


class ApplyCapabilities(BaseModel):
    methods: list[ApplyMethod] = Field(default_factory=lambda: ["MANUAL_EXTERNAL"])
    api_submit_available: bool = False
    api_submit_reason: str | None = "Employer API key required for POST applications"
    hosted_apply_url: str | None = None
    contact_email: str | None = None
    notes: list[str] = Field(default_factory=list)


class DiscoveredJob(BaseModel):
    external_id: str
    title: str
    company_name: str | None = None
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    description_html: str | None = None
    description_text: str | None = None
    source_url: str | None = None
    apply_url: str | None = None
    contact_email: str | None = None
    published_at: datetime | None = None
    salary_text: str | None = None
    technologies: list[str] = Field(default_factory=list)
    apply_capabilities: ApplyCapabilities = Field(default_factory=ApplyCapabilities)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class JobDetails(DiscoveredJob):
    """Full job detail payload; same shape as DiscoveredJob with richer description."""

    requirements: dict[str, Any] = Field(default_factory=dict)


class JobSourceAdapter(ABC):
    """Abstract adapter for a job discovery provider."""

    provider: str
    display_name: str
    support_level: AdapterSupport = "IMPLEMENTED"

    def __init__(self, configuration: dict[str, Any] | None = None):
        self.configuration = configuration or {}

    @abstractmethod
    async def list_jobs(self) -> list[DiscoveredJob]:
        """Fetch currently open postings."""

    async def get_job(self, external_id: str) -> JobDetails | None:
        """Optional detail fetch; default finds from list_jobs."""
        for job in await self.list_jobs():
            if job.external_id == external_id:
                return JobDetails(**job.model_dump())
        return None

    async def health_check(self) -> dict[str, Any]:
        try:
            jobs = await self.list_jobs()
            return {
                "status": "OK",
                "provider": self.provider,
                "support_level": self.support_level,
                "count": len(jobs),
            }
        except Exception as exc:
            return {
                "status": "ERROR",
                "provider": self.provider,
                "support_level": self.support_level,
                "error": str(exc),
            }

    def default_apply_capabilities(
        self,
        *,
        apply_url: str | None = None,
        contact_email: str | None = None,
    ) -> ApplyCapabilities:
        methods: list[ApplyMethod] = []
        notes: list[str] = []
        if contact_email:
            methods.append("EMAIL_APPROVAL_REQUIRED")
        if apply_url:
            methods.append("FORM_ASSISTED")
            methods.append("MANUAL_EXTERNAL")
        if not methods:
            methods = ["MANUAL_EXTERNAL"]
            notes.append("No hosted apply URL or contact email discovered")
        return ApplyCapabilities(
            methods=methods,
            api_submit_available=False,
            api_submit_reason="POST application requires employer-controlled API credentials",
            hosted_apply_url=apply_url,
            contact_email=contact_email,
            notes=notes,
        )
