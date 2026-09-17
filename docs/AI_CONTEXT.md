# GigSaathi AI Chatbot — System Context

This file exists to prevent context drift across chatbot development sessions.
Read it before making further changes. Update it after every meaningful milestone.

Audited commits (shallow clone, default branch `main`, audited 2026-09-17):
- Backend: https://github.com/bhargavatarun9-code/ultimate-final-backend (path: `backend/`)
- Frontend: https://github.com/bhargavatarun9-code/ultimate-final-frontend (path: `frontend/`)

---

## A. Current architecture

- **Frontend**: React 19 + Vite 8 + Redux Toolkit + react-router-dom 7 + Tailwind 4. Talks to backend
  exclusively through `axios` (`src/shared/lib/axiosInstance.js`), `baseURL` = `VITE_API_URL` (default
  `http://localhost:4000/api`), `withCredentials: true` (cookie-based auth, no bearer tokens anywhere).
- **Backend**: Node.js + Express 5 + Mongoose 9, ESM (`"type": "module"`). Entry point `server.js`.
  Cookie-based JWT auth (`accessToken` 15m, `refreshToken` 7d, both httpOnly). No refresh-token endpoint
  exists yet (refresh cookie is set but nothing reads it back).
- **Database**: MongoDB via Mongoose, one connection string `MONGO_DB_URI`, five collections total
  (`User`, `Service`, `ProfessionalProfile`, `Booking`, `Review`). No dispute/ticket/support collection.
- **No AI chatbot backend exists yet.** The frontend has a fully built chat UI
  (`src/pages/customer/AIChatbotPage.jsx`) that is customer-only, wired into the router at
  `/customer/ai-chat`, and currently answers with a hardcoded `getLocalReply()` keyword matcher — it is
  explicitly labeled "Frontend demo" in the UI and has a `// TODO: Replace this demo response with your
  Llama/FastAPI API call later.` comment. **This is the intended integration point.**
- There is no worker-facing chatbot UI or route at all today (Section 6 of the master spec requires one).

## B. Backend routes (verified from `src/routes/*.route.js`, all mounted under `/api` in `server.js`)

| Method | Path | Auth | Role | Controller |
|---|---|---|---|---|
| POST | `/api/auth/register` | none | — | `registerController` |
| POST | `/api/auth/login` | none | — | `loginController` |
| POST | `/api/auth/logout` | none | — | `logoutController` |
| GET | `/api/auth/me` | cookie | any | `meController` |
| DELETE | `/api/auth/delete/:id` | cookie | any authenticated (no role check — see gap G1) | `deleteUserController` |
| GET | `/api/services` | none | — | `getServices` (auto-seeds 6 default services if none active) |
| GET | `/api/services/:id` | none | — | `getService` |
| POST/PUT/DELETE | `/api/services...` | cookie | admin | create/update/delete |
| GET | `/api/professionals` | none | — | `getProfessionals` (query: `category`, `location`, `available`) |
| GET | `/api/professionals/:id` | none | — | `getProfessional` |
| POST/PUT/DELETE | `/api/professionals` | cookie | professional | own profile only |
| POST | `/api/bookings` | cookie | customer | `createBooking` |
| GET | `/api/bookings/customer` | cookie | customer | own bookings |
| GET | `/api/bookings/professional` | cookie | professional | own + matching broadcast requests |
| GET | `/api/bookings/:id` | cookie | any authenticated (no ownership check — see gap G2) | `getBooking` |
| PATCH | `/api/bookings/:id/status` | cookie | professional | accept broadcast / update own job status |
| PATCH | `/api/bookings/:id/decline` | cookie | professional | decline a broadcast request |
| PATCH | `/api/bookings/:id/cancel` | cookie | customer (ownership enforced) | `cancelBooking` |
| POST | `/api/reviews` | cookie | customer | review own completed booking |
| GET | `/api/reviews/professional/:id` | none | — | reviews + `{averageRating, totalReviews}` |
| GET | `/api/admin/overview` | cookie | admin | counts only |

No dispute, ticket, or support endpoints exist anywhere in the backend.

