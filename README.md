# GigSaathi AI Chatbot Service

Python AI orchestration service for GigSaathi's chatbot: a FastAPI app that talks to the real
Node/Express backend (business authority), a real MongoDB (only for its own new `disputes`
collection), and Ollama/Llama 3.1 (natural-language phrasing only — never authorization or
business decisions).

**Read `docs/AI_CONTEXT.md` first.** It has the full, verified audit of the existing backend
and frontend this service integrates with — every route, schema field, and gap referenced
below was confirmed by reading that code directly, not assumed. `docs/AI_IMPLEMENTATION_STATE.md`
tracks what's built, tested, and still open.

## Architecture

```
React frontend  →  this service (/api/chat, /api/support/tickets, /api/health)
                         │                         │
                    Ollama /api/chat          MongoDB (disputes collection only)
                    (phrasing only)
                         │
                    Node/Express backend (/api/auth, /api/services, /api/professionals,
                    /api/bookings, /api/reviews) — the business-logic authority.
                    All real mutations (booking create/cancel/accept/decline, reviews)
                    go through here. This service never writes to User/Booking/
                    Service/ProfessionalProfile/Review directly.
```

Authentication is a relay, not a duplicate: this service forwards the browser's
`accessToken` cookie to Node's existing `GET /api/auth/me` on every request and trusts
whatever identity Node returns — see `app/auth/session.py` for the full reasoning. No JWT
secret is shared between the two services.

## Prerequisites

- **Python 3.14.x** (stable release from python.org, not a release candidate — see the
  "Known limitations" section below for why this matters).
- The Node backend (`ultimate-final-backend`) running and reachable.
- A MongoDB instance reachable by both the Node backend and this service (same database).
- [Ollama](https://ollama.com) installed and running (`ollama serve`), with the model pulled:
  ```
  ollama pull llama3.1
  ```

## Installation

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or: pip install -e .
cp .env.example .env              # then edit .env with real values
```

## Running

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`GET /api/health` should return `{"status": "ok"}` once it's up.

## Testing

```bash
source .venv/bin/activate
pip install -r requirements.txt   # includes pytest/pytest-asyncio
python -m pytest tests/ -v
```

48 tests, all passing as of the last run in this repository (language detection, intent
classification, category classification against the real live category list, conversation
memory bounds/isolation, ticket ownership/privacy, the Node backend client against its
verified real routes, the Ollama client against its documented response shape, and full
end-to-end FastAPI route tests). See `docs/AI_IMPLEMENTATION_STATE.md` for exactly what each
test does and does not prove.

## API routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/health` | none | liveness |
| POST | `/api/chat` | cookie (relayed to Node) | body `{message, conversation_id?}` |
| POST | `/api/support/tickets` | cookie | create a dispute/support ticket |
| GET | `/api/support/tickets` | cookie | list the caller's own tickets (all, if admin) |
| GET | `/api/support/tickets/{id}` | cookie | one ticket — 404 if not owner/admin |

Full request/response schemas: `app/schemas/chat.py`, `app/schemas/ticket.py`. Interactive
docs at `/docs` once the server is running (FastAPI's built-in Swagger UI).

## Environment variables

See `.env.example` — every value is documented there, including why the support-contact
values are what they are (copied from the real, existing `ContactPage.jsx`, not invented).

## Known limitations (documented honestly, not silently worked around)

1. **Python 3.14**: this service was developed and tested in a sandboxed environment where
   only Python 3.14.0rc2 (a pre-release candidate) was obtainable — not final 3.14.x — and rc2
   has a `typing` module incompatibility with the current `pydantic`/`fastapi` releases (both
   of which formally declare Python 3.14 support in their PyPI classifiers). All development
   and the full test suite therefore actually ran under Python 3.13.13 in that sandbox, which
   every pinned dependency also fully supports. **Before deploying, install real, final Python
   3.14.x and re-run `python -m pytest tests/ -v` once** — this is expected to pass unchanged,
   but hasn't been executed against true 3.14 final and that claim would otherwise be
   unverified. Full detail: `docs/AI_IMPLEMENTATION_STATE.md`.
2. **Ollama/Llama 3.1**: could not be installed or reached in the development sandbox (network
   policy blocked `ollama.com`, no GPU present). `app/clients/ollama_client.py` is tested
   against a stub server that mimics Ollama's documented `/api/chat` response shape, and the
   orchestrator has a tested, honest fallback reply path for when Ollama is unreachable — but
   real model output has not been verified. Verify once `ollama serve` + `ollama pull
   llama3.1` are available.
3. **MongoDB**: no live MongoDB instance was reachable in the sandbox either (same network
   policy). `TicketRepository`'s ownership/privacy logic is tested against an in-memory fake
   (`tests/fakes.py`) that implements just enough of pymongo's async surface to exercise that
   logic — this proves the authorization rules are correct, not that pymongo's real wire
   protocol behaves identically. Point `MONGO_DB_URI` at a real instance and re-run the
   service before trusting it in production.
4. **Dispute/ticket system is a Python-side addition, not (yet) a Node one.** See
   `node_backend_patch/README.md` for the proposed Node-side equivalent, which exists so the
   real backend team can adopt it and make Node the authority for this data too, matching the
   rest of the architecture. It has been verified to load and register correctly against a
   locally-run copy of the real Node server (see `docs/AI_IMPLEMENTATION_STATE.md`), but not
   against a live database.
5. **Worker-facing chat UI does not exist yet** — the existing `AIChatbotPage.jsx` is
   customer-only. The backend already supports any role; only a frontend route is missing.
   See `frontend_integration_patch/README.md`.
6. **Confirmation-reply intent carryover is a simple heuristic** (`orchestrator.py`: a bare
   "yes"/"haan"/etc. reply reuses the previous turn's intent rather than being reclassified).
   Works for the tested cancel/accept flows; a dedicated yes/no classifier would be a more
   robust replacement if conversations get more complex.
