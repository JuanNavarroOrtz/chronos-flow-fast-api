from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from src.core.errors import InvalidDataError
from src.time_logs.domain.time_parsing import hours_from_text

_CENT = Decimal("0.01")


def compute_payout(hours: Decimal, hourly_rate: Decimal) -> Decimal:
    """The one place the payout rule lives (also used by analytics)."""
    return (hours * hourly_rate).quantize(_CENT, rounding=ROUND_HALF_UP)


def resolve_hours(
    time_text: str | None, hours: Decimal | None
) -> tuple[str | None, Decimal]:
    """Explicit hours win (manual override); otherwise hours are computed from the time text."""
    time_text = (time_text or "").strip() or None
    if hours is not None:
        resolved = Decimal(hours).quantize(_CENT, rounding=ROUND_HALF_UP)
    elif time_text:
        resolved = hours_from_text(time_text)
    else:
        raise InvalidDataError("Provide either time_text or hours")
    if resolved <= 0:
        raise InvalidDataError("Hours must be greater than zero")
    return time_text, resolved


@dataclass
class TaskEntity:
    ticket_id: int
    work_date: date
    hours: Decimal
    hourly_rate: (
        Decimal | None
    )  # snapshot of the project's rate; None for fixed-price projects
    description: str = ""
    time_text: str | None = None
    id: int | None = None

    @property
    def payout(self) -> Decimal | None:
        """Per-task payout. Fixed-price projects are paid per project, not per task."""
        if self.hourly_rate is None:
            return None
        return compute_payout(self.hours, self.hourly_rate)