## C. Frontend → backend integration points

- `src/features/auth/api/authApi.js` — login/register/me/logout, maps backend role
  (`customer`/`professional`) to frontend role (`CUSTOMER`/`WORKER`) via `roleMap.js`. **There is no
  `admin` frontend role mapping, and no `COOPERATIVE` backend role at all** — the entire Cooperative
  portal (`/cooperative/*`, `CooperativeLayout`, `CooperativeDashboard`, etc.) is frontend-only demo
  functionality driven by `mocks/data/*` and a `switchRoleDirectly` Redux action; it is **not connected to
  any real backend role or data**. Treat it as out of scope for the chatbot's authorization model.
- `src/features/bookings/api/bookingApi.js` — full CRUD wrapper matching the table above, plus a
  `statusMap`/`normalizeStatus` translation layer (`pending↔REQUESTED`, `accepted↔ACCEPTED`, etc.).
- `src/features/workers/api/workerApi.js` — `getWorkers`/`getWorkerById`, but `mapWorker()` **fabricates
  several fields the backend does not provide**: `reviewsCount`, `completedJobs`, `distanceKm: 0`,
  `responseTimeMinutes: 15`, `cooperativeName`, `verificationBadge`, `completionRate: 100`,
  `languages: ['Hindi','English']`. None of these exist on `ProfessionalProfile`. Only `category`,
  `skills`, `experience`, `hourlyRate`, `location`, `rating`, `isAvailable`, and the populated `user`
  fields are real.
- `src/features/services/api/serviceApi.js` — `getEmergencyServices()` always returns `[]` with the
  comment "No emergency flag on the backend model yet." `getCategories()` returns a **static frontend-only
  list of 12 categories** (`mocks/data/categories.js`) that is *not* sourced from the backend.
- `src/pages/customer/AIChatbotPage.jsx` — the chatbot UI itself (see section A).

## D. MongoDB schema (from `src/models/*.model.js`, verbatim field names)

**User** (`User`): `name, email(unique), phone(unique,sparse), password(hashed), role: enum[customer,
professional, admin] default customer, profileImage, address, isVerified, timestamps`.

**Service** (`Service`): `name(unique), description, category(free string, NOT an enum/ref),
image, startingPrice, isActive, timestamps`. Categories that exist today (from `ensureDefaultServices()`
and `scripts/seed.js`, auto-created if the collection is empty): `plumbing, electrical, cleaning,
appliance, carpentry, painting`. **This is the authoritative, live category list** — not the frontend's
static 12-item mock list (gap G3).

**ProfessionalProfile** (`ProfessionalProfile`): `user(ref User, unique), category(free string,
lowercased), skills[String], experience(Number), description, hourlyRate(Number), location(free string,
NOT coordinates), rating(Number, default 0), isAvailable(Boolean), timestamps`. No trust/reputation
score beyond `rating`. `rating` is stored on the profile but nothing in the audited code recalculates it
from reviews (gap G4).

**Booking** (`Booking`): `customer(ref User), professional(ref User, nullable), service(ref Service),
requestMode: enum[individual,broadcast], declinedBy[ref User], address(free string), date, timeSlot,
description, photos[String], price(Number), paymentMethod(default "Cash After Service"),
paymentStatus: enum[PENDING,PAID], status: enum[pending,accepted,in_progress,completed,cancelled],
timestamps`.

**Review** (`Review`): `customer(ref User), professional(ref User), booking(ref Booking, unique),
rating(1-5), comment, timestamps`. One review per booking, only for `status:"completed"` bookings owned
by the reviewing customer.

No `Dispute`/`Ticket`/`SupportRequest` collection exists.

## E. Authentication / authorization

- JWT signed with `JWT_ACCESS_SECRET` (15 min) / `JWT_REFRESH_SECRET` (7 days), delivered as httpOnly
  cookies `accessToken`/`refreshToken`. `authMiddleware` reads `req.cookies.accessToken`, verifies it,
  and sets `req.user = {id, role}`. `requireRole(...roles)` gates specific routes.
