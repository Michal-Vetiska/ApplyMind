"""Czech portal adapters marked UNSUPPORTED — no unauthorized scrapers.

Jobs.cz, Prace.cz, StartupJobs marketplace, and Webtrh do not offer verified
public candidate discovery APIs suitable for automated marketplace search.
Users should use manual URL import, RSS (when available), or email alerts.
"""

from __future__ import annotations

from typing import Any

from app.modules.discovery.base import DiscoveredJob, JobSourceAdapter
from app.modules.discovery.registry import register_adapter

_UNSUPPORTED_REASON = (
    "No verified public candidate API for automated discovery. "
    "Use manual URL import, company career pages (ATS adapters), "
    "RSS/Atom feeds, or email job alerts instead."
)


class _UnsupportedCZBase(JobSourceAdapter):
    support_level = "UNSUPPORTED"

    async def list_jobs(self) -> list[DiscoveredJob]:
        raise RuntimeError(
            f"{self.display_name} discovery is UNSUPPORTED: {_UNSUPPORTED_REASON}"
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "UNSUPPORTED",
            "provider": self.provider,
            "support_level": self.support_level,
            "reason": _UNSUPPORTED_REASON,
            "fallbacks": ["manual", "rss", "email alerts", "ATS company boards"],
        }


class JobsCzAdapter(_UnsupportedCZBase):
    provider = "jobs_cz"
    display_name = "Jobs.cz"


class PraceCzAdapter(_UnsupportedCZBase):
    provider = "prace_cz"
    display_name = "Prace.cz"


class StartupJobsAdapter(_UnsupportedCZBase):
    provider = "startupjobs"
    display_name = "StartupJobs"
    # Official API is company-scoped (Bearer), not candidate marketplace search.


class WebtrhAdapter(_UnsupportedCZBase):
    provider = "webtrh"
    display_name = "Webtrh"


register_adapter(JobsCzAdapter)
register_adapter(PraceCzAdapter)
register_adapter(StartupJobsAdapter)
register_adapter(WebtrhAdapter)
