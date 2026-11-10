"""The 'Indicadores Clave' / 'Resumen por Ticket' sheet, computed from task rows."""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from src.analytics.domain.entities import LogRow
from src.analytics.domain.repositories import LogRowRepository

ZERO = Decimal("0.00")
_CENT = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _avg(total: Decimal, count: int) -> Decimal:
    return _q(total / count) if count else ZERO


@dataclass
class TicketSummary:
    code: str
    description: str
    hours: Decimal
    percentage: Decimal


@dataclass
class Summary:
    total_hours: Decimal = ZERO
    total_payout: Decimal = ZERO
    avg_hours_per_day: Decimal = ZERO
    avg_hours_per_week: Decimal = ZERO
    avg_hours_per_month: Decimal = ZERO
    avg_hours_per_ticket: Decimal = ZERO
    avg_hours_per_task: Decimal = ZERO
    total_tickets: int = 0
    total_tasks: int = 0
    days_logged: int = 0
    elapsed_days: int = 0
    elapsed_months: Decimal = ZERO
    current_week_hours: Decimal = ZERO
    tickets: list[TicketSummary] = field(default_factory=list)


def _code_key(code: str) -> tuple[str, int]:
    prefix, _, number = code.rpartition("-")
    return prefix, int(number) if number.isdigit() else 0


def compute_summary(rows: list[LogRow], today: date | None = None) -> Summary:
    """Pure function: rows in, numbers out. No database, no clock unless `today` is omitted."""
    if not rows:
        return Summary()
    today = today or date.today()

    total_hours = sum((r.hours for r in rows), ZERO)
    # Hourly tasks add up; a fixed-price project counts once, however many tasks it has.
    hourly_payout = sum((r.payout for r in rows if r.payout is not None), ZERO)
    fixed_prices = {
        r.project_id: r.fixed_price for r in rows if r.fixed_price is not None
    }
    total_payout = hourly_payout + sum(fixed_prices.values(), ZERO)

    days = {r.work_date for r in rows}
    weeks = {r.work_date.isocalendar()[:2] for r in rows}
    months = {(r.work_date.year, r.work_date.month) for r in rows}
    elapsed_days = (max(days) - min(days)).days
    this_week = today.isocalendar()[:2]

    by_ticket: dict[str, list[LogRow]] = {}
    for r in rows:
        by_ticket.setdefault(r.ticket_code, []).append(r)

    tickets = [
        TicketSummary(
            code=code,
            description=group[0].ticket_description,
            hours=(hours := sum((r.hours for r in group), ZERO)),
            percentage=_q(hours / total_hours * 100) if total_hours else ZERO,
        )
        for code, group in sorted(by_ticket.items(), key=lambda kv: _code_key(kv[0]))
    ]

    return Summary(
        total_hours=_q(total_hours),
        total_payout=_q(total_payout),
        avg_hours_per_day=_avg(total_hours, len(days)),
        avg_hours_per_week=_avg(total_hours, len(weeks)),
        avg_hours_per_month=_avg(total_hours, len(months)),
        avg_hours_per_ticket=_avg(total_hours, len(by_ticket)),
        avg_hours_per_task=_avg(total_hours, len(rows)),
        total_tickets=len(by_ticket),
        total_tasks=len(rows),
        days_logged=len(days),
        elapsed_days=elapsed_days,
        elapsed_months=_q(Decimal(elapsed_days) / Decimal("30.4")),
        current_week_hours=_q(
            sum(
                (r.hours for r in rows if r.work_date.isocalendar()[:2] == this_week),
                ZERO,
            )
        ),
        tickets=tickets,
    )


class GetSummary:
    def __init__(self, repo: LogRowRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        project_id: int | None = None,
        today: date | None = None,
    ) -> Summary:
        rows = await self._repo.list_rows(date_from, date_to, project_id)
        return compute_summary(rows, today)
