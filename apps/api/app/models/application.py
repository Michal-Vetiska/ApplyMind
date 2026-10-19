"""Application lifecycle models."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_applications_idempotency"),
    )

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[str | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(64), default="DRAFTED", index=True)
    apply_method: Mapped[str] = mapped_column(String(64), default="EMAIL_APPROVAL_REQUIRED")
    generated_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    generated_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    external_application_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="cs")
    matching_explanation: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generation_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    submission_logs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence: Mapped[list["ApplicationEvidence"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["FollowUp"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationEvidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "application_evidence"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True
    )
    source_chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_chunks.id", ondelete="SET NULL"), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="evidence")


class FollowUp(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "follow_ups"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    suggested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUGGESTED")
    generated_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped[Application] = relationship(back_populates="follow_ups")
