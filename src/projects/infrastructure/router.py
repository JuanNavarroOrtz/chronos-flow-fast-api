from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.infrastructure.dependencies import get_catalog_use_cases
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.database import SQLUnitOfWork, get_db, get_uow
from src.projects.infrastructure.repositories import SQLProjectRepository
from src.projects.infrastructure.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from src.projects.use_cases.project_use_cases import ProjectUseCases


def get_project_use_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    uow: Annotated[SQLUnitOfWork, Depends(get_uow)],
    catalogs: Annotated[CatalogUseCases, Depends(get_catalog_use_cases)],
) -> ProjectUseCases:
    return ProjectUseCases(SQLProjectRepository(db), uow, catalogs)


router = APIRouter(prefix="/projects", tags=["projects"])
UseCases = Annotated[ProjectUseCases, Depends(get_project_use_cases)]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, uc: UseCases):
    return ProjectOut.from_entity(await uc.create(**body.model_dump()))


@router.get("", response_model=list[ProjectOut])
async def list_projects(uc: UseCases):
    return [ProjectOut.from_entity(p) for p in await uc.list()]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, uc: UseCases):
    return ProjectOut.from_entity(await uc.get(project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: int, body: ProjectUpdate, uc: UseCases):
    changes = body.model_dump(exclude_unset=True)
    return ProjectOut.from_entity(await uc.update(project_id, changes))


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, uc: UseCases):
    await uc.delete(project_id)
