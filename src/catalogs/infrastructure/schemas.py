from pydantic import BaseModel, ConfigDict

from src.catalogs.domain.entities import CatalogEntity


class CatalogItemOut(BaseModel):
    """The small shape other resources embed (a project's status, a ticket's status...)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class CatalogEntryOut(BaseModel):
    id: int
    code: str
    name: str
    sort_order: int
    is_active: bool

    @classmethod
    def from_entity(cls, e: CatalogEntity) -> "CatalogEntryOut":
        return cls(**{name: getattr(e, name) for name in cls.model_fields})


class CatalogItemCreate(BaseModel):
    code: str
    name: str
    sort_order: int = 0


class CatalogItemUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
