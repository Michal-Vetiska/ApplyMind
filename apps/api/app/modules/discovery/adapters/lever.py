"""Lever Postings API adapter (US + EU hosts).

US: https://api.lever.co/v0/postings/{site}
EU: https://api.eu.lever.co/v0/postings/{site}
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.modules.discovery.base import DiscoveredJob, JobDetails, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class LeverAdapter(JobSourceAdapter):
    provider = "lever"
    display_name = "Lever"
    support_level = "IMPLEMENTED"

    HOSTS = {
        "us": "https://api.lever.co/v0/postings",
        "eu": "https://api.eu.lever.co/v0/postings",
    }

    @property
    def site(self) -> str:
        site = self.configuration.get("site") or self.configuration.get("site_slug")
        if not site:
            raise ValueError("Lever adapter requires configuration.site")
        return str(site)

    @property
    def base_url(self) -> str:
        region = str(self.configuration.get("region", "us")).lower()
        return self.HOSTS.get(region, self.HOSTS["us"])

    async def list_jobs(self) -> list[DiscoveredJob]:
        url = f"{self.base_url}/{self.site}"
        params = {"mode": "json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        items = payload if isinstance(payload, list) else payload.get("data", [])
        return [self._map_job(item) for item in items]

    async def get_job(self, external_id: str) -> JobDetails | None:
        url = f"{self.base_url}/{self.site}/{external_id}"
        params = {"mode": "json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            item = response.json()
        return JobDetails(**self._map_job(item).model_dump())

    def _map_job(self, item: dict[str, Any]) -> DiscoveredJob:
        external_id = str(item.get("id") or "")
        categories = item.get("categories") or {}
        location = categories.get("location") or item.get("location")
        commitment = categories.get("commitment")
        workplace = categories.get("workplaceType") or item.get("workplaceType")

        salary_text = None
        salary = item.get("salaryRange") or item.get("salary")
        if isinstance(salary, dict):
            parts = []
            if salary.get("min") is not None:
                parts.append(str(salary["min"]))
            if salary.get("max") is not None:
                parts.append(str(salary["max"]))
            currency = salary.get("currency")
            interval = salary.get("interval")
            if parts:
                salary_text = " - ".join(parts)
                if currency:
                    salary_text = f"{salary_text} {currency}"
                if interval:
                    salary_text = f"{salary_text} / {interval}"

        apply_url = item.get("hostedUrl") or item.get("applyUrl") or item.get("url")
        published = None
        created = item.get("createdAt")
        if isinstance(created, (int, float)):
            published = datetime.fromtimestamp(created / 1000 if created > 1e12 else created, tz=UTC)

        description = item.get("description") or item.get("descriptionPlain")
        description_html = item.get("descriptionBody") or item.get("description")

        caps = self.default_apply_capabilities(apply_url=apply_url)
        return DiscoveredJob(
            external_id=external_id,
            title=item.get("text") or item.get("title") or "Untitled",
            company_name=self.configuration.get("company_name"),
            location=str(location) if location else None,
            remote_type=str(workplace).lower() if workplace else None,
            employment_type=str(commitment).lower().replace(" ", "_") if commitment else None,
            description_html=description_html if isinstance(description_html, str) else None,
            description_text=description if isinstance(description, str) else None,
            source_url=apply_url,
            apply_url=apply_url,
            published_at=published,
            salary_text=salary_text,
            apply_capabilities=caps,
            raw_payload=item,
        )


register_adapter(LeverAdapter)
