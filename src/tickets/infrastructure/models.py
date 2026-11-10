from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.catalogs.infrastructure.models import CatalogModel
from src.core.audit import AuditMixin
from src.core.database import Base


class TicketModel(AuditMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status_id: Mapped[int] = mapped_column(
        ForeignKey("catalogs.id", ondelete="RESTRICT"), index=True
    )

    status: Mapped[CatalogModel] = relationship(lazy="joined")
    images: Mapped[list["TicketImageModel"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="TicketImageModel.id"
    )


class TicketImageModel(AuditMixin, Base):
    __tablename__ = "ticket_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(512))
