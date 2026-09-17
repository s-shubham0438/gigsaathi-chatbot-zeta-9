from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class NodeBackendError(RuntimeError):

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NodeBackendClient:

    def __init__(
        self,
        cookie_header: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = settings.node_backend_url.rstrip("/")
        self._headers = {"cookie": cookie_header} if cookie_header else {}
        self._timeout = timeout
        # `transport` is only ever set in tests (httpx.MockTransport), to
        # exercise this client's request/response handling against a fake
        # server without a dependency beyond httpx itself.
        self._transport = transport

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.request(method, url, headers=self._headers, **kwargs)
        except httpx.RequestError as exc:
            raise NodeBackendError(f"Could not reach Node backend at {url}: {exc}") from exc

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400:
            message = data.get("message", f"Node backend returned {response.status_code}")
            raise NodeBackendError(message, status_code=response.status_code)

        return data

    # Services (GET /api/services, public)
    async def list_services(self) -> list[dict]:
        data = await self._request("GET", "/services")
        return data.get("services", [])

    async def get_service(self, service_id: str) -> dict | None:
        try:
            data = await self._request("GET", f"/services/{service_id}")
        except NodeBackendError as exc:
            if exc.status_code == 404:
                return None
            raise
        return data.get("service")

    async def list_live_categories(self) -> list[str]:
        services = await self.list_services()
        categories = {s.get("category", "").strip().lower() for s in services if s.get("category")}
        return sorted(c for c in categories if c)

    # Professionals / workers (GET public, mutate = own profile)
    async def list_professionals(
        self, category: str | None = None, location: str | None = None, available: bool | None = None
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if category:
            params["category"] = category
        if location:
            params["location"] = location
        if available is not None:
            params["available"] = str(available).lower()
        data = await self._request("GET", "/professionals", params=params)
        return data.get("professionals", [])

    async def get_professional(self, professional_id: str) -> dict | None:
        try:
            data = await self._request("GET", f"/professionals/{professional_id}")
        except NodeBackendError as exc:
            if exc.status_code == 404:
                return None
            raise
        return data.get("professional")

    # Reviews (real rating data — GET is public)
    async def get_professional_reviews(self, professional_id: str) -> dict:
        return await self._request("GET", f"/reviews/professional/{professional_id}")

    # Bookings (auth required; Node enforces ownership/role)
    async def get_customer_bookings(self) -> list[dict]:
        data = await self._request("GET", "/bookings/customer")
        return data.get("bookings", [])

    async def get_professional_bookings(self) -> list[dict]:
        data = await self._request("GET", "/bookings/professional")
        return data.get("bookings", [])

    async def get_booking(self, booking_id: str) -> dict | None:
        try:
            data = await self._request("GET", f"/bookings/{booking_id}")
        except NodeBackendError as exc:
            if exc.status_code == 404:
                return None
            raise
        return data.get("booking")

    async def create_booking(self, payload: dict) -> dict:
    
        data = await self._request("POST", "/bookings", json=payload)
        return data["booking"]

    async def update_booking_status(self, booking_id: str, status: str) -> dict:
        data = await self._request("PATCH", f"/bookings/{booking_id}/status", json={"status": status})
        return data["booking"]

    async def decline_booking_request(self, booking_id: str) -> dict:
        data = await self._request("PATCH", f"/bookings/{booking_id}/decline")
        return data["booking"]

    async def cancel_booking(self, booking_id: str) -> dict:
        data = await self._request("PATCH", f"/bookings/{booking_id}/cancel")
        return data["booking"]

    # Auth passthrough (rarely needed directly — session.py covers
    # the common "who is calling" case)
    async def me(self) -> dict | None:
        try:
            data = await self._request("GET", "/auth/me")
        except NodeBackendError as exc:
            if exc.status_code == 401:
                return None
            raise
        return data.get("user")
