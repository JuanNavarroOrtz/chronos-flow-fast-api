from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from src.core.types import Number
from src.time_logs.domain.entities import TaskEntity


class TaskCreate(BaseModel):
    work_date: date
    description: str = ""
    time_text: str | None = None  # e.g. "8:00 PM TO 10:00 PM, 11:00 PM TO 11:30 PM"
    hours: Decimal | None = None  # optional manual override


class TaskUpdate(BaseModel):
    work_date: date | None = None
    description: str | None = None
    time_text: str | None = None
    hours: Decimal | None = None


class TaskOut(BaseModel):
    id: int
    ticket_id: int
    work_date: date
    time_text: str | None
    hours: Number
    hourly_rate: Number | None  # None on fixed-price projects
    payout: Number | None
    description: str

    @classmethod
    def from_entity(cls, t: TaskEntity) -> "TaskOut":
        return cls(
            id=t.id,
            ticket_id=t.ticket_id,
            work_date=t.work_date,
            time_text=t.time_text,
            hours=t.hours,
            hourly_rate=t.hourly_rate,
            payout=t.payout,
            description=t.description,
        )
