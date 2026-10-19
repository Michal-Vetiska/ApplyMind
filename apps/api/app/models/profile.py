"""User profile, search preferences, and resumes."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class UserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    experience: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    education: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    languages: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    portfolio_projects: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    preferred_application_language: Mapped[str] = mapped_column(String(8), default="cs")
    tone_preference: Mapped[str] = mapped_column(String(64), default="professional_concise")


class SearchProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "search_profiles"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    job_titles: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    technologies: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    employment_types: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    remote_preferences: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    minimum_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="CZK")
    hourly_rate_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    seniority: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    exclusion_rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    matching_threshold: Mapped[float] = mapped_column(Float, default=60.0)
    auto_apply_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_technology: Mapped[float] = mapped_column(Float, default=0.35)
    weight_seniority: Mapped[float] = mapped_column(Float, default=0.20)
    weight_location: Mapped[float] = mapped_column(Float, default=0.20)
    weight_compensation: Mapped[float] = mapped_column(Float, default=0.15)
    weight_other: Mapped[float] = mapped_column(Float, default=0.10)


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resumes"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    target_roles: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
