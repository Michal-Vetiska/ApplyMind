"""IMAP sync into EmailMessage rows with classification."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.models.email import EmailAccount, EmailMessage
from app.modules.email.classifier import classify_email
from app.modules.email.imap_client import IMAPClient


def _thread_id(message_id: str, in_reply_to: str | None, references: str | None) -> str:
    if in_reply_to:
        return in_reply_to.strip()
    if references:
        parts = references.split()
        if parts:
            return parts[0].strip()
    return message_id.strip()


async def sync_account(
    db: AsyncSession,
    account: EmailAccount,
    *,
    folder: str = "INBOX",
    limit: int = 50,
) -> dict:
    password = decrypt_secret(account.encrypted_credentials)
    fetched = 0
    created = 0
    classified = 0

    with IMAPClient(
        host=account.imap_host,
        port=account.imap_port,
        username=account.email_address,
        password=password,
    ) as client:
        folders = client.list_folders()
        account.folders_json = folders
        messages = client.fetch_messages(folder, limit=limit)

    for msg in messages:
        fetched += 1
        existing = await db.execute(
            select(EmailMessage).where(
                EmailMessage.account_id == account.id,
                EmailMessage.message_id == msg.message_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        classification = classify_email(
            subject=msg.subject,
            text_body=msg.text_body,
            sender=msg.sender,
        )
        row = EmailMessage(
            account_id=account.id,
            message_id=msg.message_id,
            in_reply_to=msg.in_reply_to,
            references_header=msg.references,
            thread_identifier=_thread_id(msg.message_id, msg.in_reply_to, msg.references),
            sender=msg.sender,
            recipients=msg.recipients,
            subject=msg.subject,
            text_body=msg.text_body,
            html_body=msg.html_body,
            received_at=msg.received_at,
            classification=classification.classification,
            classification_confidence=classification.confidence,
            folder=msg.folder,
            attachment_metadata=msg.attachment_metadata,
        )
        db.add(row)
        created += 1
        classified += 1

    account.last_sync_at = datetime.now(UTC)
    account.connected = True
    await db.flush()
    return {
        "account_id": account.id,
        "fetched": fetched,
        "created": created,
        "classified": classified,
        "folder": folder,
    }
