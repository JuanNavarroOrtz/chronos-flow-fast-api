from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.infrastructure.repositories import SQLLogRowRepository
from src.analytics.use_cases.summary import GetSummary
from src.core.database import get_db
from src.core.types import Number

router = APIRouter(prefix="/analytics", tags=["analytics"])


class TicketSummaryOut(BaseModel):
    code: str
    description: str
    hours: Number
    percentage: Number


class SummaryOut(BaseModel):
    total_hours: Number
    total_payout: Number
    avg_hours_per_day: Number
    avg_hours_per_week: Number
    avg_hours_per_month: Number
    avg_hours_per_ticket: Number
    avg_hours_per_task: Number
    total_tickets: int
    total_tasks: int
    days_logged: int
    elapsed_days: int
    elapsed_months: Number
    current_week_hours: Number
    tickets: list[TicketSummaryOut]


def get_summary_use_case(db: Annotated[AsyncSession, Depends(get_db)]) -> GetSummary:
    return GetSummary(SQLLogRowRepository(db))


@router.get("/summary", response_model=SummaryOut)
async def get_summary(
    uc: Annotated[GetSummary, Depends(get_summary_use_case)],
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: int | None = None,
):
    return await uc.execute(date_from, date_to, project_id)
