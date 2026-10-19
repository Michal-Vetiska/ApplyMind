"""Registry of job source adapters."""

from __future__ import annotations

from typing import Any, Type

from app.modules.discovery.base import JobSourceAdapter

_REGISTRY: dict[str, Type[JobSourceAdapter]] = {}


def register_adapter(adapter_cls: Type[JobSourceAdapter]) -> Type[JobSourceAdapter]:
    key = adapter_cls.provider
    _REGISTRY[key] = adapter_cls
    return adapter_cls


def get_adapter(
    provider: str,
    configuration: dict[str, Any] | None = None,
) -> JobSourceAdapter:
    cls = _REGISTRY.get(provider)
    if cls is None:
        # Lazy-load adapter package to populate registry
        import app.modules.discovery.adapters  # noqa: F401

        cls = _REGISTRY.get(provider)
    if cls is None:
        raise KeyError(f"Unknown job source provider: {provider}")
    return cls(configuration=configuration)


def list_adapters() -> list[dict[str, Any]]:
    import app.modules.discovery.adapters  # noqa: F401

    return [
        {
            "provider": cls.provider,
            "display_name": cls.display_name,
            "support_level": cls.support_level,
        }
        for cls in sorted(_REGISTRY.values(), key=lambda c: c.provider)
    ]


def known_providers() -> list[str]:
    import app.modules.discovery.adapters  # noqa: F401

    return sorted(_REGISTRY.keys())
