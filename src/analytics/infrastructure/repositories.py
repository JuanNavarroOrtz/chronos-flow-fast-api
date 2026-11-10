from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.domain.entities import LogRow
from src.projects.infrastructure.models import ProjectModel
from src.tickets.infrastructure.models import TicketModel
from src.time_logs.domain.entities import compute_payout
from src.time_logs.infrastructure.models import TaskModel


class SQLLogRowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def list_rows(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        project_id: int | None = None,
    ) -> list[LogRow]:
        stmt = (
            select(
                TicketModel.code,
                TicketModel.description,
                TaskModel.work_date,
                TaskModel.hours,
                TaskModel.hourly_rate,
                TicketModel.project_id,
                ProjectModel.fixed_price,
            )
            .join(TicketModel, TicketModel.id == TaskModel.ticket_id)
            .join(ProjectModel, ProjectModel.id == TicketModel.project_id)
        )
        if date_from:
            stmt = stmt.where(TaskModel.work_date >= date_from)
        if date_to:
            stmt = stmt.where(TaskModel.work_date <= date_to)
        if project_id is not None:
            stmt = stmt.where(TicketModel.project_id == project_id)
        result = await self._s.execute(stmt)
        return [
            LogRow(
                ticket_code=code,
                ticket_description=description,
                work_date=work_date,
                hours=hours,
                payout=None if rate is None else compute_payout(hours, rate),
                project_id=pid,
                fixed_price=fixed_price,
            )
            for code, description, work_date, hours, rate, pid, fixed_price in result.all()
        ]
