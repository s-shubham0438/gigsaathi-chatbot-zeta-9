from __future__ import annotations

from fastapi import Request

from app.clients.node_backend import NodeBackendClient
from app.repositories.ticket_repository import TicketRepository


def get_node_client(request: Request) -> NodeBackendClient:
    cookie_header = request.headers.get("cookie")
    return NodeBackendClient(cookie_header=cookie_header)


def get_ticket_repository() -> TicketRepository:
    return TicketRepository()
