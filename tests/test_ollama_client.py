import httpx
import pytest

from app.clients.ollama_client import OllamaClient, OllamaError


async def test_chat_sends_documented_payload_and_parses_reply():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request.read()
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Hi there!"}})

    client = OllamaClient(base_url="http://fake-ollama", model="llama3.1", transport=httpx.MockTransport(handler))
    reply = await client.chat([{"role": "user", "content": "hello"}])

    assert reply == "Hi there!"
    assert captured["path"] == "/api/chat"
    assert b'"model":"llama3.1"' in captured["body"]


async def test_non_200_raises_ollama_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="model not loaded"))
    client = OllamaClient(base_url="http://fake-ollama", transport=transport)
    with pytest.raises(OllamaError):
        await client.chat([{"role": "user", "content": "hello"}])


async def test_missing_content_raises_ollama_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"message": {}}))
    client = OllamaClient(base_url="http://fake-ollama", transport=transport)
    with pytest.raises(OllamaError):
        await client.chat([{"role": "user", "content": "hello"}])
