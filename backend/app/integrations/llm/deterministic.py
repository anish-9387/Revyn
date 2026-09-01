"""Offline reasoning provider.

Returns ``None`` for narrative work so the deterministic engines keep ownership of the
output, and handles promise extraction with a small date and amount parser. This is the
provider used whenever no API key is configured, which keeps every demo reproducible.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.integrations.llm.base import (
    CauseNarrative,
    LeakageInsights,
    PromiseExtraction,
    StrategyProposal,
)

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
COMMITMENT_PATTERNS = (
    r"\bi(?:'| wi)?ll pay\b",
    r"\bwill (?:clear|settle|transfer|pay)\b",
    r"\bpaying (?:it )?(?:today|tomorrow|tonight)\b",
    r"\bpayment (?:will|shall) be (?:made|done)\b",
)
AMOUNT_PATTERN = r"(?:rs\.?|inr|₹)\s?([\d,]+(?:\.\d{1,2})?)"


class DeterministicReasoner:
    name = "deterministic"

    async def diagnose(self, context: dict) -> CauseNarrative | None:
        return None

    async def propose_strategy(self, context: dict) -> StrategyProposal | None:
        return None

    async def summarise_leakage(self, context: dict) -> LeakageInsights | None:
        return None

    async def extract_promise(self, transcript: str, context: dict) -> PromiseExtraction | None:
        text = transcript.lower()
        if not any(re.search(pattern, text) for pattern in COMMITMENT_PATTERNS):
            return PromiseExtraction(promised=False, confidence=0.6)

        today = date.fromisoformat(str(context.get("today", date.today().isoformat())))
        promise_date = self._resolve_date(text, today)
        amount = None
        if match := re.search(AMOUNT_PATTERN, text):
            amount = float(match.group(1).replace(",", ""))
        return PromiseExtraction(
            promised=True,
            promise_date=promise_date.isoformat(),
            amount_rupees=amount,
            confidence=0.72,
            quote=transcript.strip()[:240],
        )

    @staticmethod
    def _resolve_date(text: str, today: date) -> date:
        if "today" in text or "tonight" in text:
            return today
        if "day after tomorrow" in text:
            return today + timedelta(days=2)
        if "tomorrow" in text:
            return today + timedelta(days=1)
        if match := re.search(r"in (\d{1,2}) days?", text):
            return today + timedelta(days=int(match.group(1)))
        if "next week" in text:
            return today + timedelta(days=7)
        for index, day in enumerate(WEEKDAYS):
            if day in text:
                ahead = (index - today.weekday()) % 7 or 7
                return today + timedelta(days=ahead)
        return today + timedelta(days=3)

    async def close(self) -> None:
        return None
