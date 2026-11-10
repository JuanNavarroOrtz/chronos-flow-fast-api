from collections.abc import Iterable
from typing import Protocol

# Business rule: which image types a ticket accepts (content type -> file extension).
ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ImageStorage(Protocol):
    """Port for wherever image bytes live (local disk today, S3 tomorrow)."""

    async def save(self, ticket_id: int, extension: str, data: bytes) -> str:
        """Stores the bytes and returns an opaque relative path."""
        ...

    async def delete(self, paths: Iterable[str]) -> None: ...
