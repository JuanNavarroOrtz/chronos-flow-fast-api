from datetime import datetime

from pydantic import BaseModel

from src.catalogs.infrastructure.schemas import CatalogItemOut
from src.tickets.domain.entities import TicketEntity, TicketImage


class TicketCreate(BaseModel):
    project_id: int
    code: str  # project acronym + number, e.g. "IC-6"
    title: str
    description: str = ""
    status_id: int | None = None  # a TICKET_STATUS value; defaults to OPEN


class TicketUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    description: str | None = None
    status_id: int | None = None


class ImageOut(BaseModel):
    id: int
    filename: str
    url: str

    @classmethod
    def from_entity(cls, image: TicketImage) -> "ImageOut":
        return cls(id=image.id, filename=image.filename, url=f"/uploads/{image.path}")


class TicketOut(BaseModel):
    id: int
    project_id: int
    code: str
    title: str
    description: str
    status: CatalogItemOut
    created_at: datetime
    created_by: int | None
    modified_at: datetime
    modified_by: int | None
    images: list[ImageOut]

    @classmethod
    def from_entity(cls, t: TicketEntity) -> "TicketOut":
        data = {name: getattr(t, name) for name in cls.model_fields if name != "images"}
        return cls(**data, images=[ImageOut.from_entity(i) for i in t.images])
