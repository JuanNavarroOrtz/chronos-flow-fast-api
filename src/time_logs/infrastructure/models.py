from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.audit import AuditMixin
from src.core.database import Base


class TaskModel(AuditMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    work_date: Mapped[date] = mapped_column(Date, index=True)
    time_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
