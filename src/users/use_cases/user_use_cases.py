from src.core.errors import (
    DuplicateError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from src.core.unit_of_work import UnitOfWork
from src.users.domain.entities import UserEntity, check_password_strength
from src.users.domain.repositories import UserRepository
from src.users.domain.security import PasswordHasher, TokenService

_BAD_LOGIN = "Invalid email or password"


class UserUseCases:
    def __init__(
        self,
        repo: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        uow: UnitOfWork,
        allow_registration: bool,
    ) -> None:
        self._repo = repo
        self._hasher = hasher
        self._tokens = tokens
        self._uow = uow
        self._allow_registration = allow_registration

    async def register(self, email: str, full_name: str, password: str) -> UserEntity:
        # The first account is always allowed (that's you); later ones only if enabled in settings.
        if await self._repo.count() > 0 and not self._allow_registration:
            raise ForbiddenError("Registration is closed")
        check_password_strength(password)
        user = UserEntity(
            email=email, full_name=full_name, password_hash=self._hasher.hash(password)
        )
        if await self._repo.get_by_email(user.email):
            raise DuplicateError(f"{user.email} is already registered")
        created = await self._repo.add(user)
        await self._uow.commit()
        return created

    async def login(self, email: str, password: str) -> str:
        user = await self._repo.get_by_email(email.strip().lower())
        # Same message for "no such user" and "wrong password": don't reveal which emails exist.
        if (
            user is None
            or not user.is_active
            or not self._hasher.verify(password, user.password_hash)
        ):
            raise UnauthorizedError(_BAD_LOGIN)
        return self._tokens.issue(user.id)

    async def authenticate(self, token: str) -> UserEntity:
        user_id = self._tokens.subject_of(token)
        user = await self._repo.get(user_id) if user_id is not None else None
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid or expired token")
        return user

    async def get(self, user_id: int) -> UserEntity:
        user = await self._repo.get(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user
