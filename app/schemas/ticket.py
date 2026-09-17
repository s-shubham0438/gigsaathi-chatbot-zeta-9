from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

TicketStatus = Literal["open", "in_review", "resolved", "closed"]
TicketCategory = Literal["payment", "worker_conduct", "customer_conduct", "service_quality", "other"]


class CreateTicketRequest(BaseModel):
    category: TicketCategory
    description: str = Field(min_length=5, max_length=4000)
    booking_id: str | None = Field(
        default=None, description="Related booking id, if this dispute concerns one."
    )


class TicketResponse(BaseModel):
    id: str
    owner_id: str
    owner_role: str
    category: TicketCategory
    description: str
    booking_id: str | None
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
