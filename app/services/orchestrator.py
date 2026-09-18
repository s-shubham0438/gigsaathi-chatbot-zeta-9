from __future__ import annotations
import re
from app.clients.node_backend import NodeBackendClient, NodeBackendError
from app.clients.ollama_client import OllamaClient, OllamaError
from app.prompts.system_prompt import build_system_prompt
from app.repositories.ticket_repository import TicketRepository
from app.schemas.chat import ChatAction, ChatResponse, Intent
from app.services.category import classify_category
from app.services.conversation import ConversationState
from app.services.intent import classify_intent
from app.services.language import detect_language
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_AFFIRMATIVE_FOLLOWUP_RE = re.compile(
    r"\b(show me|yes|yeah|yep|ok|okay|sure|please|haan|ha|theek hai|go ahead|do it)\b", re.I
)


class Orchestrator:
    def __init__(
        self,
        node_client: NodeBackendClient,
        ticket_repository: TicketRepository,
        ollama_client: OllamaClient | None = None,
    ):
        self._node = node_client
        self._tickets = ticket_repository
        self._llm = ollama_client or OllamaClient()

    async def handle(
        self, *, message: str, state: ConversationState, user_id: str, user_role: str
    ) -> ChatResponse:
        language = detect_language(message)
        classified_intent = classify_intent(message)

        # A bare confirmation reply ("yes", "haan", ...) carries no intent
        # of its own — classify_intent() correctly returns UNKNOWN/
        # GENERAL_HELP for it. When the previous turn is awaiting
        # confirmation for a specific pending action and this reply has
        # just been marked "confirmed" (see routes/chat.py), carry the
        # PREVIOUS turn's intent forward instead of losing it to UNKNOWN —
        # otherwise a plain "yes" would never actually complete the
        # cancel/accept it was confirming. A message that clearly states a
        # new intent of its own still wins normally.
        if (
            state.confirmation_state == "confirmed"
            and classified_intent in (Intent.UNKNOWN, Intent.GENERAL_HELP)
            and state.intent
        ):
            intent = Intent(state.intent)
        else:
            intent = classified_intent

        state.language = language
        state.role = user_role
        state.intent = intent.value
        state.add_turn("user", message)

        known_data: dict[str, object] = {}
        actions: list[ChatAction] = []
        redirect: str | None = None

        try:
            known_data, actions, redirect = await self._route(
                intent=intent, message=message, state=state, user_role=user_role
            )
        except NodeBackendError as exc:
            logger.warning("node backend error while handling intent=%s: %s", intent, exc)
            known_data = {"backend_status": f"unavailable ({exc})"}

        reply_text = await self._generate_reply(
            role=user_role, language=language, known_data=known_data, state=state
        )
        state.add_turn("assistant", reply_text)

        return ChatResponse(
            conversation_id=state.conversation_id,
            message=reply_text,
            language=language,
            intent=intent,
            category=state.category,
            problem=state.problem,
            priority=state.priority,  # type: ignore[arg-type]
            actions=actions,
            redirect=redirect,
        )

    async def _route(
        self, *, intent: Intent, message: str, state: ConversationState, user_role: str
    ) -> tuple[dict[str, object], list[ChatAction], str | None]:
        known_data: dict[str, object] = {}
        actions: list[ChatAction] = []
        redirect: str | None = None

        if intent == Intent.GREETING:
            known_data = {"greeting": True}

        elif intent in (Intent.SERVICE_PROBLEM, Intent.CATEGORY_IDENTIFICATION, Intent.SERVICE_DISCOVERY):
            live_categories = await self._node.list_live_categories()
            match = classify_category(message, live_categories)
            state.category = match.category
            state.problem = match.problem
            state.priority = match.priority
            known_data["live_categories"] = live_categories
            if match.category:
                known_data["matched_category"] = match.category
                services = [s for s in await self._node.list_services() if s.get("category") == match.category]
                known_data["matching_services"] = [
                    {"name": s.get("name"), "startingPrice": s.get("startingPrice")} for s in services
                ]
                redirect = f"/services?category={match.category}"
            else:
                known_data["matched_category"] = None
            known_data["priority"] = match.priority
            if match.priority == "emergency":
                known_data["support_phone"] = settings.support_phone_helpline

        elif intent == Intent.WORKER_RECOMMENDATION or intent == Intent.WORKER_COMPARISON:
            category = state.category
            if not category:
                live_categories = await self._node.list_live_categories()
                match = classify_category(message, live_categories)
                category = match.category
                state.category = category
            if category:
                professionals = await self._node.list_professionals(category=category, available=True)
                # Only real fields — see docs/AI_CONTEXT.md section C for
                # which workerApi fields are frontend fabrications we do
                # NOT repeat here (distanceKm, responseTimeMinutes, etc.).
                known_data["workers"] = [
                    {
                        "id": p.get("_id"),
                        "name": (p.get("user") or {}).get("name"),
                        "rating": p.get("rating"),
                        "hourlyRate": p.get("hourlyRate"),
                        "location": p.get("location"),
                        "experience": p.get("experience"),
                    }
                    for p in professionals[:5]
                ]
            else:
                known_data["workers"] = []
                known_data["note"] = "category not yet identified"

        elif intent == Intent.PRICE_ESTIMATION:
            category = state.category
            if not category:
                live_categories = await self._node.list_live_categories()
                match = classify_category(message, live_categories)
                category = match.category
            if category:
                services = [s for s in await self._node.list_services() if s.get("category") == category]
                known_data["starting_prices"] = [
                    {"service": s.get("name"), "startingPrice": s.get("startingPrice")} for s in services
                ]
                known_data["pricing_note"] = (
                    "startingPrice is a floor, not a final quote — final price depends on the worker and job details"
                )
            else:
                known_data["note"] = "category not yet identified, cannot estimate"

        elif intent == Intent.BOOKING_STATUS:
            bookings = (
                await self._node.get_customer_bookings()
                if user_role == "customer"
                else await self._node.get_professional_bookings()
            )
            known_data["recent_bookings"] = [
                {
                    "id": b.get("_id"),
                    "status": b.get("status"),
                    "service": (b.get("service") or {}).get("name"),
                    "date": b.get("date"),
                }
                for b in bookings[:5]
            ]

        elif intent == Intent.CANCEL_SERVICE:
            if state.confirmation_state != "confirmed":
                bookings = await self._node.get_customer_bookings()
                cancellable = [b for b in bookings if b.get("status") in ("pending", "accepted", "in_progress")]
                known_data["cancellable_bookings"] = [
                    {"id": b.get("_id"), "service": (b.get("service") or {}).get("name"), "status": b.get("status")}
                    for b in cancellable[:5]
                ]
                if cancellable:
                    target = cancellable[0]
                    state.selected_booking_id = target.get("_id")
                    state.confirmation_state = "awaiting_confirmation"
                    actions.append(
                        ChatAction(
                            type="confirm_cancel_booking",
                            label=f"Cancel booking for {(target.get('service') or {}).get('name', 'this service')}?",
                            payload={"booking_id": target.get("_id")},
                        )
                    )
            else:
                booking_id = state.selected_booking_id
                if booking_id:
                    booking = await self._node.cancel_booking(booking_id)
                    known_data["cancel_result"] = {"id": booking.get("_id"), "status": booking.get("status")}
                    state.confirmation_state = None
                    state.selected_booking_id = None

        elif intent == Intent.WORKER_ACCEPT_REQUEST:
            requests = await self._node.get_professional_bookings()
            pending = [b for b in requests if b.get("status") == "pending"]
            known_data["pending_requests"] = [
                {"id": b.get("_id"), "service": (b.get("service") or {}).get("name")} for b in pending[:5]
            ]
            if state.confirmation_state == "confirmed" and state.selected_booking_id:
                booking = await self._node.update_booking_status(state.selected_booking_id, "accepted")
                known_data["accept_result"] = {"id": booking.get("_id"), "status": booking.get("status")}
                state.confirmation_state = None
                state.selected_booking_id = None
            elif pending:
                target = pending[0]
                state.selected_booking_id = target.get("_id")
                state.confirmation_state = "awaiting_confirmation"
                actions.append(
                    ChatAction(
                        type="confirm_accept_request",
                        label=f"Accept request for {(target.get('service') or {}).get('name', 'this job')}?",
                        payload={"booking_id": target.get("_id")},
                    )
                )

        elif intent == Intent.WORKER_CANCEL_REQUEST:
            if state.confirmation_state == "confirmed" and state.selected_booking_id:
                booking = await self._node.decline_booking_request(state.selected_booking_id)
                known_data["decline_result"] = {"id": booking.get("_id")}
                state.confirmation_state = None
                state.selected_booking_id = None
            else:
                known_data["note"] = "no specific request selected yet"

        elif intent == Intent.DISPUTE_REPORT:
            # Collect just enough to create a minimal ticket; a fuller
            # multi-turn collection flow is a documented next step (see
            # AI_IMPLEMENTATION_STATE.md) — this creates an "open" ticket
            # immediately with the raw description, which a human/admin
            # can triage, rather than blocking the user on more turns.
            ticket = await self._tickets.create(
                owner_id=state.user_id,
                owner_role=user_role,
                category="other",
                description=message,
                booking_id=state.selected_booking_id,
            )
            known_data["ticket_created"] = {"id": ticket["_id"], "status": ticket["status"]}
            known_data["support_email"] = settings.support_email
            known_data["support_phone"] = settings.support_phone_helpline

        elif intent == Intent.DISPUTE_STATUS:
            tickets = await self._tickets.list_for_user(requester_id=state.user_id, requester_role=user_role)
            known_data["tickets"] = [
                {"id": t["_id"], "status": t["status"], "category": t["category"]} for t in tickets[:5]
            ]

        elif intent == Intent.SUPPORT_CONTACT or state.priority == "emergency":
            known_data["support_helpline"] = settings.support_phone_helpline
            known_data["support_office_phone"] = settings.support_phone_office
            known_data["support_email"] = settings.support_email

        elif intent == Intent.EMERGENCY_SERVICE:
            state.priority = "emergency"
            known_data["support_helpline"] = settings.support_phone_helpline
            known_data["safety_first"] = True

            live_categories = await self._node.list_live_categories()
            match = classify_category(message, live_categories)
            state.category = match.category
            state.problem = match.problem
            if match.category:
                known_data["matched_category"] = match.category
                services = [s for s in await self._node.list_services() if s.get("category") == match.category]
                known_data["matching_services"] = [
                    {"name": s.get("name"), "startingPrice": s.get("startingPrice")} for s in services
                ]
                redirect = f"/services?category={match.category}"
            else:
                known_data["matched_category"] = None

        elif (
            intent in (Intent.UNKNOWN, Intent.GENERAL_HELP)
            and state.category
            and _AFFIRMATIVE_FOLLOWUP_RE.search(message)
        ):
            category = state.category
            services = [s for s in await self._node.list_services() if s.get("category") == category]
            known_data["matched_category"] = category
            known_data["matching_services"] = [
                {"name": s.get("name"), "startingPrice": s.get("startingPrice")} for s in services
            ]
            redirect = f"/services?category={category}"
            known_data["followup_confirmation"]= True

        # GREETING / GENERAL_HELP / BOOK_SERVICE / ACCOUNT_RELATED / UNKNOWN
        # fall through with whatever known_data was already set above (or
        # none) — the LLM is told explicitly to say when it has nothing to
        # ground a claim in, per prompts/system_prompt.py.

        return known_data, actions, redirect

    async def _generate_reply(
        self, *, role: str, language: str, known_data: dict[str, object], state: ConversationState
    ) -> str:
        system_prompt = build_system_prompt(role=role, language=language, known_data=known_data)
        messages = [{"role": "system", "content": system_prompt}]
        for turn in state.recent_history():
            messages.append({"role": "user" if turn.role == "user" else "assistant", "content": turn.text})

        try:
            return await self._llm.chat(messages)
        except OllamaError as exc:
            logger.warning("Ollama unavailable, using deterministic fallback reply: %s", exc)
            return _fallback_reply(language=language, known_data=known_data)


