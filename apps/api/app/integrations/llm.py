"""Provider-agnostic OpenAI-compatible LLM client with usage tracking."""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.analytics import LLMUsage

logger = get_logger(__name__)

# Rough USD per 1M tokens (estimates; not billing truth)
_COST_PER_1M = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "text-embedding-3-small": {"prompt": 0.02, "completion": 0.0},
    "text-embedding-3-large": {"prompt": 0.13, "completion": 0.0},
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1M.get(model, {"prompt": 0.5, "completion": 1.5})
    return round(
        (prompt_tokens / 1_000_000) * rates["prompt"]
        + (completion_tokens / 1_000_000) * rates["completion"],
        6,
    )


class LLMClient:
    def __init__(self, settings: Settings | None = None, db: AsyncSession | None = None):
        self.settings = settings or get_settings()
        self.db = db

    @property
    def is_configured(self) -> bool:
        return self.settings.llm_configured

    @property
    def embedding_dims(self) -> int:
        return self.settings.llm_embedding_dims

    @property
    def chat_model(self) -> str:
        return self.settings.llm_chat_model

    @property
    def embedding_model(self) -> str:
        return self.settings.llm_embedding_model

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        return headers

    async def _record_usage(
        self,
        *,
        operation: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        metadata: dict | None = None,
        error: str | None = None,
    ) -> None:
        total = prompt_tokens + completion_tokens
        cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
        if self.db is None:
            logger.info(
                "llm_usage",
                operation=operation,
                model=model,
                total_tokens=total,
                estimated_cost_usd=cost,
                error=error,
            )
            return
        self.db.add(
            LLMUsage(
                operation=operation,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total,
                estimated_cost_usd=cost,
                metadata_json=metadata or {},
                error=error,
            )
        )
        try:
            await self.db.flush()
        except Exception as exc:
            logger.warning("llm_usage_flush_failed", error=str(exc))

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        operation: str = "chat",
    ) -> str:
        if not self.is_configured:
            raise RuntimeError("LLM is not configured (set LLM_API_KEY and LLM_ENABLED=true)")

        model_id = model or self.chat_model
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            await self._record_usage(operation=operation, model=model_id, error=str(exc))
            raise

        usage = data.get("usage") or {}
        await self._record_usage(
            operation=operation,
            model=model_id,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
        choices = data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content") or ""

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        operation: str = "chat_json",
    ) -> dict[str, Any]:
        content = await self.chat(
            messages,
            model=model,
            response_format={"type": "json_object"},
            operation=operation,
        )
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            # Best-effort extract JSON object
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                return json.loads(content[start : end + 1])
            raise

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
        operation: str = "embeddings",
    ) -> list[list[float]]:
        if not self.is_configured:
            raise RuntimeError("LLM is not configured for embeddings")

        model_id = model or self.embedding_model
        url = f"{self.settings.llm_base_url.rstrip('/')}/embeddings"
        payload = {"model": model_id, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            await self._record_usage(operation=operation, model=model_id, error=str(exc))
            raise

        usage = data.get("usage") or {}
        await self._record_usage(
            operation=operation,
            model=model_id,
            prompt_tokens=int(usage.get("prompt_tokens") or usage.get("total_tokens") or 0),
            completion_tokens=0,
            metadata={"batch_size": len(texts)},
        )
        items = sorted(data.get("data") or [], key=lambda x: x.get("index", 0))
        return [list(item.get("embedding") or []) for item in items]


def get_llm_client(db: AsyncSession | None = None) -> LLMClient:
    return LLMClient(db=db)
