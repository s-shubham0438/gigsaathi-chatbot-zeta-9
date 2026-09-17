from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.session import AuthenticatedUser, get_current_user
from app.repositories.ticket_repository import TicketRepository
from app.routes.deps import get_ticket_repository
from app.schemas.ticket import CreateTicketRequest, TicketResponse

router = APIRouter(prefix="/support")


def _to_response(doc: dict) -> TicketResponse:
    return TicketResponse(
        id=doc["_id"],
        owner_id=doc["owner_id"],
        owner_role=doc["owner_role"],
        category=doc["category"],
        description=doc["description"],
        booking_id=doc.get("booking_id"),
        status=doc["status"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.post("/tickets", response_model=TicketResponse)
async def create_ticket(
    body: CreateTicketRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    repo: TicketRepository = Depends(get_ticket_repository),
) -> TicketResponse:
    try:
        doc = await repo.create(
            owner_id=user.id,
            owner_role=user.role,
            category=body.category,
            description=body.description,
            booking_id=body.booking_id,
        )
        return _to_response(doc)
    finally:
        await repo.close()


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    user: AuthenticatedUser = Depends(get_current_user),
    repo: TicketRepository = Depends(get_ticket_repository),
) -> list[TicketResponse]:
    try:
        docs = await repo.list_for_user(requester_id=user.id, requester_role=user.role)
        return [_to_response(d) for d in docs]
    finally:
        await repo.close()


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    repo: TicketRepository = Depends(get_ticket_repository),
) -> TicketResponse:
    try:
        doc = await repo.get(ticket_id, requester_id=user.id, requester_role=user.role)
        if doc is None:
            # Same response whether the ticket doesn't exist or belongs to
            # someone else — never confirm existence to a non-owner.
            raise HTTPException(status_code=404, detail="Ticket not found")
        return _to_response(doc)
    finally:
        await repo.close()