- **No bearer-token support anywhere** — a non-browser client (like a Python service called directly by
  the frontend) cannot authenticate the same way unless the browser forwards the cookie to it, or the
  Python service asks Node to validate the session on its behalf.
- Known gaps in the existing backend (report only — not caused by the chatbot):
  - G1: `DELETE /api/auth/delete/:id` has no `requireRole`/ownership check — any authenticated user can
    delete any user by id.
  - G2: `GET /api/bookings/:id` has no ownership check — any authenticated user can fetch any booking by
    id (leaks customer/professional PII: name, email, phone).
  - These are pre-existing backend issues. The chatbot must not rely on these routes for anything
    privacy-sensitive without adding its own authorization check first (see Security section of the
    design doc).

## F. Booking flow (verified in `booking.controller.js`)

- **Individual**: customer picks a specific `professional` id up front → `POST /bookings` with
  `requestMode:"individual"` → booking created `status:"pending"`, assigned to that worker → worker calls
  `PATCH /bookings/:id/status {status:"accepted"|...}` (ownership: `professional === req.user.id`).
- **Broadcast ("Raise Request")**: customer omits `professional` → `POST /bookings` with
  `requestMode:"broadcast"` → booking created with `professional:null`, visible to every worker whose
  `ProfessionalProfile.category` matches the service's category and who is not in `declinedBy`. First
  worker to `PATCH /bookings/:id/status {status:"accepted"}` wins via an atomic
  `findOneAndUpdate({professional:null, status:"pending", declinedBy:{$ne:workerId}}, {$set:{professional,
  status:"accepted"}})` — this is the concurrency-safe claim the chatbot must go through (never write to
  `professional`/`status` directly).
- Workers may `PATCH /bookings/:id/decline` a broadcast request without cancelling it for others.
- Statuses: `pending → accepted → in_progress → completed`, or `→ cancelled` at any point via
  `PATCH /bookings/:id/cancel` (customer-only, ownership-checked).

## G. Cancellation flow

`PATCH /api/bookings/:id/cancel`, customer-only, ownership enforced server-side
(`{_id, customer: req.user.id}`), sets `status:"cancelled"` unconditionally — **no business rule blocks
cancelling an `in_progress` or `accepted` job today**, and there is no cancellation-fee/refund logic.
Workers have no "cancel an accepted job" endpoint — only `updateBookingStatus` (which they could technically
set to `cancelled` since it's in `allowedStatuses`, but nothing in the UI/controller distinguishes a
worker-initiated cancellation from any other status change, and there is no separate worker-cancel route
per Section 15/16 of the spec). This is a gap (G5) if the product wants worker-initiated cancellation to be
a distinct, auditable action.

## H. Worker request flow

`GET /api/bookings/professional` returns two kinds of jobs unioned: (1) bookings already assigned to this
worker (`professional === workerId`, any status), and (2) open broadcast requests matching the worker's
category that they haven't declined. Accept = `PATCH .../status {status:"accepted"}` (atomic claim, see F).
Decline = `PATCH .../decline` (broadcast only, does not affect other workers). There is no reject/cancel
action distinct from `updateBookingStatus`.

## I. Category / service structure

Categories are **not a separate collection** — they are free-text strings on `Service.category` and
`ProfessionalProfile.category` (both lowercased/trimmed on write). The only categories that currently have
real `Service` documents behind them are the 6 auto-seeded ones (plumbing, electrical, cleaning, appliance,
carpentry, painting). The frontend's 12-category mock list includes 6 more (gardening, home-maintenance,
beauty, tutoring, moving, community) that have **no backing services or workers today** — the chatbot must
not claim these are bookable; it should either fetch live categories from `GET /api/services` or clearly
say "not yet available" for the extra six.

## J. Support / dispute functionality

**Does not exist.** No model, no route, no controller, no frontend page beyond a generic
`ContactPage.jsx` contact form that only shows a local toast (`"Message sent!"`) — it makes no backend call
at all; the "message" is never persisted anywhere. This is the single biggest gap relative to the master
spec (Sections 21–23) and needs new backend surface, not just a Python-side feature (see gap analysis).

