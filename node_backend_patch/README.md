# Proposed Node backend addition: dispute/support tickets

**Status: NOT merged, NOT running anywhere. This is a proposal, not a live route.**

The audited `ultimate-final-backend` repository has no dispute/ticket model, route, or
controller at all (see `../docs/AI_CONTEXT.md` section J). The master chatbot spec (Sections
21–23) requires one. This session has no push/merge access to that GitHub repository, so the
Python chatbot service ships its own controlled `disputes` collection directly
(`app/repositories/ticket_repository.py`) as the smallest working addition it *can* deliver
(see the "WHY DIRECT MONGO ACCESS HERE" docstring in that file for the full reasoning).

This folder is the alternative, Node-side implementation of the exact same feature, written so
the real backend team can merge it later and make Node — not the Python service — the
authority for ticket storage, consistent with the rest of the master spec. The stored
document shape is intentionally identical to what `ticket_repository.py` already writes
(`_id, owner_id, owner_role, category, description, booking_id, status, created_at,
updated_at`, collection name `disputes`), so migrating is a data copy, not a redesign.

## Files

- `models/dispute.model.js` — Mongoose schema, follows the same conventions as the audited
  `user.model.js` / `booking.model.js` (timestamps, ObjectId refs to `User`/`Booking`).
- `controllers/dispute.controller.js` — `createDispute`, `getMyDisputes`, `getDispute`,
  following the exact response-shape conventions (`{success, message, ...}`) used by every
  other controller in the audited codebase.
- `routes/dispute.route.js` — mounted the same way every other route is (see `server.js`).

## To actually adopt this

1. Copy the three files into `backend/backend/src/{models,controllers,routes}/` respectively.
2. In `server.js`, add:
   ```js
   import disputeRouter from "./src/routes/dispute.route.js";
   ...
   app.use("/api/disputes", disputeRouter);
   ```
3. Point the Python chatbot service's ticket calls at these new Node routes instead of
   `TicketRepository`'s direct Mongo access (swap `app/repositories/ticket_repository.py`'s
   call sites in `app/routes/support.py` / `app/services/orchestrator.py` for
   `NodeBackendClient` calls to `/api/disputes...`).
4. Delete `app/repositories/ticket_repository.py` once step 3 is done — its only purpose was
   filling this exact gap.

**This has not been tested against a live server in this environment** (no MongoDB was
reachable in the development sandbox — see `../docs/AI_IMPLEMENTATION_STATE.md`). It has been
verified to be syntactically valid Node/ESM (`node --check`) and to follow the audited
codebase's own conventions exactly; a real functional test still needs to happen once merged.
