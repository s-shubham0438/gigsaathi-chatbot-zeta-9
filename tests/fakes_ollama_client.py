from __future__ import annotations

from app.clients.ollama_client import OllamaError


class FakeOllamaClient:
    async def chat(self, messages: list[dict[str, str]]) -> str:
        raise OllamaError("Ollama intentionally unavailable in tests")