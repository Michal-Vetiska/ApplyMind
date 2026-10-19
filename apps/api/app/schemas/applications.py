"""Application schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ApplicationEvidenceOut(BaseModel):
    id: str
    claim: str
    source_document_id: str | None = None
    source_chunk_id: str | None = None
    verification_status: str

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    resume_id: str | None = None
    status: str
    apply_method: str
    generated_subject: str | None = None
    generated_message: str | None = None
    approved_message: str | None = None
    approved_subject: str | None = None
    recipient_email: str | None = None
    external_application_id: str | None = None
    idempotency_key: str
    language: str
    matching_explanation: dict = {}
    generation_metadata: dict = {}
    submission_logs: list = []
    sent_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_activity_at: datetime
    failure_reason: str | None = None
    evidence: list[ApplicationEvidenceOut] = []

    model_config = {"from_attributes": True}


class GenerateApplicationRequest(BaseModel):
    job_id: str
    resume_id: str | None = None
    search_profile_id: str | None = None
    language: str | None = None


class ApproveApplicationRequest(BaseModel):
    subject: str | None = None
    message: str | None = None
    recipient_email: str | None = None


class SubmitApplicationRequest(BaseModel):
    confirm: bool = False


class TransitionRequest(BaseModel):
    status: str
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
