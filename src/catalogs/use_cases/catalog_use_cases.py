from src.catalogs.domain.entities import CatalogEntity, CatalogItem
from src.catalogs.domain.repositories import CatalogRepository
from src.catalogs.domain.seed import SEED
from src.core.errors import DuplicateError, InvalidDataError, NotFoundError
from src.core.unit_of_work import UnitOfWork


class CatalogUseCases:
    def __init__(self, repo: CatalogRepository, uow: UnitOfWork) -> None:
        self._repo = repo
        self._uow = uow

    async def _catalog(self, catalog_code: str) -> CatalogEntity:
        catalog = await self._repo.get_by_code(catalog_code.strip().upper(), None)
        if catalog is None:
            raise NotFoundError(f"Catalog {catalog_code} not found")
        return catalog

    async def list_catalogs(self) -> list[CatalogEntity]:
        return await self._repo.list_roots()

    async def list_items(
        self, catalog_code: str, only_active: bool = True
    ) -> list[CatalogEntity]:
        catalog = await self._catalog(catalog_code)
        return await self._repo.list_children(catalog.id, only_active)

    async def require_item(self, item_id: int, catalog_code: str) -> CatalogItem:
        """Resolves an id sent by a client: it must be an active value of that catalog."""
        catalog = await self._catalog(catalog_code)
        item = await self._repo.get(item_id)
        if item is None or item.parent_id != catalog.id:
            raise InvalidDataError(f"{item_id} is not a valid {catalog.code} value")
        if not item.is_active:
            raise InvalidDataError(f"'{item.name}' is no longer active")
        return item.as_item()

    async def default_item(self, catalog_code: str, code: str) -> CatalogItem:
        catalog = await self._catalog(catalog_code)
        item = await self._repo.get_by_code(code, catalog.id)
        if item is None:
            raise NotFoundError(f"{catalog.code} has no value '{code}'")
        return item.as_item()

    async def create_item(
        self, catalog_code: str, code: str, name: str, sort_order: int = 0
    ) -> CatalogEntity:
        catalog = await self._catalog(catalog_code)
        entry = CatalogEntity(
            code=code, name=name, parent_id=catalog.id, sort_order=sort_order
        )
        if await self._repo.get_by_code(entry.code, catalog.id):
            raise DuplicateError(f"{catalog.code} already has a value {entry.code}")
        created = await self._repo.add(entry)
        await self._uow.commit()
        return created

    async def update_item(
        self,
        catalog_code: str,
        item_id: int,
        name: str | None = None,
        sort_order: int | None = None,
        is_active: bool | None = None,
    ) -> CatalogEntity:
        """The code is fixed (rules may depend on it); name, order and active flag can change."""
        catalog = await self._catalog(catalog_code)
        item = await self._repo.get(item_id)
        if item is None or item.parent_id != catalog.id:
            raise NotFoundError(f"{catalog.code} value {item_id} not found")
        if name is not None:
            item.name = name
        if sort_order is not None:
            item.sort_order = sort_order
        if is_active is not None:
            item.is_active = is_active
        item.validate()
        updated = await self._repo.update(item)
        await self._uow.commit()
        return updated

    async def seed_defaults(self) -> None:
        """Inserts the default catalogs and values that are missing; safe to run on every start."""
        for code, (name, values) in SEED.items():
            catalog = await self._repo.get_by_code(code, None)
            if catalog is None:
                catalog = await self._repo.add(CatalogEntity(code=code, name=name))
            for order, (value_code, value_name) in enumerate(values, start=1):
                if await self._repo.get_by_code(value_code, catalog.id) is None:
                    await self._repo.add(
                        CatalogEntity(
                            code=value_code,
                            name=value_name,
                            parent_id=catalog.id,
                            sort_order=order,
                        )
                    )
        await self._uow.commit()
