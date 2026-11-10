import re
from dataclasses import dataclass

from src.core.errors import InvalidDataError

# Catalog (root) codes. A root row has parent_id = NULL; its values are the rows pointing at it.
BILLING_TYPE = "BILLING_TYPE"
PROJECT_STATUS = "PROJECT_STATUS"
TICKET_STATUS = "TICKET_STATUS"

# Value codes the business rules depend on. Names, order and active flag are data; these codes are not.
HOURLY = "HOURLY"
FIXED = "FIXED"

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


@dataclass(frozen=True)
class CatalogItem:
    """What other features hold when they reference a catalog value (e.g. a project's status)."""

    id: int
    code: str
    name: str


@dataclass
class CatalogEntity:
    code: str
    name: str
    parent_id: int | None = (
        None  # None = this row is a catalog; otherwise it is one of its values
    )
    sort_order: int = 0
    is_active: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        self.code = self.code.strip().upper()
        self.name = self.name.strip()
        if not _CODE_RE.match(self.code):
            raise InvalidDataError(
                "Catalog code must be letters, digits or '_' and start with a letter"
            )
        if not self.name:
            raise InvalidDataError("Catalog name is required")

    def as_item(self) -> CatalogItem:
        return CatalogItem(id=self.id, code=self.code, name=self.name)
