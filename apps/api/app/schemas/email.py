"""Email schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class EmailAccountOut(BaseModel):
    id: str
    provider: str
    email_address: EmailStr
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    imap_enabled: bool
    smtp_enabled: bool
    last_sync_at: datetime | None = None
    folders_json: list = []
    allow_llm_processing: bool
    connected: bool

    model_config = {"from_attributes": True}


class EmailAccountCreate(BaseModel):
    email_address: EmailStr
    password: str
    provider: str = "email.cz"
    imap_host: str = "imap.seznam.cz"
    imap_port: int = 993
    smtp_host: str = "smtp.seznam.cz"
    smtp_port: int = 465
    allow_llm_processing: bool = False


class EmailMessageOut(BaseModel):
    id: str
    account_id: str
    message_id: str
    thread_identifier: str | None = None
    sender: str
    recipients: list
    subject: str | None = None
    text_body: str | None = None
    received_at: datetime | None = None
    classification: str
    classification_confidence: float
    related_application_id: str | None = None
    folder: str | None = None
    attachment_metadata: list = []

    model_config = {"from_attributes": True}


class SyncRequest(BaseModel):
    folder: str = "INBOX"
    limit: int = Field(default=50, ge=1, le=500)
