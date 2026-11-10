from datetime import date
from decimal import Decimal

from src.analytics.use_cases.summary import LogRow, compute_summary


def row(code, day, hours, project_id=1, fixed_price=None):
    h = Decimal(hours)
    payout = None if fixed_price is not None else (h * 7).quantize(Decimal("0.01"))
    return LogRow(code, f"desc {code}", day, h, payout, project_id, fixed_price)


def test_empty_summary_is_zeroed():
    s = compute_summary([])
    assert s.total_hours == 0 and s.tickets == []


def test_summary_matches_sheet_formulas():
    rows = [
        row("IC-10", date(2026, 7, 27), "2.00"),
        row("IC-6", date(2026, 7, 27), "2.00"),
        row("IC-10", date(2026, 8, 4), "2.48"),
        row("IC-10", date(2026, 10, 29), "2.00"),
    ]
    s = compute_summary(rows, today=date(2026, 11, 10))
    assert s.total_hours == Decimal("8.48")
    assert s.total_payout == Decimal("59.36")
    assert s.total_tasks == 4 and s.total_tickets == 2
    assert s.days_logged == 3
    assert s.elapsed_days == 94 and s.elapsed_months == Decimal("3.09")
    assert s.avg_hours_per_task == Decimal("2.12")
    assert s.avg_hours_per_month == Decimal("2.83")  # 3 distinct months
    assert s.current_week_hours == 0
    assert [t.code for t in s.tickets] == ["IC-6", "IC-10"]  # natural order
    assert s.tickets[1].percentage == Decimal("76.42")


def test_fixed_price_counts_once_per_project_not_per_task():
    rows = [
        row(
            "AB-1",
            date(2026, 8, 1),
            "2.00",
            project_id=2,
            fixed_price=Decimal("1000.00"),
        ),
        row(
            "AB-1",
            date(2026, 8, 2),
            "3.00",
            project_id=2,
            fixed_price=Decimal("1000.00"),
        ),
        row("IC-1", date(2026, 8, 2), "1.00", project_id=1),  # hourly: 1h x $7
    ]
    s = compute_summary(rows, today=date(2026, 11, 10))
    assert s.total_hours == Decimal("6.00")
    assert s.total_payout == Decimal("1007.00")
