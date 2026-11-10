from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    pass


# pool_pre_ping drops dead connections (e.g. after Postgres restarts) instead of erroring.
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    # No commit here: if a use case never commits, the session closes and everything rolls back.
    async with SessionFactory() as session:
        yield session


class SQLUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()


def get_uow(db: Annotated[AsyncSession, Depends(get_db)]) -> SQLUnitOfWork:
    return SQLUnitOfWork(db)
