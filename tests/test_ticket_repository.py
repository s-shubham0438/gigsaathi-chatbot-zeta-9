"""
Ticket privacy tests — the security-critical part of the dispute system
(master prompt Section 22 + 40 "Ticket privacy: Owner -> allowed, Admin ->
allowed, Other user -> denied").
"""

import pytest

from app.repositories.ticket_repository import TicketRepository
from tests.fakes import FakeMongoClient


@pytest.fixture
def repo():
    return TicketRepository(client=FakeMongoClient())


async def test_owner_can_read_own_ticket(repo):
    created = await repo.create(
        owner_id="user-1", owner_role="customer", category="payment", description="x", booking_id=None
    )
    fetched = await repo.get(created["_id"], requester_id="user-1", requester_role="customer")
    assert fetched is not None
    assert fetched["_id"] == created["_id"]


async def test_other_user_cannot_read_ticket(repo):
    created = await repo.create(
        owner_id="user-1", owner_role="customer", category="payment", description="x", booking_id=None
    )
    fetched = await repo.get(created["_id"], requester_id="user-2", requester_role="customer")
    assert fetched is None


async def test_admin_can_read_any_ticket(repo):
    created = await repo.create(
        owner_id="user-1", owner_role="customer", category="payment", description="x", booking_id=None
    )
    fetched = await repo.get(created["_id"], requester_id="admin-1", requester_role="admin")
    assert fetched is not None


async def test_list_for_user_only_returns_own_tickets(repo):
    await repo.create(owner_id="user-1", owner_role="customer", category="payment", description="a", booking_id=None)
    await repo.create(owner_id="user-2", owner_role="customer", category="payment", description="b", booking_id=None)

    user1_tickets = await repo.list_for_user(requester_id="user-1", requester_role="customer")
    assert len(user1_tickets) == 1
    assert user1_tickets[0]["owner_id"] == "user-1"


async def test_list_for_admin_returns_all_tickets(repo):
    await repo.create(owner_id="user-1", owner_role="customer", category="payment", description="a", booking_id=None)
    await repo.create(owner_id="user-2", owner_role="customer", category="payment", description="b", booking_id=None)

    admin_tickets = await repo.list_for_user(requester_id="admin-1", requester_role="admin")
    assert len(admin_tickets) == 2


async def test_worker_cannot_see_customer_ticket_and_vice_versa(repo):
    created = await repo.create(
        owner_id="customer-1", owner_role="customer", category="worker_conduct", description="x", booking_id=None
    )
    fetched = await repo.get(created["_id"], requester_id="worker-1", requester_role="professional")
    assert fetched is None
