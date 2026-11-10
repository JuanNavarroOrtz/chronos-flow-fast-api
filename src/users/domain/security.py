"""Ports for the two security tools the use cases need. Argon2 and JWT live in infrastructure."""

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def issue(self, user_id: int) -> str: ...

    def subject_of(self, token: str) -> int | None:
        """The user id inside a valid, unexpired token; None if the token is bad or expired."""
