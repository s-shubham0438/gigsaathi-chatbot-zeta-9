from __future__ import annotations
import re
from dataclasses import dataclass
from app.schemas.chat import Priority

# Keyword seed for the categories verified live in MongoDB today
# (plumbing, electrical, cleaning, appliance, carpentry, painting — see
# `ensureDefaultServices()` / `scripts/seed.js`). Extend as real services
# are added; do not invent categories that have no backing Service records.
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "plumbing": ["tap", "pipe", "leak", "leaking", "plumber", "plumbing", "drain", "water", "bathroom fitting", "nal"],
    "electrical": [
        "electric", "electrical", "wiring", "switchboard", "short circuit", "shortcircuit",
        "fuse", "mcb", "inverter", "fan", "light", "socket", "bijli", "current",
    ],
    "cleaning": ["clean", "cleaning", "deep clean", "sofa", "saaf", "safai"],
    "appliance": [
        "washing machine", "fridge", "refrigerator", "microwave", "ac", "air conditioner",
        "appliance", "cooler", "geyser",
    ],
    "carpentry": ["furniture", "carpenter", "carpentry", "wood", "door", "lock", "latch", "modular kitchen"],
    "painting": ["paint", "painting", "waterproof", "waterproofing", "wall"],
}

_URGENT_MARKERS = re.compile(
    r"\b(urgent|jaldi|abhi|immediately|asap|right now|today only|fried|fuse gaya|"
    r"short circuit|shortcircuit)\b",
    re.I,
)
# Reserved for situations with an active safety risk, matching the master
# prompt's own worked examples (Section 9/20): a burnt-out/"fried" board is
# Urgent (already broken, needs prompt repair) — an active fire/spark/shock/
# leak in progress is Emergency (safety risk right now). Keep these two
# tiers distinct rather than collapsing "fried" into emergency, which would
# contradict the master prompt's own example priority.
_EMERGENCY_MARKERS = re.compile(
    r"\b(emergency|danger|dangerous|fire|spark|sparking|shock|electrocut|gas leak|"
    r"flooding|burst pipe|burst)\b",
    re.I,
)


@dataclass(frozen=True)
class CategoryMatch:
    category: str | None
    confidence: float  # 0..1, purely a keyword-hit ratio — explainable, not a black box
    problem: str
    priority: Priority


def classify_category(message: str, live_categories: list[str] | None = None) -> CategoryMatch:
    text = message.lower()

    best_category: str | None = None
    best_hits = 0
    keyword_space = _CATEGORY_KEYWORDS
    if live_categories:
        # Only ever offer categories that actually exist in the live catalog.
        keyword_space = {c: kws for c, kws in _CATEGORY_KEYWORDS.items() if c in live_categories}

    for category, keywords in keyword_space.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_category = category

    confidence = min(1.0, best_hits / 2) if best_hits else 0.0

    if _EMERGENCY_MARKERS.search(text):
        priority: Priority = "emergency"
    elif _URGENT_MARKERS.search(text):
        priority = "urgent"
    else:
        priority = "normal"

    return CategoryMatch(
        category=best_category if best_hits > 0 else None,
        confidence=confidence,
        problem=message.strip(),
        priority=priority,
    )
