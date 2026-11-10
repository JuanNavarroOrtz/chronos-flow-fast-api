import re
from dataclasses import dataclass

from src.core.errors import InvalidDataError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


@dataclass
class UserEntity:
    email: str
    full_name: str
    password_hash: str
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.email = self.email.strip().lower()
        self.full_name = self.full_name.strip()
        if not _EMAIL_RE.match(self.email):
            raise InvalidDataError("A valid email is required")
        if not self.full_name:
            raise InvalidDataError("Full name is required")


def check_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidDataError(
            f"Password must have at least {MIN_PASSWORD_LENGTH} characters"
        )
