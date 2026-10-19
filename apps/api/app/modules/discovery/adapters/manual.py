"""Manual URL / paste import adapter — no remote scraping beyond user-provided data."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.modules.discovery.base import DiscoveredJob, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class ManualAdapter(JobSourceAdapter):
    provider = "manual"
    display_name = "Manual import"
    support_level = "IMPLEMENTED"

    async def list_jobs(self) -> list[DiscoveredJob]:
        """Return jobs declared in configuration.jobs (user-provided payloads)."""
        items = self.configuration.get("jobs") or []
        if isinstance(items, dict):
            items = [items]
        return [self._map_item(item) for item in items]

    def _map_item(self, item: dict[str, Any]) -> DiscoveredJob:
        url = item.get("url") or item.get("source_url") or item.get("apply_url")
        external_id = str(item.get("external_id") or url or item.get("title") or "manual")
        if url and external_id == url:
            parsed = urlparse(url)
            external_id = f"manual:{parsed.netloc}{parsed.path}"[:255]

        apply_url = item.get("apply_url") or url
        contact = item.get("contact_email")
        caps = self.default_apply_capabilities(apply_url=apply_url, contact_email=contact)
        return DiscoveredJob(
            external_id=external_id[:255],
            title=item.get("title") or "Manual import",
            company_name=item.get("company_name") or item.get("company"),
            location=item.get("location"),
            remote_type=item.get("remote_type"),
            employment_type=item.get("employment_type"),
            description_html=item.get("description_html"),
            description_text=item.get("description_text") or item.get("description"),
            source_url=url,
            apply_url=apply_url,
            contact_email=contact,
            salary_text=item.get("salary_text"),
            technologies=item.get("technologies") or [],
            apply_capabilities=caps,
            raw_payload=item,
        )


register_adapter(ManualAdapter)
