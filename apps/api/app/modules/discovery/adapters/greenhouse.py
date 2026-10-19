"""Greenhouse public Job Board API adapter.

GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.modules.discovery.base import DiscoveredJob, JobDetails, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class GreenhouseAdapter(JobSourceAdapter):
    provider = "greenhouse"
    display_name = "Greenhouse"
    support_level = "IMPLEMENTED"
    BASE = "https://boards-api.greenhouse.io/v1/boards"

    @property
    def board_token(self) -> str:
        token = self.configuration.get("board_token") or self.configuration.get("board")
        if not token:
            raise ValueError("Greenhouse adapter requires configuration.board_token")
        return str(token)

    async def list_jobs(self) -> list[DiscoveredJob]:
        url = f"{self.BASE}/{self.board_token}/jobs"
        params = {"content": "true"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        jobs: list[DiscoveredJob] = []
        for item in payload.get("jobs", []):
            jobs.append(self._map_job(item))
        return jobs

    async def get_job(self, external_id: str) -> JobDetails | None:
        url = f"{self.BASE}/{self.board_token}/jobs/{external_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            item = response.json()
        base = self._map_job(item)
        return JobDetails(**base.model_dump())

    def _map_job(self, item: dict[str, Any]) -> DiscoveredJob:
        external_id = str(item.get("id") or item.get("internal_job_id") or "")
        location = None
        if isinstance(item.get("location"), dict):
            location = item["location"].get("name")
        elif item.get("location"):
            location = str(item["location"])

        apply_url = item.get("absolute_url")
        published = None
        if item.get("updated_at"):
            try:
                published = datetime.fromisoformat(str(item["updated_at"]).replace("Z", "+00:00"))
            except ValueError:
                published = None

        caps = self.default_apply_capabilities(apply_url=apply_url)
        return DiscoveredJob(
            external_id=external_id,
            title=item.get("title") or "Untitled",
            company_name=self.configuration.get("company_name"),
            location=location,
            description_html=item.get("content"),
            source_url=apply_url,
            apply_url=apply_url,
            published_at=published,
            apply_capabilities=caps,
            raw_payload=item,
        )


register_adapter(GreenhouseAdapter)
