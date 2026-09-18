"""
Intent classification: deterministic, keyword/pattern-based, explainable.

Per Section 17/36/44 of the master prompt: classification that gates
authorization-adjacent behavior (booking, cancelling, disputes) must not be
left to free-form LLM judgement. This classifier is plain Python — the same
input always produces the same intent, and every match is traceable to the
rule that produced it. The LLM (see services/llm.py) is used only
afterwards, to phrase the natural-language reply around an already-decided
intent/entity set — never to decide the intent itself.

This is intentionally a rule-based first pass, not a trained model
(Section 51: don't reach for ML/RAG infrastructure the requirements don't
justify). It is easy to extend with more phrases as real usage reveals gaps,
and every rule is visible in one place instead of hidden in model weights.
"""

from __future__ import annotations

import re

from app.schemas.chat import Intent

# Ordered rule list: FIRST match wins. Order encodes priority — e.g. a
# cancellation mention should win over a generic "booking" mention.
_RULES: list[tuple[Intent, re.Pattern[str]]] = [
    (Intent.GREETING, re.compile(r"^\s*(hi+|hello|hey|namaste|namaskar|helo)\s*[!.,]*\s*$", re.I)),
    (
        Intent.EMERGENCY_SERVICE,
        re.compile(
            r"\b(emergency|gas leak|fire|sparking|shock|electrocut|flooding|burst pipe|"
            r"danger|dangerous|life[- ]threatening)\b",
            re.I,
        ),
    ),
    (
        Intent.DISPUTE_REPORT,
        re.compile(
            r"\b(dispute|complain|complaint|fraud|cheated|scam|"
            r"worker (misbehav|rude|did not|didn't|abus)|"
            r"payment (issue|problem|dispute)|not satisfied with)\b",
            re.I,
        ),
    ),
    (Intent.DISPUTE_STATUS, re.compile(r"\b(my (complaint|dispute|ticket)|ticket status|complaint status)\b", re.I)),
    (
        Intent.SUPPORT_CONTACT,
        re.compile(r"\b(support (number|contact|email)|helpline|customer care|talk to (a )?human|contact support)\b", re.I),
    ),
    (
        Intent.WORKER_ACCEPT_REQUEST,
        re.compile(r"\b(accept (the |this )?(request|job|booking)|i('| a)?ll take (it|this))\b", re.I),
    ),
    (
        Intent.WORKER_CANCEL_REQUEST,
        re.compile(r"\b(reject|decline) (the |this )?(request|job)|cancel (the |this )?(job|assignment)\b", re.I),
    ),
    (
        Intent.CANCEL_SERVICE,
        re.compile(r"\b(cancel|cancle|radd|cancel karna|cancel karni)\b.*\b(booking|order|request|service)?\b|\bcancel my\b", re.I),
    ),
    (
        Intent.BOOKING_STATUS,
        re.compile(
            r"\b(booking status|where is my (worker|booking)|track (my )?(booking|order)|has (my )?worker|"
            r"show (me )?my (?:(?:cancelled|canceled|past|recent|old)\s+)?(booking|bookings|service|services|order|orders)|"
            r"my (bookings|orders)|booking history)\b",
            re.I,
        ),
    ),
    (
        Intent.PRICE_ESTIMATION,
        re.compile(r"\b(price|cost|charge|kitna|kitne|paisa|paise|rupaye|rupees|estimate|quote)\b", re.I),
    ),
    (
        Intent.WORKER_COMPARISON,
        re.compile(r"\b(compare|which (worker|saathi) is better|best (rated|worker)|vs\.?)\b", re.I),
    ),
    (
        Intent.WORKER_RECOMMENDATION,
        re.compile(r"\b(recommend|suggest|find (me )?(a )?(worker|saathi|plumber|electrician)|who can (fix|repair|do))\b", re.I),
    ),
    (
        Intent.BOOK_SERVICE,
        re.compile(r"\b(book|booking|schedule|raise request|raise a request|broadcast)\b", re.I),
    ),
    (
        Intent.ACCOUNT_RELATED,
        re.compile(r"\b(my account|profile|change (my )?(phone|email|password)|update (my )?profile)\b", re.I),
    ),
    (Intent.SERVICE_DISCOVERY, re.compile(r"\b(what services|which services|do you (offer|have)|categories)\b", re.I)),
]

# A SERVICE_PROBLEM is anything that reads like a natural-language complaint
# about something broken/needed, checked after the more specific rules above
# so it acts as a fallback that still beats plain UNKNOWN.
_PROBLEM_HINT_RE = re.compile(
    r"\b(leak|leaking|broken|not working|tut[\s-]?gaya|toot[\s-]?gaya|kharab|fix|repair|repair karna|"
    r"clean|cleaning|paint|painting|wiring|short circuit|shortcircuit|installation|install|"
    r"fried|board (fried|fuel|gaya)|not cooling|jam+ed?)\b",
    re.I,
)


def classify_intent(message: str) -> Intent:
    text = message.strip()
    if not text:
        return Intent.UNKNOWN

    for intent, pattern in _RULES:
        if pattern.search(text):
            return intent

    if _PROBLEM_HINT_RE.search(text):
        return Intent.SERVICE_PROBLEM

    if re.search(r"\bhelp\b", text, re.I):
        return Intent.GENERAL_HELP

    return Intent.UNKNOWN
