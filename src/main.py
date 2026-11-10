from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.analytics.infrastructure.router import router as analytics_router
from src.catalogs.infrastructure import models as _catalog_models  # noqa: F401  (register tables)
from src.catalogs.infrastructure.repositories import SQLCatalogRepository
from src.catalogs.infrastructure.router import router as catalogs_router
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.config import settings
from src.core.database import Base, SessionFactory, SQLUnitOfWork, engine
from src.core.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InvalidDataError,
    NotFoundError,
    UnauthorizedError,
)
from src.projects.infrastructure import models as _project_models  # noqa: F401  (register tables)
from src.projects.infrastructure.router import router as projects_router
from src.tickets.infrastructure import models as _ticket_models  # noqa: F401  (register tables)
from src.tickets.infrastructure.router import router as tickets_router
from src.time_logs.infrastructure import models as _task_models  # noqa: F401  (register tables)
from src.time_logs.infrastructure.router import router as tasks_router
from src.users.infrastructure import models as _user_models  # noqa: F401  (register tables)
from src.users.infrastructure.dependencies import get_current_user
from src.users.infrastructure.router import router as auth_router

_STATUS = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (InvalidDataError, 422),
    (UnauthorizedError, 401),
    (ForbiddenError, 403),
)


def _status_for(exc: DomainError) -> int:
    # isinstance, so subclasses of these errors map correctly too
    return next((code for cls, code in _STATUS if isinstance(exc, cls)), 400)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await CatalogUseCases(
            SQLCatalogRepository(session), SQLUnitOfWork(session)
        ).seed_defaults()
    yield


app = FastAPI(title="Chronos Flow", lifespan=lifespan)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Login/register are public; everything else needs a valid token.
app.include_router(auth_router)
_protected = [Depends(get_current_user)]
app.include_router(catalogs_router, dependencies=_protected)
app.include_router(projects_router, dependencies=_protected)
app.include_router(tickets_router, dependencies=_protected)
app.include_router(tasks_router, dependencies=_protected)
app.include_router(analytics_router, dependencies=_protected)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})
