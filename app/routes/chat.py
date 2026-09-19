from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.session import AuthenticatedUser, get_current_user
from app.clients.node_backend import NodeBackendClient
from app.clients.ollama_client import OllamaClient
from app.repositories.ticket_repository import TicketRepository
from app.routes.deps import get_node_client, get_ollama_client, get_ticket_repository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation import conversation_store
from app.services.orchestrator import Orchestrator

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    node_client: NodeBackendClient = Depends(get_node_client),
    ticket_repository: TicketRepository = Depends(get_ticket_repository),
    ollama_client: OllamaClient = Depends(get_ollama_client),
) -> ChatResponse:
    state = conversation_store.get_or_create(body.conversation_id, user_id=user.id)

    # If the previous turn left a pending confirmation and this message
    # reads like an affirmative, treat it as "confirmed" — a real yes/no
    # classifier would replace this in a later iteration; documented as a
    # known simplification, not hidden.
    if state.confirmation_state == "awaiting_confirmation" and _looks_like_confirmation(body.message):
        state.confirmation_state = "confirmed"

    orchestrator = Orchestrator(node_client=node_client, ticket_repository=ticket_repository, ollama_client = ollama_client)
    try:
        return await orchestrator.handle(
            message=body.message, state=state, user_id=user.id, user_role=user.role
        )
    finally:
        await ticket_repository.close()


def _looks_like_confirmation(message: str) -> bool:
    text = message.strip().lower()
    return text in {"yes", "yes please", "confirm", "haan", "ha", "yep", "sure", "ok", "okay"}
