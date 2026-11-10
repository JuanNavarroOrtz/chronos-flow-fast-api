import re
from dataclasses import dataclass, field
from datetime import datetime

from src.catalogs.domain.entities import CatalogItem
from src.core.errors import InvalidDataError

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


@dataclass
class TicketImage:
    ticket_id: int
    filename: str
    path: str
    id: int | None = None


@dataclass
class TicketEntity:
    project_id: int
    code: str
    title: str
    status: CatalogItem  # a TICKET_STATUS catalog value
    description: str = ""
    id: int | None = None
    images: list[TicketImage] = field(default_factory=list)
    # Audit data is filled by the database layer (see core/audit.py); read-only here.
    created_at: datetime | None = None
    created_by: int | None = None
    modified_at: datetime | None = None
    modified_by: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.code = self.code.strip().upper()
        self.title = self.title.strip()
        if not _CODE_RE.match(self.code):
            raise InvalidDataError("Ticket code must look like 'IC-6'")
        if not self.title:
            raise InvalidDataError("Ticket title is required")

    def check_prefix(self, acronym: str) -> None:
        """A ticket code is the project acronym plus a number: project IC -> IC-6."""
        if not self.code.startswith(f"{acronym}-"):
            raise InvalidDataError(
                f"Ticket code must start with '{acronym}-' (the project acronym)"
            )
