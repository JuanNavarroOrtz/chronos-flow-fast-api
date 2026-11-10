from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.infrastructure.repositories import SQLCatalogRepository
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.database import SQLUnitOfWork, get_db, get_uow


def get_catalog_use_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    uow: Annotated[SQLUnitOfWork, Depends(get_uow)],
) -> CatalogUseCases:
    return CatalogUseCases(SQLCatalogRepository(db), uow)
