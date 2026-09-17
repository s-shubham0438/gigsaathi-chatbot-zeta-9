import httpx
import pytest

from app.clients.node_backend import NodeBackendClient, NodeBackendError


def _client_with_response(expected_method: str, expected_path: str, json_body: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == expected_method
        assert request.url.path == expected_path
        return httpx.Response(status_code, json=json_body)

    transport = httpx.MockTransport(handler)
    return NodeBackendClient(cookie_header="accessToken=abc", transport=transport)


async def test_list_services_hits_get_services_and_parses_real_shape():
    client = _client_with_response(
        "GET",
        "/api/services",
        {
            "success": True,
            "count": 1,
            "services": [
                {"_id": "svc1", "name": "Tap & Pipe Leak Repair", "category": "plumbing", "startingPrice": 299}
            ],
        },
    )
    services = await client.list_services()
    assert services == [{"_id": "svc1", "name": "Tap & Pipe Leak Repair", "category": "plumbing", "startingPrice": 299}]


async def test_list_live_categories_derives_from_services():
    client = _client_with_response(
        "GET",
        "/api/services",
        {
            "success": True,
            "services": [
                {"_id": "1", "category": "plumbing"},
                {"_id": "2", "category": "Electrical"},
                {"_id": "3", "category": "plumbing"},
            ],
        },
    )
    categories = await client.list_live_categories()
    assert categories == ["electrical", "plumbing"]


async def test_create_booking_posts_to_bookings_and_returns_booking():
    client = _client_with_response(
        "POST",
        "/api/bookings",
        {"success": True, "message": "Booking created successfully", "booking": {"_id": "b1", "status": "pending"}},
        status_code=201,
    )
    booking = await client.create_booking({"service": "svc1", "address": "x", "date": "2026-01-01"})
    assert booking == {"_id": "b1", "status": "pending"}


async def test_cancel_booking_patches_cancel_route():
    client = _client_with_response(
        "PATCH",
        "/api/bookings/b1/cancel",
        {"success": True, "message": "Booking cancelled successfully", "booking": {"_id": "b1", "status": "cancelled"}},
    )
    booking = await client.cancel_booking("b1")
    assert booking["status"] == "cancelled"


async def test_error_response_raises_node_backend_error_with_real_message():
    client = _client_with_response(
        "PATCH",
        "/api/bookings/b1/cancel",
        {"success": False, "message": "Booking not found"},
        status_code=404,
    )
    with pytest.raises(NodeBackendError) as exc_info:
        await client.cancel_booking("b1")
    assert "Booking not found" in str(exc_info.value)
    assert exc_info.value.status_code == 404


async def test_get_service_returns_none_on_404_not_an_exception():
    client = _client_with_response("GET", "/api/services/missing", {"success": False, "message": "Service not found"}, status_code=404)
    result = await client.get_service("missing")
    assert result is None
