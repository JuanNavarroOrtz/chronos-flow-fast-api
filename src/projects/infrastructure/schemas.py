from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from src.catalogs.infrastructure.schemas import CatalogItemOut
from src.core.types import Number
from src.projects.domain.entities import ProjectEntity


class ProjectCreate(BaseModel):
    name: str
    acronym: str
    billing_type_id: int  # a value of the BILLING_TYPE catalog (see GET /catalogs/BILLING_TYPE/items)
    hourly_rate: Decimal | None = None  # required when the billing type is HOURLY
    fixed_price: Decimal | None = None  # required when the billing type is FIXED
    start_date: date
    end_date: date | None = None
    status_id: int | None = None  # a PROJECT_STATUS value; defaults to ACTIVE


class ProjectUpdate(BaseModel):
    name: str | None = None
    acronym: str | None = None
    billing_type_id: int | None = None
    hourly_rate: Decimal | None = None
    fixed_price: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    status_id: int | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    acronym: str
    billing_type: CatalogItemOut
    hourly_rate: Number | None
    fixed_price: Number | None
    start_date: date
    end_date: date | None
    status: CatalogItemOut
    created_at: datetime
    created_by: int | None
    modified_at: datetime
    modified_by: int | None

    @classmethod
    def from_entity(cls, p: ProjectEntity) -> "ProjectOut":
        return cls(**{name: getattr(p, name) for name in cls.model_fields})
