from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.catalogs.domain.entities import CatalogItem
from src.tickets.domain.entities import TicketEntity, TicketImage
from src.tickets.infrastructure.models import TicketImageModel, TicketModel


def _image(m: TicketImageModel) -> TicketImage:
    return TicketImage(id=m.id, ticket_id=m.ticket_id, filename=m.filename, path=m.path)


def _ticket(m: TicketModel) -> TicketEntity:
    return TicketEntity(
        id=m.id,
        project_id=m.project_id,
        code=m.code,
        title=m.title,
        description=m.description,
        status=CatalogItem(m.status.id, m.status.code, m.status.name),
        images=[_image(i) for i in m.images],
        created_at=m.created_at,
        created_by=m.created_by,
        modified_at=m.modified_at,
        modified_by=m.modified_by,
    )


class SQLTicketRepository:
    """Stages changes with flush(); the Unit of Work commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _saved(self, model: TicketModel) -> TicketEntity:
        await self._s.flush()
        # Reload so the joined status and the audit columns are fresh.
        await self._s.refresh(model)
        return _ticket(model)

    async def add(self, ticket: TicketEntity) -> TicketEntity:
        model = TicketModel(
            project_id=ticket.project_id,
            code=ticket.code,
            title=ticket.title,
            description=ticket.description,
            status_id=ticket.status.id,
            images=[],
        )
        self._s.add(model)
        return await self._saved(model)

    async def get(self, ticket_id: int) -> TicketEntity | None:
        model = await self._s.get(TicketModel, ticket_id)
        return _ticket(model) if model else None

    async def get_by_code(self, code: str) -> TicketEntity | None:
        stmt = select(TicketModel).where(TicketModel.code == code)
        model = (await self._s.execute(stmt)).scalar_one_or_none()
        return _ticket(model) if model else None

    async def list(self, project_id: int | None = None) -> list[TicketEntity]:
        stmt = select(TicketModel).order_by(TicketModel.id)
        if project_id is not None:
            stmt = stmt.where(TicketModel.project_id == project_id)
        return [_ticket(m) for m in (await self._s.execute(stmt)).scalars().all()]

    async def update(self, ticket: TicketEntity) -> TicketEntity:
        model = await self._s.get(TicketModel, ticket.id)
        model.code = ticket.code
        model.title = ticket.title
        model.description = ticket.description
        model.status_id = ticket.status.id
        return await self._saved(model)

    async def delete(self, ticket_id: int) -> None:
        model = await self._s.get(TicketModel, ticket_id)
        if model:
            await self._s.delete(model)
            await self._s.flush()

    async def add_image(self, image: TicketImage) -> TicketImage:
        model = TicketImageModel(
            ticket_id=image.ticket_id, filename=image.filename, path=image.path
        )
        self._s.add(model)
        await self._s.flush()
        return _image(model)

    async def remove_image(self, ticket_id: int, image_id: int) -> TicketImage | None:
        model = await self._s.get(TicketImageModel, image_id)
        if model is None or model.ticket_id != ticket_id:
            return None
        image = _image(model)
        await self._s.delete(model)
        await self._s.flush()
        return image
