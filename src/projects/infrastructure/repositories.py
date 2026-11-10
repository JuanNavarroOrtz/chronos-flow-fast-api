from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.domain.entities import CatalogItem
from src.projects.domain.entities import ProjectEntity
from src.projects.infrastructure.models import ProjectModel
from src.tickets.infrastructure.models import TicketModel


def _project(m: ProjectModel) -> ProjectEntity:
    return ProjectEntity(
        id=m.id,
        name=m.name,
        acronym=m.acronym,
        billing_type=CatalogItem(
            m.billing_type.id, m.billing_type.code, m.billing_type.name
        ),
        hourly_rate=m.hourly_rate,
        fixed_price=m.fixed_price,
        start_date=m.start_date,
        end_date=m.end_date,
        status=CatalogItem(m.status.id, m.status.code, m.status.name),
        created_at=m.created_at,
        created_by=m.created_by,
        modified_at=m.modified_at,
        modified_by=m.modified_by,
    )


def _copy_to(m: ProjectModel, p: ProjectEntity) -> None:
    m.name = p.name
    m.acronym = p.acronym
    m.billing_type_id = p.billing_type.id
    m.hourly_rate = p.hourly_rate
    m.fixed_price = p.fixed_price
    m.start_date = p.start_date
    m.end_date = p.end_date
    m.status_id = p.status.id


class SQLProjectRepository:
    """Stages changes with flush(); the Unit of Work commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _saved(self, model: ProjectModel) -> ProjectEntity:
        await self._s.flush()
        # Reload so the joined catalog values and the audit columns are fresh.
        await self._s.refresh(model)
        return _project(model)

    async def add(self, project: ProjectEntity) -> ProjectEntity:
        model = ProjectModel()
        _copy_to(model, project)
        self._s.add(model)
        return await self._saved(model)

    async def get(self, project_id: int) -> ProjectEntity | None:
        model = await self._s.get(ProjectModel, project_id)
        return _project(model) if model else None

    async def get_by_acronym(self, acronym: str) -> ProjectEntity | None:
        stmt = select(ProjectModel).where(ProjectModel.acronym == acronym)
        model = (await self._s.execute(stmt)).scalar_one_or_none()
        return _project(model) if model else None

    async def list(self) -> list[ProjectEntity]:
        rows = (
            await self._s.execute(select(ProjectModel).order_by(ProjectModel.id))
        ).scalars()
        return [_project(m) for m in rows.all()]

    async def update(self, project: ProjectEntity) -> ProjectEntity:
        model = await self._s.get(ProjectModel, project.id)
        _copy_to(model, project)
        return await self._saved(model)

    async def delete(self, project_id: int) -> None:
        model = await self._s.get(ProjectModel, project_id)
        if model:
            await self._s.delete(model)
            await self._s.flush()

    async def ticket_count(self, project_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(TicketModel)
            .where(TicketModel.project_id == project_id)
        )
        return (await self._s.execute(stmt)).scalar_one()
