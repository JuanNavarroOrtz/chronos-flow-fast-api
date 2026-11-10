from src.catalogs.domain.entities import TICKET_STATUS
from src.catalogs.use_cases.catalog_use_cases import CatalogUseCases
from src.core.errors import DuplicateError, InvalidDataError, NotFoundError
from src.core.unit_of_work import UnitOfWork
from src.projects.domain.repositories import ProjectRepository
from src.tickets.domain.entities import TicketEntity, TicketImage
from src.tickets.domain.repositories import TicketRepository
from src.tickets.domain.storage import ALLOWED_IMAGE_TYPES, ImageStorage

_DEFAULT_STATUS = "OPEN"


class TicketUseCases:
    def __init__(
        self,
        repo: TicketRepository,
        projects: ProjectRepository,
        catalogs: CatalogUseCases,
        uow: UnitOfWork,
        storage: ImageStorage,
        max_image_bytes: int,
    ) -> None:
        self._repo = repo
        self._projects = projects
        self._catalogs = catalogs
        self._uow = uow
        self._storage = storage
        self._max_image_bytes = max_image_bytes

    async def _acronym_of(self, project_id: int) -> str:
        project = await self._projects.get(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project.acronym

    async def create(
        self,
        project_id: int,
        code: str,
        title: str,
        description: str = "",
        status_id: int | None = None,
    ) -> TicketEntity:
        if status_id is None:
            status = await self._catalogs.default_item(TICKET_STATUS, _DEFAULT_STATUS)
        else:
            status = await self._catalogs.require_item(status_id, TICKET_STATUS)
        ticket = TicketEntity(
            project_id=project_id,
            code=code,
            title=title,
            description=description,
            status=status,
        )
        ticket.check_prefix(await self._acronym_of(project_id))
        if await self._repo.get_by_code(ticket.code):
            raise DuplicateError(f"Ticket {ticket.code} already exists")
        created = await self._repo.add(ticket)
        await self._uow.commit()
        return created

    async def get(self, ticket_id: int) -> TicketEntity:
        ticket = await self._repo.get(ticket_id)
        if ticket is None:
            raise NotFoundError(f"Ticket {ticket_id} not found")
        return ticket

    async def list(self, project_id: int | None = None) -> list[TicketEntity]:
        return await self._repo.list(project_id)

    async def update(
        self,
        ticket_id: int,
        code: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status_id: int | None = None,
    ) -> TicketEntity:
        ticket = await self.get(ticket_id)
        if code is not None:
            ticket.code = code
        if title is not None:
            ticket.title = title
        if description is not None:
            ticket.description = description
        if status_id is not None:
            ticket.status = await self._catalogs.require_item(status_id, TICKET_STATUS)
        ticket.validate()
        ticket.check_prefix(await self._acronym_of(ticket.project_id))
        other = await self._repo.get_by_code(ticket.code)
        if other and other.id != ticket.id:
            raise DuplicateError(f"Ticket {ticket.code} already exists")
        updated = await self._repo.update(ticket)
        await self._uow.commit()
        return updated

    async def delete(self, ticket_id: int) -> None:
        """Deletes the ticket (tasks and image rows cascade), then its files."""
        ticket = await self.get(ticket_id)
        await self._repo.delete(ticket_id)
        await self._uow.commit()
        # Files go only after the DB commit succeeded, so a failed commit never loses images.
        await self._storage.delete([i.path for i in ticket.images])

    async def add_image(
        self, ticket_id: int, filename: str, content_type: str, data: bytes
    ) -> TicketImage:
        await self.get(ticket_id)
        extension = ALLOWED_IMAGE_TYPES.get(content_type)
        if extension is None:
            raise InvalidDataError("Only PNG, JPEG, WEBP or GIF images are allowed")
        if len(data) > self._max_image_bytes:
            raise InvalidDataError(
                f"Image exceeds {self._max_image_bytes // (1024 * 1024)} MB"
            )

        path = await self._storage.save(ticket_id, extension, data)
        try:
            image = await self._repo.add_image(
                TicketImage(ticket_id=ticket_id, filename=filename, path=path)
            )
            await self._uow.commit()
        except Exception:
            await self._storage.delete([path])  # don't leave an orphan file behind
            raise
        return image

    async def remove_image(self, ticket_id: int, image_id: int) -> None:
        image = await self._repo.remove_image(ticket_id, image_id)
        if image is None:
            raise NotFoundError(f"Image {image_id} not found on ticket {ticket_id}")
        await self._uow.commit()
        await self._storage.delete([image.path])
