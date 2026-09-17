# Implementation State

Read this before resuming work. Update after every milestone. Do not re-audit the repos —
`AI_CONTEXT.md` already has the verified findings from Phase 1/2.

## Completed

- **Phase 1 — Audit**: backend + frontend repos cloned and read in full. Written up in
  `AI_CONTEXT.md` sections A–N.
- **Phase 2 — Gap analysis**: missing capabilities enumerated (`AI_CONTEXT.md` section L).
- **Phase 3/4 — Design + implementation** of the Python chatbot service:
  - `app/config.py` — all external config via env vars, nothing hardcoded.
  - `app/auth/session.py` — auth relay to Node's real `GET /api/auth/me` (documented decision;
    see its docstring).
  - `app/clients/node_backend.py` — typed client for every verified real Node route (services,
    professionals, reviews, bookings CRUD, auth/me). No invented routes.
  - `app/clients/ollama_client.py` — minimal client against Ollama's documented `/api/chat`.
  - `app/services/language.py` — English/Hindi/Hinglish detection (heuristic, stdlib only).
  - `app/services/intent.py` — deterministic keyword/pattern intent classifier (all 19 intents
    from the master spec's `Intent` enum in `app/schemas/chat.py`).
  - `app/services/category.py` — category classification restricted to the live category list
    from Node (not the frontend's static 12-item mock list — see `AI_CONTEXT.md` section I),
    plus urgency/priority extraction (normal/urgent/emergency).
  - `app/services/conversation.py` — bounded, structured conversation state (max turns from
    `CONVERSATION_MAX_TURNS`, TTL eviction, per-user isolation).
  - `app/services/orchestrator.py` — the full pipeline (language → intent → entities → real
    data retrieval → confirmation-gated mutation → LLM phrasing → structured response), with a
    tested, honest fallback reply when Ollama is unreachable.
  - `app/repositories/ticket_repository.py` — the new dispute/ticket capability (doesn't exist
    in Node — see gap L in `AI_CONTEXT.md`), with ownership enforced server-side, never from
    client input.
  - `app/routes/{health,chat,support}.py`, `app/routes/deps.py`, `app/main.py` — FastAPI app,
    global exception handler (never leaks a traceback), CORS matching Node's existing config.
  - `node_backend_patch/` — a ready-to-merge Node-side equivalent of the ticket system, so the
    real team can make Node the authority for it later (see its own README for why this exists
    alongside the Python-side implementation, not instead of it).
  - `frontend_integration_patch/` — the exact diff needed in the existing (already-built)
    `AIChatbotPage.jsx` to call this service instead of its current hardcoded demo replies, and
    a note on the still-missing worker-facing chat entry point.
  - `.env.example`, `requirements.txt`, `pyproject.toml`, `README.md`.

## Verified (executed in this environment, not claimed)

- `git clone` of both repos — real, public, shallow clones read in full.
- Dependency install + import: `fastapi==0.141.1, uvicorn==0.53.0, pydantic==2.13.5,
  pydantic-settings==2.15.0, httpx==0.28.1, pymongo==4.18.1, python-dotenv==1.2.3` all install
  and import cleanly under Python 3.13.13 in this sandbox. All except httpx explicitly declare
  Python 3.14 support in their PyPI classifiers (checked directly, not assumed) — see the
  Python-3.14 limitation below for why the sandbox itself couldn't confirm that directly.
  `motor` was deliberately NOT used (only declares support up to 3.13) — `pymongo`'s own native
  `AsyncMongoClient` (confirmed importable, `pymongo>=4.9`) replaces it, which is both fewer
  dependencies and better 3.14 alignment.
- **`python -m pytest tests/ -v` → 48 passed, 0 failed** (last run in this session). Covers:
  language detection (English/Hindi/Hinglish, including the master spec's own three worked
  examples), intent classification (including the master spec's own worked examples — tap
  leak → SERVICE_PROBLEM, electrical board fried → SERVICE_PROBLEM/priority "Urgent" per the
  spec's own labeling, not "Emergency"), category classification restricted to live categories
  only, conversation bounding/isolation, ticket ownership privacy (owner/admin/other-user —
  exactly the three cases Section 40 asks for), the Node backend client against
  request/response shapes copied verbatim from the audited controller source, the Ollama
  client against Ollama's documented response shape, and full FastAPI end-to-end route tests
  (auth required, greeting flow, category+redirect flow, **cancel-requires-confirmation flow,
  dispute-ticket-creation-then-cross-user-denial flow**).
  - One real bug was found and fixed during this testing: a bare confirmation reply ("yes")
    was being reclassified as `UNKNOWN` instead of carrying forward the pending
    cancel/accept intent, so confirmed cancellations silently never executed. Fixed in
    `orchestrator.py` (see its docstring) and covered by
    `test_chat_cancel_requires_confirmation_before_mutating`.
- **Real process boot tests**, not just in-process TestClient:
  - `uvicorn app.main:app` started as a real subprocess; `curl` against `/api/health` (200),
    `/api/chat` with no cookie (401, no Node call attempted), `/api/chat` with a cookie while
    Node is down (503, graceful — not a crash/traceback).
  - The real Node backend: `npm install` (138 packages, clean), booted with `node server.js`
    (prints "Server running on port 4000").
  - The proposed `node_backend_patch/` files: copied into a working copy of the cloned Node
    repo, `node --check` passed on all three, wired into a working copy of `server.js`, booted
    for real, and `curl /api/disputes` returned 401 ("Access token missing") — proving Express
    registered the route correctly, not a 404. (This working-copy verification was not pushed
    anywhere — see `node_backend_patch/README.md`.)

## Blocked / unverified in this environment (reported honestly, not worked around)

- **Ollama/Llama 3.1**: `ollama.com` is blocked by this sandbox's network egress policy, and
  no GPU is present. Could not install Ollama or pull `llama3.1`. The client is structurally
  tested (`tests/test_ollama_client.py`) against a stub matching Ollama's documented response
  shape; real model output is unverified. **Action for the user**: run `ollama serve` +
  `ollama pull llama3.1` in a real environment, point `OLLAMA_BASE_URL`/`OLLAMA_MODEL` at it,
  and manually verify a few real chat turns before considering this integration done.
- **MongoDB**: no live instance reachable (same network policy; `repo.mongodb.org` and
  `fastdl.mongodb.org`, tried for `mongodb-memory-server`'s bundled binary, both blocked —
  confirmed via a real attempted download, not assumed). `TicketRepository` is tested against
  an in-memory fake of just enough of pymongo's async surface to prove its ownership logic;
  real MongoDB wire behavior is unverified. **Action for the user**: point `MONGO_DB_URI` at a
  real instance and re-run `python -m pytest tests/` plus a manual create/list/get ticket
  round-trip before production use.
- **Python 3.14 final**: only `cpython-3.14.0rc2` was obtainable via `uv`'s bundled build index
  in this sandbox (confirmed: `uv python install 3.14 --reinstall` re-resolved the same rc2,
  and no newer 3.14 build appeared in `uv python list --all-versions`). That rc2 build's
  `typing._eval_type` lacks a `prefer_fwd_module` parameter that `pydantic==2.13.5` (the
  current, only latest PyPI release) already assumes final Python 3.14 provides — confirmed by
  direct inspection of `typing._eval_type`'s live signature in that interpreter, not guessed.
  This is a sandbox/pre-release artifact, not a real pydantic/FastAPI incompatibility with
  final Python 3.14 (both packages declare 3.14 support in their PyPI classifiers). **Action
  for the user**: install real Python 3.14.x (python.org, or whatever the deployment OS's
  package manager offers once it ships it) and re-run the test suite once — expected to pass
  unchanged, but this specific claim is unverified until that run happens.
- **Push access**: this session has no GitHub credentials for either
  `ultimate-final-backend` or `ultimate-final-frontend`. `node_backend_patch/` and
  `frontend_integration_patch/` are ready-to-apply file sets / diffs, not commits.

## Needs Testing (once the blockers above are lifted)

- Real Ollama/Llama 3.1 chat turns, in English/Hindi/Hinglish, including a prompt-injection
  attempt ("ignore previous instructions...") to confirm the system prompt's stated refusal
  behavior holds up against the real model (the architecture already makes this a phrasing-only
  concern — authorization can't be bypassed via the LLM by construction, since the LLM never
  makes an authorization or mutation decision — but the actual refusal wording should still be
  eyeballed).
- Real MongoDB-backed ticket round-trip (create → list → get → cross-user denial) against a
  live instance.
- Real booking create/cancel/accept/decline through this service against a live Node + Mongo
  stack (currently only verified at the HTTP-contract level via `test_node_backend_client.py`,
  which uses response payloads copied from the audited controller source rather than a live
  call).
- The `node_backend_patch/` dispute routes against a live database (currently only verified to
  boot and route-register correctly, not to actually read/write).
- Load/concurrency behavior of the in-process `ConversationStore` (documented single-instance
  limitation — see its docstring — not yet a problem worth solving before this ships to more
  than one replica).
