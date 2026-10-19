"""IMAP client defaults for Email.cz / Seznam.cz (imap.seznam.cz:993)."""

from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Any


DEFAULT_IMAP_HOST = "imap.seznam.cz"
DEFAULT_IMAP_PORT = 993


@dataclass
class FetchedMessage:
    message_id: str
    in_reply_to: str | None
    references: str | None
    sender: str
    recipients: list[str]
    subject: str | None
    text_body: str | None
    html_body: str | None
    received_at: datetime | None
    folder: str
    attachment_metadata: list[dict[str, Any]]
    raw_headers: dict[str, str]


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_bodies(msg: Message) -> tuple[str | None, str | None]:
    text_body = None
    html_body = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if ctype == "text/plain" and text_body is None:
                text_body = decoded
            elif ctype == "text/html" and html_body is None:
                html_body = decoded
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload is not None:
                charset = msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    html_body = decoded
                else:
                    text_body = decoded
        except Exception:
            pass
    return text_body, html_body


def _attachment_meta(msg: Message) -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    for part in msg.walk():
        disposition = str(part.get("Content-Disposition") or "")
        filename = part.get_filename()
        if filename or "attachment" in disposition:
            meta.append(
                {
                    "filename": _decode_header_value(filename) if filename else None,
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                }
            )
    return meta


class IMAPClient:
    def __init__(
        self,
        *,
        host: str = DEFAULT_IMAP_HOST,
        port: int = DEFAULT_IMAP_PORT,
        username: str,
        password: str,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._conn.login(self.username, self.password)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def __enter__(self) -> IMAPClient:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def conn(self) -> imaplib.IMAP4_SSL:
        if self._conn is None:
            raise RuntimeError("IMAP client not connected")
        return self._conn

    def list_folders(self) -> list[str]:
        status, data = self.conn.list()
        if status != "OK" or not data:
            return []
        folders: list[str] = []
        for raw in data:
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
            # Last token is folder name (may be quoted)
            parts = line.split(' "/" ')
            if len(parts) == 2:
                folders.append(parts[1].strip().strip('"'))
            else:
                folders.append(line.split()[-1].strip('"'))
        return folders

    def test_connection(self) -> dict[str, Any]:
        folders = self.list_folders()
        return {"ok": True, "host": self.host, "port": self.port, "folders": folders}

    def fetch_messages(
        self,
        folder: str = "INBOX",
        *,
        limit: int = 50,
        unseen_only: bool = False,
    ) -> list[FetchedMessage]:
        status, _ = self.conn.select(folder, readonly=True)
        if status != "OK":
            raise RuntimeError(f"Unable to select folder {folder}")

        criteria = "UNSEEN" if unseen_only else "ALL"
        status, data = self.conn.search(None, criteria)
        if status != "OK" or not data or not data[0]:
            return []

        ids = data[0].split()
        ids = ids[-limit:]
        results: list[FetchedMessage] = []
        for msg_id in ids:
            status, msg_data = self.conn.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            message_id = msg.get("Message-ID") or msg.get("Message-Id") or f"imap-{msg_id.decode()}"
            received = None
            date_hdr = msg.get("Date")
            if date_hdr:
                try:
                    received = parsedate_to_datetime(date_hdr)
                except (TypeError, ValueError, IndexError):
                    received = None
            text_body, html_body = _extract_bodies(msg)
            to_raw = msg.get_all("To", [])
            recipients: list[str] = []
            for item in to_raw:
                recipients.extend([p.strip() for p in str(item).split(",") if p.strip()])
            results.append(
                FetchedMessage(
                    message_id=message_id.strip(),
                    in_reply_to=(msg.get("In-Reply-To") or None),
                    references=(msg.get("References") or None),
                    sender=_decode_header_value(msg.get("From")),
                    recipients=recipients,
                    subject=_decode_header_value(msg.get("Subject")) or None,
                    text_body=text_body,
                    html_body=html_body,
                    received_at=received,
                    folder=folder,
                    attachment_metadata=_attachment_meta(msg),
                    raw_headers={k: str(v) for k, v in msg.items()},
                )
            )
        return results
