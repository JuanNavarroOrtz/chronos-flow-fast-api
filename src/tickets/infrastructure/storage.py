from collections.abc import Iterable
from pathlib import Path
from uuid import uuid4

from src.core.config import settings


class LocalImageStorage:
    """Adapter for the ImageStorage port: files on local disk under UPLOAD_DIR."""

    async def save(self, ticket_id: int, extension: str, data: bytes) -> str:
        relative = f"{ticket_id}/{uuid4().hex}{extension}"
        destination = Path(settings.upload_dir) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return relative

    async def delete(self, paths: Iterable[str]) -> None:
        for relative in paths:
            (Path(settings.upload_dir) / relative).unlink(missing_ok=True)
