from __future__ import annotations
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Intent(StrEnum):
    GREETING = "GREETING"
    GENERAL_HELP = "GENERAL_HELP"
    SERVICE_DISCOVERY = "SERVICE_DISCOVERY"
    SERVICE_PROBLEM = "SERVICE_PROBLEM"
    CATEGORY_IDENTIFICATION = "CATEGORY_IDENTIFICATION"
    WORKER_RECOMMENDATION = "WORKER_RECOMMENDATION"
    WORKER_COMPARISON = "WORKER_COMPARISON"
    PRICE_ESTIMATION = "PRICE_ESTIMATION"
    BOOK_SERVICE = "BOOK_SERVICE"
    CANCEL_SERVICE = "CANCEL_SERVICE"
    BOOKING_STATUS = "BOOKING_STATUS"
    WORKER_ACCEPT_REQUEST = "WORKER_ACCEPT_REQUEST"
    WORKER_CANCEL_REQUEST = "WORKER_CANCEL_REQUEST"
    DISPUTE_REPORT = "DISPUTE_REPORT"
    DISPUTE_STATUS = "DISPUTE_STATUS"
    SUPPORT_CONTACT = "SUPPORT_CONTACT"
    EMERGENCY_SERVICE = "EMERGENCY_SERVICE"
    ACCOUNT_RELATED = "ACCOUNT_RELATED"
    UNKNOWN = "UNKNOWN"


Priority = Literal["normal", "urgent", "emergency"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(
        default=None,
        description="Omit to start a new conversation; the response returns the id to reuse.",
    )


class ChatAction(BaseModel):
    """A frontend-actionable suggestion — never a claim that a mutation already happened."""

    type: str  # e.g. "navigate", "confirm_booking", "confirm_cancel"
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    language: str
    intent: Intent
    category: str | None = None
    problem: str | None = None
    priority: Priority | None = None
    actions: list[ChatAction] = Field(default_factory=list)
    redirect: str | None = None
