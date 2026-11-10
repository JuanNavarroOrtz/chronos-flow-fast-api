from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.domain.entities import UserEntity
from src.users.infrastructure.models import UserModel


def _user(m: UserModel) -> UserEntity:
    return UserEntity(
        id=m.id,
        email=m.email,
        full_name=m.full_name,
        password_hash=m.password_hash,
        is_active=m.is_active,
    )


class SQLUserRepository:
    """Stages changes with flush(); the Unit of Work commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, user: UserEntity) -> UserEntity:
        model = UserModel(
            email=user.email,
            full_name=user.full_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
        )
        self._s.add(model)
        await self._s.flush()
        return _user(model)

    async def get(self, user_id: int) -> UserEntity | None:
        model = await self._s.get(UserModel, user_id)
        return _user(model) if model else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        stmt = select(UserModel).where(UserModel.email == email)
        model = (await self._s.execute(stmt)).scalar_one_or_none()
        return _user(model) if model else None

    async def count(self) -> int:
        return (
            await self._s.execute(select(func.count()).select_from(UserModel))
        ).scalar_one()
