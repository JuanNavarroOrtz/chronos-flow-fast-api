from pydantic import BaseModel

from src.users.domain.entities import UserEntity


class RegisterIn(BaseModel):
    email: str
    full_name: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool

    @classmethod
    def from_entity(cls, u: UserEntity) -> "UserOut":
        return cls(**{name: getattr(u, name) for name in cls.model_fields})


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
