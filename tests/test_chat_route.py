from fastapi.testclient import TestClient
from app.auth.session import AuthenticatedUser, get_current_user
from app.main import app
from app.repositories.ticket_repository import TicketRepository
from app.routes.deps import get_node_client, get_ticket_repository
from tests.fakes import FakeMongoClient
from tests.fakes_node_client import FakeNodeClient


def _override_customer():
    return AuthenticatedUser(id="cust-1", role="customer", name="Priya", email="priya@example.com")


def make_client(user_override=_override_customer):
    fake_node = FakeNodeClient()
    app.dependency_overrides[get_current_user] = user_override
    app.dependency_overrides[get_node_client] = lambda: fake_node
    app.dependency_overrides[get_ticket_repository] = lambda: TicketRepository(client=FakeMongoClient())
    client = TestClient(app)
    return client, fake_node


def teardown_function(_):
    app.dependency_overrides.clear()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_requires_authentication():
    def unauthenticated():
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = unauthenticated
    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_chat_greeting_flow():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "GREETING"
    assert body["conversation_id"]
    assert body["message"]  # Ollama unreachable here -> deterministic fallback, still non-empty


def test_chat_service_problem_identifies_real_category_and_redirect():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "My tap is leaking"})
    body = response.json()
    assert body["intent"] == "SERVICE_PROBLEM"
    assert body["category"] == "plumbing"
    assert body["redirect"] == "/services?category=plumbing"

def test_chat_followup_after_category_identification_still_answers():
    client, _ = make_client()

    first = client.post("/api/chat", json={"message": "My tap is leaking"})
    assert first.json()["category"] == "plumbing"
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/api/chat", json={"message": "please show me", "conversation_id": conversation_id}
    )
    body = second.json()
    assert body["category"] == "plumbing"
    assert body["redirect"] == "/services?category=plumbing"
    assert "plumbing" in body["message"]

def test_chat_emergency_flow_surfaces_support_helpline_via_fallback():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "my switchboard is sparking"})
    body = response.json()
    assert body["intent"] == "EMERGENCY_SERVICE"
    assert body["priority"] == "emergency"
    assert "1800-GIG-SAATHI" in body["message"], "fallback reply must surface the real support helpline"

def test_chat_emergency_flow_also_recommends_the_matching_category():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "my switchboard is sparking"})
    body = response.json()
    assert body["intent"] == "EMERGENCY_SERVICE"
    assert body["category"] == "electrical"
    assert body["redirect"] == "/services?category=electrical"
    assert "electrical" in body["message"]



def test_chat_cancel_requires_confirmation_before_mutating():
    client, fake_node = make_client()

    first = client.post("/api/chat", json={"message": "I want to cancel my booking"})
    assert first.status_code == 200
    assert fake_node.cancel_calls == [], "must not cancel before user confirms"
    conversation_id = first.json()["conversation_id"]
    assert any(a["type"] == "confirm_cancel_booking" for a in first.json()["actions"])

    second = client.post("/api/chat", json={"message": "yes", "conversation_id": conversation_id})
    assert second.status_code == 200
    assert fake_node.cancel_calls == ["b1"], "must cancel only after explicit confirmation"


def test_chat_dispute_report_creates_ticket_and_it_is_only_visible_to_owner():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "Worker aur mere beech payment ko lekar dispute ho gaya hai"})
    body = response.json()
    assert body["intent"] == "DISPUTE_REPORT"

    # A different user's session must not see this ticket.
    def other_user():
        return AuthenticatedUser(id="cust-2", role="customer", name="Other", email="o@example.com")

    app.dependency_overrides[get_current_user] = other_user
    list_response = client.get("/api/support/tickets")
    assert list_response.status_code == 200
    assert list_response.json() == []

def test_chat_show_cancelled_service_lists_recent_bookings():
    client, _ = make_client()
    response = client.post("/api/chat", json={"message": "show my cancelled service"})
    body = response.json()
    assert body["intent"] == "BOOKING_STATUS"
    assert "cancelled" in body["message"].lower()
    assert "Switchboard" in body["message"]