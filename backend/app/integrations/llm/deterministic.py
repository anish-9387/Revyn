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
    r"\bpaisa\b.*\b(?:aa jayega|bhej dunga|kar dunga|de dunga)\b",
    r"\bpay(?:ment)?\b.*\bkar dunga\b",
    r"\bclear ho jayega\b",
    r"\bthoda time do\b",
    r"\bsalary aane ke baad\b",
    r"\bkar dunga\b",
)
HINGLISH_DATE_HINTS = {
    "kal": 1,
    "parso": 2,
    "agle monday": 7,
    "next monday": 7,
    "salary": 5,
}
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
        if "today" in text or "tonight" in text or "aaj" in text:
            return today
        if "day after tomorrow" in text or "parso" in text:
            return today + timedelta(days=2)
        if "tomorrow" in text or re.search(r"\bkal\b", text):
            # kal could be yesterday/tomorrow - in Hinglish promise context, kal = tomorrow
            return today + timedelta(days=1)
        if "agle monday" in text:
            # next Monday
            idx = WEEKDAYS.index("monday")
            ahead = (idx - today.weekday()) % 7 or 7
            return today + timedelta(days=ahead)
        if match := re.search(r"in (\d{1,2}) days?", text):
            return today + timedelta(days=int(match.group(1)))
        if "next week" in text:
            return today + timedelta(days=7)
        if "salary" in text:
            # salary cycle: assume 1st of next month or 5 days ahead
            if today.day < 28:
                return today + timedelta(days=5)
            # next month 1st
            if today.month == 12:
                return date(today.year + 1, 1, 1)
            return date(today.year, today.month + 1, 1)
        for index, day in enumerate(WEEKDAYS):
            if day in text:
                ahead = (index - today.weekday()) % 7 or 7
                return today + timedelta(days=ahead)
        return today + timedelta(days=3)

    async def generate_message(self, context: dict) -> dict | None:
        return None

    async def close(self) -> None:
        return None
