"""Generic RSS/Atom feed job discovery adapter."""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from app.modules.discovery.base import DiscoveredJob, JobSourceAdapter
from app.modules.discovery.registry import register_adapter


class RSSAdapter(JobSourceAdapter):
    provider = "rss"
    display_name = "RSS / Atom"
    support_level = "IMPLEMENTED"

    @property
    def feed_url(self) -> str:
        url = self.configuration.get("feed_url") or self.configuration.get("url")
        if not url:
            raise ValueError("RSS adapter requires configuration.feed_url")
        return str(url)

    async def list_jobs(self) -> list[DiscoveredJob]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(self.feed_url)
            response.raise_for_status()
            body = response.text

        parsed = feedparser.parse(body)
        jobs: list[DiscoveredJob] = []
        for entry in parsed.entries:
            jobs.append(self._map_entry(entry))
        return jobs

    def _map_entry(self, entry: Any) -> DiscoveredJob:
        external_id = str(
            getattr(entry, "id", None)
            or getattr(entry, "guid", None)
            or getattr(entry, "link", None)
            or getattr(entry, "title", "unknown")
        )
        link = getattr(entry, "link", None)
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        title = getattr(entry, "title", None) or "Untitled"
        published = None
        published_raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
        if published_raw:
            try:
                published = parsedate_to_datetime(published_raw)
            except (TypeError, ValueError, IndexError):
                try:
                    published = datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
                except ValueError:
                    published = None

        caps = self.default_apply_capabilities(apply_url=link)
        return DiscoveredJob(
            external_id=external_id[:255],
            title=title,
            company_name=self.configuration.get("company_name")
            or getattr(entry, "author", None),
            description_html=summary,
            description_text=summary,
            source_url=link,
            apply_url=link,
            published_at=published,
            apply_capabilities=caps,
            raw_payload=dict(entry) if hasattr(entry, "keys") else {"title": title, "link": link},
        )


register_adapter(RSSAdapter)
