from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from src.tickets.infrastructure.dependencies import get_ticket_use_cases
from src.tickets.infrastructure.schemas import (
    ImageOut,
    TicketCreate,
    TicketOut,
    TicketUpdate,
)
from src.tickets.use_cases.ticket_use_cases import TicketUseCases

router = APIRouter(prefix="/tickets", tags=["tickets"])
UseCases = Annotated[TicketUseCases, Depends(get_ticket_use_cases)]


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(body: TicketCreate, uc: UseCases):
    return TicketOut.from_entity(await uc.create(**body.model_dump()))


@router.get("", response_model=list[TicketOut])
async def list_tickets(uc: UseCases, project_id: int | None = None):
    return [TicketOut.from_entity(t) for t in await uc.list(project_id)]


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: int, uc: UseCases):
    return TicketOut.from_entity(await uc.get(ticket_id))


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(ticket_id: int, body: TicketUpdate, uc: UseCases):
    return TicketOut.from_entity(
        await uc.update(ticket_id, **body.model_dump(exclude_unset=True))
    )


@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(ticket_id: int, uc: UseCases):
    await uc.delete(ticket_id)


@router.post("/{ticket_id}/images", response_model=ImageOut, status_code=201)
async def upload_image(ticket_id: int, file: UploadFile, uc: UseCases):
    # The router only translates HTTP -> plain values; the use case owns the flow.
    image = await uc.add_image(
        ticket_id, file.filename or "image", file.content_type or "", await file.read()
    )
    return ImageOut.from_entity(image)


@router.delete("/{ticket_id}/images/{image_id}", status_code=204)
async def delete_image(ticket_id: int, image_id: int, uc: UseCases):
    await uc.remove_image(ticket_id, image_id)
