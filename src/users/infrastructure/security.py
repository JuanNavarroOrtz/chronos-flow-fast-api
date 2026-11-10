from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hash = PasswordHash.recommended()  # Argon2id

    def hash(self, password: str) -> str:
        return self._hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._hash.verify(password, password_hash)


class JwtTokenService:
    def __init__(self, secret_key: str, algorithm: str, expires_minutes: int) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._expires = timedelta(minutes=expires_minutes)

    def issue(self, user_id: int) -> str:
        payload = {"sub": str(user_id), "exp": datetime.now(UTC) + self._expires}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def subject_of(self, token: str) -> int | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return int(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            return None
