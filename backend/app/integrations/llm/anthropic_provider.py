"""Claude-backed reasoning provider.

Uses the Messages API with a JSON schema on ``output_config.format`` so every response is
machine-checkable before it reaches the decision engine. Any failure - refusal, timeout,
schema drift - returns ``None`` and the deterministic path takes over.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.llm.base import (
    CauseNarrative,
    LeakageInsights,
    PromiseExtraction,
    StrategyProposal,
)
from app.integrations.llm.prompts import (
    DIAGNOSIS_FORMAT,
    DIAGNOSIS_SYSTEM,
    LEAKAGE_FORMAT,
    LEAKAGE_SYSTEM,
    PROMISE_FORMAT,
    PROMISE_SYSTEM,
    STRATEGY_FORMAT,
    STRATEGY_SYSTEM,
)

log = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-06-01"


def _dump(payload: dict[str, Any]) -> str:
    """Sorted keys keep the request body byte-stable, which keeps the prompt cache warm."""
    return json.dumps(payload, sort_keys=True, default=str)


class AnthropicReasoner:
    name = "claude"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds, max_retries=1
        )
        self._fallback_supported = True

    async def _structured(
        self,
        *,
        system: str,
        payload: dict[str, Any],
        response_format: dict[str, Any],
        model_cls: type[ModelT],
        instruction: str,
    ) -> ModelT | None:
        # Stable system prompt first, volatile payload last, so the cached prefix holds.
        request: dict[str, Any] = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [
                {
                    "role": "user",
                    "content": f"{instruction}\n\n{_dump(payload)}",
                }
            ],
            "output_config": {"format": response_format, "effort": settings.llm_effort},
        }
        if self._fallback_supported and settings.llm_fallback_model:
            request["betas"] = [FALLBACK_BETA]
            request["fallbacks"] = [{"model": settings.llm_fallback_model}]

        try:
            response = await self._client.messages.create(**request)
        except Exception as exc:
            if self._fallback_supported and "fallback" in str(exc).lower():
                # Account or region without the beta: drop it and stay on the primary model.
                log.info("llm.fallback_unsupported", extra={"error": str(exc)[:200]})
                self._fallback_supported = False
                return await self._structured(
                    system=system,
                    payload=payload,
                    response_format=response_format,
                    model_cls=model_cls,
                    instruction=instruction,
                )
            log.warning("llm.request_failed", extra={"error": str(exc)[:300]})
            return None

        if getattr(response, "stop_reason", None) == "refusal":
            log.warning(
                "llm.refused", extra={"details": str(getattr(response, "stop_details", ""))}
            )
            return None

        text = next((block.text for block in response.content if block.type == "text"), "")
        if not text:
            return None
        try:
            return model_cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            log.warning("llm.invalid_payload", extra={"error": str(exc)[:300]})
            return None

    async def diagnose(self, context: dict) -> CauseNarrative | None:
        return await self._structured(
            system=DIAGNOSIS_SYSTEM,
            payload=context,
            response_format=DIAGNOSIS_FORMAT,
            model_cls=CauseNarrative,
            instruction="Diagnose this revenue-loss event.",
        )

    async def propose_strategy(self, context: dict) -> StrategyProposal | None:
        return await self._structured(
            system=STRATEGY_SYSTEM,
            payload=context,
            response_format=STRATEGY_FORMAT,
            model_cls=StrategyProposal,
            instruction="Propose a recovery journey for this event.",
        )

    async def summarise_leakage(self, context: dict) -> LeakageInsights | None:
        return await self._structured(
            system=LEAKAGE_SYSTEM,
            payload=context,
            response_format=LEAKAGE_FORMAT,
            model_cls=LeakageInsights,
            instruction="Write insights about where this merchant is losing revenue.",
        )

    async def extract_promise(self, transcript: str, context: dict) -> PromiseExtraction | None:
        return await self._structured(
            system=PROMISE_SYSTEM,
            payload={**context, "transcript": transcript},
            response_format=PROMISE_FORMAT,
            model_cls=PromiseExtraction,
            instruction="Extract any promise to pay from this conversation.",
        )

    async def close(self) -> None:
        await self._client.close()
