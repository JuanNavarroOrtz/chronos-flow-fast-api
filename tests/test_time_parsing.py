from decimal import Decimal

import pytest

from src.core.errors import InvalidDataError
from src.time_logs.domain.entities import resolve_hours
from src.time_logs.domain.time_parsing import hours_from_text


@pytest.mark.parametrize(
    "text, expected",
    [
        ("8:20 PM - 10:20 PM", "2.00"),
        ("7:50 PM TO 10:11 PM", "2.35"),  # real bitácora rows
        ("2:30PM TO 6:07 PM", "3.62"),
        ("5:37 AM - 6:42 AM, 4:10 PM - 5:29 PM", "2.40"),  # multiple ranges
        ("10:19 PM - 1:19 AM", "3.00"),  # crosses midnight
        ("11:00 AM TO 01:00 PM", "2.00"),
        ("8:31 PM TO 9:54 pm", "1.38"),  # lowercase meridiem
    ],
)
def test_hours_from_text(text, expected):
    assert hours_from_text(text) == Decimal(expected)


@pytest.mark.parametrize(
    "text", ["", "750 PM TO 10:25 PM", "7:05 PM TO 9:3 PM", "13:00 PM - 2:00 PM"]
)
def test_invalid_text_is_rejected(text):
    with pytest.raises(InvalidDataError):
        hours_from_text(text)


def test_explicit_hours_override_time_text():
    # 2026-09-26 row: times say 1.83h but the log says 1.50h
    assert resolve_hours("8:32 AM TO 10:22 AM", Decimal("1.5"))[1] == Decimal("1.50")


def test_needs_text_or_hours():
    with pytest.raises(InvalidDataError):
        resolve_hours(None, None)
