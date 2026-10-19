"""Job deduplication helpers: content hashing and soft fingerprints."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_company_name(name: str | None) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _normalize_ws(text)
    text = re.sub(r"\b(s\.?\s*r\.?\s*o\.?|a\.?\s*s\.?|ltd\.?|inc\.?|gmbh|llc)\b", "", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return _normalize_ws(text)


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    text = unicodedata.normalize("NFKD", title)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _normalize_ws(text)
    text = re.sub(r"[^a-z0-9+#.\s/-]", "", text)
    return _normalize_ws(text)


def content_hash(
    *,
    title: str | None,
    company: str | None,
    description: str | None,
    location: str | None = None,
) -> str:
    """Stable SHA-256 hash of normalized job content for change detection."""
    payload = "|".join(
        [
            normalize_title(title),
            normalize_company_name(company),
            _normalize_ws(description or "")[:8000],
            _normalize_ws(location or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def job_fingerprint(
    *,
    company_normalized: str | None,
    title_normalized: str | None,
    content_hash_value: str | None,
) -> str:
    """Soft unique key used for cross-source duplicate detection."""
    parts = [
        (company_normalized or "").strip().lower(),
        (title_normalized or "").strip().lower(),
        (content_hash_value or "")[:32],
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def external_key(source_id: str | None, external_id: str | None) -> str:
    """Primary uniqueness key within a single source."""
    return f"{source_id or 'none'}::{external_id or ''}"


def is_duplicate_pair(
    left_hash: str | None,
    right_hash: str | None,
    *,
    left_fingerprint: str | None = None,
    right_fingerprint: str | None = None,
) -> bool:
    if left_hash and right_hash and left_hash == right_hash:
        return True
    if left_fingerprint and right_fingerprint and left_fingerprint == right_fingerprint:
        return True
    return False


def content_fingerprint(
    *,
    title: str,
    company: str | None,
    description: str | None,
    location: str | None = None,
) -> str:
    return content_hash(title=title, company=company, description=description, location=location)


def normalize_text(value: str | None) -> str:
    return _normalize_ws(value or "")


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    cleaned = url.strip().split("?")[0].split("#")[0].rstrip("/")
    return cleaned.lower()


def is_duplicate(
    *,
    existing_external_id: str | None,
    new_external_id: str | None,
    existing_hash: str | None,
    new_hash: str | None,
    existing_url: str | None = None,
    new_url: str | None = None,
) -> bool:
    if existing_external_id and new_external_id and existing_external_id == new_external_id:
        return True
    if is_duplicate_pair(existing_hash, new_hash):
        return True
    left = canonical_url(existing_url)
    right = canonical_url(new_url)
    return bool(left and right and left == right)
