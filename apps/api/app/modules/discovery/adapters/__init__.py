"""Concrete job source adapters.

Importing this package registers adapters with the discovery registry.
"""

from app.modules.discovery.adapters import (  # noqa: F401
    ashby,
    greenhouse,
    lever,
    manual,
    rss,
    smartrecruiters,
    unsupported_cz,
)

__all__ = [
    "ashby",
    "greenhouse",
    "lever",
    "manual",
    "rss",
    "smartrecruiters",
    "unsupported_cz",
]
