"""Audit columns shared by every table: who created / last changed a row, and when.

The logged-in user's id travels in a ContextVar (set once per request by the auth dependency), and
SQLAlchemy fills the columns on insert/update. Use cases and entities never have to pass an "actor"
around. NULL in created_by / modified_by means "no user" (seed data).
"""

from contextvars import ContextVar
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def _now() -> datetime:
    return datetime.now(UTC)


def _actor() -> int | None:
    return current_user_id.get()


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=_actor
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    modified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=_actor, onupdate=_actor
    )
