"""Job discovery adapters and registry."""

from app.modules.discovery.base import (
    ApplyCapabilities,
    DiscoveredJob,
    JobDetails,
    JobSourceAdapter,
)
from app.modules.discovery.registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "ApplyCapabilities",
    "DiscoveredJob",
    "JobDetails",
    "JobSourceAdapter",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