def _fallback_reply(*, language: str, known_data: dict[str, object]) -> str:
    """
    Used only when Ollama is unreachable (Section 38: graceful, honest
    degradation — never a stack trace, never fabricated success). This is
    deliberately plain and a little robotic; it is a safety net, not the
    intended normal-path experience.
    """
    if known_data.get("greeting"):
        return "Hi! Welcome to GigSaathi. How can I help you today?"
    # Checked before matched_category/generic fallback: an EMERGENCY_SERVICE
    # turn (see orchestrator._route) never sets matched_category — it skips
    # category classification entirely — so without this case a real safety
    # issue (sparking switchboard, gas leak, ...) fell through to the vague
    # generic message below instead of surfacing the real support number.
    # Found via live manual browser testing, not a unit test gap.
    if known_data.get("safety_first"):
        helpline = known_data.get("support_helpline") or known_data.get("support_phone") or "our support helpline"
        base = (
            "This sounds like it could be an emergency. If there's immediate danger, please "
            f"prioritize your safety first. For urgent help, call {helpline} right away."
        )
        category = known_data.get("matched_category")
        if category:
            base += f" This also looks like a {category} issue — I can show you available {category} professionals."
        return base
    # Checked before the plain matched_category case below: a
    # followup_confirmation turn (see orchestrator._route) reuses the SAME
    # known_data["matched_category"] the original identification turn set,
    # so without this branch both turns produce the identical "This looks
    # like a plumbing issue..." sentence — which reads as if the follow-up
    # ("please show me" / "yes") did nothing. Found via live manual browser
    # testing, 2026-09-18.
    if known_data.get("followup_confirmation") and known_data.get("matched_category"):
        category = known_data["matched_category"]
        return f"Sure — here are the {category} services and professionals near you."
    if "recent_bookings" in known_data:
        bookings = known_data["recent_bookings"]
        if not bookings:
            return "You don't have any bookings yet."
        listed = "; ".join(
            f"{b.get('service') or 'a service'} — {b.get('status')}" for b in bookings
        )
        return f"Here are your recent bookings: {listed}."

    if "ticket_created" in known_data:
        return (
            f"I've logged your report as ticket {known_data['ticket_created']['id']}. "
            f"Our team will follow up. You can also reach {known_data.get('support_email', 'support')}."
        )
    if known_data.get("matched_category"):
        return f"This looks like a {known_data['matched_category']} issue. I can show you the matching services."
    return "I'm having trouble reaching the AI model right now, but I've noted your message. Please try again shortly."