`ContactPage.jsx` does contain the **only existing "official" support contact info** in the whole
codebase, hardcoded directly in JSX (not an env var, not backend-configured):
- Toll-Free 24×7 Helpline: `1800-GIG-SAATHI`
- Pune Operations Office: `+91 98230 44120`
- Public email: `support@gigsaathi.demo`
- Union Partnerships email: `federation@gigsaathi.demo`

These are the real, existing values (not invented) — the chatbot should surface exactly these, sourced
from a new backend-configured env var (`SUPPORT_PHONE`, `SUPPORT_EMAIL`) rather than duplicating the
hardcoded JSX string, per Section 23.

## K. Existing admin functionality

`GET /api/admin/overview`, admin-role-gated, returns six counts (`totalUsers, totalProfessionals,
totalCustomers, totalBookings, completedBookings, totalServices`). No admin UI for managing bookings,
disputes, or users beyond this exists in the frontend (`CooperativeDashboard` etc. is unrelated mock data,
see section C).

## L. Missing capabilities (chatbot cannot use what doesn't exist)

1. No dispute/support ticket system (models, routes, ownership rules) — must be added.
2. No worker-initiated "cancel an accepted job" endpoint distinct from generic status update.
3. No trust/reputation score beyond a raw `rating` field that isn't auto-recomputed from reviews.
4. No location coordinates or distance calculation — `location`/`address` are free-text strings.
5. No emergency/urgent flag on `Service` or `Booking`.
6. No backend-configured support contact (`SUPPORT_PHONE`/`SUPPORT_EMAIL` env vars) — currently hardcoded
   in frontend JSX only.
7. No bearer-token or service-to-service auth path — only browser-cookie JWT.
8. No admin ticket-review UI/API.

## M. Environment / sandbox verification (2026-09-17, this development environment only)

Executed, not assumed:
- `git clone` of both repos: succeeded (public repos, shallow clone).
- Node: v22.22.2 present.
- Python 3.14: **not preinstalled**; `uv python install 3.14` succeeded but only resolved
  `cpython-3.14.0rc2` in this sandbox's cached build index — this is a release candidate, not a
  confirmed-stable final 3.14.x. The deployment target should install whatever the official
  python.org 3.14.x stable release is at deploy time; treat "3.14.0rc2 here" as **unverified against
  final 3.14** and re-check in the real deployment environment.
- Ollama: **not installed, and could not be installed** — outbound access to `ollama.com` is blocked by
  this sandbox's network allowlist (proxy returned 403). No GPU is present either. **Live Ollama/Llama 3.1
  connectivity and generation cannot be tested in this environment.** The service will be built against
  Ollama's documented local HTTP API (`/api/generate`, `/api/chat`, configurable `OLLAMA_BASE_URL` /
  `OLLAMA_MODEL`), with clear instructions for the user to run `ollama serve` + `ollama pull llama3.1`
  themselves, but this integration is **unverified end-to-end** until run in an environment with Ollama
  installed.
- MongoDB: no live instance available by default; a local `mongod` can potentially be started in this
  sandbox for integration testing (to be verified in Phase 4).
- The real Node backend is not deployed anywhere reachable — it can be run locally in this sandbox
  (`npm install && npm start`) against a local MongoDB for integration testing, which is a truer test than
  unit tests against mocks.

## N. Environment variables (existing + new, all consumed via `os.environ` / `dotenv`, never hardcoded)

Existing backend `.env.example`: `PORT, JWT_ACCESS_SECRET, JWT_REFRESH_SECRET, MONGO_DB_URI, CLIENT_URL`.

New, for the Python service (see `ai-chatbot/.env.example` once created): `OLLAMA_BASE_URL, OLLAMA_MODEL,
NODE_BACKEND_URL, MONGO_DB_URI (read access, same database), SUPPORT_PHONE, SUPPORT_EMAIL,
CHATBOT_SERVICE_PORT`, plus whatever the auth-relay design settles on (see open decision in the
implementation-state doc).
