from datetime import date
from decimal import Decimal

from src.core.errors import NotFoundError
from src.core.unit_of_work import UnitOfWork
from src.projects.domain.repositories import ProjectRepository
from src.tickets.domain.repositories import TicketRepository
from src.time_logs.domain.entities import TaskEntity, resolve_hours
from src.time_logs.domain.repositories import TaskRepository


class TaskUseCases:
    def __init__(
        self,
        repo: TaskRepository,
        tickets: TicketRepository,
        projects: ProjectRepository,
        uow: UnitOfWork,
    ) -> None:
        self._repo = repo
        self._tickets = tickets
        self._projects = projects
        self._uow = uow

    async def _require_ticket(self, ticket_id: int):
        ticket = await self._tickets.get(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        return ticket

    async def log(
        self,
        ticket_id: int,
        work_date: date,
        description: str = "",
        time_text: str | None = None,
        hours: Decimal | None = None,
    ) -> TaskEntity:
        ticket = await self._require_ticket(ticket_id)
        project = await self._projects.get(ticket.project_id)
        time_text, hours = resolve_hours(time_text, hours)
        task = TaskEntity(
            ticket_id=ticket_id,
            work_date=work_date,
            hours=hours,
            # Snapshot: later rate changes on the project don't rewrite history.
            hourly_rate=project.task_hourly_rate,
            description=description,
            time_text=time_text,
        )
        created = await self._repo.add(task)
        await self._uow.commit()
        return created

    async def get(self, task_id: int) -> TaskEntity:
        task = await self._repo.get(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def list_for_ticket(self, ticket_id: int) -> list[TaskEntity]:
        await self._require_ticket(ticket_id)
        return await self._repo.list_by_ticket(ticket_id)

    async def update(
        self,
        task_id: int,
        work_date: date | None = None,
        description: str | None = None,
        time_text: str | None = None,
        hours: Decimal | None = None,
    ) -> TaskEntity:
        task = await self.get(task_id)
        if work_date is not None:
            task.work_date = work_date
        if description is not None:
            task.description = description
        if time_text is not None or hours is not None:
            task.time_text, task.hours = resolve_hours(
                time_text if time_text is not None else task.time_text, hours
            )
        updated = await self._repo.update(task)
        await self._uow.commit()
        return updated

    async def delete(self, task_id: int) -> None:
        await self.get(task_id)
        await self._repo.delete(task_id)
        await self._uow.commit()
