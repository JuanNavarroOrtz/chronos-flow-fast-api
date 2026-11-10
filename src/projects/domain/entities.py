import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from src.catalogs.domain.entities import FIXED, HOURLY, CatalogItem
from src.core.errors import InvalidDataError

_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}$")
_CENT = Decimal("0.01")


def _money(value: Decimal | None) -> Decimal | None:
    return (
        None
        if value is None
        else Decimal(value).quantize(_CENT, rounding=ROUND_HALF_UP)
    )


@dataclass
class ProjectEntity:
    name: str
    acronym: str
    billing_type: CatalogItem  # a BILLING_TYPE catalog value (HOURLY / FIXED)
    status: CatalogItem  # a PROJECT_STATUS catalog value
    start_date: date
    hourly_rate: Decimal | None = None
    fixed_price: Decimal | None = None
    end_date: date | None = None
    id: int | None = None
    # Audit data is filled by the database layer (see core/audit.py); read-only here.
    created_at: datetime | None = None
    created_by: int | None = None
    modified_at: datetime | None = None
    modified_by: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.name = self.name.strip()
        self.acronym = self.acronym.strip().upper()
        self.hourly_rate = _money(self.hourly_rate)
        self.fixed_price = _money(self.fixed_price)
        if not self.name:
            raise InvalidDataError("Project name is required")
        if not _ACRONYM_RE.match(self.acronym):
            raise InvalidDataError(
                "Acronym must be 2-10 letters/digits and start with a letter (e.g. 'IC')"
            )
        if self.end_date and self.end_date < self.start_date:
            raise InvalidDataError("end_date cannot be before start_date")
        if self.billing_type.code == HOURLY:
            if self.hourly_rate is None or self.hourly_rate <= 0:
                raise InvalidDataError(
                    "Hourly projects need an hourly_rate greater than zero"
                )
            if self.fixed_price is not None:
                raise InvalidDataError("fixed_price must be empty for hourly projects")
        elif self.billing_type.code == FIXED:
            if self.fixed_price is None or self.fixed_price <= 0:
                raise InvalidDataError(
                    "Fixed-price projects need a fixed_price greater than zero"
                )
            if self.hourly_rate is not None:
                raise InvalidDataError(
                    "hourly_rate must be empty for fixed-price projects"
                )
        else:
            raise InvalidDataError(
                f"Billing type '{self.billing_type.code}' has no pricing rules yet"
            )

    @property
    def task_hourly_rate(self) -> Decimal | None:
        """Rate copied onto each new task. Fixed-price projects have no per-hour rate."""
        return self.hourly_rate if self.billing_type.code == HOURLY else None
