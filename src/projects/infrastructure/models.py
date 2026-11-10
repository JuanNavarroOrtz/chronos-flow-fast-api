from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.catalogs.infrastructure.models import CatalogModel
from src.core.audit import AuditMixin
from src.core.database import Base


class ProjectModel(AuditMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    acronym: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    billing_type_id: Mapped[int] = mapped_column(
        ForeignKey("catalogs.id", ondelete="RESTRICT"), index=True
    )
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    fixed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status_id: Mapped[int] = mapped_column(
        ForeignKey("catalogs.id", ondelete="RESTRICT"), index=True
    )

    # Two foreign keys point at the same table, so each relationship names its own.
    billing_type: Mapped[CatalogModel] = relationship(
        foreign_keys=[billing_type_id], lazy="joined"
    )
    status: Mapped[CatalogModel] = relationship(foreign_keys=[status_id], lazy="joined")
