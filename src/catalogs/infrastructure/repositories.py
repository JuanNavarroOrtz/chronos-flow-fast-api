from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.domain.entities import CatalogEntity
from src.catalogs.infrastructure.models import CatalogModel


def _entity(m: CatalogModel) -> CatalogEntity:
    return CatalogEntity(
        id=m.id,
        parent_id=m.parent_id,
        code=m.code,
        name=m.name,
        sort_order=m.sort_order,
        is_active=m.is_active,
    )


class SQLCatalogRepository:
    """Stages changes with flush(); the Unit of Work commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, catalog_id: int) -> CatalogEntity | None:
        model = await self._s.get(CatalogModel, catalog_id)
        return _entity(model) if model else None

    async def get_by_code(
        self, code: str, parent_id: int | None
    ) -> CatalogEntity | None:
        parent = (
            CatalogModel.parent_id.is_(None)
            if parent_id is None
            else CatalogModel.parent_id == parent_id
        )
        stmt = select(CatalogModel).where(CatalogModel.code == code, parent)
        model = (await self._s.execute(stmt)).scalar_one_or_none()
        return _entity(model) if model else None

    async def list_roots(self) -> list[CatalogEntity]:
        stmt = (
            select(CatalogModel)
            .where(CatalogModel.parent_id.is_(None))
            .order_by(CatalogModel.id)
        )
        return [_entity(m) for m in (await self._s.execute(stmt)).scalars().all()]

    async def list_children(
        self, parent_id: int, only_active: bool = True
    ) -> list[CatalogEntity]:
        stmt = select(CatalogModel).where(CatalogModel.parent_id == parent_id)
        if only_active:
            stmt = stmt.where(CatalogModel.is_active.is_(True))
        stmt = stmt.order_by(CatalogModel.sort_order, CatalogModel.id)
        return [_entity(m) for m in (await self._s.execute(stmt)).scalars().all()]

    async def add(self, entry: CatalogEntity) -> CatalogEntity:
        model = CatalogModel(
            parent_id=entry.parent_id,
            code=entry.code,
            name=entry.name,
            sort_order=entry.sort_order,
            is_active=entry.is_active,
        )
        self._s.add(model)
        await self._s.flush()
        return _entity(model)

    async def update(self, entry: CatalogEntity) -> CatalogEntity:
        model = await self._s.get(CatalogModel, entry.id)
        model.name = entry.name
        model.sort_order = entry.sort_order
        model.is_active = entry.is_active
        await self._s.flush()
        return _entity(model)
