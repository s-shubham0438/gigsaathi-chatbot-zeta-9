from __future__ import annotations

import httpx

from app.config import settings


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model = model or settings.ollama_model
        self._timeout = settings.ollama_request_timeout_seconds
        # See NodeBackendClient — same testability pattern, no new dependency.
        self._transport = transport

    async def chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self._base_url}/api/chat"
        payload = {"model": self._model, "messages": messages, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(url, json=payload)
        except httpx.RequestError as exc:
            raise OllamaError(f"Could not reach Ollama at {url}: {exc}") from exc

        if response.status_code != 200:
            raise OllamaError(f"Ollama returned HTTP {response.status_code}: {response.text[:300]}")

        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not content:
            raise OllamaError("Ollama response did not contain message.content")
        return content
