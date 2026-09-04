"""Money helpers. Amounts are stored as integer paise, never floats."""

from __future__ import annotations

PAISE_PER_RUPEE = 100


def rupees_to_paise(rupees: float) -> int:
    return int(round(rupees * PAISE_PER_RUPEE))


def paise_to_rupees(paise: int) -> float:
    return paise / PAISE_PER_RUPEE


def format_inr(paise: int) -> str:
    """Render paise in Indian short-scale notation used across the dashboard."""
    rupees = abs(paise) / PAISE_PER_RUPEE
    sign = "-" if paise < 0 else ""
    if rupees >= 1_00_00_000:
        return f"{sign}₹{rupees / 1_00_00_000:.2f}Cr"
    if rupees >= 1_00_000:
        return f"{sign}₹{rupees / 1_00_000:.2f}L"
    if rupees >= 1_000:
        return f"{sign}₹{rupees / 1_000:.1f}K"
    return f"{sign}₹{rupees:,.0f}"


def pct(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator
