from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.infrastructure.dependencies import get_catalog_use_cases
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.config import settings
from src.core.database import SQLUnitOfWork, get_db, get_uow
from src.projects.infrastructure.repositories import SQLProjectRepository
from src.tickets.infrastructure.repositories import SQLTicketRepository
from src.tickets.infrastructure.storage import LocalImageStorage
from src.tickets.use_cases.ticket_use_cases import TicketUseCases


def get_ticket_use_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    uow: Annotated[SQLUnitOfWork, Depends(get_uow)],
    catalogs: Annotated[CatalogUseCases, Depends(get_catalog_use_cases)],
) -> TicketUseCases:
    return TicketUseCases(
        SQLTicketRepository(db),
        SQLProjectRepository(db),
        catalogs,
        uow,
        LocalImageStorage(),
        max_image_bytes=settings.max_upload_mb * 1024 * 1024,
    )
