from datetime import date
from decimal import Decimal

from src.catalogs.domain.entities import BILLING_TYPE, HOURLY, PROJECT_STATUS
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.errors import (
    ConflictError,
    DuplicateError,
    InvalidDataError,
    NotFoundError,
)
from src.core.unit_of_work import UnitOfWork
from src.projects.domain.entities import ProjectEntity
from src.projects.domain.repositories import ProjectRepository

_REQUIRED = {"name", "acronym", "billing_type_id", "start_date", "status_id"}
_DEFAULT_STATUS = "ACTIVE"


class ProjectUseCases:
    def __init__(
        self, repo: ProjectRepository, uow: UnitOfWork, catalogs: CatalogUseCases
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._catalogs = catalogs

    async def create(
        self,
        name: str,
        acronym: str,
        billing_type_id: int,
        start_date: date,
        hourly_rate: Decimal | None = None,
        fixed_price: Decimal | None = None,
        end_date: date | None = None,
        status_id: int | None = None,
    ) -> ProjectEntity:
        billing_type = await self._catalogs.require_item(billing_type_id, BILLING_TYPE)
        if status_id is None:
            status = await self._catalogs.default_item(PROJECT_STATUS, _DEFAULT_STATUS)
        else:
            status = await self._catalogs.require_item(status_id, PROJECT_STATUS)
        project = ProjectEntity(
            name=name,
            acronym=acronym,
            billing_type=billing_type,
            status=status,
            start_date=start_date,
            hourly_rate=hourly_rate,
            fixed_price=fixed_price,
            end_date=end_date,
        )
        if await self._repo.get_by_acronym(project.acronym):
            raise DuplicateError(
                f"A project with acronym {project.acronym} already exists"
            )
        created = await self._repo.add(project)
        await self._uow.commit()
        return created

    async def get(self, project_id: int) -> ProjectEntity:
        project = await self._repo.get(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def list(self) -> list[ProjectEntity]:
        return await self._repo.list()

    async def update(self, project_id: int, changes: dict) -> ProjectEntity:
        """`changes` holds only the fields the caller sent (an explicit None clears optional ones)."""
        changes = dict(changes)
        for key, value in changes.items():
            if value is None and key in _REQUIRED:
                raise InvalidDataError(f"{key} cannot be empty")

        project = await self.get(project_id)

        # Catalog ids sent by the client become catalog values on the entity.
        if "billing_type_id" in changes:
            new_billing = await self._catalogs.require_item(
                changes.pop("billing_type_id"), BILLING_TYPE
            )
            if new_billing.id != project.billing_type.id:
                # Switching billing mode drops the old mode's price unless the caller sets it.
                stale = "fixed_price" if new_billing.code == HOURLY else "hourly_rate"
                changes.setdefault(stale, None)
            changes["billing_type"] = new_billing
        if "status_id" in changes:
            changes["status"] = await self._catalogs.require_item(
                changes.pop("status_id"), PROJECT_STATUS
            )

        old_acronym = project.acronym
        for key, value in changes.items():
            setattr(project, key, value)
        project.validate()

        if project.acronym != old_acronym:
            if await self._repo.get_by_acronym(project.acronym):
                raise DuplicateError(
                    f"A project with acronym {project.acronym} already exists"
                )
            if await self._repo.ticket_count(project_id):
                raise ConflictError(
                    "Acronym can't change: tickets already use it as their prefix"
                )

        updated = await self._repo.update(project)
        await self._uow.commit()
        return updated

    async def delete(self, project_id: int) -> None:
        await self.get(project_id)
        count = await self._repo.ticket_count(project_id)
        if count:
            raise ConflictError(
                f"Project still has {count} ticket(s); delete them first"
            )
        await self._repo.delete(project_id)
        await self._uow.commit()
