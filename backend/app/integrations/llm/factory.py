"""Reasoning provider selection."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.llm.base import ReasoningProvider
from app.integrations.llm.deterministic import DeterministicReasoner

log = get_logger(__name__)

_reasoner: ReasoningProvider | None = None


def get_reasoner() -> ReasoningProvider:
    global _reasoner
    if _reasoner is None:
        if settings.llm_available:
            from app.integrations.llm.anthropic_provider import AnthropicReasoner

            try:
                _reasoner = AnthropicReasoner()
                log.info("reasoner.claude_ready", extra={"model": settings.llm_model})
            except Exception as exc:
                log.warning("reasoner.claude_unavailable", extra={"error": str(exc)})
                _reasoner = DeterministicReasoner()
        else:
            _reasoner = DeterministicReasoner()
            log.info("reasoner.deterministic", extra={"reason": "no_api_key"})
    return _reasoner


async def reset_reasoner() -> None:
    global _reasoner
    if _reasoner is not None:
        await _reasoner.close()
        _reasoner = None
