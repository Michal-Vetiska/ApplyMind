"""Job discovery and matching models."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class JobSource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_minutes: Mapped[int] = mapped_column(Integer, default=180)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_jobs_count: Mapped[int] = mapped_column(Integer, default=0)

    jobs: Mapped[list["Job"]] = relationship(back_populates="source")


class Company(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    briefing: Mapped[str | None] = mapped_column(Text, nullable=True)
    intelligence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_jobs_source_external"),
        Index("ix_jobs_content_hash", "content_hash"),
        Index("ix_jobs_status", "status"),
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[str | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_salary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_flag: Mapped[str] = mapped_column(String(32), default="SALARY_UNKNOWN")
    technologies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    apply_method: Mapped[str] = mapped_column(String(64), default="MANUAL_EXTERNAL")
    apply_capabilities: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DISCOVERED")
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source: Mapped[JobSource | None] = relationship(back_populates="jobs")
    company: Mapped[Company | None] = relationship(back_populates="jobs")
    matches: Mapped[list["JobMatch"]] = relationship(back_populates="job")


class JobMatch(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "search_profile_id", name="uq_job_matches_job_profile"),
    )

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    search_profile_id: Mapped[str] = mapped_column(
        ForeignKey("search_profiles.id", ondelete="CASCADE"), index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_score: Mapped[float] = mapped_column(Float, default=0)
    seniority_score: Mapped[float] = mapped_column(Float, default=0)
    location_score: Mapped[float] = mapped_column(Float, default=0)
    compensation_score: Mapped[float] = mapped_column(Float, default=0)
    other_score: Mapped[float] = mapped_column(Float, default=0)
    decision: Mapped[str] = mapped_column(String(32), default="REVIEW")
    explanation_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    missing_skills_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    rule_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="matches")
