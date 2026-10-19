"""Email account and message models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class EmailAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "email_accounts"

    provider: Mapped[str] = mapped_column(String(64), default="email.cz")
    email_address: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), default="imap.seznam.cz")
    imap_port: Mapped[int] = mapped_column(default=993)
    smtp_host: Mapped[str] = mapped_column(String(255), default="smtp.seznam.cz")
    smtp_port: Mapped[int] = mapped_column(default=465)
    imap_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    folders_json: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    allow_llm_processing: Mapped[bool] = mapped_column(Boolean, default=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=True)

    messages: Mapped[list["EmailMessage"]] = relationship(back_populates="account")


class EmailMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint("account_id", "message_id", name="uq_email_messages_account_msgid"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[str] = mapped_column(String(512), nullable=False)
    in_reply_to: Mapped[str | None] = mapped_column(String(512), nullable=True)
    references_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    thread_identifier: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    sender: Mapped[str] = mapped_column(String(512), nullable=False)
    recipients: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classification: Mapped[str] = mapped_column(String(64), default="UNCERTAIN")
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    related_application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    association_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    folder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_metadata: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[EmailAccount] = relationship(back_populates="messages")
