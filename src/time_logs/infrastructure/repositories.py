from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.time_logs.domain.entities import TaskEntity
from src.time_logs.infrastructure.models import TaskModel


def _task(m: TaskModel) -> TaskEntity:
    return TaskEntity(
        id=m.id,
        ticket_id=m.ticket_id,
        work_date=m.work_date,
        time_text=m.time_text,
        hours=m.hours,
        hourly_rate=m.hourly_rate,
        description=m.description,
    )


class SQLTaskRepository:
    """Stages changes with flush(); the Unit of Work commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, task: TaskEntity) -> TaskEntity:
        model = TaskModel(
            ticket_id=task.ticket_id,
            work_date=task.work_date,
            time_text=task.time_text,
            hours=task.hours,
            hourly_rate=task.hourly_rate,
            description=task.description,
        )
        self._s.add(model)
        await self._s.flush()
        return _task(model)

    async def get(self, task_id: int) -> TaskEntity | None:
        model = await self._s.get(TaskModel, task_id)
        return _task(model) if model else None

    async def list_by_ticket(self, ticket_id: int) -> list[TaskEntity]:
        stmt = (
            select(TaskModel)
            .where(TaskModel.ticket_id == ticket_id)
            .order_by(TaskModel.work_date, TaskModel.id)
        )
        return [_task(m) for m in (await self._s.execute(stmt)).scalars().all()]

    async def update(self, task: TaskEntity) -> TaskEntity:
        model = await self._s.get(TaskModel, task.id)
        model.work_date = task.work_date
        model.time_text = task.time_text
        model.hours = task.hours
        model.description = task.description
        await self._s.flush()
        return _task(model)

    async def delete(self, task_id: int) -> None:
        model = await self._s.get(TaskModel, task_id)
        if model:
            await self._s.delete(model)
            await self._s.flush()
