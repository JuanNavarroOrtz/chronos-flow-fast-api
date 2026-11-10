from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.audit import current_user_id
from src.core.config import settings
from src.core.database import SQLUnitOfWork, get_db, get_uow
from src.core.errors import UnauthorizedError
from src.users.domain.entities import UserEntity
from src.users.infrastructure.repositories import SQLUserRepository
from src.users.infrastructure.security import Argon2PasswordHasher, JwtTokenService
from src.users.use_cases.user_use_cases import UserUseCases

# Makes the "Authorize" button in /docs work (username field = email).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_use_cases(
    db: Annotated[AsyncSession, Depends(get_db)],
    uow: Annotated[SQLUnitOfWork, Depends(get_uow)],
) -> UserUseCases:
    return UserUseCases(
        SQLUserRepository(db),
        Argon2PasswordHasher(),
        JwtTokenService(
            settings.secret_key, settings.jwt_algorithm, settings.access_token_minutes
        ),
        uow,
        allow_registration=settings.allow_registration,
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    uc: Annotated[UserUseCases, Depends(get_user_use_cases)],
) -> AsyncIterator[UserEntity]:
    """Resolves the bearer token to a user, and tells the audit columns who is acting."""
    try:
        user = await uc.authenticate(token)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}
        ) from exc
    marker = current_user_id.set(user.id)
    try:
        yield user
    finally:
        current_user_id.reset(marker)
