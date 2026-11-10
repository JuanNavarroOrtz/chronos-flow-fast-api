from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import SQLUnitOfWork, get_db, get_uow
from src.projects.infrastructure.repositories import SQLProjectRepository
from src.tickets.infrastructure.repositories import SQLTicketRepository
from src.time_logs.infrastructure.repositories import SQLTaskRepository
from src.time_logs.infrastructure.schemas import TaskCreate, TaskOut, TaskUpdate
from src.time_logs.use_cases.task_use_cases import TaskUseCases


def get_task_use_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    uow: Annotated[SQLUnitOfWork, Depends(get_uow)],
) -> TaskUseCases:
    return TaskUseCases(
        SQLTaskRepository(db), SQLTicketRepository(db), SQLProjectRepository(db), uow
    )


router = APIRouter(tags=["tasks"])
UseCases = Annotated[TaskUseCases, Depends(get_task_use_cases)]


@router.post("/tickets/{ticket_id}/tasks", response_model=TaskOut, status_code=201)
async def log_task(ticket_id: int, body: TaskCreate, uc: UseCases):
    return TaskOut.from_entity(await uc.log(ticket_id, **body.model_dump()))


@router.get("/tickets/{ticket_id}/tasks", response_model=list[TaskOut])
async def list_tasks(ticket_id: int, uc: UseCases):
    return [TaskOut.from_entity(t) for t in await uc.list_for_ticket(ticket_id)]


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, body: TaskUpdate, uc: UseCases):
    return TaskOut.from_entity(
        await uc.update(task_id, **body.model_dump(exclude_unset=True))
    )


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, uc: UseCases):
    await uc.delete(task_id)
