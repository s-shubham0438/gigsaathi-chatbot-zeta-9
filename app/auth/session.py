from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    role: str  # "customer" | "professional" | "admin" — exactly as Node returns it
    name: str
    email: str


async def get_current_user(request: Request) -> AuthenticatedUser:
    cookie_header = request.headers.get("cookie")
    if not cookie_header:
        raise HTTPException(status_code=401, detail="Not authenticated")

    url = f"{settings.node_backend_url.rstrip('/')}/auth/me"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, headers={"cookie": cookie_header})
    except httpx.RequestError as exc:
        logger.error("auth relay failed: could not reach Node backend at %s (%s)", url, exc)
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = response.json()
    user = payload.get("user") or {}
    user_id = user.get("_id") or user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return AuthenticatedUser(
        id=str(user_id),
        role=str(user.get("role", "customer")),
        name=str(user.get("name", "")),
        email=str(user.get("email", "")),
    )
