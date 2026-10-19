"""SmartRecruiters public Posting API adapter.

GET https://api.smartrecruiters.com/v1/companies/{companyIdentifier}/postings
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.modules.discovery.base import DiscoveredJob, JobDetails, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class SmartRecruitersAdapter(JobSourceAdapter):
    provider = "smartrecruiters"
    display_name = "SmartRecruiters"
    support_level = "IMPLEMENTED"
    BASE = "https://api.smartrecruiters.com/v1/companies"

    @property
    def company_identifier(self) -> str:
        ident = (
            self.configuration.get("company_identifier")
            or self.configuration.get("companyIdentifier")
            or self.configuration.get("company")
        )
        if not ident:
            raise ValueError("SmartRecruiters adapter requires configuration.company_identifier")
        return str(ident)

    async def list_jobs(self) -> list[DiscoveredJob]:
        url = f"{self.BASE}/{self.company_identifier}/postings"
        params = {"limit": 100}
        jobs: list[DiscoveredJob] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            offset = 0
            while True:
                params["offset"] = offset
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                content = payload.get("content") or []
                for item in content:
                    jobs.append(self._map_list_item(item))
                total = payload.get("totalFound") or len(content)
                offset += len(content)
                if not content or offset >= total:
                    break
        return jobs

    async def get_job(self, external_id: str) -> JobDetails | None:
        url = f"{self.BASE}/{self.company_identifier}/postings/{external_id}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            item = response.json()
        return self._map_detail(item)

    def _map_list_item(self, item: dict[str, Any]) -> DiscoveredJob:
        external_id = str(item.get("id") or item.get("uuid") or "")
        location = None
        loc = item.get("location") or {}
        if isinstance(loc, dict):
            parts = [loc.get("city"), loc.get("region"), loc.get("country")]
            location = ", ".join(p for p in parts if p)
        ref = item.get("ref") or item.get("applyUrl")
        apply_url = ref if isinstance(ref, str) else None
        published = None
        if item.get("releasedDate"):
            try:
                published = datetime.fromisoformat(str(item["releasedDate"]).replace("Z", "+00:00"))
            except ValueError:
                published = None
        caps = self.default_apply_capabilities(apply_url=apply_url)
        return DiscoveredJob(
            external_id=external_id,
            title=item.get("name") or item.get("title") or "Untitled",
            company_name=self.configuration.get("company_name") or self.company_identifier,
            location=location,
            source_url=apply_url,
            apply_url=apply_url,
            published_at=published,
            apply_capabilities=caps,
            raw_payload=item,
        )

    def _map_detail(self, item: dict[str, Any]) -> JobDetails:
        base = self._map_list_item(item)
        job_ad = item.get("jobAd") or {}
        sections = job_ad.get("sections") or {}
        description_parts = []
        for key in ("jobDescription", "qualifications", "additionalInformation"):
            section = sections.get(key) or {}
            text = section.get("text")
            if text:
                description_parts.append(text)
        description_html = "\n".join(description_parts) or None
        data = base.model_dump()
        data["description_html"] = description_html
        return JobDetails(**data)


register_adapter(SmartRecruitersAdapter)
