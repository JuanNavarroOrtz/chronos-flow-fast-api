"""Turns bitácora time text ("7:05 PM TO 9:56 PM, 8:00 AM - 9:00 AM") into decimal hours."""

import re
from decimal import ROUND_HALF_UP, Decimal

from src.core.errors import InvalidDataError

_TIME = r"(\d{1,2}):(\d{2})\s*([AaPp][Mm])"
_RANGE = re.compile(rf"^{_TIME}\s*(?:-|–|—|to)\s*{_TIME}$", re.IGNORECASE)


def _minutes(hour: str, minute: str, meridiem: str) -> int:
    h, m = int(hour), int(minute)
    if not 1 <= h <= 12 or not 0 <= m <= 59:
        raise InvalidDataError(f"Invalid time: {hour}:{minute} {meridiem}")
    h = h % 12 + (12 if meridiem.lower() == "pm" else 0)
    return h * 60 + m


def parse_minutes(text: str) -> int:
    """Total minutes across all comma-separated ranges. A range ending before it starts crosses midnight."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise InvalidDataError("Time range is empty")
    total = 0
    for part in parts:
        match = _RANGE.match(part)
        if not match:
            raise InvalidDataError(
                f"Cannot read time range '{part}'. Use e.g. '8:00 PM TO 10:00 PM'"
            )
        start = _minutes(*match.group(1, 2, 3))
        end = _minutes(*match.group(4, 5, 6))
        total += (end - start) % (24 * 60) or 24 * 60
    return total


def hours_from_text(text: str) -> Decimal:
    return (Decimal(parse_minutes(text)) / 60).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
