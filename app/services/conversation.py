from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.config import settings


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    text: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationState:
    conversation_id: str
    user_id: str
    language: str | None = None
    role: str | None = None
    intent: str | None = None
    category: str | None = None
    problem: str | None = None
    requirement: str | None = None
    priority: str | None = None
    location: str | None = None
    selected_worker_id: str | None = None
    selected_booking_id: str | None = None
    pending_action: dict[str, Any] | None = None
    confirmation_state: str | None = None  # None | "awaiting_confirmation" | "confirmed"
    turns: list[Turn] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)

    def add_turn(self, role: str, text: str) -> None:
        self.turns.append(Turn(role=role, text=text))
        # Hard cap — oldest turns drop off. Structured fields above (not
        # raw history) are what carry meaning forward across turns.
        max_turns = settings.conversation_max_turns
        if len(self.turns) > max_turns:
            self.turns = self.turns[-max_turns:]
        self.last_active = time.time()

    def recent_history(self) -> list[Turn]:
        return list(self.turns)


class ConversationStore:
    def __init__(self) -> None:
        self._conversations: dict[str, ConversationState] = {}

    def _purge_expired(self) -> None:
        ttl_seconds = settings.conversation_ttl_minutes * 60
        now = time.time()
        expired = [cid for cid, state in self._conversations.items() if now - state.last_active > ttl_seconds]
        for cid in expired:
            del self._conversations[cid]

    def get_or_create(self, conversation_id: str | None, user_id: str) -> ConversationState:
        self._purge_expired()
        if conversation_id and conversation_id in self._conversations:
            state = self._conversations[conversation_id]
            if state.user_id != user_id:
                # Never hand one user's conversation state to another —
                # start a fresh one instead of leaking cross-user context.
                conversation_id = None
            else:
                return state

        new_id = conversation_id or str(uuid4())
        state = ConversationState(conversation_id=new_id, user_id=user_id)
        self._conversations[new_id] = state
        return state


# Process-wide singleton — see class docstring for the documented scope
# limitation.
conversation_store = ConversationStore()
