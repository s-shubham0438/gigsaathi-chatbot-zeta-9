"""
Language detection: English / Hindi / Hinglish.

Deliberately NOT a machine-learning dependency (Section 51: don't
overengineer). `langdetect`/`fasttext`-style detectors are trained on
"pure" languages and are unreliable on code-switched Hinglish
("mere ghar ka tap leak ho raha hai"), which is exactly the case this
product needs most. A small, explainable heuristic — standard library only
— is more predictable and cheaper to reason about:

  1. Any Devanagari script present (U+0900–U+097F)              -> "hindi"
  2. No Devanagari, but recognizable romanized Hindi/Hinglish
     function words present                                     -> "hinglish"
  3. Otherwise                                                   -> "english"

This mirrors how a human support agent would triage the same message.
"""

from __future__ import annotations

import re
from typing import Literal

Language = Literal["english", "hindi", "hinglish"]

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Common romanized Hindi/Hinglish function words and connectors — not an
# exhaustive dictionary, just enough high-frequency tokens to reliably flag
# code-switching. Extend this list from real conversation logs over time
# rather than guessing more words up front.
_HINGLISH_MARKERS = {
    "mera", "meri", "mere", "mujhe", "hume", "humara",
    "ghar", "ka", "ki", "ke", "ko", "se", "me", "mein", "nahi", "nahin",
    "hai", "hain", "raha", "rahi", "rahe", "ho", "gaya", "gayi", "gaye",
    "kya", "kaise", "kab", "kyun", "kyu", "chahiye", "karo", "kardo",
    "karna", "dikhao", "batao", "theek", "thik", "abhi", "jaldi",
    "paise", "rupaye", "kitna", "kitne", "lagega", "lagenge",
}


def detect_language(text: str) -> Language:
    if not text or not text.strip():
        return "english"

    if _DEVANAGARI_RE.search(text):
        return "hindi"

    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return "english"

    hinglish_hits = sum(1 for t in tokens if t in _HINGLISH_MARKERS)
    # Require at least one clear marker, or a meaningful share of the
    # message, so an English sentence with an incidental "ka" as a
    # substring elsewhere doesn't get misflagged.
    if hinglish_hits >= 1 and (hinglish_hits / len(tokens)) >= 0.12:
        return "hinglish"

    return "english"
