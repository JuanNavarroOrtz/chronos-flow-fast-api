from typing import Annotated

from fastapi import APIRouter, Depends

from src.catalogs.infrastructure.dependencies import get_catalog_use_cases
from src.catalogs.infrastructure.schemas import (
    CatalogEntryOut,
    CatalogItemCreate,
    CatalogItemUpdate,
)
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases

router = APIRouter(prefix="/catalogs", tags=["catalogs"])
UseCases = Annotated[CatalogUseCases, Depends(get_catalog_use_cases)]


@router.get("", response_model=list[CatalogEntryOut])
async def list_catalogs(uc: UseCases):
    return [CatalogEntryOut.from_entity(c) for c in await uc.list_catalogs()]


@router.get("/{catalog_code}/items", response_model=list[CatalogEntryOut])
async def list_items(catalog_code: str, uc: UseCases, include_inactive: bool = False):
    items = await uc.list_items(catalog_code, only_active=not include_inactive)
    return [CatalogEntryOut.from_entity(i) for i in items]


@router.post("/{catalog_code}/items", response_model=CatalogEntryOut, status_code=201)
async def create_item(catalog_code: str, body: CatalogItemCreate, uc: UseCases):
    return CatalogEntryOut.from_entity(
        await uc.create_item(catalog_code, **body.model_dump())
    )


@router.patch("/{catalog_code}/items/{item_id}", response_model=CatalogEntryOut)
async def update_item(
    catalog_code: str, item_id: int, body: CatalogItemUpdate, uc: UseCases
):
    return CatalogEntryOut.from_entity(
        await uc.update_item(
            catalog_code, item_id, **body.model_dump(exclude_unset=True)
        )
    )
