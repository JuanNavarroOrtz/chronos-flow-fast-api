from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.audit import AuditMixin
from src.core.database import Base


class CatalogModel(AuditMixin, Base):
    """One table for every catalog. parent_id NULL = a catalog (BILLING_TYPE); otherwise one of its values."""

    __tablename__ = "catalogs"
    __table_args__ = (UniqueConstraint("parent_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalogs.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
