from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from app.config import settings

_ADMIN_ROLE = "admin"


class TicketRepository:
    def __init__(self, client: AsyncMongoClient | None = None):
        self._client = client or AsyncMongoClient(settings.mongo_db_uri)
        self._collection: AsyncCollection = self._client[settings.mongo_db_name]["disputes"]

    async def create(
        self,
        *,
        owner_id: str,
        owner_role: str,
        category: str,
        description: str,
        booking_id: str | None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        doc = {
            "_id": str(uuid4()),
            "owner_id": owner_id,
            "owner_role": owner_role,
            "category": category,
            "description": description,
            "booking_id": booking_id,
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        return doc

    async def get(self, ticket_id: str, *, requester_id: str, requester_role: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one({"_id": ticket_id})
        if doc is None:
            return None
        if not self._authorized(doc, requester_id, requester_role):
            # Return None rather than 403 with details — do not reveal
            # that a ticket with this id exists to a non-owner.
            return None
        return doc

    async def list_for_user(self, *, requester_id: str, requester_role: str) -> list[dict[str, Any]]:
        if requester_role == _ADMIN_ROLE:
            cursor = self._collection.find({}).sort("created_at", -1)
        else:
            cursor = self._collection.find({"owner_id": requester_id}).sort("created_at", -1)
        return [doc async for doc in cursor]

    @staticmethod
    def _authorized(doc: dict[str, Any], requester_id: str, requester_role: str) -> bool:
        if requester_role == _ADMIN_ROLE:
            return True
        return doc.get("owner_id") == requester_id

    async def close(self) -> None:
        await self._client.close()
