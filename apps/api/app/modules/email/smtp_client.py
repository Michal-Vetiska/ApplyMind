"""SMTP client defaults for Email.cz / Seznam.cz (smtp.seznam.cz:465).

EMAIL_DRY_RUN defaults to True — messages are logged, not sent.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_SMTP_HOST = "smtp.seznam.cz"
DEFAULT_SMTP_PORT = 465


@dataclass
class SendResult:
    success: bool
    dry_run: bool
    message_id: str | None
    detail: str
    provider_response: str | None = None


class SMTPClient:
    def __init__(
        self,
        *,
        host: str = DEFAULT_SMTP_HOST,
        port: int = DEFAULT_SMTP_PORT,
        username: str,
        password: str,
        dry_run: bool | None = None,
        sending_enabled: bool | None = None,
    ):
        settings = get_settings()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.dry_run = settings.email_dry_run if dry_run is None else dry_run
        self.sending_enabled = (
            settings.email_sending_enabled if sending_enabled is None else sending_enabled
        )

    def build_message(
        self,
        *,
        from_addr: str,
        to_addrs: list[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        reply_to: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")
        for filename, content, mime in attachments or []:
            maintype, _, subtype = mime.partition("/")
            msg.add_attachment(
                content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=filename,
            )
        return msg

    def send(self, message: EmailMessage) -> SendResult:
        message_id = message.get("Message-ID")
        if self.dry_run or not self.sending_enabled:
            logger.info(
                "email_dry_run",
                to=message.get("To"),
                subject=message.get("Subject"),
                dry_run=self.dry_run,
                sending_enabled=self.sending_enabled,
            )
            return SendResult(
                success=True,
                dry_run=True,
                message_id=message_id,
                detail="Dry-run: message not sent (EMAIL_DRY_RUN or sending disabled)",
            )

        recipients = [a.strip() for a in str(message.get("To") or "").split(",") if a.strip()]
        try:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as smtp:
                smtp.login(self.username, self.password)
                refused = smtp.send_message(message)
            if refused:
                return SendResult(
                    success=False,
                    dry_run=False,
                    message_id=message_id,
                    detail="SMTP accepted with refused recipients",
                    provider_response=str(refused),
                )
            # SMTP acceptance != employer received
            return SendResult(
                success=True,
                dry_run=False,
                message_id=message_id,
                detail="SMTP accepted message (SENT_UNCONFIRMED until Sent-folder reconciliation)",
            )
        except smtplib.SMTPException as exc:
            return SendResult(
                success=False,
                dry_run=False,
                message_id=message_id,
                detail=f"SMTP error: {exc}",
            )
        except TimeoutError as exc:
            return SendResult(
                success=False,
                dry_run=False,
                message_id=message_id,
                detail=f"SMTP timeout: {exc}",
            )

    def test_connection(self) -> dict[str, Any]:
        if self.dry_run and not self.sending_enabled:
            return {
                "ok": True,
                "dry_run": True,
                "detail": "Skipped live SMTP login because EMAIL_DRY_RUN is enabled",
            }
        try:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=15) as smtp:
                smtp.login(self.username, self.password)
            return {"ok": True, "dry_run": False, "host": self.host, "port": self.port}
        except Exception as exc:
            return {"ok": False, "dry_run": False, "error": str(exc)}
