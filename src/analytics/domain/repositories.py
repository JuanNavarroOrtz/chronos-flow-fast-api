from datetime import date
from typing import Protocol

from src.analytics.domain.entities import LogRow


class LogRowRepository(Protocol):
    async def list_rows(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        project_id: int | None = None,
    ) -> list[LogRow]: ...
