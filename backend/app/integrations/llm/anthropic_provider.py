from __future__ import annotations

import inspect
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
    HINGLISH_FORMAT,
    HINGLISH_SYSTEM,
    LEAKAGE_FORMAT,
    LEAKAGE_SYSTEM,
    PROMISE_FORMAT,
    PROMISE_SYSTEM_HINGLISH,
    STRATEGY_FORMAT,
    STRATEGY_SYSTEM,
)

log = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

FALLBACK_BETA = "server-side-fallback-2026-06-01"


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


class AnthropicReasoner:
    name = "claude"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds, max_retries=1)
        self._fallback_supported = True
        try:
            sig = inspect.signature(self._client.messages.create)
            self._supports_betas = "betas" in sig.parameters
            self._supports_output_config = "output_config" in sig.parameters
        except Exception:
            self._supports_betas = False
            self._supports_output_config = True

    def _build_request(self, system: str, payload: dict[str, Any], response_format: dict[str, Any], instruction: str) -> dict[str, Any]:
        req: dict[str, Any] = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": f"{instruction}\n\n{_dump(payload)}"}],
        }
        if self._supports_output_config:
            req["output_config"] = {"format": response_format, "effort": settings.llm_effort}
        else:
            req["messages"][0]["content"] += f"\n\nRespond strictly as JSON matching: {json.dumps(response_format)}"
        if self._fallback_supported and self._supports_betas and settings.llm_fallback_model:
            req["betas"] = [FALLBACK_BETA]
            req["fallbacks"] = [{"model": settings.llm_fallback_model}]
        return req

    async def _structured(self, *, system: str, payload: dict[str, Any], response_format: dict[str, Any], model_cls: type[ModelT], instruction: str) -> ModelT | None:
        request = self._build_request(system, payload, response_format, instruction)
        try:
            response = await self._client.messages.create(**request)
        except TypeError as exc:
            msg = str(exc).lower()
            if "betas" in msg and "betas" in request:
                self._supports_betas = False
                request.pop("betas", None)
                request.pop("fallbacks", None)
                try:
                    response = await self._client.messages.create(**request)
                except Exception as e2:
                    log.warning("llm.request_failed", extra={"error": str(e2)[:300]})
                    return None
            elif "output_config" in msg and "output_config" in request:
                self._supports_output_config = False
                request.pop("output_config", None)
                try:
                    response = await self._client.messages.create(**request)
                except Exception as e2:
                    log.warning("llm.request_failed", extra={"error": str(e2)[:300]})
                    return None
            else:
                log.warning("llm.request_failed", extra={"error": str(exc)[:300]})
                return None
        except Exception as exc:
            if self._fallback_supported and "fallback" in str(exc).lower():
                log.info("llm.fallback_unsupported", extra={"error": str(exc)[:200]})
                self._fallback_supported = False
                return await self._structured(system=system, payload=payload, response_format=response_format, model_cls=model_cls, instruction=instruction)
            # Connection errors are expected when no valid API key / no internet - fall back silently to deterministic
            if "connection" in str(exc).lower():
                log.info("llm.unreachable_fallback_deterministic", extra={"error": str(exc)[:200]})
            else:
                log.warning("llm.request_failed", extra={"error": str(exc)[:300]})
            return None

        if getattr(response, "stop_reason", None) == "refusal":
            log.warning("llm.refused", extra={"details": str(getattr(response, "stop_details", ""))})
            return None
        text = next((block.text for block in response.content if block.type == "text"), "")
        if not text:
            return None
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "output" in data and isinstance(data["output"], dict):
                data = data["output"]
            return model_cls.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            log.warning("llm.invalid_payload", extra={"error": str(exc)[:300], "text": text[:500]})
            return None

    async def diagnose(self, context: dict) -> CauseNarrative | None:
        return await self._structured(system=DIAGNOSIS_SYSTEM, payload=context, response_format=DIAGNOSIS_FORMAT, model_cls=CauseNarrative, instruction="Diagnose this revenue-loss event.")

    async def propose_strategy(self, context: dict) -> StrategyProposal | None:
        return await self._structured(system=STRATEGY_SYSTEM, payload=context, response_format=STRATEGY_FORMAT, model_cls=StrategyProposal, instruction="Propose a recovery journey for this event.")

    async def summarise_leakage(self, context: dict) -> LeakageInsights | None:
        return await self._structured(system=LEAKAGE_SYSTEM, payload=context, response_format=LEAKAGE_FORMAT, model_cls=LeakageInsights, instruction="Write insights about where this merchant is losing revenue.")

    async def extract_promise(self, transcript: str, context: dict) -> PromiseExtraction | None:
        return await self._structured(system=PROMISE_SYSTEM_HINGLISH, payload={**context, "transcript": transcript}, response_format=PROMISE_FORMAT, model_cls=PromiseExtraction, instruction="Extract any promise to pay from this conversation.")

    async def generate_message(self, context: dict) -> dict | None:
        from pydantic import BaseModel

        class HinglishOut(BaseModel):
            body: str

        out = await self._structured(system=HINGLISH_SYSTEM, payload=context, response_format=HINGLISH_FORMAT, model_cls=HinglishOut, instruction="Generate the Hinglish recovery message.")
        return {"body": out.body} if out else None

    async def close(self) -> None:
        await self._client.close()
