"""ApplyRouter — select submission strategy based on capabilities and settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings, get_settings


@dataclass
class ApplyDecision:
    method: str
    reason: str
    available: bool = True
    requires_approval: bool = True
    dry_run: bool = True
    apply_url: str | None = None
    contact_email: str | None = None
    notes: list[str] = field(default_factory=list)


class ApplyRouter:
    """Choose among EMAIL_*, FORM_ASSISTED, MANUAL_EXTERNAL, API_AUTHORIZED."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def decide(
        self,
        *,
        apply_capabilities: dict[str, Any] | None = None,
        apply_method_hint: str | None = None,
        apply_url: str | None = None,
        contact_email: str | None = None,
        api_credentials_present: bool = False,
    ) -> ApplyDecision:
        caps = apply_capabilities or {}
        methods = list(caps.get("methods") or [])
        hosted = caps.get("hosted_apply_url") or apply_url
        email = caps.get("contact_email") or contact_email
        api_available = bool(caps.get("api_submit_available")) and api_credentials_present

        notes: list[str] = list(caps.get("notes") or [])

        # Explicit API path only with real credentials
        if api_available or (apply_method_hint == "API_AUTHORIZED" and api_credentials_present):
            return ApplyDecision(
                method="API_AUTHORIZED",
                reason="Employer-authorized API credentials are configured",
                available=True,
                requires_approval=True,
                dry_run=False,
                apply_url=hosted,
                contact_email=email,
                notes=notes,
            )

        if apply_method_hint == "API_AUTHORIZED" and not api_credentials_present:
            notes.append("API_AUTHORIZED requested but credentials missing — falling back")

        # Prefer email when contact is known
        if email or "EMAIL_APPROVAL_REQUIRED" in methods or "EMAIL_DRY_RUN" in methods:
            dry = self.settings.email_dry_run or not self.settings.email_sending_enabled
            method = "EMAIL_DRY_RUN" if dry else "EMAIL_APPROVAL_REQUIRED"
            return ApplyDecision(
                method=method,
                reason=(
                    "EMAIL_DRY_RUN default — real SMTP disabled"
                    if dry
                    else "Email submission requires explicit approval"
                ),
                available=True,
                requires_approval=True,
                dry_run=dry,
                apply_url=hosted,
                contact_email=email,
                notes=notes,
            )

        if hosted or "FORM_ASSISTED" in methods:
            return ApplyDecision(
                method="FORM_ASSISTED",
                reason="Hosted application form available; Playwright assist with CAPTCHA pause",
                available=True,
                requires_approval=True,
                dry_run=False,
                apply_url=hosted,
                contact_email=email,
                notes=notes + ["Stop on CAPTCHA or login wall; no credential bypass"],
            )

        return ApplyDecision(
            method="MANUAL_EXTERNAL",
            reason="No email contact or hosted form — open source URL manually",
            available=True,
            requires_approval=True,
            dry_run=False,
            apply_url=hosted,
            contact_email=email,
            notes=notes or ["Manual external application"],
        )


def select_apply_method(**kwargs: Any) -> ApplyDecision:
    return ApplyRouter().decide(**kwargs)
