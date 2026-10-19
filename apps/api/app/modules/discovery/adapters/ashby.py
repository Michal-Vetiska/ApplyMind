"""Ashby public job board posting API.

GET https://api.ashbyhq.com/posting-api/job-board/{board_name}?includeCompensation=true
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.modules.discovery.base import DiscoveredJob, JobDetails, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class AshbyAdapter(JobSourceAdapter):
    provider = "ashby"
    display_name = "Ashby"
    support_level = "IMPLEMENTED"
    BASE = "https://api.ashbyhq.com/posting-api/job-board"

    @property
    def board_name(self) -> str:
        name = self.configuration.get("board_name") or self.configuration.get("board")
        if not name:
            raise ValueError("Ashby adapter requires configuration.board_name")
        return str(name)

    async def list_jobs(self) -> list[DiscoveredJob]:
        url = f"{self.BASE}/{self.board_name}"
        params = {"includeCompensation": "true"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        jobs_raw = payload.get("jobs") if isinstance(payload, dict) else payload
        jobs_raw = jobs_raw or []
        return [self._map_job(item) for item in jobs_raw]

    async def get_job(self, external_id: str) -> JobDetails | None:
        for job in await self.list_jobs():
            if job.external_id == external_id:
                return JobDetails(**job.model_dump())
        return None

    def _map_job(self, item: dict[str, Any]) -> DiscoveredJob:
        external_id = str(item.get("id") or item.get("jobId") or "")
        location = None
        loc = item.get("location")
        if isinstance(loc, str):
            location = loc
        elif isinstance(loc, dict):
            location = loc.get("name") or loc.get("address")

        salary_text = None
        comp = item.get("compensation") or item.get("compensationTierSummary")
        if isinstance(comp, str):
            salary_text = comp
        elif isinstance(comp, dict):
            parts = []
            if comp.get("minValue") is not None:
                parts.append(str(comp["minValue"]))
            if comp.get("maxValue") is not None:
                parts.append(str(comp["maxValue"]))
            if parts:
                salary_text = " - ".join(parts)
                if comp.get("currencyCode"):
                    salary_text = f"{salary_text} {comp['currencyCode']}"

        apply_url = item.get("applyUrl") or item.get("jobUrl") or item.get("url")
        published = None
        if item.get("publishedAt"):
            try:
                published = datetime.fromisoformat(str(item["publishedAt"]).replace("Z", "+00:00"))
            except ValueError:
                published = None

        workplace = item.get("workplaceType") or item.get("employmentType")
        caps = self.default_apply_capabilities(apply_url=apply_url)
        return DiscoveredJob(
            external_id=external_id,
            title=item.get("title") or "Untitled",
            company_name=self.configuration.get("company_name"),
            location=location,
            remote_type=str(workplace).lower() if workplace else None,
            description_html=item.get("descriptionHtml") or item.get("description"),
            description_text=item.get("descriptionPlain"),
            source_url=item.get("jobUrl") or apply_url,
            apply_url=apply_url,
            published_at=published,
            salary_text=salary_text,
            apply_capabilities=caps,
            raw_payload=item,
        )


register_adapter(AshbyAdapter)
