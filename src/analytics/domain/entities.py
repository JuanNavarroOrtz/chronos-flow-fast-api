from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LogRow:
    """One task, flattened with its ticket and project: the only input the summary needs."""

    ticket_code: str
    ticket_description: str
    work_date: date
    hours: Decimal
    payout: Decimal | None  # None for tasks on fixed-price projects
    project_id: int
    fixed_price: Decimal | None = None  # the project's fixed price, when it has one
