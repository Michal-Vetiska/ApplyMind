"""Job and match schemas."""

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class JobOut(BaseModel):
    id: str
    external_id: str
    title: str
    normalized_title: str | None = None
    description: str | None = None
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    salary_period: str | None = None
    original_salary_text: str | None = None
    salary_flag: str
    technologies: list = []
    published_at: datetime | None = None
    discovered_at: datetime
    source_url: str | None = None
    apply_url: str | None = None
    contact_email: str | None = None
    apply_method: str
    apply_capabilities: dict = {}
    status: str
    content_hash: str | None = None
    source_id: str | None = None
    company_id: str | None = None

    model_config = {"from_attributes": True}


class JobMatchOut(BaseModel):
    id: str
    job_id: str
    search_profile_id: str
    overall_score: float
    skill_score: float
    seniority_score: float
    location_score: float
    compensation_score: float
    other_score: float
    decision: str
    explanation_json: dict
    missing_skills_json: list
    evidence_json: dict
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class JobDetailOut(JobOut):
    matches: list[JobMatchOut] = []
    company_name: str | None = None
    normalized_description: str | None = None
    requirements_json: dict = {}
    raw_payload: dict = {}


class ManualJobImport(BaseModel):
    title: str
    company_name: str | None = None
    url: str | None = Field(
        default=None, validation_alias=AliasChoices("url", "source_url")
    )
    apply_url: str | None = None
    location: str | None = None
    description: str | None = None
    description_html: str | None = None
    salary_text: str | None = Field(
        default=None, validation_alias=AliasChoices("salary_text", "original_salary_text")
    )
    contact_email: str | None = None
    technologies: list[str] = Field(default_factory=list)
    remote_type: str | None = None
    employment_type: str | None = None


class EvaluateRequest(BaseModel):
    search_profile_id: str | None = None
