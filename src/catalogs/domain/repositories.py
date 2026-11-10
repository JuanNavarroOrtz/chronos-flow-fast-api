from typing import Protocol

from src.catalogs.domain.entities import CatalogEntity


class CatalogRepository(Protocol):
    async def get(self, catalog_id: int) -> CatalogEntity | None: ...

    async def get_by_code(
        self, code: str, parent_id: int | None
    ) -> CatalogEntity | None:
        """parent_id=None looks among the catalogs themselves; otherwise among that catalog's values."""

    async def list_roots(self) -> list[CatalogEntity]: ...

    async def list_children(
        self, parent_id: int, only_active: bool = True
    ) -> list[CatalogEntity]: ...

    async def add(self, entry: CatalogEntity) -> CatalogEntity: ...

    async def update(self, entry: CatalogEntity) -> CatalogEntity: ...
