from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service
    chatbot_service_host: str = "0.0.0.0"
    chatbot_service_port: int = 8000
    log_level: str = "INFO"

    # Node/Express backend — the business-logic authority. The chatbot
    # never mutates booking/user/review state itself; it always calls
    # through to these real, existing routes.
    node_backend_url: str = "http://localhost:4000/api"

    # MongoDB — same database as the Node backend. Only used for the new
    # `disputes` collection (see docs/AI_CONTEXT.md section J/L — no
    # dispute/ticket system exists in the Node backend today).
    mongo_db_uri: str = "mongodb://127.0.0.1:27017/gigsaathi"
    mongo_db_name: str = "gigsaathi"

    # Ollama / Llama 3.1
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_request_timeout_seconds: float = 30.0

    # Support contact — the real values already published on the existing
    # ContactPage.jsx. Configurable here rather than hardcoded a second time
    # anywhere in the chatbot.
    support_phone_helpline: str = "1800-GIG-SAATHI"
    support_phone_office: str = "+91 98230 44120"
    support_email: str = "support@gigsaathi.demo"
    support_email_federation: str = "federation@gigsaathi.demo"

    # Conversation memory bounds — hard cap so context never grows
    # unboundedly (master-prompt rule: no context window drift).
    conversation_max_turns: int = 6
    conversation_ttl_minutes: int = 120


settings = Settings()
